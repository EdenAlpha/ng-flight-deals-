import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024
REGIONS=(('hard',512),('easy',2304))
BANK=((1,0),(2,0),(3,0),(4,0),(6,0),(8,0),(12,0),(16,0),(24,0),(32,0),(48,0),(64,0),
      (0,-1),(0,-2),(0,-4),(0,-8),(1,-1),(1,1),(1,-2),(1,2),(1,-4),(1,4),(1,-8),(1,8),
      (2,-1),(2,1),(2,-2),(2,2),(4,-1),(4,1))
SIZES=(8,16,30);STRENGTHS=(0.25,0.5,1.0);CLIP_K=4.0

def shift_field(K,dt,dc,t0,t1):
 out=np.zeros((C,t1-t0),np.float64)
 for j,t in enumerate(range(t0,t1)):
  s=t-dt
  if s<0:continue
  if dc<0:out[-dc:,j]=K[:C+dc,s]
  elif dc>0:out[:C-dc,j]=K[dc:,s]
  else:out[:,j]=K[:,s]
 return out

def robust_fit(A,y):
 lam=1e-2;G=A.T@A+lam*np.eye(A.shape[1]);rhs=A.T@y;co=np.linalg.solve(G,rhs)
 for _ in range(5):
  r=y-A@co;sc=1.4826*np.median(np.abs(r-np.median(r)))+1e-6;w=np.minimum(1.0,(1.5*sc)/np.maximum(np.abs(r),1e-12))
  co=np.linalg.solve(A.T@(A*w[:,None])+lam*np.eye(A.shape[1]),A.T@(y*w))
 return co

def fit_models(X,Rb,Kb):
 t0=P;t1=TRAIN;pred=Rb[:,t0:t1].astype(np.float64)-STEP*Kb[:,t0:t1].astype(np.float64);y=((X[:,t0:t1]-pred)/STEP).ravel(order='F')
 A=np.column_stack([shift_field(Kb,dt,dc,t0,t1).ravel(order='F') for dt,dc in BANK]);co=robust_fit(A,y);score=np.abs(co)*np.std(A,axis=0);order=np.argsort(score)[::-1];models=[]
 for n in SIZES:
  ids=np.sort(order[:n]);As=A[:,ids];cs=robust_fit(As,y).astype(np.float32);models.append((ids.astype(np.uint8),cs,float(np.sqrt(np.mean((y-As@cs.astype(np.float64))**2)))))
 return models

def shifted_vec(K,t,dt,dc):
 v=np.zeros(C,np.float64);s=t-dt
 if s<0:return v
 if dc<0:v[-dc:]=K[:C+dc,s]
 elif dc>0:v[:C-dc]=K[dc:,s]
 else:v[:]=K[:,s]
 return v

def corr_k(K,t,c,lag,same,co,strength,base):
 s=base[c]
 for j,(dt,dc) in same:
  cc=c+dc
  if 0<=cc<C:s+=float(co[j])*float(K[cc,t])
 return float(np.clip(strength*s,-CLIP_K,CLIP_K))

def run_model(X,arco,ids,co,strength):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a0=float(arco[0]);b=np.asarray(arco[1:],np.float32);taps=[BANK[int(i)] for i in ids];lag=[(j,tap) for j,tap in enumerate(taps) if tap[0]>0];same=[(j,tap) for j,tap in enumerate(taps) if tap[0]==0]
 for t in range(NT):
  tp=np.zeros(C,np.int32) if t<P else np.rint(a0+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32);base=np.zeros(C,np.float64)
  if t>=TRAIN:
   for j,(dt,dc) in lag:base+=float(co[j])*shifted_vec(K,t,dt,dc)
  for c in range(C):
   ck=0.0 if t<TRAIN else corr_k(K,t,c,lag,same,co,strength,base);pred=int(tp[c])+int(np.rint(STEP*ck));k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;R[c,t]=pred+STEP*k
 return R,K

