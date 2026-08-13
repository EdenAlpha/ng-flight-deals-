import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_ar32_innovation_gaussian_rd as g

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;TRAIN=1024;END=4096;P=32;STEP=267;TB=1024
LAMBDA_FACTORS=(0.25,1.0,4.0,16.0,64.0)


def canonical_basis(J):
    J=np.asarray(J,np.float64)
    mu=J.mean(axis=1)
    A=J-mu[:,None]
    cov=(A@A.T)/max(1,A.shape[1]-1)
    w,U=np.linalg.eigh(cov)
    ix=np.argsort(w)[::-1];w=np.maximum(w[ix],0.0);U=U[:,ix]
    # Canonicalize eigenvector sign so decoder reconstruction is deterministic.
    for j in range(U.shape[1]):
        k=int(np.argmax(np.abs(U[:,j])))
        if U[k,j]<0: U[:,j]*=-1.0
    return mu,w,U


def predictor(R,t,coef):
    if t<P:return np.zeros(R.shape[0],np.int32)
    a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
    H=R[:,t-P:t][:,::-1].astype(np.float32)
    return np.rint(a+H@b).astype(np.int32)


def encode_frames(A):
    total=0;reps={};decoded=np.empty_like(A,dtype=np.int32)
    for t0 in range(0,A.shape[1],TB):
        n,rep,D=m.encode_k(np.asarray(A[:,t0:t0+TB],np.int32))
        total+=int(n);reps[rep]=reps.get(rep,0)+1;decoded[:,t0:t0+D.shape[1]]=D
        if not np.array_equal(D,A[:,t0:t0+D.shape[1]]):raise RuntimeError('frame decode mismatch')
    return total,reps,decoded


def scalar_baseline(X,coef,eps):
    R,K,_=g.run_ar(X,coef)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError(('baseline hard',me,eps))
    kb,reps,Kd=encode_frames(K)
    if not np.array_equal(Kd,K):raise RuntimeError('baseline K')
    model=4*len(coef)+40
    return {'bytes':model+kb,'model_bytes':model,'innovation_bytes':kb,'reps':reps,'bps':8*(model+kb)/X.size,'maxerr':me},R,K


