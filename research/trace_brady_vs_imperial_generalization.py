import json, math, os, sys
import h5py
import numpy as np

SPACE=128
TIME=1024
NKEEP=256
SAFETY=1.0-1e-4


def entropy_norm(v):
    v=np.asarray(v,dtype=np.float64).ravel()
    s=float(v.sum())
    if s<=0 or v.size<=1:return 0.0
    p=v[v>0]/s
    h=float(-(p*np.log2(p)).sum())
    return h/math.log2(v.size)


def corr_rows(a,b):
    a=a.astype(np.float64,copy=False);b=b.astype(np.float64,copy=False)
    a=a-a.mean(axis=1,keepdims=True);b=b-b.mean(axis=1,keepdims=True)
    den=np.sqrt((a*a).sum(axis=1)*(b*b).sum(axis=1))
    m=den>0
    if not np.any(m):return 0.0,0.0
    c=(a[m]*b[m]).sum(axis=1)/den[m]
    return float(np.mean(c)),float(np.median(c))


def top_energy(power,n):
    flat=power.ravel()
    n=min(n,flat.size)
    if n==flat.size:return 1.0
    idx=np.argpartition(flat,-n)[-n:]
    return float(flat[idx].sum()/flat.sum())


def predictor_metrics(W,eps):
    W=np.asarray(W,np.float32)
    nc,nt=W.shape
    F=np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
    power=np.abs(F)**2
    flat=F.ravel(); n=min(NKEEP,flat.size)
    ii=np.argpartition(np.abs(flat),-n)[-n:]
    v=flat[ii]
    xy=np.stack([v.real,v.imag],axis=-1)
    scale=max(float(np.max(np.abs(xy)))/127.0,1e-30)
    q=np.clip(np.rint(xy/scale),-127,127).astype(np.int8)
    Cq=np.zeros_like(F)
    cqf=Cq.ravel()
    cqf[ii]=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*np.float32(scale)
    Cq=cqf.reshape(F.shape)
    P=np.fft.irfft(np.fft.ifft(Cq,axis=0),n=nt,axis=1).real.astype(np.float32)
    step=2.0*eps*SAFETY
    Q=np.rint((W.astype(np.float64)-P.astype(np.float64))/step).astype(np.int32)
    nz=float(np.mean(Q!=0))
    one=float(np.mean(np.abs(Q)==1))
    qflat=Q.ravel()
    vals,cnts=np.unique(qflat,return_counts=True)
    pq=cnts/cnts.sum()
    q_entropy=float(-(pq*np.log2(pq)).sum())
    K=Q.copy();K[:,1:]-=Q[:,:-1]
    vals2,cnts2=np.unique(K,return_counts=True);pk=cnts2/cnts2.sum()
    k_entropy=float(-(pk*np.log2(pk)).sum())
    local_std=float(W.std(dtype=np.float64))
    adj_mean,adj_median=corr_rows(W[:-1],W[1:]) if nc>1 else (0.0,0.0)
    tmp_mean,tmp_median=corr_rows(W[:,:-1],W[:,1:]) if nt>1 else (0.0,0.0)
    s=np.linalg.svd(W.astype(np.float64),compute_uv=False)
    se=s*s; ss=float(se.sum())
    rank_fracs={str(k):float(se[:min(k,len(se))].sum()/ss) if ss else 0.0 for k in (1,4,8,16,32)}
    tf=power.sum(axis=0); sf=power.sum(axis=1)
    return {
      'local_std':local_std,
      'eps_over_local_std':float(eps/local_std) if local_std>0 else None,
      'adjacent_channel_corr_mean':adj_mean,
      'adjacent_channel_corr_median':adj_median,
      'temporal_lag1_corr_mean':tmp_mean,
      'temporal_lag1_corr_median':tmp_median,
      'spectral_entropy_2d':entropy_norm(power),
      'temporal_spectral_entropy':entropy_norm(tf),
      'spatial_wavenumber_entropy':entropy_norm(sf),
      'top_energy':{str(k):top_energy(power,k) for k in (32,64,128,256,512,1024,2048)},
      'svd_energy':rank_fracs,
      'correction_nonzero_fraction':nz,
      'correction_abs1_fraction':one,
      'correction_symbol_entropy_bits':q_entropy,
      'correction_temporal_delta_entropy_bits':k_entropy,
      'prediction_rmse':float(np.sqrt(np.mean((W.astype(np.float64)-P.astype(np.float64))**2))),
      'prediction_rmse_over_eps':float(np.sqrt(np.mean((W.astype(np.float64)-P.astype(np.float64))**2))/eps),
    }