def decode_model(K,arco,ids,co,strength):
 R=np.zeros(K.shape,np.int32);a0=float(arco[0]);b=np.asarray(arco[1:],np.float32);taps=[BANK[int(i)] for i in ids];lag=[(j,tap) for j,tap in enumerate(taps) if tap[0]>0];same=[(j,tap) for j,tap in enumerate(taps) if tap[0]==0]
 for t in range(K.shape[1]):
  tp=np.zeros(K.shape[0],np.int32) if t<P else np.rint(a0+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32);base=np.zeros(K.shape[0],np.float64)
  if t>=TRAIN:
   for j,(dt,dc) in lag:base+=float(co[j])*shifted_vec(K,t,dt,dc)
  for c in range(K.shape[0]):
   ck=0.0 if t<TRAIN else corr_k(K,t,c,lag,same,co,strength,base);pred=int(tp[c])+int(np.rint(STEP*ck));R[c,t]=pred+STEP*int(K[c,t])
 return R

def backend(K,extra):
 n=a.MODEL_BYTES+extra
 for t0 in range(0,NT,TB):
  z,rep,D=a.m.encode_k(K[:,t0:t0+TB]);
  if not np.array_equal(D,K[:,t0:t0+TB]):raise RuntimeError(('backend',t0))
  n+=int(z)
 return n

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu);base_bytes,_,_,Kbd=a.arithmetic(Kb)
   if not np.array_equal(a.decode_source(Kbd,hu),Rb):raise RuntimeError((region,'base decode'))
   models=fit_models(X,Rb,Kb);screen=[]
   for ids,co,trmse in models:
    extra=18+5*len(ids)
    for strength in STRENGTHS:
     R,K=run_model(X,hu,ids,co,strength);me=float(np.max(np.abs(X-R.astype(np.float64))))
     if me>eps*(1+1e-12):raise RuntimeError((region,'hard',len(ids),strength,me,eps))
     bb=backend(K,extra);screen.append({'taps':len(ids),'strength':strength,'ids':ids,'co':co,'train_rmse_k':trmse,'backend_bytes':bb,'backend_bps':8*bb/X.size,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'_K':K,'_R':R})
   best=min(screen,key=lambda q:q['backend_bytes']);extra=18+5*best['taps'];cab,bits,nb,Kd=a.arithmetic(best['_K']);cab+=extra;Rd=decode_model(Kd,hu,best['ids'],best['co'],best['strength'])
   if not np.array_equal(Rd,best['_R']):raise RuntimeError((region,'replay'))
   me=float(np.max(np.abs(X-Rd.astype(np.float64))));sz=0
   for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
   clean=[]
   for q in screen:
    clean.append({k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in q.items() if not k.startswith('_') and k not in ('ids','co')}|{'tap_ids':[int(i) for i in q['ids']],'tap_offsets':[list(BANK[int(i)]) for i in q['ids']]})
   row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base_bytes),'baseline_bps':8*base_bytes/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':{'taps':best['taps'],'strength':best['strength'],'bytes':int(cab),'bps':8*cab/X.size,'gain_vs_arithmetic':base_bytes/cab,'gain_vs_sz3':sz/cab,'backend_bytes':best['backend_bytes'],'k_zero_fraction':best['k_zero_fraction'],'k_std':best['k_std'],'maxerr':me,'tap_ids':[int(i) for i in best['ids']],'tap_offsets':[list(BANK[int(i)]) for i in best['ids']]},'screen':clean};rows.append(row);print(json.dumps(row,indent=2),flush=True)
  json.dump({'global_std':gstd,'eps':eps,'step':STEP,'train':TRAIN,'clip_k':CLIP_K,'strengths':list(STRENGTHS),'rows':rows,'scope':'Stabilized nonlocal residual-stencil fast gate. Prefix-trained 8/16/30-tap K corrections reach 64 samples and +/-8 channels, but their decoder-real correction is multiplicatively shrunk and hard-clipped to +/-4 innovation units before being added to Huber AR32, preventing recursive blow-up. Hard/easy only. All candidates are screened with exact byte-decoded incumbent backend; only the best per region pays a full cold-start arithmetic rerun. Selected tap IDs/coefficients/framing are charged, exact K and source replay are verified, and max error is unchanged. No AI.'},open('imperial_ar32_nonlocal_residual_stencil.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
