#!/usr/bin/env python3
import struct, math
import numpy as np
MAGIC=b'V6L1'

def vi(n):
 o=bytearray()
 while n>=128:o.append((n&127)|128);n>>=7
 o.append(n);return bytes(o)
def uv(b,p):
 n=s=0
 while 1:
  x=b[p];p+=1;n|=(x&127)<<s
  if x<128:return n,p
  s+=7

def zig(r):
 s=np.where(r<128,r.astype(np.int16),r.astype(np.int16)-256)
 return np.where(s>=0,s*2,-s*2-1).astype(np.uint8)
def unzig(z):
 z=z.astype(np.int16);s=np.where((z&1)==0,z//2,-((z+1)//2));return (s&255).astype(np.uint8)
def pack_ids(ids):
 o=bytearray((len(ids)+1)//2)
 for i,x in enumerate(ids):
  if i&1:o[i//2]|=(x&15)<<4
  else:o[i//2]=x&15
 return bytes(o)
def unpack_ids(b,n):
 return [(b[i//2]>>(4*(i&1)))&15 for i in range(n)]

def bitplane(z):
 n=len(z);a=np.frombuffer(z,dtype=np.uint8);out=bytearray()
 for bit in range(8):out+=np.packbits((a>>bit)&1,bitorder='little').tobytes()
 return bytes(out)
def unbitplane(b,n):
 m=(n+7)//8;o=np.zeros(n,dtype=np.uint8)
 for bit in range(8):
  q=np.unpackbits(np.frombuffer(b[bit*m:(bit+1)*m],dtype=np.uint8),bitorder='little')[:n]
  o|=(q.astype(np.uint8)<<bit)
 return o.tobytes()

def candidates(a):
 # a: [t,h,w] uint8. All laws are causal and exactly invertible.
 T,H,W=a.shape; q=a.astype(np.int16)
 prev=np.zeros_like(q);prev[1:]=q[:-1]
 prev2=np.zeros_like(q);prev2[2:]=q[:-2]
 left=np.zeros_like(q);left[:,:,1:]=q[:,:,:-1]
 up=np.zeros_like(q);up[:,1:]=q[:,:-1]
 pleft=np.zeros_like(q);pleft[:,:,1:]=prev[:,:,:-1]
 pup=np.zeros_like(q);pup[:,1:]=prev[:,:-1]
 # Predictor semantics: 0 temporal, 1 left, 2 up, 3 left+temporal-prevleft,
 # 4 up+temporal-prevup, 5 second temporal. First frame degrades causally.
 preds=[prev,left,up,left+prev-pleft,up+prev-pup,2*prev-prev2]
 # for first frame: temporal predictors predict 0; second temporal predicts 0.
 return [((q-p)&255).astype(np.uint8) for p in preds]

def choose_blocks(a,block):
 T,H,W=a.shape;cs=candidates(a);ids=[];groups=[bytearray() for _ in cs];shapes=[]
 for t in range(T):
  for y0 in range(0,H,block):
   y1=min(H,y0+block)
   for x0 in range(0,W,block):
    x1=min(W,x0+block);best=None;bestz=None
    for k,r in enumerate(cs):
     z=zig(r[t,y0:y1,x0:x1]).ravel()
     # MDL-like cheap local score: favor zero/small centered residuals, but penalize
     # diffuse tails. This chooses laws, not entropy backends.
     zz=z.astype(np.int16);score=int(np.minimum(zz,96).sum())+12*int(np.count_nonzero(zz>=32))
     if best is None or score<best:best=score;bestz=z;kbest=k
    ids.append(kbest);groups[kbest]+=bestz.tobytes();shapes.append((y1-y0,x1-x0))
 # Each law gets its own coordinate band. Select byte or bitplane representation
 # using a deterministic zero-order entropy proxy; decoder sees the flag.
 gb=[]
 for g in groups:
  z=bytes(g); bp=bitplane(z) if z else b''
  def h0(x):
   if not x:return 0.0
   c=np.bincount(np.frombuffer(x,dtype=np.uint8),minlength=256);c=c[c>0];n=len(x)
   return float(-np.sum(c*np.log2(c/n)))
  # bitplane often exposes sparse high bits; retain it only if entropy proxy wins.
  if bp and h0(bp)+0.001 < h0(z):gb.append((1,bp,len(z)))
  else:gb.append((0,z,len(z)))
 return ids,gb,shapes

def restore_plane(ids,gb,T,H,W,block):
 data=[]
 for flag,b,n in gb:
  z=unbitplane(b,n) if flag else b
  data.append(np.frombuffer(z,dtype=np.uint8));
 pos=[0]*len(gb);out=np.zeros((T,H,W),dtype=np.uint8);ip=0
 for t in range(T):
  for y0 in range(0,H,block):
   y1=min(H,y0+block)
   for x0 in range(0,W,block):
    x1=min(W,x0+block);k=ids[ip];ip+=1;n=(y1-y0)*(x1-x0);z=data[k][pos[k]:pos[k]+n].reshape(y1-y0,x1-x0);pos[k]+=n;r=unzig(z).astype(np.int16)
    prev=out[t-1] if t else None;prev2=out[t-2] if t>=2 else None
    if k==0:
     pr=prev[y0:y1,x0:x1].astype(np.int16) if t else 0;out[t,y0:y1,x0:x1]=((pr+r)&255).astype(np.uint8)
    elif k==5:
     if t>=2:pr=2*prev[y0:y1,x0:x1].astype(np.int16)-prev2[y0:y1,x0:x1].astype(np.int16)
     elif t==1:pr=2*prev[y0:y1,x0:x1].astype(np.int16)
     else:pr=0
     out[t,y0:y1,x0:x1]=((pr+r)&255).astype(np.uint8)
    elif k in (1,3):
     # Horizontal recurrence. r is delta for k=1, or temporal delta-of-delta for k=3.
     if t:
      pv=prev[y0:y1,x0:x1].astype(np.int16);pl=np.empty_like(pv);pl[:,0]=prev[y0:y1,x0-1].astype(np.int16) if x0 else 0;pl[:,1:]=pv[:,:-1];dr=(pv-pl) if k==3 else 0
     else:dr=0
     d=(r+dr)&255;base=out[t,y0:y1,x0-1].astype(np.int16) if x0 else np.zeros(y1-y0,dtype=np.int16)
     out[t,y0:y1,x0:x1]=((base[:,None]+np.cumsum(d,axis=1))&255).astype(np.uint8)
    elif k in (2,4):
     if t:
      pv=prev[y0:y1,x0:x1].astype(np.int16);pu=np.empty_like(pv);pu[0]=prev[y0-1,x0:x1].astype(np.int16) if y0 else 0;pu[1:]=pv[:-1];dr=(pv-pu) if k==4 else 0
     else:dr=0
     d=(r+dr)&255;base=out[t,y0-1,x0:x1].astype(np.int16) if y0 else np.zeros(x1-x0,dtype=np.int16)
     out[t,y0:y1,x0:x1]=((base[None,:]+np.cumsum(d,axis=0))&255).astype(np.uint8)
    else:raise ValueError('law')
 for k in range(len(data)):
  if pos[k]!=len(data[k]):raise ValueError('band length')
 return out

def pack(raw,w=320,h=180,block=16):
 fs=w*h*3//2
 if len(raw)%fs:return None
 T=len(raw)//fs;a=np.frombuffer(raw,dtype=np.uint8);p=0;planes=[]
 for _ in range(T):
  planes.append((a[p:p+w*h].reshape(h,w),a[p+w*h:p+w*h+w*h//4].reshape(h//2,w//2),a[p+w*h+w*h//4:p+fs].reshape(h//2,w//2)));p+=fs
 arrs=[np.stack([x[j] for x in planes]) for j in range(3)];o=bytearray(MAGIC)+struct.pack('<HHIH',w,h,T,block)
 for A in arrs:
  ids,gb,_=choose_blocks(A,block if A.shape[2]>=w else max(8,block//2));ib=pack_ids(ids);o+=vi(len(ids))+vi(len(ib))+ib+vi(len(gb))
  for flag,b,n in gb:o+=bytes([flag])+vi(n)+vi(len(b))+b
 return bytes(o)
def unpack(rep):
 if rep[:4]!=MAGIC:raise ValueError('magic')
 p=4;w,h,T,block=struct.unpack_from('<HHIH',rep,p);p+=10;outs=[]
 for H,W,B in ((h,w,block),(h//2,w//2,max(8,block//2)),(h//2,w//2,max(8,block//2))):
  ni,p=uv(rep,p);il,p=uv(rep,p);ids=unpack_ids(rep[p:p+il],ni);p+=il;ng,p=uv(rep,p);gb=[]
  for _ in range(ng):flag=rep[p];p+=1;n,p=uv(rep,p);l,p=uv(rep,p);b=rep[p:p+l];p+=l;gb.append((flag,b,n))
  outs.append(restore_plane(ids,gb,T,H,W,B))
 if p!=len(rep):raise ValueError('trailing')
 o=bytearray()
 for t in range(T):o+=outs[0][t].tobytes()+outs[1][t].tobytes()+outs[2][t].tobytes()
 return bytes(o)
