import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;MODEL_BYTES=177
MODES=('channel_prev4','prev4_left4','channel_prev4_signleft')
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30

class BO:
 def __init__(self):self.a=[]
 def put(self,b):self.a.append(int(b))
 def finish(self):
  z=bytearray((len(self.a)+7)//8)
  for i,b in enumerate(self.a):
   if b:z[i>>3]|=1<<(7-(i&7))
  return bytes(z),len(self.a)
class BI:
 def __init__(self,d,n):self.d=d;self.n=n;self.i=0
 def get(self):
  if self.i>=self.n:return 0
  b=(self.d[self.i>>3]>>(7-(self.i&7)))&1;self.i+=1;return b
class AE:
 def __init__(self,nctx,counts=None):
  self.lo=0;self.hi=MAX;self.pending=0;self.o=BO();self.c=np.ones((nctx,2),np.int32) if counts is None else counts.copy()
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending):self.o.put(1-b)
  self.pending=0
 def put(self,b,ctx):
  c0=int(self.c[ctx,0]);c1=int(self.c[ctx,1]);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if b==0:self.hi=sp
  else:self.lo=sp+1
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1
  self.c[ctx,b]+=1
  if int(self.c[ctx].sum())>16384:self.c[ctx]=(self.c[ctx]+1)//2
 def finish(self):
  self.pending+=1
  if self.lo<Q1:self.emit(0)
  else:self.emit(1)
  return self.o.finish()
class AD:
 def __init__(self,d,n,nctx,counts):
  self.lo=0;self.hi=MAX;self.i=BI(d,n);self.v=0;self.c=counts.copy()
  for _ in range(32):self.v=((self.v<<1)&MAX)|self.i.get()
 def get(self,ctx):
  c0=int(self.c[ctx,0]);c1=int(self.c[ctx,1]);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if self.v<=sp:b=0;self.hi=sp
  else:b=1;self.lo=sp+1
  while True:
   if self.hi<HALF:pass
   elif self.lo>=HALF:self.lo-=HALF;self.hi-=HALF;self.v-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.lo-=Q1;self.hi-=Q1;self.v-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1;self.v=((self.v<<1)&MAX)|self.i.get()
  self.c[ctx,b]+=1
  if int(self.c[ctx].sum())>16384:self.c[ctx]=(self.c[ctx]+1)//2
  return b

def zig(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzig(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)
def clip4(x):return int(max(-4,min(4,int(x))))+4

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def build_k(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def decode_source(K,coef):
 R=np.zeros(K.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(C):
  for t in range(K.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   R[c,t]=p+STEP*int(K[c,t])
 return R

def nctx(mode,nb):
 if mode=='channel_prev4':return C*9*nb*4
 if mode=='prev4_left4':return 9*9*nb*4
 if mode=='channel_prev4_signleft':return C*9*3*nb*4
 raise ValueError(mode)
def ctxid(mode,c,prev,left,bitpos,prefix2,nb):
 pv=clip4(prev);lv=clip4(left);ls=0 if left==0 else (1 if left>0 else 2)
 if mode=='channel_prev4':base=c*9+pv;B=C*9
 elif mode=='prev4_left4':base=pv*9+lv;B=81
 elif mode=='channel_prev4_signleft':base=(c*9+pv)*3+ls;B=C*9*3
 else:raise ValueError(mode)
 return ((base*nb+bitpos)*4+prefix2)

def seed_counts(Kprefix,mode,nb):
 counts=np.ones((nctx(mode,nb),2),np.int32);u=zig(Kprefix)
 for t in range(Kprefix.shape[1]):
  for c in range(C):
   prev=int(Kprefix[c,t-1]) if t>0 else 0;left=int(Kprefix[c-1,t]) if c>0 else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=ctxid(mode,c,prev,left,pos,pref,nb);counts[cx,b]+=1;pref=((pref<<1)|b)&3
 return counts

def arithmetic_heldout(K,mode,nb):
 init=seed_counts(K[:,:TRAIN],mode,nb);enc=AE(nctx(mode,nb),init);u=zig(K)
 for t in range(TRAIN,K.shape[1]):
  for c in range(C):
   prev=int(K[c,t-1]);left=int(K[c-1,t]) if c>0 else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=ctxid(mode,c,prev,left,pos,pref,nb);enc.put(b,cx);pref=((pref<<1)|b)&3
 bb,nbit=enc.finish()
 # Exact decoder starts with already-decoded prefix.
 Kd=np.zeros_like(K);Kd[:,:TRAIN]=K[:,:TRAIN];ud=np.zeros(K.shape,np.uint64);ud[:,:TRAIN]=u[:,:TRAIN]
 dec=AD(bb,nbit,nctx(mode,nb),init)
 for t in range(TRAIN,K.shape[1]):
  for c in range(C):
   prev=int(Kd[c,t-1]);left=int(Kd[c-1,t]) if c>0 else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=ctxid(mode,c,prev,left,pos,pref,nb);b=dec.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
   ud[c,t]=val;Kd[c,t]=int(unzig(np.asarray([val],np.uint64))[0])
 if not np.array_equal(Kd,K):raise RuntimeError(('arith decode',mode))
 return len(bb)+16,nbit,Kd

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K=build_k(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,me,eps))
   # Prefix is a normal incumbent frame and fully decoded before adaptive arithmetic starts.
   pn,prep,Kp=m.encode_k(K[:,:TRAIN]);
   if not np.array_equal(Kp,K[:,:TRAIN]):raise RuntimeError('prefix decode')
   actual=MODEL_BYTES
   for t0 in range(0,NT,1024):n,_,D=m.encode_k(K[:,t0:t0+1024]);actual+=n
   umax=int(zig(K).max());nb=max(1,umax.bit_length());cand=[]
   for mode in MODES:
    ab,nbit,Kd=arithmetic_heldout(K,mode,nb);total=MODEL_BYTES+pn+ab+32
    Rd=decode_source(Kd,coef);err=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if err>eps*(1+1e-12):raise RuntimeError((region,mode,'hard',err))
    cand.append({'mode':mode,'bytes':total,'bps':8*total/X.size,'gain_vs_incumbent':actual/total,'arithmetic_bytes':ab,'arithmetic_bits':nbit,'prefix_bytes':pn,'nbits_per_symbol':nb,'maxerr':err})
   cand.sort(key=lambda x:x['bytes']);sz=0
   for t0 in range(0,NT,1024):b,_=m.szrun(X[:,t0:t0+1024],eps);sz+=b
   for x in cand:x['gain_vs_sz3']=sz/x['bytes']
   row={'region':region,'c0':c0,'samples':int(X.size),'incumbent_bytes':actual,'incumbent_bps':8*actual/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':cand[0],'candidates':cand,'maxerr':me}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'modes':list(MODES),'rows':rows,'scope':'Real self-decoding arithmetic backend on the exact shared-AR32 step267 innovation field, motivated by PR #382 oracle H(K|channel,prev) headroom. One ordinary prefix frame t<1024 is first encoded/decoded, then its exact K deterministically seeds adaptive binary counts. Held-out symbols are coded symbol-major MSB-to-LSB so previous-time and current-left full innovations are decoder-known. Contexts use channel identity, clipped previous K, optional current-left magnitude/sign, bit position and two higher current bits. No probability tables are transmitted; counts update identically online. Arithmetic bytes, prefix/model/framing bytes are charged, exact K is decoded, the complete AR32 source trajectory is regenerated, hard error checked and matched SZ3 rerun. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_channel_prev_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
