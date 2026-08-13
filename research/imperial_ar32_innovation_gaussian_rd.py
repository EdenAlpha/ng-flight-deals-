import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024

def fit_shared_ar(X):
    rows=[];ys=[]
    for c in range(X.shape[0]):
        x=np.asarray(X[c,:TRAIN],np.float64)
        for t in range(P,TRAIN):
            rows.append(np.r_[1.0,x[t-P:t][::-1]])
            ys.append(x[t])
    A=np.asarray(rows,np.float64);y=np.asarray(ys,np.float64)
    coef=np.linalg.lstsq(A,y,rcond=None)[0].astype(np.float32)
    return coef

def run_ar(X,coef):
    R=np.zeros_like(X,dtype=np.int32);K=np.zeros_like(X,dtype=np.int32);E=np.zeros_like(X,dtype=np.float64)
    b=np.asarray(coef[1:],np.float32);a=float(coef[0])
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            if t<P:p=0
            else:p=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            e=float(X[c,t])-p;E[c,t]=e;k=int(np.rint(e/STEP));r=p+STEP*k
            R[c,t]=r;K[c,t]=k
    return R,K,E

def waterfill(eigs,D):
    e=np.maximum(np.asarray(eigs,np.float64).ravel(),0.0)
    if D>=float(e.mean()):return float(e.max()),0.0
    lo=0.0;hi=float(e.max())
    for _ in range(100):
        th=(lo+hi)/2;dist=float(np.mean(np.minimum(e,th)))
        if dist<D:lo=th
        else:hi=th
    th=(lo+hi)/2;mask=e>th
    R=float(np.mean(np.where(mask,0.5*np.log2(np.maximum(e,th)/th),0.0)))
    return th,R

def psd2(A):
    A=np.asarray(A,np.float64);A=A-A.mean(axis=1,keepdims=True);A=A-A.mean(axis=0,keepdims=True)+A.mean()
    F=np.fft.fft2(A,norm='ortho');return np.abs(F)**2

def moments(a):
    z=np.asarray(a,np.float64).ravel();mu=z.mean();sd=max(z.std(),1e-300);q=(z-mu)/sd
    return float(sd),float(np.mean(q**3)),float(np.mean(q**4)-3)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K,E=run_ar(X,coef)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'hard',me,eps))
            # Actual incumbent payload on the same held-out 7 frames, plus one shared float32 model.
            actual=4*len(coef)+40;reps={}
            for t0 in range(TRAIN,NT,TB):
                n,rep,Kd=m.encode_k(K[:,t0:t0+TB]);actual+=n;reps[rep]=reps.get(rep,0)+1
                if not np.array_equal(Kd,K[:,t0:t0+TB]):raise RuntimeError('K decode')
            target_samples=C*(NT-TRAIN);actual_bps=8*actual/target_samples
            # Average stationary 2-D spectrum of the decoder-known-predictor residual.
            Ps=[]
            for t0 in range(TRAIN,NT,TB):Ps.append(psd2(E[:,t0:t0+TB]))
            S=np.mean(Ps,axis=0);theta,rd=waterfill(S,eps*eps)
            sd,sk,ku=moments(E[:,TRAIN:]);flat=float(np.exp(np.mean(np.log(S+1e-30)))/(np.mean(S)+1e-30))
            sz=0
            for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
            szbps=8*sz/target_samples
            row={'region':name,'c0':c0,'samples':target_samples,'eps':eps,'ar_order':P,'step':STEP,'actual_ar32_bps':actual_bps,'actual_ar32_bytes':int(actual),'actual_reps':reps,'matched_sz3_bps':szbps,'matched_sz3_bytes':int(sz),'two_x_sz3_target_bps':szbps/2,'innovation_std':sd,'innovation_skew':sk,'innovation_excess_kurtosis':ku,'innovation_spectral_flatness':flat,'innovation_gaussian_mse_RD_bps':rd,'innovation_waterfill_theta':theta,'actual_over_gaussian_RD':actual_bps/rd if rd>0 else None,'gaussian_RD_over_2x_target':rd/(szbps/2) if szbps>0 else None,'maxerr':me}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'rows':rows,'scope':'Decision audit that conditions on the current decoder-real shared AR32 state before asking how much rate remains. One shared float32 AR32+intercept is fitted only on t<1024. The exact recursive step267 reconstruction is generated through t<8192, and the source residual E=X-P against that decoder-known predictor is measured on held-out t>=1024. Seven 128x1024 residual tiles provide an averaged 2-D covariance spectrum; reverse waterfilling at D=epsilon^2 gives the exact MSE rate-distortion function of a Gaussian field with that residual spectrum. Because max-error<=epsilon implies MSE<=epsilon^2, this is a model-based lower bound for a max-error residual codec IF the held-out innovation field were Gaussian. It is not a theorem for the fixed seismic file. The actual AR32 innovation bytes use the incumbent self-decoding backend on exactly the same held-out frames, model bytes are charged, matched SZ3 is rerun, and residual skew/kurtosis/flatness expose Gaussian plausibility. Purpose: determine whether the remaining gap is mostly quantizer/coding inefficiency or irreducible innovation information. No AI.'}
    json.dump(out,open('imperial_ar32_innovation_gaussian_rd.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
