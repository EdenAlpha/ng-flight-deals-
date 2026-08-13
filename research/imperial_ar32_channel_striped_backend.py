import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
GROUPS=(1,2,4,8,16,32,64,128)
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def encode_grouped(K,g):
 total=MODEL_BYTES;reps={};parts=0
 for t0 in range(TRAIN,NT,TB):
  for c0 in range(0,C,g):
   A=K[c0:min(c0+g,C),t0:min(t0+TB,NT)];n,rep,D=m.encode_k(A)
   if not np.array_equal(A,D):raise RuntimeError(('K decode',g,c0,t0))
   total+=n;parts+=1;reps[rep]=reps.get(rep,0)+1
 return total,reps,parts

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=fit_shared_ar(X);R,K=run_ar(X,co);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((name,me,eps))
   sz=0
   for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   ns=C*(NT-TRAIN);cand=[]
   for g in GROUPS:
    b,reps,parts=encode_grouped(K,g);cand.append({'channel_group':g,'bytes':b,'bps':8*b/ns,'gain_vs_sz3':sz/b,'parts':parts,'reps':reps})
    print(json.dumps({'region':name,'candidate':cand[-1]},indent=2),flush=True)
   cand.sort(key=lambda x:x['bytes']);base=[x for x in cand if x['channel_group']==128][0];best=cand[0]
   rows.append({'region':name,'c0':c0,'samples':ns,'sz3_bytes':sz,'sz3_bps':8*sz/ns,'baseline_128':base,'best':best,'gain_best_vs_baseline':base['bytes']/best['bytes'],'candidates':cand,'maxerr':me})
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'heldout':[TRAIN,NT],'groups':list(GROUPS),'rows':rows,'scope':'Real-byte backend factorization test on the exact current shared-AR32 step267 innovation K. The predictor/model and reconstruction are unchanged. Each heldout 128x1024 K frame is either encoded as one incumbent 128-channel frame or split into fixed contiguous channel stripes of width 1/2/4/8/16/32/64; each stripe independently runs the existing self-decoding encode_k representation menu. This lets entropy/representation selection adapt to stable channel heterogeneity without transmitting any learned context; every extra stripe pays the full existing frame overhead and byte-decodes to exact K. Shared AR32 model bytes are charged once, matched SZ3 is rerun on identical heldout tiles, and source hard error is verified. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_channel_striped_backend.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
