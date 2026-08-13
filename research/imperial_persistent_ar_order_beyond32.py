import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
ORDERS=(16,32,48,64,96,128)
C=128;NT=8192;TRAIN=1024;STEP=267;TB=1024

def fit_shared_ar(X,p):
 n=C*(TRAIN-p);A=np.empty((n,p+1),np.float32);y=np.empty(n,np.float32);j=0
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float32)
  for t in range(p,TRAIN):
   A[j,0]=1.0;A[j,1:]=x[t-p:t][::-1];y[j]=x[t];j+=1
 return np.linalg.lstsq(A.astype(np.float64),y.astype(np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,coef,p):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   pred=0 if t<p else int(np.rint(a+float(np.dot(b,R[c,t-p:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;R[c,t]=pred+STEP*k
 return R,K

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;sz=0
   for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   ns=C*(NT-TRAIN);cand=[]
   for p in ORDERS:
    co=fit_shared_ar(X,p);R,K=run_ar(X,co,p);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((name,p,me,eps))
    model_bytes=4*len(co)+45;total=model_bytes;reps={}
    for t0 in range(TRAIN,NT,TB):
     n,rep,Kd=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
     if not np.array_equal(Kd,K[:,t0:t0+TB]):raise RuntimeError(('K decode',name,p,t0))
    cand.append({'order':p,'model_bytes':model_bytes,'bytes':total,'bps':8*total/ns,'gain_vs_sz3':sz/total,'k_std':float(K[:,TRAIN:].std()),'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'reps':reps,'maxerr':me})
    print(json.dumps({'region':name,'candidate':cand[-1]},indent=2),flush=True)
   cand.sort(key=lambda x:x['bytes']);base=[x for x in cand if x['order']==32][0];best=cand[0]
   rows.append({'region':name,'c0':c0,'samples':ns,'sz3_bytes':sz,'sz3_bps':8*sz/ns,'baseline_ar32':base,'best':best,'gain_best_vs_ar32':base['bytes']/best['bytes'],'candidates':cand})
 out={'global_std':gstd,'eps':eps,'step':STEP,'train':TRAIN,'heldout':[TRAIN,NT],'orders':list(ORDERS),'rows':rows,'scope':'Exact persistent shared-AR order sweep beyond the current AR32 incumbent. Each order is fitted only from the first 1024 source samples of the same 128-channel region, coefficients are float32 and fully charged, then frozen and recursively replayed through t<8192 at the unchanged legal step267. Held-out innovations use the existing self-decoding encode_k backend; every K frame byte-decodes exactly and source max error is checked. Matched SZ3 is rerun on identical heldout 128x1024 tiles. Purpose: determine whether the strong lag-1 residual dependence seen after AR32 is simply under-modeling by order 32 before inventing another representation. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_persistent_ar_order_beyond32.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
