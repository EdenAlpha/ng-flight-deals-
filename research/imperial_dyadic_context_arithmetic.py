import json,sys,math
import h5py,numpy as np
import imperial_dyadic_legal_grid_full_array as d

C=128;T=1024
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
CTXMODES=('nbr3','nbr3_prefix2','nbr4_prefix2','nbr3_prefix2_tpar')
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30

class BitOut:
 def __init__(self):self.a=[]
 def put(self,b):self.a.append(int(b))
 def finish(self):
  z=bytearray((len(self.a)+7)//8)
  for i,b in enumerate(self.a):
   if b:z[i>>3]|=1<<(7-(i&7))
  return bytes(z),len(self.a)
class BitIn:
 def __init__(self,data,nb):self.d=data;self.nb=nb;self.i=0
 def get(self):
  if self.i>=self.nb:return 0
  b=(self.d[self.i>>3]>>(7-(self.i&7)))&1;self.i+=1;return b
class ACEnc:
 def __init__(self,nctx):self.lo=0;self.hi=MAX;self.pending=0;self.o=BitOut();self.c=np.ones((nctx,2),np.int32)
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
class ACDec:
 def __init__(self,data,nb,nctx):
  self.lo=0;self.hi=MAX;self.i=BitIn(data,nb);self.v=0;self.c=np.ones((nctx,2),np.int32)
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
 base=tp|(sp<<1)|(dg<<2)
 if mode=='nbr3':return base,8
 pref=0
 if len(higher)>=1:pref|=int(higher[-1][c,t])
 if len(higher)>=2:pref|=int(higher[-2][c,t])<<1
 if mode=='nbr3_prefix2':return base|(pref<<3),32
 if mode=='nbr4_prefix2':return base|(t2<<3)|(pref<<4),64
 if mode=='nbr3_prefix2_tpar':return base|(pref<<3)|((t&1)<<5),64
 raise ValueError(mode)

def encode_planes(u,mode):
 u=np.asarray(u,np.uint64);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());planes=[((u>>(nb-1-k))&1).astype(np.uint8) for k in range(nb)];streams=[];higher=[]
 for plane in planes:
  cur=np.zeros_like(plane,np.uint8);_,nctx=ctxid(cur,higher,0,0,mode);ac=ACEnc(nctx)
  for t in range(plane.shape[1]):
   for c in range(plane.shape[0]):
    ctx,_=ctxid(cur,higher,c,t,mode);b=int(plane[c,t]);ac.put(b,ctx);cur[c,t]=b
  bb,nbit=ac.finish();streams.append((bb,nbit));higher.append(cur.copy())
 # decoder-equivalent rebuild
 dh=[]
 for bb,nbit in streams:
  cur=np.zeros(u.shape,np.uint8);_,nctx=ctxid(cur,dh,0,0,mode);ac=ACDec(bb,nbit,nctx)
  for t in range(cur.shape[1]):
   for c in range(cur.shape[0]):
    ctx,_=ctxid(cur,dh,c,t,mode);cur[c,t]=ac.get(ctx)
  dh.append(cur)
 uu=np.zeros(u.shape,np.uint64)
 for p in dh:uu=(uu<<1)|p.astype(np.uint64)
 if not np.array_equal(uu,u):raise RuntimeError(('arith decode mismatch',mode))
 total=sum(len(x[0]) for x in streams)+4*nb+48
 return total,nb,uu,[x[1] for x in streams]

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=d.stats(ds);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(ds[t0:t0+T,c0:c0+C],np.float64).T;sb,ori=d.szround(X,eps)[:2] if hasattr(d,'szround') else (None,None)
   # PR287 helper uses szrun? retain compatibility with current file.
   if sb is None:
    import imperial_dyadic_legal_grid_full_array as q
    sr=q.szrun(X,eps) if hasattr(q,'szrun') else None
    if sr is None:raise RuntimeError('no SZ3 helper')
    sb=sr[0];ori=sr[1]
   base=d.encode_dyadic(X,eps);q=np.rint(X/256.0).astype(np.int32);u=d.zigzag(q) if hasattr(d,'zigzag') else ((q.astype(np.int64)<<1)^(q.astype(np.int64)>>63)).astype(np.uint64)
   tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'zstd_dyadic_bytes':base['bytes'],'zstd_dyadic_bps':8*base['bytes']/X.size,'zstd_rep':base['rep']})
   for mode in CTXMODES:
    b,nb,ud,bits=encode_planes(u,mode);qq=d.unzig(ud).reshape(q.shape) if hasattr(d,'unzig') else ((ud>>1).astype(np.int64)^-(ud&1).astype(np.int64)).astype(np.int32).reshape(q.shape)
    R=qq.astype(np.float64)*256.0;me=float(np.max(np.abs(X-R)))
    if not np.array_equal(qq,q):raise RuntimeError('q mismatch')
    if me>eps*(1+1e-12):raise RuntimeError(('hard',mode,me,eps))
    r={'tile':name,'mode':mode,'bytes':b,'bps':8*b/X.size,'nbits_symbol':nb,'sz3_bytes':sb,'gain_vs_sz3':sb/b,'gain_vs_pr287_zstd':base['bytes']/b,'pr287_bytes':base['bytes'],'maxerr':me,'plane_coded_bits':bits};rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='plane_coded_bits'}),flush=True)
  combos=[];sz=sum(t['sz3_bytes'] for t in tiles);zb=sum(t['zstd_dyadic_bytes'] for t in tiles);n=C*T*len(tiles)
  for mode in CTXMODES:
   rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr)
   combos.append({'mode':mode,'bytes':b,'sz3_bytes':sz,'pr287_zstd_bytes':zb,'bps':8*b/n,'gain_vs_sz3':sz/b,'gain_vs_pr287_zstd':zb/b,'min_tile_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':256,'patch_shape':[C,T],'context_modes':list(CTXMODES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Real adaptive arithmetic coding audit for the fixed binary-native 256-grid high-byte field. Zigzag symbol bitplanes are encoded MSB-to-LSB with deterministic online probabilities; no trained tables or model metadata are transmitted. Contexts use already-decoded same-plane temporal/spatial/diagonal bits, optional t-2 bit, already-decoded higher symbol bits, and optional time parity. The exact arithmetic streams are decoded to reconstruct every bitplane and q symbol before the <=128 hard-error check. PR287 Zstd dyadic bytes and matched SZ3 are rerun/compared on the same four 128x1024 tiles. Backend screen only; no full-array claim until a winner is frozen.'};print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_dyadic_context_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
