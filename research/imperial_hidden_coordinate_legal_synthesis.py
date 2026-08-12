import json,math,os,sys
import h5py
import numpy as np

TILE_C=128
TILE_T=1024
LAG=32


def shannon_int(a):
    a=np.asarray(a).ravel()
    if a.size==0:return 0.0
    _,c=np.unique(a,return_counts=True)
    p=c.astype(np.float64)/a.size
    return float(-(p*np.log2(p)).sum())


def top_energy(A,k=16):
    X=np.asarray(A,np.float64)
    C=X@X.T
    v=np.linalg.eigvalsh(C)
    s=float(v.sum())
    return float(v[-min(k,len(v)):].sum()/s) if s>0 else 1.0


def norm_rows(W):
    X=W.astype(np.float64)
    X-=X.mean(axis=1,keepdims=True)
    s=X.std(axis=1,keepdims=True)
    s[s==0]=1
    return X/s


def batch_ref_align(W):
    X=norm_rows(W)
    n=2048
    F=np.fft.rfft(X,n=n,axis=1)
    r=X.shape[0]//2
    cross=np.fft.irfft(F*np.conj(F[r:r+1]),n=n,axis=1)
    lags=np.arange(-LAG,LAG+1)
    vals=np.concatenate([cross[:,-LAG:],cross[:,:LAG+1]],axis=1)
    den=np.linalg.norm(X,axis=1)*np.linalg.norm(X[r])
    den[den==0]=1
    vals=vals/den[:,None]
    j=np.argmax(np.abs(vals),axis=1)
    bestlags=lags[j]
    bestcorr=vals[np.arange(X.shape[0]),j]
    Y=np.empty_like(X)
    for i,(lag,c) in enumerate(zip(bestlags,bestcorr)):
        Y[i]=np.roll(X[i],-int(lag))*(1.0 if c>=0 else -1.0)
    Y=Y[:,LAG:-LAG]
    return Y,bestlags,bestcorr


def adjacent_lag_stats(W):
    X=norm_rows(W)
    idx=np.linspace(0,X.shape[0]-2,16,dtype=int)
    rows=[]
    for i in idx:
        a=X[i];b=X[i+1]
        n=2048
        fa=np.fft.rfft(a,n=n);fb=np.fft.rfft(b,n=n)
        cc=np.fft.irfft(fa*np.conj(fb),n=n)
        vals=np.concatenate([cc[-LAG:],cc[:LAG+1]])/(np.linalg.norm(a)*np.linalg.norm(b)+1e-30)
        lags=np.arange(-LAG,LAG+1)
        j=int(np.argmax(np.abs(vals)))
        rows.append((float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)+1e-30)),float(vals[j]),int(lags[j])))
    return {
      'zero_lag_corr_median':float(np.median([r[0] for r in rows])),
      'max_abs_lag_corr_median':float(np.median([abs(r[1]) for r in rows])),
      'best_lag_abs_median':float(np.median([abs(r[2]) for r in rows])),
      'polarity_flip_fraction':float(np.mean([r[1]<0 for r in rows]))}


def welch_adjacent_coherence(W):
    X=norm_rows(W)
    idx=np.linspace(0,X.shape[0]-2,12,dtype=int)
    vals=[]
    win=np.hanning(128)
    for i in idx:
        a=X[i].reshape(8,128)*win
        b=X[i+1].reshape(8,128)*win
        A=np.fft.rfft(a,axis=1);B=np.fft.rfft(b,axis=1)
        Sxy=np.mean(A*np.conj(B),axis=0)
        Sxx=np.mean(np.abs(A)**2,axis=0);Syy=np.mean(np.abs(B)**2,axis=0)
        coh=np.abs(Sxy)**2/(Sxx*Syy+1e-30)
        vals.append(float(np.mean(coh[1:])))
    return float(np.median(vals))


def detrend_axis(A,axis):
    X=np.asarray(A,np.float64).copy()
    if axis==1:
        n=X.shape[1];u=np.linspace(0,1,n)[None,:]
        X-=X[:,0:1]*(1-u)+X[:,-1:] * u
    else:
        n=X.shape[0];u=np.linspace(0,1,n)[:,None]
        X-=X[0:1,:]*(1-u)+X[-1:,:] * u
    return X


def min_plateau_count(x,eps):
    lo=-np.inf;hi=np.inf;n=0
    for v in np.asarray(x,np.float64):
        nl=max(lo,v-eps);nh=min(hi,v+eps)
        if n==0 or nl>nh:
            n+=1;lo=v-eps;hi=v+eps
        else:
            lo=nl;hi=nh
    return n


