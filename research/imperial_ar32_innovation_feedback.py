import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;BASE_MODEL_BYTES=177
ORDERS=(1,2,4,8,16,32)
FITMODES=('index_ls','residual_ls')


def fit_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):
   rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)


def run(X,ar,beta):
 M=len(beta);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);A=np.zeros(X.shape,np.int32)
 a=float(ar[0]);b=np.asarray(ar[1:],np.float32);q=np.asarray(beta,np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   pa=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   fb=0.0 if M==0 or t<M else float(np.dot(q,K[c,t-M:t][::-1].astype(np.float32)))*STEP
   p=int(np.rint(pa+fb));k=int(np.rint((float(X[c,t])-p)/STEP));A[c,t]=pa;K[c,t]=k;R[c,t]=p+STEP*k
 return R,K,A


def fit_beta_iter(X,ar,M,mode,iters=4):
 beta=np.zeros(M,np.float32)
 history=[]
 Xp=X[:,:TRAIN]
 for it in range(iters):
  R,K,A=run(Xp,ar,beta);rows=[];ys=[]
  tstart=max(P,M)
  for c in range(C):
   for t in range(tstart,TRAIN):
    rows.append(K[c,t-M:t][::-1].astype(np.float64))
    if mode=='index_ls':ys.append(float(K[c,t]))
    elif mode=='residual_ls':ys.append((float(Xp[c,t])-float(A[c,t]))/STEP)
    else:raise ValueError(mode)
  Z=np.asarray(rows,np.float64);y=np.asarray(ys,np.float64)
  nb=np.linalg.lstsq(Z,y,rcond=None)[0]
  nb=np.clip(nb,-4.0,4.0).astype(np.float32)
  history.append({'iter':it,'beta':[float(x) for x in nb],'norm':float(np.linalg.norm(nb)),'prefix_k_std':float(K[:,tstart:].std()),'prefix_k_zero':float(np.mean(K[:,tstart:]==0))})
  if np.max(np.abs(nb-beta))<1e-5:beta=nb;break
  beta=nb
 return beta,history


def enc_bytes(K,model_bytes):
 total=model_bytes;reps={};frames=[]
 for t0 in range(0,K.shape[1],TB):
  A=K[:,t0:min(t0+TB,K.shape[1])];n,rep,D=m.encode_k(A)
  if not np.array_equal(A,D):raise RuntimeError(('K decode',t0,rep))
  total+=n;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'bytes':n,'rep':rep})
 return total,reps,frames


def lagcorr(K,lag=1):
 a=K[:,TRAIN+lag:].astype(np.float64).ravel();b=K[:,TRAIN:-lag].astype(np.float64).ravel()
 if a.std()==0 or b.std()==0:return 0.0
 return float(np.corrcoef(a,b)[0,1])


def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;ar=fit_ar(X)
   R0,K0,A0=run(X,ar,np.empty(0,np.float32));me0=float(np.max(np.abs(X-R0.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard',me0,eps))
   base,breps,bframes=enc_bytes(K0,BASE_MODEL_BYTES)
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   cand=[]
   for mode in FITMODES:
    for M in ORDERS:
     beta,hist=fit_beta_iter(X,ar,M,mode);R,K,A=run(X,ar,beta);me=float(np.max(np.abs(X-R.astype(np.float64))))
     if me>eps*(1+1e-12):raise RuntimeError((region,mode,M,'hard',me,eps))
     model_bytes=BASE_MODEL_BYTES+4*M+12
     n,reps,frames=enc_bytes(K,model_bytes)
     cand.append({'fit':mode,'ma_order':M,'beta':[float(x) for x in beta],'train_history':hist,'bytes':n,'bps':8*n/X.size,'gain_vs_ar32':base/n,'gain_vs_sz3':sz/n,'model_bytes':model_bytes,'k_std':float(K[:,TRAIN:].std()),'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'k_lag1_corr':lagcorr(K,1),'reps':reps,'frames':frames,'maxerr':me})
   cand.sort(key=lambda x:x['bytes']);best=cand[0]
   row={'region':region,'c0':c0,'samples':int(X.size),'baseline':{'bytes':base,'bps':8*base/X.size,'gain_vs_sz3':sz/base,'k_std':float(K0[:,TRAIN:].std()),'k_zero_fraction':float(np.mean(K0[:,TRAIN:]==0)),'k_lag1_corr':lagcorr(K0,1),'reps':breps,'maxerr':me0},'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'top6':[{k:v for k,v in x.items() if k not in ('frames','train_history')} for x in cand[:6]]}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'innovation_feedback_orders':list(ORDERS),'fit_modes':list(FITMODES),'rows':rows,'scope':'Real decoder-known innovation-feedback predictor on top of the current persistent shared AR32. The AR32+intercept is fit only from t<1024. For each MA order, feedback coefficients are learned only from that prefix by deterministic fixed-point refits using the candidate prefix trajectory, then serialized as float32. The decoder predicts with AR32 reconstructed-history state plus STEP times a linear combination of already-decoded past innovation indices K. Exact step267 innovations are encoded/byte-decoded with the incumbent backend, all added coefficient/framing bytes are charged, the complete recursive source trajectory is regenerated and hard-error verified, and matched SZ3 is rerun on identical 128x8192 regions. Both fitting the current innovation index and the pre-feedback continuous residual are tested. This is an ARMA/error-feedback direction, not a context entropy estimate and not target-trained beyond the allowed prefix. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_innovation_feedback.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
