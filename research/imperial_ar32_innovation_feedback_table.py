import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
SCHEMES=(('prev2',128,2),('group32_prev2',32,2),('group16_prev2',16,2),('group16_prev4',16,4))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def ctx_id(c,prev,g,r):
 q=max(-r,min(r,int(prev)))+r
 return (c//g)*(2*r+1)+q

def nctx(g,r):return ((C+g-1)//g)*(2*r+1)

def run(X,co,g,r,tab):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Ebase=np.zeros(X.shape,np.int32);CTX=np.zeros(X.shape,np.int32)
 a=float(co[0]);b=np.asarray(co[1:],np.float32);tab=np.asarray(tab,np.int32)
 for c in range(C):
  for t in range(NT):
   base=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   prev=int(K[c,t-1]) if t>0 else 0;ci=ctx_id(c,prev,g,r);corr=int(tab[ci]);p=base+corr
   e=int(X[c,t])-p;k=int(np.rint(e/STEP));K[c,t]=k;R[c,t]=p+STEP*k;Ebase[c,t]=int(X[c,t])-base;CTX[c,t]=ci
 return R,K,Ebase,CTX

def learn(Ebase,CTX,n):
 tab=np.zeros(n,np.int32);counts=np.zeros(n,np.int64)
 e=np.asarray(Ebase,np.int32).ravel();c=np.asarray(CTX,np.int32).ravel()
 for j in range(n):
  v=e[c==j];counts[j]=len(v)
  if len(v):tab[j]=int(np.rint(np.median(v)))
 return tab,counts

def table_bytes(tab):
 n,D,dt=m.signed_blob(np.asarray(tab,np.int32))
 if not np.array_equal(D,np.asarray(tab,np.int32)):raise RuntimeError('table decode')
 return n+16,dt

def payload(K):
 total=0;reps={}
 for t0 in range(0,NT,TB):
  n,rep,D=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
  if not np.array_equal(D,K[:,t0:t0+TB]):raise RuntimeError(('K decode',t0))
 return total,reps

def score(X,R,K,tab,eps,label):
 me=float(np.max(np.abs(X-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError((label,'hard',me,eps))
 kb,reps=payload(K);tb,dt=table_bytes(tab);total=MODEL_BYTES+tb+kb
 return {'mode':label,'bytes':int(total),'bps':float(8*total/X.size),'innovation_bytes':int(kb),'feedback_table_bytes':int(tb),'feedback_dtype':dt,'table_entries':int(len(tab)),'table_min':int(np.min(tab)),'table_max':int(np.max(tab)),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'reps':reps,'maxerr':me}

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int32).T;co=fit_shared_ar(X)
   # Exact zero-feedback baseline, using the prev2 context only for bookkeeping.
   z=np.zeros(nctx(128,2),np.int32);R0,K0,E0,C0=run(X,co,128,2,z);base=score(X,R0,K0,z,eps,'ar32_zero_feedback')
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
   cand=[base]
   for name,g,r in SCHEMES:
    # Build the first correction table from the source under the ordinary decoder-real AR32 path.
    # This is legal target adaptation because every final table entry is transmitted and charged.
    zz=np.zeros(nctx(g,r),np.int32);Rb,Kb,Eb,Cb=run(X,co,g,r,zz);tab,cnt=learn(Eb,Cb,nctx(g,r))
    best=None
    for it in range(3):
     R,K,E,CX=run(X,co,g,r,tab);q=score(X,R,K,tab,eps,f'{name}_iter{it}');q.update({'scheme':name,'group':g,'clip':r,'iter':it,'min_context_count':int(cnt.min()),'max_context_count':int(cnt.max())})
     cand.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
     nt,nc=learn(E,CX,nctx(g,r));cnt=nc
     if np.array_equal(nt,tab):break
     tab=nt
   
   cand.sort(key=lambda x:x['bytes']);best=cand[0]
   for q in cand:q['gain_vs_sz3']=float(sz/q['bytes']);q['gain_vs_zero_feedback']=float(base['bytes']/q['bytes'])
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':int(sz),'sz3_bps':float(8*sz/X.size),'baseline':base,'best':best,'candidates':cand};rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'shape':[C,NT],'schemes':[list(x) for x in SCHEMES],'rows':rows,'scope':'Real-byte nonlinear predictor correction gate. The shared AR32+intercept is fit only from t<1024. At each sample the decoder already knows the same-channel previous innovation K and sensor group, so a small transmitted integer table can add a context-dependent correction to the ordinary AR32 prediction before exact step267 quantization. Tables for previous-K clip2 and channel-group32/16 combined with clipped previous K are learned by deterministic target-adaptive median coordinate iterations; this is legal rather than hidden oracle information because every final correction entry is actually compressed, byte-decoded and fully charged. The corrected reconstruction drives future AR state, exact K frames byte-decode, source hard error is checked, and matched SZ3 is rerun identically. Purpose: turn the residual conditional dependence from PR #382 into source-model gain rather than only backend probability gain. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_innovation_feedback_table.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
