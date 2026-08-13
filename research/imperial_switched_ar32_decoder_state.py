import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
SCHEMES=('clip1','clip2','mag7','group32_clip1')
C=128;NT=8192;P=32;STEP=267;TB=1024

def ctx(scheme,c,k):
 k=int(k)
 if scheme=='clip1':return max(-1,min(1,k))+1
 if scheme=='clip2':return max(-2,min(2,k))+2
 if scheme=='mag7':
  if k==0:return 0
  if k==1:return 1
  if k==-1:return 2
  if 2<=k<=4:return 3
  if -4<=k<=-2:return 4
  if k>4:return 5
  return 6
 if scheme=='group32_clip1':return (c//32)*3+(max(-1,min(1,k))+1)
 raise ValueError(scheme)
def nctx(s):return {'clip1':3,'clip2':5,'mag7':7,'group32_clip1':12}[s]

def fit_plain_prefix(X):
 A=[];y=[]
 for c in range(C):
  x=np.asarray(X[c,:1024],np.float64)
  for t in range(P,1024):A.append(np.r_[1.,x[t-P:t][::-1]]);y.append(x[t])
 return np.linalg.lstsq(np.asarray(A,np.float64),np.asarray(y,np.float64),rcond=None)[0].astype(np.float32)

def run_plain(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def fit_switched(X,R,K,scheme):
 nc=nctx(scheme);G=np.zeros((nc,P+1,P+1),np.float64);v=np.zeros((nc,P+1),np.float64);cnt=np.zeros(nc,np.int64)
 for c in range(C):
  H=np.lib.stride_tricks.sliding_window_view(R[c],P)[:-1][:,::-1].astype(np.float64) # row t=P..NT-1
  Y=X[c,P:].astype(np.float64);prev=K[c,P-1:NT-1]
  ids=np.asarray([ctx(scheme,c,q) for q in prev],np.int32)
  for j in range(nc):
   mask=ids==j
   if not np.any(mask):continue
   Z=np.empty((int(mask.sum()),P+1),np.float64);Z[:,0]=1.;Z[:,1:]=H[mask];yy=Y[mask]
   G[j]+=Z.T@Z;v[j]+=Z.T@yy;cnt[j]+=len(yy)
 co=np.zeros((nc,P+1),np.float32)
 # A tiny ridge is only numerical stabilization; all resulting float32 coefficients are transmitted.
 for j in range(nc):
  if cnt[j]<P+2:continue
  ridge=max(1e-8,float(np.trace(G[j]))/(P+1)*1e-10);M=G[j].copy();M.flat[::P+2]+=ridge
  co[j]=np.linalg.solve(M,v[j]).astype(np.float32)
 return co,cnt

def run_switched(X,co,scheme):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for c in range(C):
  for t in range(NT):
   pv=int(K[c,t-1]) if t>0 else 0;j=ctx(scheme,c,pv);cc=co[j]
   p=0 if t<P else int(np.rint(float(cc[0])+float(np.dot(cc[1:],R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def payload(K,model_bytes):
 total=model_bytes;reps={}
 for t0 in range(0,NT,TB):
  n,rep,D=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
  if not np.array_equal(D,K[:,t0:t0+TB]):raise RuntimeError(('K decode',t0))
 return total,reps

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;baseco=fit_plain_prefix(X);R0,K0=run_plain(X,baseco);me=float(np.max(np.abs(X-R0.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'base hard',me,eps))
   base_mb=4*len(baseco)+45;baseb,basereps=payload(K0,base_mb);sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
   cand=[]
   for scheme in SCHEMES:
    R=R0;K=K0;best=None
    for it in range(3):
     co,cnt=fit_switched(X,R,K,scheme);raw=np.asarray(co,'<f4').tobytes();cd=np.frombuffer(raw,'<f4').reshape(co.shape).copy();Rn,Kn=run_switched(X,cd,scheme);err=float(np.max(np.abs(X-Rn.astype(np.float64))))
     if err>eps*(1+1e-12):raise RuntimeError((region,scheme,it,'hard',err,eps))
     mb=len(raw)+64;b,reps=payload(Kn,mb);q={'scheme':scheme,'iter':it,'contexts':nctx(scheme),'model_bytes':mb,'bytes':b,'bps':8*b/X.size,'gain_vs_plain_ar32':baseb/b,'gain_vs_sz3':sz/b,'k_zero_fraction':float(np.mean(Kn==0)),'k_std':float(Kn.std()),'context_counts':[int(x) for x in cnt],'reps':reps,'maxerr':err};cand.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True);R,K=Rn,Kn
   cand.sort(key=lambda x:x['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'plain_ar32':{'bytes':baseb,'bps':8*baseb/X.size,'gain_vs_sz3':sz/baseb,'model_bytes':base_mb,'reps':basereps,'maxerr':me},'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':cand[0],'candidates':cand};rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'shape':[C,NT],'schemes':list(SCHEMES),'rows':rows,'scope':'Real-byte switched nonlinear source-model gate. The control is the current shared AR32 fit from t<1024. Candidate codecs use several separately transmitted AR32+intercept laws selected at each sample by decoder-known state: clipped previous innovation, a seven-state signed magnitude class, or sensor-group32 plus clipped previous innovation. Starting from the control trajectory, deterministic coordinate iterations refit each context law on the target source using the current decoder reconstruction/state, then replay the complete codec. This target adaptation is fully legal because every final float32 coefficient of every state law is serialized/byte-decoded and charged; fixed context rules need no side information. Exact step267 K frames byte-decode, reconstructed state drives future contexts, source hard error is verified, and matched SZ3 is rerun identically. Purpose: test whether Imperial contains nonlinear regime-dependent dynamics that one global AR32 law averages away. No AI. Draft/do not merge.'};json.dump(out,open('imperial_switched_ar32_decoder_state.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
