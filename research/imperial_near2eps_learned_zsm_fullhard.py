import json,sys
import h5py,numpy as np
import imperial_near2eps_full_hard_128x30000 as f
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

C=128;NT=30000;SCREEN=4096;WINDOWS=(4,8,64);FAC=1.99995;HEADER=48
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30
NZERO=9*9*6;NSIGN=3*3*6;NPREF=6*6*16;NSUFF=16*16*6
OFF_SIGN=NZERO;OFF_PREF=OFF_SIGN+NSIGN;OFF_SUFF=OFF_PREF+NPREF;NCTX=OFF_SUFF+NSUFF

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

def ac_state(sumabs,count):
 if count<=0:return 0
 z=2*int(sumabs)
 for i,q in enumerate((1,3,7,15,31)):
  if z<=q*count:return i
 return 5
def clip4(x):return int(max(-4,min(4,int(x))))+4
def sgncat(x):x=int(x);return 0 if x<0 else (2 if x>0 else 1)
def magbin(x):
 x=abs(int(x))
 if x==0:return 0
 if x==1:return 1
 if x==2:return 2
 if x<=4:return 3
 if x<=8:return 4
 return 5
def zero_ctx(prev,left,ac):return ((clip4(prev)*9+clip4(left))*6+ac)
def sign_ctx(prev,left,ac):return OFF_SIGN+((sgncat(prev)*3+sgncat(left))*6+ac)
def pref_ctx(prev,ac,qpos):return OFF_PREF+((magbin(prev)*6+ac)*16+min(qpos,15))
def suff_ctx(q,bitpos,ac):return OFF_SUFF+((min(q,15)*16+min(bitpos,15))*6+ac)

def encode_zsm(K,W,nt=None):
 if nt is None:nt=K.shape[1]
 E=AE(NCTX);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(nt):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;k=int(K[c,t])
   iz=1 if k==0 else 0;E.put(iz,zero_ctx(prev,left,ac))
   if not iz:
    E.put(1 if k<0 else 0,sign_ctx(prev,left,ac));mag=abs(k);q=mag.bit_length()-1
    for j in range(q):E.put(0,pref_ctx(prev,ac,j))
    E.put(1,pref_ctx(prev,ac,q));rem=mag-(1<<q)
    for bp in range(q-1,-1,-1):E.put((rem>>bp)&1,suff_ctx(q,q-1-bp,ac))
   old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return E.finish()

def decode_zsm(bb,nbit,W,shape):
 D=AD(bb,nbit,NCTX);K=np.zeros(shape,np.int32);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(shape[1]):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;iz=D.get(zero_ctx(prev,left,ac))
   if iz:k=0
   else:
    neg=D.get(sign_ctx(prev,left,ac));q=0
    while True:
     b=D.get(pref_ctx(prev,ac,q))
     if b:break
     q+=1
     if q>30:raise RuntimeError(('gamma overflow',c,t))
    rem=0
    for pos in range(q):rem=(rem<<1)|D.get(suff_ctx(q,pos,ac))
    mag=(1<<q)+rem;k=-mag if neg else mag
   K[c,t]=int(k);old=int(ring[c,rp]);new=abs(int(k));ring[c,rp]=new;sums[c]+=new-old
 return K

def build_full(X,eps):
 old=f.FAC;f.FAC=FAC
 try:return f.build(X,eps)
 finally:f.FAC=old

def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,f.C0:f.C0+C],np.float64).T
 h,Q,D,dts,dcs,co,intercept,changes,meanlegal=build_full(X,eps)
 mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
 dense=m.encode_k(np.ascontiguousarray(D,np.int32));dense_bytes=int(mb)+int(dense[0])+HEADER
 screens=[]
 for W in WINDOWS:
  bb,nb=encode_zsm(D,W,SCREEN);screens.append((len(bb),W,int(nb)))
 _,W,_=min(screens)
 bb,nbit=encode_zsm(D,W,NT);Dd=decode_zsm(bb,nbit,W,D.shape)
 if not np.array_equal(Dd,D):raise RuntimeError('ZSM defect decode')
 Qd=f.q_decode(Dd,ddt,ddc,dco,dinter,f.SCALE)
 if not np.array_equal(Qd,Q):raise RuntimeError('ZSM Q replay')
 me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
 zsm_bytes=int(mb)+len(bb)+HEADER+1
 hist_champion=2478995
 current_sz3=2767977
 out={'region':'hard','c0':f.C0,'shape':[C,NT],'samples':int(X.size),'global_std':std,'eps':eps,'hfac':FAC,'h':h,'mean_legal_states':meanlegal,'projection_changes':int(changes),'model_bytes':int(mb),'model_rep':mrep,'defect_zero_fraction':float(np.mean(D==0)),'defect_std':float(D.astype(np.float64).std()),'dense_bytes':dense_bytes,'dense_rep':dense[1],'zsm_bytes':zsm_bytes,'selected_window':int(W),'zsm_payload_bytes':len(bb),'zsm_arithmetic_bits':int(nbit),'screen_payload_bytes':{str(w):int(n) for n,w,_ in screens},'maxerr':me,'historical_huber_ar32_zsm_bytes':hist_champion,'gain_vs_historical_ar32_zsm':hist_champion/zsm_bytes,'current_matched_sz3_bytes':current_sz3,'gain_vs_current_sz3':current_sz3/zsm_bytes,'scope':'Exact composition test of the new near-2epsilon learned 20-tap causal generator with the historical PR482 zero/sign/Elias-gamma adaptive arithmetic language. The source object is the identical canonical c0=512 128x30000 hard block and unchanged survey-global epsilon. h=1.99995epsilon is public and fixed. The generator is learned/quantized exactly as in the full near-2epsilon audit and its model bytes are charged. The resulting signed defect field is screened at W=4/8/64 using only its first 4096 symbols, one selector byte is charged, then exactly one full ZSM stream is encoded and independently decoded using the original PR482 contexts. The decoded defects causally regenerate identical Q and source hard error is checked. The generic dense backend is also materialized as a control. Comparison to historical 2,478,995 B is same c0/shape/epsilon scope.'}
 json.dump(out,open('imperial_near2eps_learned_zsm_fullhard.json','w'),indent=2)
 print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
