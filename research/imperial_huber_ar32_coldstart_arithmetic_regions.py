import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177
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
 def __init__(self,nctx):self.lo=0;self.hi=MAX;self.pending=0;self.o=BO();self.c=np.ones((nctx,2),np.int32)
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
 def finish(self):self.pending+=1;self.emit(0 if self.lo<Q1 else 1);return self.o.finish()
class AD:
 def __init__(self,d,n,nctx):
  self.lo=0;self.hi=MAX;self.i=BI(d,n);self.v=0;self.c=np.ones((nctx,2),np.int32)
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
def clip4(x):return int(max(-4,min(4,int(x))))+4
def design(X):
 n=C*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);j=0
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
 return A,y
def fits(X):
 A,y=design(X);ls=np.linalg.lstsq(A,y,rcond=None)[0];co=ls.copy()
 for _ in range(6):
  r=y-A@co;w=np.minimum(1.0,267.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 return np.asarray(ls,np.float32),np.asarray(co,np.float32)
def run_ar(X,co):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K
def decode_source(K,co):
 R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(K.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   R[c,t]=p+STEP*int(K[c,t])
 return R
