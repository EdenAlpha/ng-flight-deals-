import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg

C=128; NT=30000; C0=512; STEP=267; RAD=133
INCUMBENT=2468803; MATCHED_SZ3=2767977
CONFIGS={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}


def wrap_phase(x):
    return ((np.asarray(x,dtype=np.int64)+RAD)%STEP)-RAD


def proxy_cost_k(k):
    k=np.asarray(k,dtype=np.int64);a=np.abs(k);nz=a>0
    out=np.ones(a.shape,dtype=np.float64)
    if np.any(nz):
        q=np.floor(np.log2(a[nz])).astype(np.int64);out[nz]+=2.0+2.0*q
    return float(out.sum())


def choose_phase(n,stride=1):
    v=np.asarray(n,dtype=np.int64).reshape(-1)[::stride];best=(1e300,0)
    for d in range(-RAD,RAD+1):
        k=np.floor_divide(v-d+RAD,STEP);sc=proxy_cost_k(k)
        if sc<best[0]:best=(sc,d)
    return int(best[1]),float(best[0])


def choose_channel_phases(n):
    ph=np.zeros(C,np.int16);score=0.0
    for c in range(C):
        d,_=choose_phase(n[c],stride=8);best=(1e300,d)
        for z in sorted(set(int(wrap_phase(d+j)) for j in range(-4,5))):
            k=np.floor_divide(n[c]-z+RAD,STEP);s=proxy_cost_k(k)
            if s<best[0]:best=(s,z)
        ph[c]=best[1];score+=best[0]
    return ph,score


def choose_time_phases(n,B):
    nb=(NT+B-1)//B;ph=np.zeros(nb,np.int16);score=0.0
    for b in range(nb):
        sl=slice(b*B,min(NT,(b+1)*B));d,_=choose_phase(n[:,sl],stride=16);best=(1e300,d)
        for z in sorted(set(int(wrap_phase(d+j)) for j in range(-4,5))):
            k=np.floor_divide(n[:,sl]-z+RAD,STEP);s=proxy_cost_k(k)
            if s<best[0]:best=(s,z)
        ph[b]=best[1];score+=best[0]
    return ph,score


def separable_phases(n,B):
    pc,_=choose_channel_phases(n);nb=(NT+B-1)//B;pt=np.zeros(nb,np.int16)
    for b in range(nb):
        sl=slice(b*B,min(NT,(b+1)*B));base=pc[:,None].astype(np.int64);best=(1e300,0)
        for z in range(-RAD,RAD+1):
            d=wrap_phase(base+z);k=np.floor_divide(n[:,sl]-d+RAD,STEP);s=proxy_cost_k(k)
            if s<best[0]:best=(s,z)
        pt[b]=best[1]
    score=0.0
    for b in range(nb):
        sl=slice(b*B,min(NT,(b+1)*B));d=wrap_phase(pc[:,None].astype(np.int64)+int(pt[b]));k=np.floor_divide(n[:,sl]-d+RAD,STEP);score+=proxy_cost_k(k)
    return pc,pt,score


def phase_matrix(mode,params):
    if mode=='zero':return np.zeros((C,NT),np.int16)
    if mode=='global':return np.full((C,NT),int(params['d']),np.int16)
    if mode=='channel':return np.repeat(np.asarray(params['pc'],np.int16)[:,None],NT,axis=1)
    B=int(params['B']);nb=(NT+B-1)//B
    if mode=='time':
        out=np.empty((C,NT),np.int16)
        for b in range(nb):out[:,b*B:min(NT,(b+1)*B)]=int(params['pt'][b])
        return out
    if mode=='separable':
        out=np.empty((C,NT),np.int16);pc=np.asarray(params['pc'],np.int64)
        for b in range(nb):out[:,b*B:min(NT,(b+1)*B)]=wrap_phase(pc+int(params['pt'][b]))[:,None]
        return out
    raise ValueError(mode)


