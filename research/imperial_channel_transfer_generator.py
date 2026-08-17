import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg

C=128;NT=30000;C0=512;STEP=267;BEST=2465652
CONFIGS={
 'p1_l0':[(1,0)],
 'p1_pm2':[(1,j) for j in range(-2,3)],
 'p1_pm4':[(1,j) for j in range(-4,5)],
 'p1_pm8':[(1,j) for j in range(-8,9)],
 'p1_pm16':[(1,j) for j in range(-16,17)],
 'p12_pm4':[(dc,j) for dc in (1,2) for j in range(-4,5)],
 'p12_pm8':[(dc,j) for dc in (1,2) for j in range(-8,9)],
}
KCFG={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}

def shifted(v,lag):
    o=np.zeros_like(v,dtype=np.float64)
    if lag==0:o[:]=v
    elif lag>0:o[:-lag]=v[lag:]
    else:o[-lag:]=v[:lag]
    return o

def fit(X,features):
    rng=np.random.default_rng(20260817+len(features));N=400000
    cs=rng.integers(2 if any(dc==2 for dc,_ in features) else 1,C,size=N);ts=rng.integers(16,NT-16,size=N)
    F=np.empty((N,len(features)),np.float64)
    for j,(dc,lag) in enumerate(features):F[:,j]=X[cs-dc,ts+lag]
    y=X[cs,ts];mu=F.mean(0);sc=F.std(0);sc[sc<1e-9]=1.0;ym=float(y.mean());ys=max(float(y.std()),1.0)
    A=np.column_stack([np.ones(N),(F-mu)/sc]);b,*_=np.linalg.lstsq(A,(y-ym)/ys,rcond=1e-8)
    w=(ys*b[1:]/sc);inter=ym+ys*b[0]-float(np.dot(w,mu));co=np.r_[inter,w].astype(np.float32)
    return co

def model_frame(co):
    raw=np.asarray(co,dtype='<f4').tobytes();buf=b'CTG1'+struct.pack('<H',len(co))+raw
    if buf[:4]!=b'CTG1':raise RuntimeError('frame');n=struct.unpack_from('<H',buf,4)[0];cod=np.frombuffer(buf[6:6+4*n],dtype='<f4').copy()
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('model replay')
    return buf,cod

def ar0_trace(X0,aco):
    R=np.zeros(NT,np.int32);K=np.zeros(NT,np.int32);a=float(aco[0]);w=np.asarray(aco[1:],np.float32)
    for t in range(NT):
        p=0 if t<ah.P else int(np.rint(a+float(np.dot(w,R[t-ah.P:t][::-1].astype(np.float32)))))
        k=int(np.rint((float(X0[t])-p)/STEP));R[t]=p+STEP*k;K[t]=k
    return R,K

def predict_channel(R,c,co,features):
    p=np.full(NT,float(co[0]),np.float64)
    for w,(dc,lag) in zip(co[1:],features):
        if c>=dc:p+=float(w)*shifted(R[c-dc],lag)
    return np.rint(p).astype(np.int32)

def build(X,aco,co,features):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);R[0],K[0]=ar0_trace(X[0],aco)
    for c in range(1,C):
        p=predict_channel(R,c,co,features);k=np.rint((X[c]-p.astype(np.float64))/STEP).astype(np.int32);R[c]=p+STEP*k;K[c]=k
    return R,K

def replay(K,aco,co,features):
    R=np.zeros(K.shape,np.int32);a=float(aco[0]);w=np.asarray(aco[1:],np.float32)
    for t in range(NT):
        p=0 if t<ah.P else int(np.rint(a+float(np.dot(w,R[0,t-ah.P:t][::-1].astype(np.float32)))))
        R[0,t]=p+STEP*int(K[0,t])
    for c in range(1,C):R[c]=predict_channel(R,c,co,features)+STEP*K[c]
    return R

def proxy(K):
    a=np.abs(K.astype(np.int64));z=np.ones(a.shape,np.float64);nz=a>0
    if np.any(nz):z[nz]+=2+2*np.floor(np.log2(a[nz]))
    return float(z.sum()/(C*NT))
def encode_components(K):
    stream=bytearray();entries={};rows={}
    for comp in cg.COMPONENTS:
        gr,W=KCFG[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W);stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb);rows[comp]={'payload_bytes':len(bb),'bits':int(nb),'grammar':gr,'W':W}
    return bytes(stream),entries,rows

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,aco0=ah.fits(X);arbuf,aco=cg.model_frame(aco0);baseR,baseK=ah.run_ar(X,aco);baseproxy=proxy(baseK)
    screens=[];cache={}
    for name,features in CONFIGS.items():
        co0=fit(X,features);fbuf,co=model_frame(co0);R,K=build(X,aco,co,features);me=float(np.max(np.abs(X-R.astype(np.float64))));pr=proxy(K)+8*len(fbuf)/(C*NT);row={'model':name,'features':features,'fir_coeffs':len(co),'fir_model_bytes':len(fbuf),'charged_proxy_bps':pr,'delta_proxy_vs_ar32':pr-baseproxy,'maxerr':me,'zero_fraction':float(np.mean(K==0))};screens.append(row);cache[name]=(fbuf,co,R,K);print(json.dumps({'screen':row}),flush=True)
    top=sorted(screens,key=lambda r:r['charged_proxy_bps'])[:3];exact=[]
    for row in top:
        name=row['model'];fbuf,co,R,K=cache[name];stream,entries,parts=encode_components(K);total=cg.OUTER_BYTES+len(arbuf)+len(fbuf)+len(stream);er={**row,'bytes':int(total),'delta_vs_best':int(total-BEST),'component_stream_bytes':len(stream),'components':parts};exact.append(er);print(json.dumps({'exact':er}),flush=True)
    win=min(exact,key=lambda r:r['bytes']);name=win['model'];features=CONFIGS[name];fbuf,co,R,K=cache[name];stream,entries,parts=encode_components(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    n=struct.unpack_from('<H',fbuf,4)[0];cod=np.frombuffer(fbuf[6:6+4*n],dtype='<f4').copy();Rd=replay(Kd,aco,cod,features)
    if not np.array_equal(Rd,R):raise RuntimeError('R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=cg.OUTER_BYTES+len(arbuf)+len(fbuf)+len(stream)
    out={'winner':name,'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_best':int(total-BEST),'gain_vs_best':BEST/total,'maxerr':me,'eps':eps,'ar_model_bytes':len(arbuf),'fir_model_bytes':len(fbuf),'component_stream_bytes':len(stream),'features':features,'coefficients':cod.tolist(),'screens':screens,'exact_candidates':exact,'components':parts,'scope':'Channel-major transfer-generator experiment. Channel 0 uses the frozen transmitted AR32 model. Each later channel is generated from the complete already-decoded previous one or two channels through a small source-fitted float32 FIR using both negative and positive time lags, which is decoder-valid because earlier channels are fully available. The FIR is physically serialized/decoded. Step267 nearest correction preserves hard error. Only top proxy candidates are physically component-coded; final K is independently decoded and the entire generator replayed. Comparator is the 2,465,652-byte reconstruction-policy incumbent.'};json.dump(out,open('imperial_channel_transfer_generator.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
