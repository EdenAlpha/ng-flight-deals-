import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_decoder_phase_automaton as m

C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024
SPECS=(('hard',512),('easy',2304));GROUPS=(4,8,16,32,64,128)
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def fit_one(X):
 n=X.shape[0]*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);q=0
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):A[q,0]=1.;A[q,1:]=x[t-P:t][::-1];y[q]=x[t];q+=1
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 for _ in range(6):
  r=y-A@co;w=np.minimum(1.0,267.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 return np.asarray(co,np.float32)

def fit_groups(X,g):
 B=np.stack([fit_one(X[c:c+g]) for c in range(0,C,g)]).astype(np.float32);raw=B.astype('<f4').tobytes();bb=Z.compress(raw);Bd=np.frombuffer(D.decompress(bb),'<f4').reshape(B.shape).copy()
 if not np.array_equal(Bd,B):raise RuntimeError('model decode')
 return Bd,len(bb)+32

def run(X,B,g):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for c in range(C):
  co=B[c//g];a=float(co[0]);b=co[1:]
  for t in range(NT):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def decode(K,B,g):
 R=np.zeros(K.shape,np.int32)
 for c in range(C):
  co=B[c//g];a=float(co[0]);b=co[1:]
  for t in range(K.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   R[c,t]=p+STEP*int(K[c,t])
 return R

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,shared=h.fits(X);R0,K0=h.run_ar(X,shared);base,_,_,D0=h.arithmetic(K0)
   if not np.array_equal(h.decode_source(D0,shared),R0):raise RuntimeError('base decode')
   sz=sum(int(m.szrun(X[:,t:t+TB],eps)[0]) for t in range(0,NT,TB));cand=[];keep={}
   for g in GROUPS:
    B,model=fit_groups(X,g);R,K=run(X,B,g);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,g,'hard',me,eps))
    n,reps=h.backend_bytes(K);n=n-h.MODEL_BYTES+model;z={'group_channels':g,'models':C//g,'backend_bytes':int(n),'backend_bps':8*n/X.size,'model_bytes':model,'gain_backend_vs_shared':None,'gain_backend_vs_sz3':sz/n,'k_std':float(K.std()),'k_zero':float(np.mean(K==0)),'maxerr':me,'reps':reps};cand.append(z);keep[g]=(B,R,K);print(json.dumps({'region':region,**{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
   b=min(cand,key=lambda z:z['backend_bytes']);B,R,K=keep[b['group_channels']];an,bits,nb,Kd=h.arithmetic(K);an=an-h.MODEL_BYTES+b['model_bytes'];Rd=decode(Kd,B,b['group_channels']);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,'decode',me,eps))
   best={'group_channels':b['group_channels'],'models':b['models'],'bytes':int(an),'bps':8*an/X.size,'model_bytes':b['model_bytes'],'gain_vs_shared_arithmetic':base/an,'gain_vs_sz3':sz/an,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me};rows.append({'region':region,'shared_bytes':int(base),'shared_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'screen':cand});print(json.dumps({'summary':region,'best':best},indent=2),flush=True)
  json.dump({'eps':eps,'group_sizes':list(GROUPS),'rows':rows},open('imperial_huber_ar32_model_granularity.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
