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
 def finish(self):
  self.pending+=1
  self.emit(0 if self.lo<Q1 else 1)
  return self.o.finish()
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

def zig(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzig(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)
def clip4(x):return int(max(-4,min(4,int(x))))+4
def ctx(prev,left,bitpos,prefix2,nb):return (((clip4(prev)*9+clip4(left))*nb+bitpos)*4+prefix2)
def nctx(nb):return 9*9*nb*4

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
  for t in range(NT):
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

def backend_bytes(K):
 total=MODEL_BYTES;reps={}
 for t0 in range(0,NT,TB):
  A=K[:,t0:t0+TB];n,rep,D=m.encode_k(A)
  if not np.array_equal(A,D):raise RuntimeError(('backend decode',t0))
  total+=n;reps[rep]=reps.get(rep,0)+1
 return total,reps

def arithmetic(K):
 u=zig(K);nb=max(1,int(u.max()).bit_length());E=AE(nctx(nb))
 for t in range(NT):
  for c in range(C):
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=ctx(prev,left,pos,pref,nb);E.put(b,cx);pref=((pref<<1)|b)&3
 bb,nbit=E.finish();D=AD(bb,nbit,nctx(nb));Kd=np.zeros_like(K)
 for t in range(NT):
  for c in range(C):
   prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=ctx(prev,left,pos,pref,nb);b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
   Kd[c,t]=int(unzig(np.asarray([val],np.uint64))[0])
 if not np.array_equal(Kd,K):raise RuntimeError('arithmetic K decode')
 return len(bb)+MODEL_BYTES+32,nbit,nb,Kd

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;ls,hu=fits(X);Rls,Kls=run_ar(X,ls);Rh,Kh=run_ar(X,hu)
   for label,R in [('ls',Rls),('huber',Rh)]:
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,label,'hard',me,eps))
   lsb,lsrep=backend_bytes(Kls);hub,hrep=backend_bytes(Kh);cab,nbit,nb,Kd=arithmetic(Kh);Rd=decode_source(Kd,hu);cme=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if cme>eps*(1+1e-12):raise RuntimeError((region,'candidate hard',cme,eps))
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
        'ls_ar32':{'bytes':lsb,'bps':8*lsb/X.size,'gain_vs_sz3':sz/lsb,'reps':lsrep},
        'huber_ar32':{'bytes':hub,'bps':8*hub/X.size,'gain_vs_ls':lsb/hub,'gain_vs_sz3':sz/hub,'reps':hrep},
        'huber_coldstart_arithmetic':{'bytes':cab,'bps':8*cab/X.size,'gain_vs_ls':lsb/cab,'gain_vs_huber_backend':hub/cab,'gain_vs_sz3':sz/cab,'arithmetic_bits':nbit,'symbol_bits':nb,'maxerr':cme}}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'rows':rows,'scope':'Promotion gate stacking two independently positive real mechanisms: prefix-only Huber267 IRLS fitting for shared AR32 and a cold-start exact adaptive arithmetic backend on the complete K stream. No K seed/probability model is transmitted: unit priors are fixed, and both encoder/decoder update contexts online from already decoded previous-time and current-left innovations. AR coefficients, arithmetic framing/bit length and stream bytes are charged; exact K is decoded, the full recursive source is regenerated and hard-error checked. Ordinary LS AR32, Huber AR32 with incumbent backend and matched SZ3 are rerun on identical complete 128x8192 hard/easy/medium/far regions. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_huber_ar32_coldstart_arithmetic_regions.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
