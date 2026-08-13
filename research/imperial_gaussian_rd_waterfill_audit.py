import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784));C=128;NT=8192;TB=1024

def waterfill(eigs,D):
    e=np.maximum(np.asarray(eigs,np.float64).ravel(),0.0)
    if D>=float(e.mean()):return float(e.max()),0.0
    lo=0.0;hi=float(e.max())
    for _ in range(100):
        th=(lo+hi)/2;d=float(np.mean(np.minimum(e,th)))
        if d<D:lo=th
        else:hi=th
    th=(lo+hi)/2;mask=e>th;R=float(np.mean(0.5*np.log2(e[mask]/th))) if np.any(mask) else 0.0
    # mean above is over active only; rate integral is over all frequencies.
    R*=float(np.mean(mask))
    return th,R

def stats1(x):
    z=np.asarray(x,np.float64).ravel();mu=float(z.mean());v=float(np.mean((z-mu)**2));sd=math.sqrt(max(v,1e-300));q=(z-mu)/sd
    return {'mean':mu,'std':sd,'skew':float(np.mean(q**3)),'excess_kurtosis':float(np.mean(q**4)-3.0)}

def psd2(X):
    ps=[]
    for t0 in range(0,X.shape[1],TB):
        A=np.asarray(X[:,t0:t0+TB],np.float64);A=A-A.mean(axis=1,keepdims=True);A=A-A.mean(axis=0,keepdims=True)+A.mean()
        F=np.fft.fft2(A,norm='ortho');ps.append(np.abs(F)**2)
    P=np.mean(ps,axis=0)
    return P

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;mom=stats1(X);P=psd2(X);D=eps*eps;theta,R=waterfill(P,D)
            # Matched SZ3 on the identical 128x1024 partition.
            sz=0
            for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
            szbps=8*sz/X.size;target=szbps/2
            # scalar iid Gaussian reference (intentionally less correlation-aware)
            iid=max(0.0,math.log2(max(mom['std'],eps)/eps))
            active=float(np.mean(P>theta));row={'region':name,'c0':c0,'samples':int(X.size),'local_std':mom['std'],'eps_over_local_std':eps/mom['std'],'skew':mom['skew'],'excess_kurtosis':mom['excess_kurtosis'],'mean_2d_spectral_power':float(P.mean()),'spectral_flatness':float(np.exp(np.mean(np.log(P+1e-30)))/(np.mean(P)+1e-30)),'waterfill_theta':theta,'active_spectral_fraction':active,'gaussian_2d_mse_RD_bps':R,'iid_gaussian_reference_bps':iid,'matched_sz3_bytes':int(sz),'matched_sz3_bps':szbps,'two_x_sz3_target_bps':target,'gaussian_RD_over_2x_target':R/target if target>0 else None};rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'tile_shape':[C,TB],'analysis_samples_per_region':C*NT,'rows':rows,'scope':'Model-based information diagnostic, NOT a theorem about the actual non-Gaussian fixed file. Each 128x8192 region is centered per channel/time and its stationary 2-D Gaussian covariance spectrum is approximated by averaging orthonormal 2-D periodograms over eight 128x1024 tiles. Reverse waterfilling computes the exact squared-error rate-distortion function of the Gaussian field with that spectrum at D=epsilon^2. Any reconstruction satisfying the stronger L-infinity max-error <=epsilon also has MSE<=epsilon^2, so under the Gaussian-field model this R(D) is a lower bound for a max-error codec. It is not a rigorous lower bound for the real non-Gaussian seismic process; skew/kurtosis/spectral-flatness are reported so Gaussian plausibility is visible. Matched SZ3 and its 2x target are rerun on identical tiles. No AI.'}
    print(json.dumps({'eps':eps,'summary':[{k:r[k] for k in ('region','gaussian_2d_mse_RD_bps','matched_sz3_bps','two_x_sz3_target_bps','gaussian_RD_over_2x_target')} for r in rows]},indent=2),flush=True);json.dump(out,open('imperial_gaussian_rd_waterfill_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
