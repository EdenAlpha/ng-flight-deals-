import json,math,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

C=128;T=1024;ORDER=16
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
TIMES=(0,14488,28976)

def recursive_residual(X):
    co=ar.fit_shared(X,ORDER);_,cd=ar.model_frame(co);R=np.zeros(X.shape,np.int32);P=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,ORDER,'shared');k=int(np.rint((float(X[c,t])-pred)/m.STEP));P[c,t]=pred;R[c,t]=pred+m.STEP*k
    E=np.rint(X).astype(np.int32)-P
    return E.astype(np.float64),cd

def mp_median(q):
    a=(1-math.sqrt(q))**2;b=(1+math.sqrt(q))**2
    x=np.linspace(a+1e-7,b-1e-7,300000)
    dens=np.sqrt(np.maximum(0,(b-x)*(x-a)))/(2*math.pi*q*x)
    dx=x[1]-x[0];cdf=np.cumsum(dens)*dx;cdf/=cdf[-1]
    return float(x[np.searchsorted(cdf,0.5)]),a,b

def corr(a,b):
    x=np.asarray(a,np.float64).ravel();y=np.asarray(b,np.float64).ravel();x-=x.mean();y-=y.mean();den=float(np.sqrt(np.dot(x,x)*np.dot(y,y)))
    return float(np.dot(x,y)/den) if den else 0.0

def spectral_flatness(E):
    X=E-E.mean(axis=1,keepdims=True);F=np.fft.rfft(X,axis=1);P=(F.real*F.real+F.imag*F.imag)[:,1:];tiny=max(float(P.mean())*1e-15,1e-30)
    return float(np.median(np.exp(np.mean(np.log(P+tiny),axis=1))/np.mean(P+tiny,axis=1)))

def welch_adjacent_coherence(E,nseg=8):
    n=E.shape[1]//nseg;vals=[]
    w=np.hanning(n)
    for c in range(E.shape[0]-1):
        Sxx=Syy=Sxy=None
        for j in range(nseg):
            a=(E[c,j*n:(j+1)*n]-np.mean(E[c,j*n:(j+1)*n]))*w;b=(E[c+1,j*n:(j+1)*n]-np.mean(E[c+1,j*n:(j+1)*n]))*w
            A=np.fft.rfft(a);B=np.fft.rfft(b);xx=(A*np.conj(A)).real;yy=(B*np.conj(B)).real;xy=A*np.conj(B)
            Sxx=xx if Sxx is None else Sxx+xx;Syy=yy if Syy is None else Syy+yy;Sxy=xy if Sxy is None else Sxy+xy
        coh=(np.abs(Sxy)**2)/(np.maximum(Sxx*Syy,1e-30));vals.append(np.median(coh[1:]))
    return float(np.median(vals)),float(np.percentile(vals,90))

def eig_audit(E):
    X=E-E.mean(axis=1,keepdims=True);cov=(X@X.T)/X.shape[1];ev,U=np.linalg.eigh(cov);idx=np.argsort(ev)[::-1];ev=ev[idx];U=U[:,idx]
    q=X.shape[0]/X.shape[1];medfac,a,b=mp_median(q);sigma2=float(np.median(ev)/medfac);upper=sigma2*b;lower=sigma2*a
    above=ev>upper;outlier_excess=np.maximum(ev-upper,0)
    out={
      'q':q,'mp_median_factor':medfac,'noise_variance_from_mp_median':sigma2,'mp_lower_edge':lower,'mp_upper_edge':upper,
      'modes_above_mp_upper':int(np.count_nonzero(above)),'energy_fraction_in_modes_above_edge':float(ev[above].sum()/ev.sum()) if np.any(above) else 0.0,
      'excess_energy_fraction_above_mp_edge':float(outlier_excess.sum()/ev.sum()),
      'top1_energy_fraction':float(ev[0]/ev.sum()),'top4_energy_fraction':float(ev[:4].sum()/ev.sum()),'top8_energy_fraction':float(ev[:8].sum()/ev.sum()),'top16_energy_fraction':float(ev[:16].sum()/ev.sum()),'top32_energy_fraction':float(ev[:32].sum()/ev.sum()),
      'condition_ratio_top_to_median':float(ev[0]/np.median(ev)),'eigenvalues':ev.tolist()
    }
    return out,U

