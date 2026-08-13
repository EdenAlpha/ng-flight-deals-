import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP267=267;STEP2=536;TB=1024;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_int267(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP267));K[c,t]=k;R[c,t]=p+STEP267*k
 return R,K

def run_half(X,co,origin2):
 origin2=np.asarray(origin2,np.int32);R2=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Pred=np.zeros(X.shape,np.int32)
 a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  o=int(origin2[c])
  if (o&1)!=1:raise RuntimeError(('origin must be odd',c,o))
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R2[c,t-P:t][::-1].astype(np.float32)*np.float32(.5)))))
   d=int(2*int(X[c,t])-2*p-o);k=(d+268)//STEP2
   K[c,t]=k;Pred[c,t]=p;R2[c,t]=2*p+o+STEP2*k
 return R2,K,Pred

def densest_origin(e):
 s=np.sort(np.asarray(e,np.int64).ravel());n=len(s);bestn=-1;besti=0;j=0
 for i in range(n):
  if j<i:j=i
  while j+1<n and s[j+1]-s[i]<=267:j+=1
  nn=j-i+1
  if nn>bestn:
   bestn=nn;besti=i
 # center of the full legal 268-integer window [lo,lo+267]
 return int(2*int(s[besti])+267),int(bestn)

def choose_origins(E):
 O=np.empty(C,np.int32);mass=[]
 for c in range(C):
  O[c],n=densest_origin(E[c]);mass.append(n/E.shape[1])
 return O,float(np.mean(mass)),float(np.min(mass)),float(np.max(mass))

def origin_frame(O):
 n,D,dt=m.signed_blob(np.asarray(O,np.int32))
 if not np.array_equal(D,np.asarray(O,np.int32)):raise RuntimeError('origin decode')
 return n+12,dt

def payload(K):
 total=0;reps={}
 for t0 in range(0,NT,TB):
  n,rep,D=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
  if not np.array_equal(D,K[:,t0:t0+TB]):raise RuntimeError(('K decode',t0))
 return total,reps

def half_candidate(X,co,O,label,eps):
 R2,K,Pd=run_half(X,co,O);me=float(np.max(np.abs(2*X-R2.astype(np.float64))*.5))
 if me>eps*(1+1e-12):raise RuntimeError((label,'hard',me,eps))
 ob,odt=origin_frame(O);kb,reps=payload(K);total=MODEL_BYTES+ob+kb
 E=(X-Pd.astype(np.float64)).astype(np.int64)
 return {'mode':label,'bytes':int(total),'bps':float(8*total/X.size),'origin_bytes':int(ob),'origin_dtype':odt,'innovation_bytes':int(kb),'reps':reps,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'origin2_min':int(np.min(O)),'origin2_max':int(np.max(O)),'maxerr':me},E

def main(path):
 m.STEP=STEP267
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=fit_shared_ar(X)
   R,K=run_int267(X,co);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'int267',me,eps))
   kb,reps=payload(K);intb=MODEL_BYTES+kb
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
   common=np.ones(C,np.int32);c0row,Ecommon=half_candidate(X,co,common,'half268_common_origin_0p5',eps)
   # Prefix-only per-sensor origins: decoder receives them, but selection uses only t<1024 source residuals.
   Op,pm,pmin,pmax=choose_origins(Ecommon[:,:TRAIN]);prow,_=half_candidate(X,co,Op,'half268_perchannel_prefix_densest',eps);prow.update({'training_zero_window_mean':pm,'training_zero_window_min':pmin,'training_zero_window_max':pmax})
   # Target-adaptive coordinate descent is legal because the final 128 origins are explicitly transmitted and charged.
   O=common.copy();iters=[];best=None
   for it in range(4):
    rr,E=half_candidate(X,co,O,f'half268_perchannel_target_iter{it}',eps)
    rr['iter']=it;iters.append(rr)
    if best is None or rr['bytes']<best['bytes']:best=rr.copy()
    On,zm,zmin,zmax=choose_origins(E);iters[-1].update({'next_densest_mass_mean':zm,'next_densest_mass_min':zmin,'next_densest_mass_max':zmax})
    if np.array_equal(On,O):break
    O=On
   base={'mode':'int267','bytes':int(intb),'bps':float(8*intb/X.size),'innovation_bytes':int(kb),'reps':reps,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'maxerr':me}
   allc=[base,c0row,prow]+iters;allc.sort(key=lambda x:x['bytes']);winner=allc[0]
   for q in allc:q['gain_vs_sz3']=float(sz/q['bytes']);q['gain_vs_int267']=float(intb/q['bytes'])
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':int(sz),'sz3_bps':float(8*sz/X.size),'int267':base,'common_half268':c0row,'prefix_phase':prow,'target_phase_iters':iters,'best':winner}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'integer_step':STEP267,'halfgrid_step':268,'analysis_shape':[C,NT],'rows':rows,'scope':'Exact phase-freedom codec gate. Integer source values permit a half-integer reconstruction lattice with spacing 268 while keeping worst-case error 133.5 < epsilon. Unlike a single common origin, every sensor may use any odd doubled-unit origin (a half-integer) without changing that guarantee. One shared AR32+intercept is still fit only from t<1024. Prefix-only origins choose the densest legal 268-integer residual window per sensor from t<1024; a separate target-adaptive coordinate-descent variant may inspect the target but is fully legal because all 128 chosen origins are actually serialized/byte-decoded and charged before decoding. For every origin set, the decoder recursively predicts from its own half-integer state, exact innovation K frames are byte-decoded, all model/origin/framing bytes are counted, and matched SZ3 plus source max error are rerun. Target adaptation is not hidden training; only the transmitted origins carry it. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_perchannel_halfgrid_phase.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
