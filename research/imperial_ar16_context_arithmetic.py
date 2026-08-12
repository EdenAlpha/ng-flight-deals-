import json,sys,math
import h5py,numpy as np
import imperial_dyadic_shared_resonator as r
import imperial_decoder_phase_automaton as m

P=16;C=128;T=1024
SPECS=m.SPECS
CTXMODES=('nbr3_prefix2','nbr4_prefix2')
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
  if self.lo<Q1:self.emit(0)
  else:self.emit(1)
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

def ctxid(cur,higher,c,t,mode):
 tp=int(cur[c,t-1]) if t>0 else 0;sp=int(cur[c-1,t]) if c>0 else 0;dg=int(cur[c-1,t-1]) if c>0 and t>0 else 0;t2=int(cur[c,t-2]) if t>1 else 0
 base=tp|(sp<<1)|(dg<<2);pref=0
 if len(higher)>=1:pref|=int(higher[-1][c,t])
 if len(higher)>=2:pref|=int(higher[-2][c,t])<<1
 if mode=='nbr3_prefix2':return base|(pref<<3),32
 if mode=='nbr4_prefix2':return base|(t2<<3)|(pref<<4),64
 raise ValueError(mode)

def zig(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzig(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)

def arithmetic_k(K,mode):
 u=zig(K);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());planes=[((u>>(nb-1-k))&1).astype(np.uint8) for k in range(nb)];streams=[];higher=[]
 for p in planes:
  cur=np.zeros_like(p,np.uint8);_,nctx=ctxid(cur,higher,0,0,mode);ac=AE(nctx)
  for t in range(p.shape[1]):
   for c in range(p.shape[0]):
    cx,_=ctxid(cur,higher,c,t,mode);b=int(p[c,t]);ac.put(b,cx);cur[c,t]=b
  streams.append(ac.finish());higher.append(cur.copy())
 dh=[]
 for bb,nbit in streams:
  cur=np.zeros(K.shape,np.uint8);_,nctx=ctxid(cur,dh,0,0,mode);ac=AD(bb,nbit,nctx)
  for t in range(cur.shape[1]):
   for c in range(cur.shape[0]):
    cx,_=ctxid(cur,dh,c,t,mode);cur[c,t]=ac.get(cx)
  dh.append(cur)
 uu=np.zeros(K.shape,np.uint64)
 for p in dh:uu=(uu<<1)|p.astype(np.uint64)
 Kd=unzig(uu).reshape(K.shape)
 if not np.array_equal(Kd,K):raise RuntimeError(('arith K mismatch',mode))
 return sum(len(x[0]) for x in streams)+4*nb+48,Kd,nb

def build_k(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for c in range(C):
  for t in range(T):
   p=r.predict_hist(R,c,t,coef,P,'shared');k=int(np.rint((float(X[c,t])-p)/m.STEP));R[c,t]=p+m.STEP*k;K[c,t]=k
 return R,K

def decode_k(Kd,coef):
 R=np.zeros(Kd.shape,np.int32)
 for c in range(C):
  for t in range(T):R[c,t]=r.predict_hist(R,c,t,coef,P,'shared')+m.STEP*int(Kd[c,t])
 return R

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb,ori=m.szrun(X,eps);coef=r.fit_shared(X,P);mb,cd=r.model_frame(coef);R,K=build_k(X,cd)
   z=m.encode_k(K);Rz=decode_k(z[2],cd)
   if not np.array_equal(Rz,R):raise RuntimeError(('zstd recursive',name))
   mez=float(np.max(np.abs(X-Rz.astype(float))))
   zbytes=mb+z[0]+20
   base={'tile':name,'backend':'zstd_menu','bytes':zbytes,'bps':8*zbytes/X.size,'model_bytes':mb,'innovation_bytes':z[0],'rep':z[1],'sz3_bytes':sb,'gain_vs_sz3':sb/zbytes,'maxerr':mez};rows.append(base)
   best=base
   for mode in CTXMODES:
    ab,Kd,nb=arithmetic_k(K,mode);Ra=decode_k(Kd,cd);me=float(np.max(np.abs(X-Ra.astype(float))))
    if me>eps*(1+1e-12):raise RuntimeError(('arith hard',name,mode,me,eps))
    total=mb+ab+21
    q={'tile':name,'backend':'arith_'+mode,'bytes':total,'bps':8*total/X.size,'model_bytes':mb,'innovation_bytes':ab,'symbol_bits':nb,'sz3_bytes':sb,'gain_vs_sz3':sb/total,'gain_vs_ar16_zstd':zbytes/total,'maxerr':me};rows.append(q)
    if q['bytes']<best['bytes']:best=q
   tiles.append({'tile':name,'sz3_bytes':sb,'ar16_zstd_bytes':zbytes,'best_composed_backend':best['backend'],'best_composed_bytes':best['bytes'],'best_gain_vs_sz3':sb/best['bytes']})
   print(json.dumps({'tile':name,'zstd':base,'best':best},indent=2),flush=True)
  sz=sum(t['sz3_bytes'] for t in tiles);zb=sum(t['ar16_zstd_bytes'] for t in tiles);bb=sum(t['best_composed_bytes'] for t in tiles);n=C*T*len(tiles)
  out={'std':std,'eps':eps,'order':P,'step':m.STEP,'context_modes':list(CTXMODES),'tiles':tiles,'rows':rows,'aggregate':{'samples':n,'sz3_bytes':sz,'ar16_zstd_bytes':zb,'best_composed_bytes':bb,'sz3_bps':8*sz/n,'ar16_zstd_bps':8*zb/n,'best_composed_bps':8*bb/n,'ar16_zstd_gain_vs_sz3':sz/zb,'best_composed_gain_vs_sz3':sz/bb,'best_composed_gain_vs_ar16_zstd':zb/bb,'min_tile_gain':min(t['best_gain_vs_sz3'] for t in tiles)},'scope':'Exact composition of PR301 shared AR16 dyadic state reconstruction with PR302 causal adaptive arithmetic innovation coding. AR16 coefficients are float32 serialized/decoded. Encoder forms k=round((X-P)/256) from the recursively decoded state equation. Innovations are encoded either by the existing Zstd frame menu or real MSB-first adaptive arithmetic bitplanes with causal nbr3/nbr4+two-higher-bit contexts; streams are fully decoded to exact K, then the AR recursion is rerun and <=128 hard error verified. Per tile the smaller backend is selected with one-byte-scale mode overhead included. Four precommitted 128x1024 regimes and matched SZ3. Real-byte codec screen, no AI.'}
  print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_ar16_context_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