def build_phase(X,co,D):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32);Xi=np.rint(X).astype(np.int64)
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            d=int(D[c,t]);n=int(Xi[c,t])-p-d;k=(n+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',c,t,int(Xi[c,t]),p,d,k,r))
            K[c,t]=k;R[c,t]=r
    return R,K


def decode_phase(K,co,D):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            R[c,t]=p+int(D[c,t])+STEP*int(K[c,t])
    return R


def serialize_side(mode,params):
    mid={'global':1,'channel':2,'time':3,'separable':4}[mode];z=bytearray([mid])
    if mode=='global':z.extend(struct.pack('<h',int(params['d'])))
    elif mode=='channel':z.extend(np.asarray(params['pc'],dtype='<i2').tobytes())
    elif mode=='time':z.extend(struct.pack('<H',int(params['B'])));z.extend(np.asarray(params['pt'],dtype='<i2').tobytes())
    elif mode=='separable':z.extend(struct.pack('<H',int(params['B'])));z.extend(np.asarray(params['pc'],dtype='<i2').tobytes());z.extend(np.asarray(params['pt'],dtype='<i2').tobytes())
    return bytes(z)


def parse_side(bb):
    mid=bb[0];mode={1:'global',2:'channel',3:'time',4:'separable'}[mid];o=1
    if mode=='global':return mode,{'d':struct.unpack_from('<h',bb,o)[0]}
    if mode=='channel':return mode,{'pc':np.frombuffer(bb[o:o+2*C],dtype='<i2').copy()}
    B=struct.unpack_from('<H',bb,o)[0];o+=2;nb=(NT+B-1)//B
    if mode=='time':return mode,{'B':B,'pt':np.frombuffer(bb[o:o+2*nb],dtype='<i2').copy()}
    pc=np.frombuffer(bb[o:o+2*C],dtype='<i2').copy();o+=2*C;pt=np.frombuffer(bb[o:o+2*nb],dtype='<i2').copy();return mode,{'B':B,'pc':pc,'pt':pt}


def k_proxy(K):return proxy_cost_k(K)/(C*NT)


def encode_fixed(K):
    entries={};stream=bytearray();chosen={}
    for comp in cg.COMPONENTS:
        gr,W=CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W)
        stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb);chosen[comp]={'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb)}
    return bytes(stream),entries,chosen


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if int(math.floor(eps))!=RAD:raise RuntimeError(('unexpected eps',eps))
    if np.max(np.abs(X-np.rint(X)))>1e-6:raise RuntimeError('noninteger source')
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
    candidates=[];dglob,_=choose_phase(N,stride=32);candidates.append(('global',{'d':dglob}));pc,_=choose_channel_phases(N);candidates.append(('channel',{'pc':pc}))
    for B in (512,1024,2048,4096):
        pt,_=choose_time_phases(N,B);candidates.append(('time',{'B':B,'pt':pt}))
    for B in (1024,2048,4096):
        pc2,pt2,_=separable_phases(N,B);candidates.append(('separable',{'B':B,'pc':pc2,'pt':pt2}))
    screens=[{'mode':'zero','proxy_bps':k_proxy(K0),'side_bytes':0}];best=('zero',{},screens[0]['proxy_bps']);print(json.dumps({'screen':screens[-1]}),flush=True)
    for mode,params in candidates:
        D=phase_matrix(mode,params);R,K=build_phase(X,cod,D);me=float(np.max(np.abs(X-R.astype(np.float64))));pr=k_proxy(K);side=len(serialize_side(mode,params));row={'mode':mode,'B':int(params.get('B',0)),'proxy_bps':pr,'side_bytes':side,'maxerr':me};screens.append(row);print(json.dumps({'screen':row}),flush=True);adj=pr+8.0*side/(C*NT)
        if adj<best[2]:best=(mode,params,adj)
    mode,params,_=best
    if mode=='zero':
        out={'winner':'incumbent','bytes':INCUMBENT,'screens':screens,'eps':eps,'scope':'Residue-class GCA search found no proxy candidate worth materializing.'};json.dump(out,open('imperial_gca_residue_codebook.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True);return
    side=serialize_side(mode,params);mode2,params2=parse_side(side);D=phase_matrix(mode2,params2);R,K=build_phase(X,cod,D);stream,entries,chosen=encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=decode_phase(Kd,cod,D)
    if not np.array_equal(Rd,R):raise RuntimeError('phase replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
    out={'winner':mode,'params_summary':{'B':int(params.get('B',0))},'shape':[C,NT],'eps':eps,'step':STEP,'legal_integer_radius':RAD,'phase_side_bytes':len(side),'model_bytes':len(model),'component_stream_bytes':len(stream),'bytes':int(total),'bps':8.0*total/(C*NT),'maxerr':me,'incumbent_bytes':INCUMBENT,'delta_vs_incumbent':int(total-INCUMBENT),'gain_vs_incumbent':INCUMBENT/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'chosen_fixed_component_configs':chosen,'screens':screens,'scope':'GCA residue-class codebook. The integer hard-error interval contains exactly 267 values and lattice spacing is 267, so every residue class modulo 267 contains exactly one legal reconstruction per sample. Encoder searches compact global/channel/time/separable phase rules, transmits the selected rule, then emits the resulting AR32 K address. This creates legal reconstruction multiplicity without reducing lattice spacing. Final bytes are physical component arithmetic streams plus model, side information and framing; decoder independently parses K, regenerates the phase field, replays AR32 and rechecks hard error.'};json.dump(out,open('imperial_gca_residue_codebook.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