def candidate(X,coef,Rprefix,Kprefix,mu,w,U,eps,factor):
    dist=float(factor*eps*eps)
    active=np.flatnonzero(w>dist)
    Ua=U[:,active]
    qstep=math.sqrt(12.0*dist)
    nt=X.shape[1];target=nt-TRAIN
    R=np.zeros((C,nt),np.int32);R[:,:TRAIN]=Rprefix
    Q=np.zeros((len(active),target),np.int32)
    Corr=np.zeros((C,target),np.int32)
    for t in range(TRAIN,nt):
        p=predictor(R,t,coef)
        e=X[:,t]-p.astype(np.float64)
        if len(active):
            z=Ua.T@(e-mu)
            q=np.rint(z/qstep).astype(np.int32)
            base=np.rint(mu+Ua@(q.astype(np.float64)*qstep)).astype(np.int32)
            Q[:,t-TRAIN]=q
        else:
            base=np.rint(mu).astype(np.int32)
        c=np.rint((e-base.astype(np.float64))/STEP).astype(np.int32)
        r=p+base+STEP*c
        r=np.clip(r,-32768,32767).astype(np.int32)
        R[:,t]=r;Corr[:,t-TRAIN]=c
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError(('encoder hard',factor,me,eps))
    qb=0;qreps={};Qd=Q
    if len(active): qb,qreps,Qd=encode_frames(Q)
    cb,creps,Cd=encode_frames(Corr)
    # Exact decoder replay from prefix using only decoded modal coordinates + correction.
    D=np.zeros_like(R);D[:,:TRAIN]=Rprefix
    for t in range(TRAIN,nt):
        p=predictor(D,t,coef)
        j=t-TRAIN
        if len(active):base=np.rint(mu+Ua@(Qd[:,j].astype(np.float64)*qstep)).astype(np.int32)
        else:base=np.rint(mu).astype(np.int32)
        rr=p+base+STEP*Cd[:,j]
        D[:,t]=np.clip(rr,-32768,32767).astype(np.int32)
    if not np.array_equal(D,R):raise RuntimeError(('replay mismatch',factor))
    me2=float(np.max(np.abs(X-D.astype(np.float64))))
    if me2>eps*(1+1e-12):raise RuntimeError(('decoder hard',factor,me2,eps))
    # Same transmitted AR model as the incumbent. Prefix innovations are common but fully charged.
    pb,preps,Kpd=encode_frames(Kprefix)
    if not np.array_equal(Kpd,Kprefix):raise RuntimeError('prefix K')
    model=4*len(coef)+40
    total=model+pb+qb+cb+8
    return {
        'lambda_factor':factor,'active_modes':int(len(active)),'qstep':qstep,
        'bytes':int(total),'bps':8*total/X.size,'model_bytes':model,'prefix_bytes':int(pb),
        'mode_bytes':int(qb),'correction_bytes':int(cb),'selector_bytes':8,
        'mode_reps':qreps,'correction_reps':creps,'prefix_reps':preps,
        'correction_zero_fraction':float(np.mean(Corr==0)),
        'correction_abs_le1_fraction':float(np.mean(np.abs(Corr)<=1)),
        'maxerr':me2,
    }


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[];summary=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T
            coef=g.fit_shared_ar(X)
            base,Rbase,Kbase=scalar_baseline(X,coef,eps)
            # Prefix state is decoder-known after its exact innovation stream is decoded.
            Rprefix=Rbase[:,:TRAIN].copy();Kprefix=Kbase[:,:TRAIN].copy()
            J=(STEP*Kprefix).astype(np.float64)
            mu,w,U=canonical_basis(J)
            sz=0
            for t0 in range(0,END,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
            candidates=[]
            for factor in LAMBDA_FACTORS:
                r=candidate(X,coef,Rprefix,Kprefix,mu,w,U,eps,factor)
                r.update({'region':name,'c0':c0,'matched_sz3_bytes':sz,'matched_sz3_bps':8*sz/X.size,
                          'gain_vs_sz3':sz/r['bytes'],'gain_vs_ar32':base['bytes']/r['bytes']})
                candidates.append(r);rows.append(r);print(json.dumps(r,indent=2),flush=True)
            best=min(candidates,key=lambda r:r['bytes'])
            sr={'region':name,'c0':c0,'baseline_ar32':base,'matched_sz3_bytes':sz,'matched_sz3_bps':8*sz/X.size,
                'best':best,'best_gain_vs_ar32':base['bytes']/best['bytes'],'best_gain_vs_sz3':sz/best['bytes'],
                'prefix_eigenvalues_top16':[float(x) for x in w[:16]],
                'prefix_modes_for_90pct_energy':int(np.searchsorted(np.cumsum(w)/max(w.sum(),1e-300),.90)+1)}
            summary.append(sr);print(json.dumps({'summary':sr},indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'train_samples':TRAIN,'end_sample':END,'step':STEP,'order':P,
         'lambda_factors':list(LAMBDA_FACTORS),'summary':summary,'rows':rows,
         'scope':('Decoder-real specialist screen. One shared AR32+intercept is fitted from t<1024 and transmitted. Its exact decoded prefix innovations define a canonical spatial eigenbasis and mode scales, so no target basis/model is hidden. For held-out samples the current decoder-known AR predictor is formed from the candidate reconstruction itself; the source residual is projected onto prefix-derived energetic modes, mode coordinates are quantized using a fixed waterfilling-inspired lambda menu, inverse-projected and rounded to an integer residual contribution, and an exact step267 correction field guarantees the unchanged global 10%-std max-error bound. Prefix, modal-coordinate, correction, model and selector bytes are all charged through self-decoding frames. Matched SZ3 and ordinary scalar step267 AR32 are rerun on identical 128x4096 regions. No AI; screen only.')}
    json.dump(out,open('imperial_ar32_persistent_spatial_modes.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
