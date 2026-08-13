import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Pred=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   e=float(X[c,t])-p;k=int(np.rint(e/STEP));Pred[c,t]=p;K[c,t]=k;R[c,t]=p+STEP*k
 return R,K,Pred

def hard_ba(values,rad,maxiter=160,tol=1e-9):
 v=np.asarray(values,np.int64).ravel();xmin=int(v.min());xmax=int(v.max());n=(xmax-xmin)+2*rad+1
 cnt=np.bincount((v-xmin).astype(np.int64),minlength=xmax-xmin+1).astype(np.float64);p=cnt/cnt.sum();xidx=np.arange(rad,rad+len(p),dtype=np.int64)
 q=np.full(n,1.0/n,np.float64);yy=np.arange(n,dtype=np.int64);lo=np.maximum(yy-rad,0);hi=np.minimum(yy+rad+1,n);prev=None
 for it in range(maxiter):
  cs=np.empty(n+1,np.float64);cs[0]=0.;np.cumsum(q,out=cs[1:]);Z=cs[xidx+rad+1]-cs[xidx-rad]
  rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])));w=np.zeros(n,np.float64);w[xidx]=np.divide(p,Z,out=np.zeros_like(p),where=Z>0)
  ws=np.empty(n+1,np.float64);ws[0]=0.;np.cumsum(w,out=ws[1:]);qn=q*(ws[hi]-ws[lo]);qn/=qn.sum()
  if prev is not None and abs(rate-prev)<tol:q=qn;break
  prev=rate;q=qn
 cs=np.r_[0.,np.cumsum(q)];Z=cs[xidx+rad+1]-cs[xidx-rad];rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])))
 return rate,it+1

def grouped_ba(E,ctx,rad,label):
 e=np.asarray(E,np.int32).ravel();c=np.asarray(ctx,np.int64).ravel();u,inv,cnt=np.unique(c,return_inverse=True,return_counts=True);bits=0.;groups=[]
 for j,key in enumerate(u):
  vv=e[inv==j];r,it=hard_ba(vv,rad);bits+=len(vv)*r;groups.append({'ctx':int(key),'samples':int(len(vv)),'rate_bps':r,'iterations':it})
 rate=bits/len(e)
 return {'context':label,'rate_bps':float(rate),'contexts_seen':int(len(u)),'min_context_samples':int(cnt.min()),'max_context_samples':int(cnt.max()),'groups':groups if len(u)<=12 else None}

def clipk(A,r):return np.clip(np.asarray(A,np.int64),-r,r)+r

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rad=int(math.floor(eps));rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=fit_shared_ar(X);R,K,Pred=run_ar(X,co);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,me,eps))
   E=np.rint(X[:,TRAIN:]-Pred[:,TRAIN:].astype(np.float64)).astype(np.int32);prev=K[:,TRAIN-1:NT-1]
   base_r,it=hard_ba(E,rad);tests=[{'context':'none','rate_bps':base_r,'contexts_seen':1,'iterations':it}]
   # Previous innovation is decoder-known at zero side cost.
   for r in (1,2,4):tests.append(grouped_ba(E,clipk(prev,r),rad,f'prevK_clip{r}'))
   # Stable sensor identity, coarsened to avoid thousands of tiny oracle distributions.
   ch=np.broadcast_to(np.arange(C,dtype=np.int64)[:,None],E.shape)
   for g in (32,16,8):tests.append(grouped_ba(E,ch//g,rad,f'channel_group{g}'))
   # Combine stable sensor region with the strongest short causal state.
   for g,r in ((32,2),(16,2),(16,4)):
    ck=clipk(prev,r);ctx=(ch//g)*(2*r+1)+ck;tests.append(grouped_ba(E,ctx,rad,f'channel_group{g}+prevK_clip{r}'))
   # Causal current-left innovation: time-major decoder can know K[c-1,t]. Use sentinel for c=0.
   left=np.empty_like(K[:,TRAIN:],np.int64);left[0]=-999;left[1:]=K[:-1,TRAIN:]
   own2=clipk(prev,2);left2=np.where(left==-999,5,clipk(left,2));ctx=own2*6+left2;tests.append(grouped_ba(E,ctx,rad,'prevK_clip2+left_current_clip2'))
   tests.sort(key=lambda x:x['rate_bps']);sz=0
   for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
   ns=E.size;szbps=8*sz/ns;target=szbps/2
   for q in tests:q['saving_vs_marginal_bps']=float(base_r-q['rate_bps']);q['over_2x_target']=float(q['rate_bps']/target)
   row={'region':region,'c0':c0,'samples':int(ns),'eps':eps,'integer_radius':rad,'marginal_hardbox_ba_bps':base_r,'matched_sz3_bps':szbps,'two_x_target_bps':target,'best':tests[0],'tests':tests,'maxerr':me}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'integer_radius':rad,'ar_order':P,'step':STEP,'heldout':[TRAIN,NT],'rows':rows,'scope':'Optimistic decoder-context hard-box information audit, not a compression claim or process-level impossibility theorem. The current shared AR32 model is fit only from t<1024 and the exact recursive step267 predictor/residual is replayed. On heldout residual E=X-P, zero-distortion Blahut-Arimoto under |E-Y|<=floor(epsilon) is solved separately inside decoder-known context classes: previous K, fixed channel groups, their combinations, and causal current-left K. Context IDs themselves cost zero because the decoder already knows them; additionally, each context is allowed its own TARGET-ADAPTIVE reproduction law without charging model transmission, making these deliberately optimistic lower-rate diagnostics. If even this favorable conditional hard-box rate remains far above half of matched SZ3, simple context-dependent scalar/vector-covering explanations cannot supply the missing 2x. No AI. Do not merge.'}
 json.dump(out,open('imperial_ar32_conditional_hardbox_ba.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