def plateau_density(W,eps):
    ts=sum(min_plateau_count(W[i],eps) for i in range(W.shape[0]))/(W.size)
    ss=sum(min_plateau_count(W[:,j],eps) for j in range(W.shape[1]))/(W.size)
    return float(ts),float(ss)


def predictor_hits(W,eps):
    X=W.astype(np.float64)
    out={}
    out['temporal_hold']=float(np.mean(np.abs(X[:,1:]-X[:,:-1])<=eps))
    out['temporal_signflip']=float(np.mean(np.abs(X[:,1:]+X[:,:-1])<=eps))
    out['temporal_linear']=float(np.mean(np.abs(X[:,2:]-(2*X[:,1:-1]-X[:,:-2]))<=eps))
    out['spatial_hold']=float(np.mean(np.abs(X[1:]-X[:-1])<=eps))
    out['lorenzo']=float(np.mean(np.abs(X[1:,1:]-(X[:-1,1:]+X[1:,:-1]-X[:-1,:-1]))<=eps))
    xp=X[:,:-1].ravel();yt=X[:,1:].ravel();a=float((xp@yt)/(xp@xp+1e-30))
    out['ar1_a']=a;out['ar1_hit']=float(np.mean(np.abs(yt-a*xp)<=eps))
    M=np.stack([X[:,1:-1].ravel(),X[:,:-2].ravel()],axis=1);y=X[:,2:].ravel();coef=np.linalg.lstsq(M,y,rcond=None)[0]
    out['ar2_coef']=[float(coef[0]),float(coef[1])];out['ar2_hit']=float(np.mean(np.abs(y-M@coef)<=eps))
    best=(-1,None)
    for lag in range(-16,17):
        if lag>=0:
            a=X[1:,lag:];b=X[:-1,:X.shape[1]-lag] if lag else X[:-1]
        else:
            a=X[1:,:X.shape[1]+lag];b=X[:-1,-lag:]
        h=float(np.mean(np.abs(a-b)<=eps))
        if h>best[0]:best=(h,lag)
    out['best_shifted_spatial_hit']=best[0];out['best_shifted_spatial_lag']=best[1]
    return out


def recursive_temporal(W,eps,coef=None):
    X=W.astype(np.float64);step=2*eps*(1-1e-6)
    R=np.empty_like(X);K=np.zeros(X.shape,np.int32)
    R[:,0]=step*np.rint(X[:,0]/step);K[:,0]=np.rint(X[:,0]/step).astype(np.int32)
    if coef is None:
        for t in range(1,X.shape[1]):
            p=R[:,t-1];k=np.rint((X[:,t]-p)/step);K[:,t]=k.astype(np.int32);R[:,t]=p+k*step
    else:
        if X.shape[1]>1:
            p=coef[0]*R[:,0];k=np.rint((X[:,1]-p)/step);K[:,1]=k.astype(np.int32);R[:,1]=p+k*step
        for t in range(2,X.shape[1]):
            p=coef[0]*R[:,t-1]+coef[1]*R[:,t-2];k=np.rint((X[:,t]-p)/step);K[:,t]=k.astype(np.int32);R[:,t]=p+k*step
    me=float(np.max(np.abs(X-R)))
    return {'zero_fraction':float(np.mean(K[:,1:]==0)),'symbol_entropy':shannon_int(K[:,1:]),'maxerr':me}


def tile_metrics(W,eps):
    q=np.rint(W/(2*eps*(1-1e-6))).astype(np.int32)
    Y,lags,corr=batch_ref_align(W)
    U=detrend_axis(np.cumsum(W.astype(np.float64),axis=1),1)
    V=detrend_axis(np.cumsum(W.astype(np.float64),axis=0),0)
    td,sd=plateau_density(W,eps)
    ph=predictor_hits(W,eps)
    return {
      'local_std':float(W.std(dtype=np.float64)),
      'eps_over_local_std':float(eps/(W.std(dtype=np.float64)+1e-30)),
      'q_entropy_bits':shannon_int(q),
      'q_time_change_fraction':float(np.mean(q[:,1:]!=q[:,:-1])),
      'q_space_change_fraction':float(np.mean(q[1:]!=q[:-1])),
      'raw_top16_svd_energy':top_energy(W,16),
      'row_normalized_top16_svd_energy':top_energy(norm_rows(W),16),
      'delay_polarity_aligned_top16_svd_energy':top_energy(Y,16),
      'time_integrated_detrended_top16_svd_energy':top_energy(U,16),
      'space_integrated_detrended_top16_svd_energy':top_energy(V,16),
      'alignment_median_abs_lag':float(np.median(np.abs(lags))),
      'alignment_median_abs_corr':float(np.median(np.abs(corr))),
      'adjacent':adjacent_lag_stats(W),
      'adjacent_welch_coherence':welch_adjacent_coherence(W),
      'minimum_legal_constant_segment_density_time':td,
      'minimum_legal_constant_segment_density_space':sd,
      'predictor_hit_rates':ph,
      'recursive_hold_legal_quantizer':recursive_temporal(W,eps),
      'recursive_ar2_legal_quantizer':recursive_temporal(W,eps,ph['ar2_coef'])
    }


