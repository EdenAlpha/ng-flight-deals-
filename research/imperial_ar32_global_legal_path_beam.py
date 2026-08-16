import json,sys,math
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(240,248,256,260,264)
LAMBDAS=(0.25,0.75)
BEAM=32
SELECTOR_BYTES=3


def zz(v):return 2*int(v) if v>=0 else -2*int(v)-1

def eglen(v):
    u=zz(v);return 2*((u+1).bit_length()-1)+1

def legal(x,p,eps,step):
    b=float(eps)*(1-2e-12);return int(math.ceil((float(x)-b-p)/step)),int(math.floor((float(x)+b-p)/step))

def local_cost(k,pk,leftk,lam):
    z=zz(k);return eglen(k)+lam*((z^zz(pk)).bit_count()+(z^zz(leftk)).bit_count())+0.015*abs(k)

def beam_channel(x,coef,eps,step,lam,leftK):
    P=32;hist=np.zeros((1,P),np.int32);lastk=np.zeros(1,np.int32);scores=np.zeros(1,np.float64)
    parents=[];kvals=[]
    for t in range(x.size):
        if t<P:pred=np.zeros(hist.shape[0],np.int64)
        else:pred=np.rint(float(coef[-1])+hist.astype(np.float64)@np.asarray(coef[:P],np.float64)).astype(np.int64)
        cs=[];cp=[];ck=[];cr=[]
        lk=int(leftK[t]) if leftK is not None else 0
        for i in range(hist.shape[0]):
            lo,hi=legal(x[t],int(pred[i]),eps,step)
            if lo>hi:raise RuntimeError(('empty beam legal',t,int(pred[i]),lo,hi))
            for k in range(lo,hi+1):
                cs.append(float(scores[i])+local_cost(k,int(lastk[i]),lk,lam));cp.append(i);ck.append(k);cr.append(int(pred[i])+step*k)
        order=np.argsort(np.asarray(cs,np.float64),kind='stable')[:BEAM];par=np.asarray(cp,np.int32)[order];kv=np.asarray(ck,np.int32)[order];rv=np.asarray(cr,np.int32)[order]
        nh=np.zeros((len(order),P),np.int32);nh[:,1:]=hist[par,:P-1];nh[:,0]=rv
        hist=nh;lastk=kv;scores=np.asarray(cs,np.float64)[order];parents.append(par);kvals.append(kv)
    idx=int(np.argmin(scores));K=np.empty(x.size,np.int32)
    for t in range(x.size-1,-1,-1):
        K[t]=kvals[t][idx];idx=int(parents[t][idx])
    return K,float(np.min(scores))

def build(X,eps,coef,step,lam):
    C,T=X.shape;K=np.zeros((C,T),np.int32);sur=0.0
    for c in range(C):
        left=K[c-1] if c>0 else None;K[c],s=beam_channel(X[c],coef,eps,step,lam,left);sur+=s
    R=np.zeros_like(K)
    for c in range(C):
        for t in range(T):R[c,t]=g.ar.predict_hist(R,c,t,coef,32,'shared')+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('beam hard',step,lam,me,eps))
    return R,K,me,sur

def exact(X,eps,mb,coef,step,lam,R,K,me,sur):
    ab,rep,Kd,detail=ac.autocomplexity_frame(K);Kd=np.asarray(Kd,np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError(('beam K replay',step,lam))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,coef,32,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('beam AR replay',step,lam))
    me2=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me2>eps*(1+5e-6):raise RuntimeError(('beam replay hard',me2,eps))
    total=int(mb)+int(ab)+base.HEADER+SELECTOR_BYTES
    return {'step':int(step),'lambda':float(lam),'beam':BEAM,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(ab),'selector_bytes':SELECTOR_BYTES,'maxerr':me2,'surrogate_cost':float(sur),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'rep':rep,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=g.ar.fit_shared(X[:,:g.TRAIN],32);mb,coef=g.ar.model_frame(co)
    _,_,R0,K0=base.build_ar32(X);ab0,_,Kd0,_=ac.autocomplexity_frame(K0)
    if not np.array_equal(Kd0,K0):raise RuntimeError('incumbent K replay')
    incumbent={'bytes':int(mb+ab0+base.HEADER),'address_bytes':int(ab0),'step':267}
    rows=[]
    for step in STEPS:
        for lam in LAMBDAS:
            R,K,me,sur=build(X,eps,coef,step,lam);z=exact(X,eps,mb,coef,step,lam,R,K,me,sur);z['gain_vs_incumbent']=incumbent['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'steps':list(STEPS),'lambdas':list(LAMBDAS),'beam':BEAM,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'incumbent':incumbent,'rows':rows,'best':best,'scope':'Non-greedy legal-path search on the frozen shared AR32 model. For each candidate step below 267, the encoder maintains a beam of up to 32 complete legal causal reconstruction trajectories per channel. Every beam state stores the exact previous 32 reconstructed samples needed by AR32. At each source sample all K values satisfying the unchanged +/-epsilon box are enumerated; alternative legal choices branch the AR state and therefore can change many future predictors. A public surrogate favors short signed integers and bit agreement with previous/current-left K, then keeps the best beam paths. After the complete path is selected, no surrogate rate is claimed: its entire K field is physically encoded/decoded with the exact AUTO-COMPLEXITY rank stream, identical R is recursively reproduced, and source hard error is verified. Step/lambda selector bytes are charged. This tests the GCA/NOVA idea at path scale rather than the failed greedy local choice scale: encoder computation searches a legal reconstruction trajectory whose downstream exact address may be globally shorter.'}
    json.dump(out,open('imperial_ar32_global_legal_path_beam.json','w'),indent=2)
    print(json.dumps({'summary':{'best_step':best['step'],'best_lambda':best['lambda'],'best_bytes':best['bytes'],'incumbent_bytes':incumbent['bytes'],'sz3_bytes':int(szb),'gain_incumbent':incumbent['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
