import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024

def design(X):
 n=C*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);j=0
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
 return A,y

def wsolve(A,y,w):
 sw=np.sqrt(np.asarray(w,np.float64));Aw=A*sw[:,None];yw=y*sw
 return np.linalg.lstsq(Aw,yw,rcond=None)[0]

def fits(A,y):
 ls=np.linalg.lstsq(A,y,rcond=None)[0];out={'ls':ls}
 for name,kind,delta in [('huber128','huber',128.),('huber267','huber',267.),('l1floor64','l1',64.),('l1floor128','l1',128.)]:
  co=ls.copy()
  for _ in range(6):
   r=y-A@co;a=np.abs(r)
   if kind=='huber':w=np.minimum(1.0,delta/np.maximum(a,1e-12))
   else:w=1.0/np.maximum(a,delta)
   co=wsolve(A,y,w)
  out[name]=co
 return {k:np.asarray(v,np.float32) for k,v in out.items()}

def run_ar(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;A,y=design(X);models=fits(A,y);sz=0
   for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   ns=C*(NT-TRAIN);cand=[]
   for name,co in models.items():
    raw=np.asarray(co,'<f4').tobytes();cd=np.frombuffer(raw,'<f4').copy();mb=len(raw)+45
    R,K=run_ar(X,cd);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,name,me,eps))
    total=mb;reps={}
    for t0 in range(TRAIN,NT,TB):
     n,rep,Kd=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
     if not np.array_equal(Kd,K[:,t0:t0+TB]):raise RuntimeError(('K decode',region,name,t0))
    rr=y-A@np.asarray(co,np.float64)
    cand.append({'fit':name,'bytes':total,'bps':8*total/ns,'gain_vs_sz3':sz/total,'model_bytes':mb,'prefix_mae':float(np.mean(np.abs(rr))),'prefix_rmse':float(np.sqrt(np.mean(rr*rr))),'held_k_std':float(K[:,TRAIN:].std()),'held_k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'reps':reps,'maxerr':me})
    print(json.dumps({'region':region,'candidate':cand[-1]},indent=2),flush=True)
   cand.sort(key=lambda x:x['bytes']);base=[x for x in cand if x['fit']=='ls'][0];best=cand[0]
   rows.append({'region':region,'c0':c0,'samples':ns,'sz3_bytes':sz,'sz3_bps':8*sz/ns,'ls':base,'best':best,'gain_best_vs_ls':base['bytes']/best['bytes'],'candidates':cand})
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'train':TRAIN,'heldout':[TRAIN,NT],'rows':rows,'scope':'Robust predictor-fit gate motivated by the strongly leptokurtic AR32 innovations measured in PR #369. All models use only the identical first 1024 source samples and transmit the same float32 AR32+intercept footprint. Ordinary least squares is compared with deterministic six-iteration Huber IRLS (delta 128/267) and L1-like IRLS with residual floors 64/128. No heldout target information chooses coefficients. Each frozen model is recursively replayed through t<8192 at step267, heldout innovations are encoded by the existing exact self-decoding backend, all model bytes are charged, and matched SZ3/hard error are identical. Purpose: test whether LS wastes entropy by fitting rare heavy-tail excursions instead of concentrating the bulk innovation law. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_robust_prefix_fit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