def med(rows,keypath):
    vals=[]
    for r in rows:
        x=r
        for k in keypath:x=x[k]
        vals.append(x)
    return float(np.median(vals))


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'] if 'Acoustic' in f else max((o for o in f.values() if isinstance(o,h5py.Dataset) and o.ndim==2),key=lambda z:z.size*z.dtype.itemsize)
        s=ss=0.0;n=0
        for t in range(0,d.shape[0],2048):
            x=np.asarray(d[t:min(t+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
        mu=s/n;std=float(np.sqrt(max(0,ss/n-mu*mu)));eps=.1*std
        ts=np.linspace(0,d.shape[0]-TILE_T,5,dtype=int);cs=np.linspace(0,d.shape[1]-TILE_C,5,dtype=int)
        rows=[]
        for t0 in ts:
            for c0 in cs:
                W=np.asarray(d[t0:t0+TILE_T,c0:c0+TILE_C]).T.astype(np.float32)
                m=tile_metrics(W,eps);m['t0']=int(t0);m['c0']=int(c0);rows.append(m)
                print(json.dumps({'t0':int(t0),'c0':int(c0),'plateau_t':m['minimum_legal_constant_segment_density_time'],'aligned_rank16':m['delay_polarity_aligned_top16_svd_energy'],'maxlagcorr':m['adjacent']['max_abs_lag_corr_median'],'hold_zero':m['recursive_hold_legal_quantizer']['zero_fraction']}),flush=True)
        summary={
          'eps':eps,'global_std':std,'tiles':len(rows),
          'median_eps_over_local_std':med(rows,['eps_over_local_std']),
          'median_q_entropy_bits':med(rows,['q_entropy_bits']),
          'median_q_time_change_fraction':med(rows,['q_time_change_fraction']),
          'median_raw_top16_svd_energy':med(rows,['raw_top16_svd_energy']),
          'median_delay_polarity_aligned_top16_svd_energy':med(rows,['delay_polarity_aligned_top16_svd_energy']),
          'median_time_integrated_top16_svd_energy':med(rows,['time_integrated_detrended_top16_svd_energy']),
          'median_space_integrated_top16_svd_energy':med(rows,['space_integrated_detrended_top16_svd_energy']),
          'median_adjacent_zero_lag_corr':med(rows,['adjacent','zero_lag_corr_median']),
          'median_adjacent_maxlag_abs_corr':med(rows,['adjacent','max_abs_lag_corr_median']),
          'median_adjacent_welch_coherence':med(rows,['adjacent_welch_coherence']),
          'median_min_legal_plateau_density_time':med(rows,['minimum_legal_constant_segment_density_time']),
          'median_min_legal_plateau_density_space':med(rows,['minimum_legal_constant_segment_density_space']),
          'median_best_shifted_spatial_hit':med(rows,['predictor_hit_rates','best_shifted_spatial_hit']),
          'median_recursive_hold_zero_fraction':med(rows,['recursive_hold_legal_quantizer','zero_fraction']),
          'median_recursive_hold_symbol_entropy':med(rows,['recursive_hold_legal_quantizer','symbol_entropy']),
          'median_recursive_ar2_zero_fraction':med(rows,['recursive_ar2_legal_quantizer','zero_fraction']),
          'median_recursive_ar2_symbol_entropy':med(rows,['recursive_ar2_legal_quantizer','symbol_entropy'])
        }
        out={'dataset_shape':list(d.shape),'dtype':str(d.dtype),'summary':summary,'tile_metrics':rows}
        print(json.dumps(summary,indent=2),flush=True)
        json.dump(out,open('imperial_hidden_coordinate_legal_synthesis.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
