import json,sys,math
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32;STEP=267;TRAIN=1024;END=8192;C=128
BLOCKS=(256,512,1024,2048)
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
m.STEP=STEP

def fit_models(X):
    f=r.fit_shared(X[:,:TRAIN],P);b=r.fit_shared(X[:,:TRAIN][:,::-1],P)
    fb,fd=r.model_frame(f);bb,bd=r.model_frame(b)
    return int(fb+bb),fd,bd

def rollout_left(anchor,co,n):
    s=np.asarray(anchor,np.int64).copy();out=np.empty(n,np.int64)
    for i in range(n):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*float(s[-1-j])
        y=int(np.rint(v));out[i]=y;s[:-1]=s[1:];s[-1]=y
    return out

def rollout_right(anchor,co,n):
    # anchor supplied in chronological order for samples after the interior.
    s=np.asarray(anchor[::-1],np.int64).copy();tmp=np.empty(n,np.int64)
    for i in range(n):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*float(s[-1-j])
        y=int(np.rint(v));tmp[i]=y;s[:-1]=s[1:];s[-1]=y
    return tmp[::-1]

def encode_int(a):
    a=np.asarray(a,np.int64);b,rep,dec=m.encode_k(a);dec=np.asarray(dec,np.int64).reshape(a.shape)
    if not np.array_equal(dec,a):raise RuntimeError('integer frame mismatch')
    return int(b)+24,rep,dec

def make_anchors(X,start,stop,B,eps):
    nb=(stop-start)//B;mask=np.zeros((C,stop-start),bool);Q=[]
    for bi in range(nb):
        s=bi*B;e=s+B;mask[:,s:s+P]=True;mask[:,e-P:e]=True
    vals=X[:,start:stop][mask]
    q=np.rint(vals/STEP).astype(np.int64);R=STEP*q
    if float(np.max(np.abs(vals-R)))>eps*(1+1e-10):raise RuntimeError('anchor hard')
    qb,qrep,qd=encode_int(q);A=np.zeros((C,stop-start),np.int64);A[mask]=STEP*qd
    return mask,A,qb,qrep