def subspace_overlap(U,V,k):
    s=np.linalg.svd(U[:,:k].T@V[:,:k],compute_uv=False)
    return float(np.mean(s*s)),float(np.min(s))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];byreg={}
        for name,c0 in REGIONS:
            byreg[name]=[]
            for t0 in TIMES:
                X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;E,coef=recursive_residual(X);ea,U=eig_audit(E);wc50,wc90=welch_adjacent_coherence(E)
                row={'region':name,'c0':c0,'t0':t0,'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),'residual_std':float(E.std()),'eps_over_residual_std':float(eps/E.std()),'residual_lag1_corr':corr(E[:,:-1],E[:,1:]),'residual_lag2_corr':corr(E[:,:-2],E[:,2:]),'residual_adjacent_channel_corr':corr(E[:-1,:],E[1:,:]),'spectral_flatness_median':spectral_flatness(E),'welch_adjacent_coherence_median':wc50,'welch_adjacent_coherence_p90':wc90,'ar16_coefficients':coef.tolist(),'rmt':ea}
                rows.append(row);byreg[name].append((row,U));print(json.dumps({'region':name,'t0':t0,'resid_std':row['residual_std'],'flatness':row['spectral_flatness_median'],'coherence':wc50,'mp_modes':ea['modes_above_mp_upper'],'mp_energy':ea['energy_fraction_in_modes_above_edge'],'excess':ea['excess_energy_fraction_above_mp_edge'],'top16':ea['top16_energy_fraction']}),flush=True)
        stability=[]
        for name,items in byreg.items():
            for i in range(len(items)):
                for j in range(i+1,len(items)):
                    z={'region':name,'t0_a':items[i][0]['t0'],'t0_b':items[j][0]['t0']}
                    for k in (4,8,16,32):
                        mean2,mins=subspace_overlap(items[i][1],items[j][1],k);z[f'top{k}_mean_squared_canonical_overlap']=mean2;z[f'top{k}_min_canonical_correlation']=mins
                    stability.append(z)
        summary=[]
        for name,_ in REGIONS:
            rr=[r for r in rows if r['region']==name]
            summary.append({'region':name,'median_residual_std':float(np.median([r['residual_std'] for r in rr])),'median_eps_over_residual_std':float(np.median([r['eps_over_residual_std'] for r in rr])),'median_spectral_flatness':float(np.median([r['spectral_flatness_median'] for r in rr])),'median_adjacent_coherence':float(np.median([r['welch_adjacent_coherence_median'] for r in rr])),'median_mp_outlier_mode_count':float(np.median([r['rmt']['modes_above_mp_upper'] for r in rr])),'median_energy_in_mp_outlier_modes':float(np.median([r['rmt']['energy_fraction_in_modes_above_edge'] for r in rr])),'median_excess_energy_above_mp_edge':float(np.median([r['rmt']['excess_energy_fraction_above_mp_edge'] for r in rr])),'median_top16_energy':float(np.median([r['rmt']['top16_energy_fraction'] for r in rr]))})
        out={'global_std':std,'eps':eps,'shape':[30000,6912],'region_width':C,'window_length':T,'order':ORDER,'times':list(TIMES),'summary':summary,'rows':rows,'subspace_stability':stability,'scope':'Residual dimensionality audit, not a claim that incoherent energy is instrument noise and not a compression lower bound. Each 128x1024 window is first whitened by a locally fitted, serialized/decoder-real shared AR16 recursion identical in form to PR301. Spatial residual covariance is compared with a Marchenko-Pastur random-matrix bulk at q=128/1024; noise variance is robustly matched through the theoretical MP median, and outlier-mode counts/energy are reported. Welch adjacent-channel coherence, residual time correlations, spectral flatness and cross-window leading-subspace stability distinguish repeatable coherent structure from high-dimensional incoherent innovation. If a large stable outlier subspace survives, it is a compression target; if most residual energy lies in an unstable MP-like bulk, the current L-infinity contract is forcing preservation of largely unpredictable information.'}
        print(json.dumps({'summary':summary,'stability':stability},indent=2),flush=True);json.dump(out,open('imperial_residual_random_matrix_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
