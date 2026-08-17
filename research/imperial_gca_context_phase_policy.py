import json, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133;INCUMBENT=2468803
POLICIES=('gp','gpl','gpld')


def s3(x):return 0 if x<0 else (2 if x>0 else 1)
def p9(x):return max(-4,min(4,int(x)))+4

def ctx(policy,c,t,K):
    g=c//16;prev=int(K[c,t-1]) if t else 0
    z=g*9+p9(prev)
    if policy=='gp':return z
    left=int(K[c-1,t]) if c else 0;z=z*3+s3(left)
    if policy=='gpl':return z
    diag=int(K[c-1,t-1]) if c and t else 0
    return z*3+s3(diag)

def nctx(policy):return {'gp':72,'gpl':216,'gpld':648}[policy]

def baseline_contexts(policy,K):
    out=[[] for _ in range(nctx(policy))]
    for c in range(C):
        for t in range(NT):out[ctx(policy,c,t,K)].append((c,t))
    return out

def train_table(policy,N,K):
    groups=baseline_contexts(policy,K);tab=np.zeros(nctx(policy),np.int16);stats=[]
    for j,idx in enumerate(groups):
        if not idx:continue
        # Bound encoder-only search cost while sampling the full recording.
        step=max(1,len(idx)//4096);sel=idx[::step];v=np.fromiter((N[c,t] for c,t in sel),dtype=np.int64,count=len(sel))
        d,_=rc.choose_phase(v);tab[j]=d;stats.append(len(idx))
    return tab,{'contexts':len(tab),'nonempty':len(stats),'median_events':float(np.median(stats)) if stats else 0.0}

def build_policy(X,co,policy,tab):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Xi=np.rint(X).astype(np.int64);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            d=int(tab[ctx(policy,c,t,K)]);n=int(Xi[c,t])-p-d;k=(n+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',policy,c,t))
            K[c,t]=k;R[c,t]=r
    return R,K

def decode_policy(K,co,policy,tab):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            d=int(tab[ctx(policy,c,t,K)]);R[c,t]=p+d+STEP*int(K[c,t])
    return R

def encode_fixed(K):
    stream=bytearray();entries={};chosen={}
    for comp in cg.COMPONENTS:
        gr,W=rc.CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W);stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb);chosen[comp]={'grammar':gr,'W':W,'payload_bytes':len(bb)}
    return bytes(stream),entries,chosen

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);N=np.rint(X).astype(np.int64)-(R0.astype(np.int64)-STEP*K0.astype(np.int64))
    screens=[{'policy':'fixed_phase0','proxy_bps':rc.k_proxy(K0),'side_bytes':0}];best=None;print(json.dumps({'screen':screens[-1]}),flush=True)
    tables={}
    for policy in POLICIES:
        tab,ts=train_table(policy,N,K0);tables[policy]=tab;R,K=build_policy(X,cod,policy,tab);side=2*len(tab)+1;pr=rc.k_proxy(K);adj=pr+8.0*side/(C*NT);row={'policy':policy,'proxy_bps':pr,'side_bytes':side,'maxerr':float(np.max(np.abs(X-R.astype(np.float64)))),'table':ts};screens.append(row);print(json.dumps({'screen':row}),flush=True)
        if best is None or adj<best[0]:best=(adj,policy,K,R)
    if best[0]>=screens[0]['proxy_bps']:
        out={'winner':'incumbent','bytes':INCUMBENT,'eps':eps,'screens':screens,'scope':'Decoder-causal context phase policies did not beat phase0 on charged proxy.'};json.dump(out,open('imperial_gca_context_phase_policy.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True);return
    _,policy,K,R=best;tab=tables[policy];side=bytes([POLICIES.index(policy)])+np.asarray(tab,dtype='<i2').tobytes();tabd=np.frombuffer(side[1:],dtype='<i2').copy();stream,entries,chosen=encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=decode_policy(Kd,cod,policy,tabd)
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
    out={'winner':policy,'bytes':int(total),'bps':8.0*total/(C*NT),'delta_vs_incumbent':int(total-INCUMBENT),'gain_vs_incumbent':INCUMBENT/total,'side_bytes':len(side),'model_bytes':len(model),'component_stream_bytes':len(stream),'maxerr':me,'eps':eps,'chosen_fixed_component_configs':chosen,'screens':screens,'scope':'Decoder-causal GCA phase policy. The decoder chooses one of 267 legal residue classes at every sample from already-decoded context (channel group, previous K, and optionally left/diagonal K). Only a small phase table is transmitted once; no per-sample phase selectors are sent. Exact K arithmetic streams, table bytes, model and framing are charged and the decoder independently reconstructs the full source approximation under the unchanged hard error.'};json.dump(out,open('imperial_gca_context_phase_policy.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