def bridge_encode(X,eps,fco,bco,B):
    start=TRAIN;stop=TRAIN+((END-TRAIN)//B)*B
    mask,A,ab,arep=make_anchors(X,start,stop,B,eps);N=stop-start;Pred=np.zeros((C,N),np.int64);K=[];positions=[]
    for c in range(C):
        for s in range(0,N,B):
            e=s+B;left=A[c,s:s+P];right=A[c,e-P:e];n=B-2*P
            fl=rollout_left(left,fco,n);br=rollout_right(right,bco,n)
            if n>1:w=np.linspace(1.0,0.0,n,dtype=np.float64)
            else:w=np.array([.5])
            pr=np.rint(w*fl+(1-w)*br).astype(np.int64);Pred[c,s+P:e-P]=pr;Pred[c,s:s+P]=left;Pred[c,e-P:e]=right
            src=X[c,start+s+P:start+e-P];kk=np.rint((src-pr)/STEP).astype(np.int64);rr=pr+STEP*kk
            if float(np.max(np.abs(src-rr)))>eps*(1+1e-10):raise RuntimeError(('bridge hard',B,c,s))
            K.extend(kk.tolist());positions.extend([(c,start+s+P+i) for i in range(n)])
    K=np.asarray(K,np.int64);kb,krep,kd=encode_int(K)
    D=A.copy();off=0
    for c in range(C):
        for s in range(0,N,B):
            e=s+B;n=B-2*P;left=D[c,s:s+P];right=D[c,e-P:e]
            fl=rollout_left(left,fco,n);br=rollout_right(right,bco,n);w=np.linspace(1.0,0.0,n,dtype=np.float64) if n>1 else np.array([.5])
            pr=np.rint(w*fl+(1-w)*br).astype(np.int64);D[c,s+P:e-P]=pr+STEP*kd[off:off+n];off+=n
    if off!=len(kd):raise RuntimeError('bridge replay length')
    me=float(np.max(np.abs(X[:,start:stop]-D)))
    if me>eps*(1+1e-10):raise RuntimeError(('bridge replay hard',B,me,eps))
    return {'B':B,'target_start':start,'target_stop':stop,'samples':C*N,'anchor_bytes':ab,'anchor_rep':arep,'innovation_bytes':kb,'innovation_rep':krep,
            'bytes':ab+kb+40,'bps':8*(ab+kb+40)/(C*N),'anchor_fraction':float(mask.mean()),'maxerr':me}

def causal_encode(X,eps,fco,start,stop):
    R=np.zeros((C,stop),np.int64);K=np.zeros((C,stop),np.int64)
    # Replay from t=0 because causal model needs exact previous decoded state.
    for c in range(C):
        for t in range(stop):
            if t<P:p=0
            else:
                v=float(fco[-1])
                for j in range(P):v+=float(fco[j])*float(R[c,t-1-j])
                p=int(np.rint(v))
            k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError('causal hard')
            R[c,t]=y;K[c,t]=k
    b,rep,d=encode_int(K[:,start:stop]);return {'bytes':b,'bps':8*b/(C*(stop-start)),'rep':rep,'maxerr':float(np.max(np.abs(X[:,start:stop]-R[:,start:stop])))}

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError('sz hard')
        z=(int(b.size),me,'T' if tr else 'CT')
        if best is None or z[0]<best[0]:best=z
    return best

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;mb,fco,bco=fit_models(X);reg=[]
            for B in BLOCKS:
                z=bridge_encode(X,eps,fco,bco,B);z['model_bytes']=mb;z['total_bytes']=z['bytes']+mb;z['total_bps']=8*z['total_bytes']/z['samples']
                ca=causal_encode(X,eps,fco,z['target_start'],z['target_stop']);szb=szrun(X[:,z['target_start']:z['target_stop']],eps)
                z.update({'region':name,'c0':c0,'causal_bytes':ca['bytes'],'causal_bps':ca['bps'],'gain_vs_causal':ca['bytes']/z['total_bytes'],'causal_rep':ca['rep'],
                          'sz3_bytes':szb[0],'sz3_bps':8*szb[0]/z['samples'],'gain_vs_sz3':szb[0]/z['total_bytes'],'sz3_orientation':szb[2]})
                reg.append(z);rows.append(z);print(json.dumps(z),flush=True)
    combos=[]
    for B in BLOCKS:
        rr=[z for z in rows if z['B']==B];b=sum(z['total_bytes'] for z in rr);ca=sum(z['causal_bytes'] for z in rr);sz=sum(z['sz3_bytes'] for z in rr);n=sum(z['samples'] for z in rr)
        combos.append({'B':B,'bytes':b,'bps':8*b/n,'causal_bytes':ca,'causal_bps':8*ca/n,'gain_vs_causal':ca/b,'sz3_bytes':sz,'sz3_bps':8*sz/n,'gain_vs_sz3':sz/b,
                       'anchor_fraction':float(np.mean([z['anchor_fraction'] for z in rr]))})
    combos.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'step':STEP,'order':P,'train':TRAIN,'blocks':list(BLOCKS),'regions':[list(x) for x in SPECS],
         'combos':combos,'rows':rows,'scope':'Bidirectional state-bridge codec gate. Shared forward AR32 is trained only on t<1024; an independent reverse-time AR32 is trained on the same prefix reversed. For each target block the encoder transmits two P=32 boundary state strips as legal absolute step267 states. Decoder rolls the forward model from the left strip and reverse model from the right strip; a deterministic linear meet-in-the-middle blend predicts every interior sample. Only interior step267 innovations are transmitted. Boundary states, both float32 AR models, innovation frames and framing are counted and byte-decoded; complete target reconstruction is hard-error verified. B=256/512/1024/2048 tests the anchor-rate tradeoff. Matched causal AR32 and matched SZ3 are rerun on each exact target interval. No AI, four-region gate, not whole-array.'}
    print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_bidirectional_ar32_bridge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
