import json,math,sys,h5py,numpy as np
T=1024;C=128;SAFETY=1-1e-5

def H(a):
 _,cnt=np.unique(a,return_counts=True);p=cnt/cnt.sum();return float(-(p*np.log2(p)).sum())
def Hcond(a,b):
 # H(b|a)=H(a,b)-H(a)
 x=np.stack([a.ravel(),b.ravel()],axis=1);_,cnt=np.unique(x,axis=0,return_counts=True);p=cnt/cnt.sum();hj=float(-(p*np.log2(p)).sum());return hj-H(a.ravel())
def Hcond2(a,b,y):
 c=np.stack([a.ravel(),b.ravel()],axis=1);t=np.stack([a.ravel(),b.ravel(),y.ravel()],axis=1)
 _,cc=np.unique(c,axis=0,return_counts=True);pc=cc/cc.sum();hc=float(-(pc*np.log2(pc)).sum())
 _,ct=np.unique(t,axis=0,return_counts=True);pt=ct/ct.sum();ht=float(-(pt*np.log2(pt)).sum());return ht-hc
def stats(d):
 s=ss=s3=s4=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);n+=x.size;s+=x.sum();ss+=(x*x).sum()
 m=s/n;v=ss/n-m*m;sd=math.sqrt(v)
 # higher moments on a deterministic stride sample
 x=np.asarray(d[::97,::23],np.float64).ravel();z=(x-m)/sd
 return float(m),float(sd),float(np.mean(z**3)),float(np.mean(z**4))
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];mu,std,skew,kurt=stats(d);pub=.1*std;step=2*pub*SAFETY
  tpos=[0,7244,14488,21732,28976];cpos=[0,1696,3392,5088,6784]
  rawtiles=[]
  for t0 in tpos:
   for c0 in cpos:rawtiles.append(np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T)
  sample=np.concatenate([x.ravel()[::17] for x in rawtiles])
  phases=np.linspace(0,step,64,endpoint=False);best=None
  for ph in phases:
   q=np.rint((sample-ph)/step).astype(np.int32);h=H(q)
   if best is None or h<best[0]:best=(h,float(ph))
  ph=best[1];qs=[np.rint((x-ph)/step).astype(np.int16) for x in rawtiles]
  h0=float(np.mean([H(q) for q in qs]));metrics={}
  for lag in [1,2,3,4,8,16,32]:metrics[f'time_lag_{lag}']=float(np.mean([Hcond(q[:,:-lag],q[:,lag:]) for q in qs]))
  for lag in [1,2,4,8,16,32]:metrics[f'chan_lag_{lag}']=float(np.mean([Hcond(q[:-lag,:],q[lag:,:]) for q in qs]))
  both=[]
  for q in qs:
   both.append(Hcond2(q[:-1,:-1],q[:-1,1:],q[1:,1:]))
  metrics['two_neighbor_context']=float(np.mean(both))
  sz3_ratio=4.242 # verified PR208 aggregate order of magnitude; used only to define requested 2x target
  sz3_bps=16/sz3_ratio;target_bps=sz3_bps/2
  gaussian_mse_rd=math.log2(std/pub) # 0.5log2(sigma^2/eps^2)=log2(10)
  out={'std':std,'public_eps':pub,'step':step,'skew_sample':skew,'kurtosis_sample':kurt,'best_phase':ph,'sample_phase_H0':best[0],'tile_H0':h0,'conditional_entropies_bps':metrics,'gaussian_iid_MSE_rate_distortion_lower_bound_bps':gaussian_mse_rd,'note_bound':'Because max-absolute error <= eps implies MSE <= eps^2, an IID Gaussian source would require at least this many bits/sample; this is a model-based lower bound, not a universal bound for the measured dependent source.','verified_sz3_approx_bps':sz3_bps,'two_x_better_target_bps':target_bps,'raw16_ratio_at_gaussian_bound':16/gaussian_mse_rd,'raw16_ratio_at_empirical_best_context':16/min(metrics.values()),'scope':'25 deterministic tiles for entropy-rate proxies; diagnostic only, not a proof of universal optimality'}
  print(json.dumps(out,indent=2));json.dump(out,open('imperial_rate_headroom_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
