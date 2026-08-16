import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_resonant_learned_law_address as g
q.f.q_decode=sc.q_decode
C=128;NT=30000;SCREEN=4096;WINDOWS=(4,8,64);STRENGTHS=(2,4,8,16,32,64)
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30;NG=284
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
class BE:
 def __init__(self,S):self.S=S;self.lo=0;self.hi=MAX;self.pending=0;self.o=BO();self.l=np.zeros((q.NCTX,2),np.int32);self.g=np.ones((NG,2),np.int32)
 def counts(self,cx,gid):
  a=int(self.g[gid,0]);b=int(self.g[gid,1]);tot=a+b;p0=max(1,(self.S*a+tot//2)//tot);p1=max(1,(self.S*b+tot//2)//tot);return int(self.l[cx,0])+p0,int(self.l[cx,1])+p1
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending):self.o.put(1-b)
  self.pending=0
 def put(self,b,cx,gid):
  c0,c1=self.counts(cx,gid);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if b==0:self.hi=sp
  else:self.lo=sp+1
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1
  self.l[cx,b]+=1;self.g[gid,b]+=1
  if int(self.l[cx].sum())>16384:self.l[cx]=(self.l[cx]+1)//2
  if int(self.g[gid].sum())>262144:self.g[gid]=(self.g[gid]+1)//2
 def finish(self):self.pending+=1;self.emit(0 if self.lo<Q1 else 1);return self.o.finish()
class BD:
 def __init__(self,d,n,S):
  self.S=S;self.lo=0;self.hi=MAX;self.i=BI(d,n);self.v=0;self.l=np.zeros((q.NCTX,2),np.int32);self.g=np.ones((NG,2),np.int32)
  for _ in range(32):self.v=((self.v<<1)&MAX)|self.i.get()
 def counts(self,cx,gid):
  a=int(self.g[gid,0]);b=int(self.g[gid,1]);tot=a+b;p0=max(1,(self.S*a+tot//2)//tot);p1=max(1,(self.S*b+tot//2)//tot);return int(self.l[cx,0])+p0,int(self.l[cx,1])+p1
 def get(self,cx,gid):
  c0,c1=self.counts(cx,gid);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if self.v<=sp:b=0;self.hi=sp
  else:b=1;self.lo=sp+1
  while True:
   if self.hi<HALF:pass
   elif self.lo>=HALF:self.lo-=HALF;self.hi-=HALF;self.v-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.lo-=Q1;self.hi-=Q1;self.v-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1;self.v=((self.v<<1)&MAX)|self.i.get()
  self.l[cx,b]+=1;self.g[gid,b]+=1
  if int(self.l[cx].sum())>16384:self.l[cx]=(self.l[cx]+1)//2
  if int(self.g[gid].sum())>262144:self.g[gid]=(self.g[gid]+1)//2
  return b
def gid_zero(ac):return ac
def gid_sign(ac):return 6+ac
def gid_pref(pos):return 12+min(pos,15)
def gid_suff(qq,pos):return 28+min(qq,15)*16+min(pos,15)
def encode(K,W,nt,S):
 E=BE(S);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(nt):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=q.ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;k=int(K[c,t]);iz=1 if k==0 else 0
   E.put(iz,q.zero_ctx(prev,left,ac),gid_zero(ac))
   if not iz:
    E.put(1 if k<0 else 0,q.sign_ctx(prev,left,ac),gid_sign(ac));mag=abs(k);qq=mag.bit_length()-1
    for j in range(qq):E.put(0,q.pref_ctx(prev,ac,j),gid_pref(j))
    E.put(1,q.pref_ctx(prev,ac,qq),gid_pref(qq));rem=mag-(1<<qq)
    for bp in range(qq-1,-1,-1):
     pos=qq-1-bp;E.put((rem>>bp)&1,q.suff_ctx(qq,pos,ac),gid_suff(qq,pos))
   old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return E.finish()
def decode(bb,nbit,W,shape,S):
 D=BD(bb,nbit,S);K=np.zeros(shape,np.int32);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(shape[1]):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=q.ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;iz=D.get(q.zero_ctx(prev,left,ac),gid_zero(ac))
   if iz:k=0
   else:
    neg=D.get(q.sign_ctx(prev,left,ac),gid_sign(ac));qq=0
    while True:
     b=D.get(q.pref_ctx(prev,ac,qq),gid_pref(qq))
     if b:break
     qq+=1
     if qq>30:raise RuntimeError('gamma')
    rem=0
    for pos in range(qq):rem=(rem<<1)|D.get(q.suff_ctx(qq,pos,ac),gid_suff(qq,pos))
    mag=(1<<qq)+rem;k=-mag if neg else mag
   K[c,t]=k;old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return K
def choose(A,label):
 rows=[]
 for S in STRENGTHS:
  for W in WINDOWS:
   bb,nb=encode(A,W,SCREEN,S);r={'stream':label,'S':S,'W':W,'prefix_bytes':len(bb),'prefix_bits':int(nb)};rows.append(r);print(json.dumps(r),flush=True)
 rows.sort(key=lambda r:r['prefix_bytes']);return rows[0],rows
def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=q.m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+C],np.float64).T
 h,Q,D,dt,dc,co,it,changes,meanlegal=q.build_full(X,eps);mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it);ah.NT=NT;_,aco=ah.fits(X);R,K=ah.run_ar(X,aco)
 lb,lrows=choose(D,'learned');ab,arows=choose(K,'ar32');full=[]
 for label,A,best in [('learned',D,lb),('ar32',K,ab)]:
  S=best['S'];W=best['W'];bb,nb=encode(A,W,NT,S);Ad=decode(bb,nb,W,A.shape,S)
  if not np.array_equal(Ad,A):raise RuntimeError((label,'decode'))
  if label=='learned':
   Qd=q.f.q_decode(Ad,ddt,ddc,dco,dit,q.f.SCALE);me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)));total=int(mb)+len(bb)+q.HEADER+2
  else:
   Rd=ah.decode_source(Ad,aco);me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=len(bb)+ah.MODEL_BYTES+34
  if me>eps*(1+5e-6):raise RuntimeError((label,'hard',me,eps))
  full.append({'stream':label,'S':S,'W':W,'payload_bytes':len(bb),'bits':int(nb),'total_bytes':int(total),'maxerr':me})
 histL=2486110;histA=2478995;newL=[r for r in full if r['stream']=='learned'][0]['total_bytes'];newA=[r for r in full if r['stream']=='ar32'][0]['total_bytes'];bestL=min(histL,newL);bestA=min(histA,newA);out={'full':full,'learned_best_bytes':bestL,'ar32_best_bytes':bestA,'gain_learned_vs_ar32':bestA/bestL,'historical_learned':histL,'historical_ar32':histA,'screens':lrows+arows,'scope':'Fair decoder-shared hierarchical backoff ZSM on the identical full hard block. Every local historical ZSM context borrows a deterministic adaptive pseudo-prior from broader causal groups (zero by activity, sign by activity, gamma prefix by position, suffix by exponent/position). Global and local counts are updated online from already decoded bits; no probability table is transmitted. Public strengths S=2..64 and W=4/8/64 are prefix-screened independently for learned and AR32 streams, with strength+W selector bytes charged. Exactly one full candidate per representation is decoded/replayed under the unchanged hard error, and each final strongest result is min(new candidate, its historical baseline), so generic entropy gains are granted to AR32 equally.'};json.dump(out,open('imperial_fair_zsm_backoff.json','w'),indent=2);print(json.dumps({'summary':{'learned':bestL,'ar32':bestA,'gain':bestA/bestL,'full':full}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
