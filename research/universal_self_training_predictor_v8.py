#!/usr/bin/env python3
from __future__ import annotations
import json,math,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

V1_BYTES=22390
QOFF=((1,0),(2,0),(4,0),(8,0),(16,0),(0,-1),(1,-1),(1,1))
CONFIGS=((16,512,4096,8),(32,512,4096,8),(32,1024,4096,8),(32,1024,8192,12),(64,1024,8192,12),(64,2048,8192,16))
MINTRAIN=256
SEED=20260820


def qval(Q,c,t,off):
    dt,dc=off;tt=t-dt;cc=c+dc
    if tt<0 or cc<0 or cc>=Q.shape[0] or (dt==0 and dc>=0):return 0.0
    return float(Q[cc,tt])


def context(R,Q,c,t,basep,offs):
    ref=float(R[c,t-1]) if t>0 else 0.0
    z=[]
    for off in offs:
        v=u.off_value(R,c,t,off);z.append(np.clip((v-ref)/u.STEP,-16,16)/16.0)
    qs=[qval(Q,c,t,o) for o in QOFF]
    z.extend([np.clip(q,-16,16)/16.0 for q in qs])
    z.append(min(1.0,sum(abs(q) for q in qs)/(8.0*8.0)))
    z.append(float(np.clip((float(basep)-ref)/u.STEP,-16,16))/16.0)
    z.append((2.0*c/max(1,R.shape[0]-1))-1.0)
    z.append((2.0*t/max(1,R.shape[1]-1))-1.0)
    return np.asarray(z,np.float64)


def public_features(ctx,W,b):
    h=np.tanh(ctx@W+b)
    return np.concatenate(([1.0],ctx,h))


def fit_beta(F,Y,history):
    if len(Y)<MINTRAIN:return None
    n=min(history,len(Y));X=np.asarray(F[-n:],np.float64);y=np.asarray(Y[-n:],np.float64)
    lam=0.2
    G=X.T@X+lam*np.eye(X.shape[1],dtype=np.float64);G[0,0]-=lam
    try:beta=np.linalg.solve(G,X.T@y)
    except np.linalg.LinAlgError:beta=np.linalg.lstsq(G,X.T@y,rcond=1e-7)[0]
    return beta


def run(X,base_co,offs,H,chunk,history,cap,Kgiven=None):
    D=20;rng=np.random.default_rng(SEED+H)
    W=rng.normal(0.0,1.0/math.sqrt(D),size=(D,H)).astype(np.float64);b=rng.uniform(-1.0,1.0,size=H).astype(np.float64)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Q=np.zeros(X.shape,np.int32)
    F=[];Y=[];beta=None;idx=0;nonzero_corr=0;sum_abs_corr=0
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            if idx%chunk==0:beta=fit_beta(F,Y,history)
            bp=u.sample_pred(R,c,t,base_co,offs);ctx=context(R,Q,c,t,bp,offs);phi=public_features(ctx,W,b)
            corr=0 if beta is None else int(np.rint(float(phi@beta)));corr=max(-cap,min(cap,corr))
            if corr:nonzero_corr+=1
            sum_abs_corr+=abs(corr);p=bp+u.STEP*corr
            k=int(Kgiven[c,t]) if Kgiven is not None else int(np.rint((float(X[c,t])-p)/u.STEP))
            K[c,t]=k;R[c,t]=p+u.STEP*k;q=int(corr+k);Q[c,t]=q
            F.append(phi);Y.append(float(q));idx+=1
    return R,K,Q,{'correction_nonzero_fraction':nonzero_corr/K.size,'mean_abs_correction':sum_abs_corr/K.size}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,shist=u.search_sample(X);_,Rbase,Kbase,mb,ob,cod=sbest
    basefield,_,_=u.exact_field(Kbase);rows=[]
    for H,chunk,hist,cap in CONFIGS:
        R,K,Q,diag=run(X,cod,offs,H,chunk,hist,cap)
        field,Kd,detail=u.exact_field(K)
        Rd,Kcheck,Qd,diagd=run(X,cod,offs,H,chunk,hist,cap,Kgiven=Kd)
        if not np.array_equal(Kcheck,K) or not np.array_equal(Rd,R) or not np.array_equal(Qd,Q):raise RuntimeError(('replay',H,chunk,hist,cap))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps,H,chunk))
        # One public configuration selector byte; random nonlinear basis and all online fits are decoder-recreated.
        total=fair.COMMON_HEADER+1+len(ob)+len(mb)+1+field
        row={'hidden':H,'chunk':chunk,'history':hist,'cap':cap,'bytes':int(total),'field_bytes':int(field),'maxerr':me,
             'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total),'k_zero_fraction':float(np.mean(K==0)),**diag}
        rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-self-training-predictor-v8','shape':list(X.shape),'eps':eps,'step':u.STEP,'base_offsets':[list(x) for x in offs],
         'v1_bytes':V1_BYTES,'base_field_bytes':int(basefield),'sz3_bytes':int(szb),'sz3_orientation':ori,'best':best,'rows':rows,
         'principle':'A fixed public nonlinear random-feature basis plus a ridge readout is re-fit at public chunk boundaries using only features and correction targets generated from already reconstructed samples. Encoder and decoder therefore learn the current file in lockstep without transmitting learned weights. The learned output predicts an integer correction to the rate-discovered base predictor before ordinary error-bounded quantization.'}
    json.dump(out,open('universal_self_training_predictor_v8.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