def summarize(rows):
    scalar_keys=['local_std','eps_over_local_std','adjacent_channel_corr_mean','temporal_lag1_corr_mean','spectral_entropy_2d','temporal_spectral_entropy','spatial_wavenumber_entropy','correction_nonzero_fraction','correction_abs1_fraction','correction_symbol_entropy_bits','correction_temporal_delta_entropy_bits','prediction_rmse','prediction_rmse_over_eps']
    out={'tiles':len(rows)}
    for k in scalar_keys:
        a=np.array([r[k] for r in rows if r[k] is not None],float)
        out[k]={'mean':float(a.mean()),'median':float(np.median(a)),'min':float(a.min()),'max':float(a.max())}
    for group in ['top_energy','svd_energy']:
        out[group]={}
        for sub in rows[0][group]:
            a=np.array([r[group][sub] for r in rows],float)
            out[group][sub]={'mean':float(a.mean()),'median':float(np.median(a)),'min':float(a.min()),'max':float(a.max())}
    return out


def parse_brady(path):
    size=os.path.getsize(path);h=open(path,'rb').read(3600);cand=[]
    for bo,nb in [('big','>'),('little','<')]:
        dt=int.from_bytes(h[3216:3218],bo);ns=int.from_bytes(h[3220:3222],bo);fmt=int.from_bytes(h[3224:3226],bo);st=240+4*ns
        if fmt==5 and dt>0 and ns>0 and (size-3600)%st==0:cand.append((nb,ns,(size-3600)//st,st))
    if not cand:raise RuntimeError('cannot parse Brady SEG-Y')
    nb,ns,ntr,st=cand[0];mm=np.memmap(path,np.uint8,'r');A=np.ndarray((ntr,ns),dtype=np.dtype(nb+'f4'),buffer=mm,offset=3840,strides=(st,4))
    s=ss=0.0;n=0
    for i in range(0,ntr,256):
        x=A[i:min(i+256,ntr)].astype(np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mu=s/n;std=float(np.sqrt(max(0,ss/n-mu*mu)));eps=.1*std
    X=A[4096:4224,6000:14192].astype(np.float32,copy=True)
    rows=[]
    for t0 in range(0,8192,TIME):
        r={'dataset':'Brady','t0':t0,'s0':4096};r.update(predictor_metrics(X[:,t0:t0+TIME],eps));rows.append(r)
    return {'global_std':std,'eps':eps,'rows':rows,'summary':summarize(rows)}


def parse_imperial(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];s=ss=0.0;n=0
        for t in range(0,d.shape[0],2048):
            x=np.asarray(d[t:min(t+2048,d.shape[0])]).astype(np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
        mu=s/n;std=float(np.sqrt(max(0,ss/n-mu*mu)));eps=.1*std
        times=[0,7168,14336,21504,28672];spaces=[0,1664,3328,4992,6784]
        rows=[]
        for t0 in times:
            for s0 in spaces:
                W=np.asarray(d[t0:t0+TIME,s0:s0+SPACE]).T.astype(np.float32,copy=False)
                r={'dataset':'Imperial Valley','t0':t0,'s0':s0};r.update(predictor_metrics(W,eps));rows.append(r)
    return {'global_std':std,'eps':eps,'rows':rows,'summary':summarize(rows)}


def ratios(b,i):
    bs=b['summary'];is_=i['summary'];out={}
    # Values >1 here mean Imperial is structurally worse in the named cost metric.
    for k in ['correction_nonzero_fraction','correction_symbol_entropy_bits','correction_temporal_delta_entropy_bits','prediction_rmse_over_eps','spectral_entropy_2d','temporal_spectral_entropy','spatial_wavenumber_entropy']:
        bv=bs[k]['median'];iv=is_[k]['median'];out[k+'_imperial_over_brady']=float(iv/bv) if bv else None
    out['top256_energy_brady_median']=bs['top_energy']['256']['median'];out['top256_energy_imperial_median']=is_['top_energy']['256']['median']
    out['svd16_energy_brady_median']=bs['svd_energy']['16']['median'];out['svd16_energy_imperial_median']=is_['svd_energy']['16']['median']
    out['adjacent_corr_brady_median']=bs['adjacent_channel_corr_mean']['median'];out['adjacent_corr_imperial_median']=is_['adjacent_channel_corr_mean']['median']
    out['temporal_corr_brady_median']=bs['temporal_lag1_corr_mean']['median'];out['temporal_corr_imperial_median']=is_['temporal_lag1_corr_mean']['median']
    return out


def main(brady,imperial):
    b=parse_brady(brady);print('BRADY',json.dumps(b['summary'],indent=2),flush=True)
    i=parse_imperial(imperial);print('IMPERIAL',json.dumps(i['summary'],indent=2),flush=True)
    out={'brady':b,'imperial':i,'comparison':ratios(b,i),'definition':{'tile':[SPACE,TIME],'topN':NKEEP,'epsilon':'10% global dataset std','int8_complex_topN':True}}
    json.dump(out,open('brady_imperial_generalization_trace.json','w'),indent=2)
    print('COMPARISON',json.dumps(out['comparison'],indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
