import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;MODEL_BYTES=177
CHUNKS=(1024,2048,4096,7168)

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def encode_chunks(K,chunk):
 total=MODEL_BYTES;reps={};frames=[]
 for t0 in range(TRAIN,K.shape[1],chunk):
  A=K[:,t0:min(t0+chunk,K.shape[1])];n,rep,D=m.encode_k(A)
  if not np.array_equal(A,D):raise RuntimeError(('decode',chunk,t0))
  total+=n;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'nt':A.shape[1],'bytes':n,'rep':rep})
 return total,reps,frames

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K=run_ar(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((name,me,eps))
   sz=0
   for t0 in range(TRAIN,NT,1024):b,_=m.szrun(X[:,t0:min(t0+1024,NT)],eps);sz+=b
   samples=C*(NT-TRAIN);cand=[]
   for ch in CHUNKS:
    b,reps,frames=encode_chunks(K,ch);cand.append({'chunk':ch,'bytes':b,'bps':8*b/samples,'gain_vs_sz3':sz/b,'reps':reps,'frames':frames})
   cand.sort(key=lambda x:x['bytes']);base=[x for x in cand if x['chunk']==1024][0];best=cand[0]
   row={'region':name,'c0':c0,'samples':samples,'sz3_bytes':sz,'sz3_bps':8*sz/samples,'baseline_1024':base,'best':best,'gain_best_vs_1024':base['bytes']/best['bytes'],'maxerr':me}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'heldout':[TRAIN,NT],'chunks':list(CHUNKS),'rows':rows,'scope':'Exact long-context backend gate on the current decoder-real AR32 step267 innovations. One shared AR32 model is fit only from t<1024. The held-out K field is unchanged. Existing self-decoding encode_k is rerun with innovation frame lengths 1024/2048/4096/7168; every stream byte-decodes to exact K, model/framing bytes are charged, and matched SZ3 remains on the incumbent identical 1024 partition. This isolates whether resetting the lossless innovation backend every 1024 samples is discarding useful long temporal context. No AI; draft diagnostic; do not merge.'}
 json.dump(out,open('imperial_ar32_long_frames.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
