#!/usr/bin/env python3
"""Exact-stream codec core for quantized 3-D migrated seismic tiles.

The public error contract is enforced by one scalar quantization. Everything
that follows is reversible integer coding. Candidate transforms are structural,
not dataset-labelled: temporal/spatial differences, 2-D/3-D Lorenzo, and a
causal per-trace predictor that can use left/up traces with small time lags,
a spatial plane, temporal delta, or zero. Predictor choices are serialized.
"""
from __future__ import annotations
import argparse,struct
import numpy as np
import zstandard as zstd

MAGIC=b'MV3D01\0\0'; HDR='<8sddIIIHHII'; HSZ=struct.calcsize(HDR); MARGIN=1-1e-4
CCTX=zstd.ZstdCompressor(level=12); DCTX=zstd.ZstdDecompressor()
T_RAW=0;T_TIME=1;T_FAST=2;T_SLOW=3;T_SPATIAL_LORENZO=4;T_FULL_LORENZO=5;T_ADAPT=6
NAMES={T_RAW:'raw_q',T_TIME:'time_delta',T_FAST:'fast_delta',T_SLOW:'slow_delta',T_SPATIAL_LORENZO:'spatial_lorenzo',T_FULL_LORENZO:'full_lorenzo_3d',T_ADAPT:'adaptive_causal_lag'}
RADIUS=8

def hard(a,b):return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))
def shift(x,lag):
 out=np.zeros_like(x);n=x.size
 if lag>=0:
  if lag<n:out[:n-lag]=x[lag:]
 else:
  q=-lag
  if q<n:out[q:]=x[:n-q]
 return out

def static_forward(Q,tid):
 if tid==T_RAW:return Q.copy()
 if tid==T_TIME:return np.diff(Q,axis=2,prepend=np.zeros(Q.shape[:2]+(1,),dtype=np.int32))
 if tid==T_FAST:return np.diff(Q,axis=1,prepend=np.zeros((Q.shape[0],1,Q.shape[2]),dtype=np.int32))
 if tid==T_SLOW:return np.diff(Q,axis=0,prepend=np.zeros((1,Q.shape[1],Q.shape[2]),dtype=np.int32))
 if tid==T_SPATIAL_LORENZO:
  a=np.diff(Q,axis=0,prepend=np.zeros((1,Q.shape[1],Q.shape[2]),dtype=np.int32));return np.diff(a,axis=1,prepend=np.zeros((Q.shape[0],1,Q.shape[2]),dtype=np.int32))
 if tid==T_FULL_LORENZO:
  a=np.diff(Q,axis=0,prepend=np.zeros((1,Q.shape[1],Q.shape[2]),dtype=np.int32));b=np.diff(a,axis=1,prepend=np.zeros((Q.shape[0],1,Q.shape[2]),dtype=np.int32));return np.diff(b,axis=2,prepend=np.zeros(Q.shape[:2]+(1,),dtype=np.int32))
 raise ValueError(tid)
def static_inverse(R,tid):
 if tid==T_RAW:return R.copy()
 if tid==T_TIME:return np.cumsum(R,axis=2,dtype=np.int32)
 if tid==T_FAST:return np.cumsum(R,axis=1,dtype=np.int32)
 if tid==T_SLOW:return np.cumsum(R,axis=0,dtype=np.int32)
 if tid==T_SPATIAL_LORENZO:return np.cumsum(np.cumsum(R,axis=1,dtype=np.int32),axis=0,dtype=np.int32)
 if tid==T_FULL_LORENZO:return np.cumsum(np.cumsum(np.cumsum(R,axis=2,dtype=np.int32),axis=1,dtype=np.int32),axis=0,dtype=np.int32)
 raise ValueError(tid)

def adaptive_forward(Q):
 ny,nx,nt=Q.shape;R=np.empty_like(Q);codes=np.zeros((ny,nx),np.uint8)
 for y in range(ny):
  for x in range(nx):
   cur=Q[y,x];cands=[]
   # mode 0 zero
   cands.append((int(np.abs(cur.astype(np.int64)).sum()),0,np.zeros(nt,np.int32)))
   # mode 1 temporal DPCM (predict previous sample inside this trace)
   pt=np.zeros(nt,np.int32);pt[1:]=cur[:-1];cands.append((int(np.abs(cur.astype(np.int64)-pt.astype(np.int64)).sum()),32,pt))
   if x>0:
    for lag in range(-RADIUS,RADIUS+1):
     p=shift(Q[y,x-1],lag);score=int(np.abs(cur.astype(np.int64)-p.astype(np.int64)).sum());cands.append((score,64+(lag+RADIUS),p))
   if y>0:
    for lag in range(-RADIUS,RADIUS+1):
     p=shift(Q[y-1,x],lag);score=int(np.abs(cur.astype(np.int64)-p.astype(np.int64)).sum());cands.append((score,96+(lag+RADIUS),p))
   if y>0 and x>0:
    p64=Q[y,x-1].astype(np.int64)+Q[y-1,x].astype(np.int64)-Q[y-1,x-1].astype(np.int64)
    if np.all((p64>=np.iinfo(np.int32).min)&(p64<=np.iinfo(np.int32).max)):
     p=p64.astype(np.int32);cands.append((int(np.abs(cur.astype(np.int64)-p64).sum()),128,p))
   score,code,pred=min(cands,key=lambda q:(q[0],q[1]));codes[y,x]=np.uint8(code);R[y,x]=cur-pred
 return R,codes.tobytes()
def adaptive_inverse(R,side):
 ny,nx,nt=R.shape;codes=np.frombuffer(side,np.uint8)
 if codes.size!=ny*nx:raise RuntimeError(('adaptive side',codes.size,ny*nx))
 codes=codes.reshape(ny,nx);Q=np.empty_like(R)
 for y in range(ny):
  for x in range(nx):
   code=int(codes[y,x])
   if code==0:Q[y,x]=R[y,x]
   elif code==32:
    q=np.empty(nt,np.int32);q[0]=R[y,x,0]
    for t in range(1,nt):q[t]=R[y,x,t]+q[t-1]
    Q[y,x]=q
   elif 64<=code<=64+2*RADIUS:
    if x==0:raise RuntimeError(('left code at edge',y,x,code))
    Q[y,x]=R[y,x]+shift(Q[y,x-1],code-64-RADIUS)
   elif 96<=code<=96+2*RADIUS:
    if y==0:raise RuntimeError(('up code at edge',y,x,code))
    Q[y,x]=R[y,x]+shift(Q[y-1,x],code-96-RADIUS)
   elif code==128:
    if y==0 or x==0:raise RuntimeError(('plane code at edge',y,x))
    p=Q[y,x-1].astype(np.int64)+Q[y-1,x].astype(np.int64)-Q[y-1,x-1].astype(np.int64);Q[y,x]=R[y,x]+p.astype(np.int32)
   else:raise RuntimeError(('bad adaptive code',code))
 return Q

def shuffle(a):
 a=np.ascontiguousarray(a);w=a.dtype.itemsize;return a.view(np.uint8).reshape(-1,w).T.copy().tobytes()
def unshuffle(raw,dt,n):
 dt=np.dtype(dt);w=dt.itemsize;u=np.frombuffer(raw,np.uint8)
 if u.size!=n*w:raise RuntimeError(('unshuffle',u.size,n,w))
 return u.reshape(w,n).T.copy().reshape(n*w).view(dt)
def zig(x):
 a=np.asarray(x,np.int64).reshape(-1);z=(a<<1)^(a>>63)
 if np.any((z<0)|(z>np.iinfo(np.uint32).max)):raise OverflowError('zigzag')
 return z.astype(np.uint32)
def unzig(z):
 z=np.asarray(z,np.uint32).astype(np.uint64);a=(z>>1).astype(np.int64)^-((z&1).astype(np.int64));return a.astype(np.int32)
def pack(R):
 a=np.asarray(R,np.int32).reshape(-1);mn=int(a.min());mx=int(a.max());tr=[]
 if -128<=mn and mx<=127:tr.append((0,CCTX.compress(a.astype(np.int8).tobytes())))
 if -32768<=mn and mx<=32767:
  q=a.astype('<i2');tr.extend([(1,CCTX.compress(q.tobytes())),(2,CCTX.compress(shuffle(q)))])
 q=a.astype('<i4');tr.extend([(3,CCTX.compress(q.tobytes())),(4,CCTX.compress(shuffle(q)))])
 z=zig(a)
 if int(z.max())<=65535:tr.append((5,CCTX.compress(shuffle(z.astype('<u2')))))
 tr.append((6,CCTX.compress(shuffle(z.astype('<u4')))))
 return min(tr,key=lambda q:(len(q[1]),q[0]))
def unpack(pid,body,shape):
 n=int(np.prod(shape));raw=DCTX.decompress(body)
 if pid==0:a=np.frombuffer(raw,np.int8,count=n).astype(np.int32)
 elif pid==1:a=np.frombuffer(raw,'<i2',count=n).astype(np.int32)
 elif pid==2:a=unshuffle(raw,'<i2',n).astype(np.int32)
 elif pid==3:a=np.frombuffer(raw,'<i4',count=n).astype(np.int32)
 elif pid==4:a=unshuffle(raw,'<i4',n).astype(np.int32)
 elif pid==5:a=unzig(unshuffle(raw,'<u2',n).astype(np.uint32))
 elif pid==6:a=unzig(unshuffle(raw,'<u4',n).astype(np.uint32))
 else:raise RuntimeError(('pack id',pid))
 return a.reshape(shape)

def encode(X,eps,tid):
 internal=float(eps)*MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
 if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('quantized int32')
 Q=q.astype(np.int32)
 if tid==T_ADAPT:R,side=adaptive_forward(Q)
 else:R=static_forward(Q,tid);side=b''
 sideb=CCTX.compress(side) if side else b'';pid,payload=pack(R);ny,nx,nt=Q.shape
 h=struct.pack(HDR,MAGIC,float(eps),internal,ny,nx,nt,tid,pid,len(sideb),len(payload));blob=h+sideb+payload
 return blob,{'transform':NAMES[tid],'pack_id':pid,'side_bytes':len(sideb),'payload_bytes':len(payload),'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64))))}
def decode(blob):
 if len(blob)<HSZ:raise RuntimeError('short')
 magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(HDR,blob[:HSZ])
 if magic!=MAGIC or len(blob)!=HSZ+ns+npay:raise RuntimeError('bad stream')
 side=DCTX.decompress(blob[HSZ:HSZ+ns]) if ns else b'';R=unpack(pid,blob[HSZ+ns:],(ny,nx,nt));Q=adaptive_inverse(R,side) if tid==T_ADAPT else static_inverse(R,tid);return Q.astype(np.float64)*(2*internal),{'shape':[ny,nx,nt],'transform':NAMES[tid],'eps':eps}
def compete(X,eps):
 rows=[]
 for tid in NAMES:
  b,d=encode(X,eps,tid);Y,m=decode(b);e=hard(X,Y)
  if e>eps*(1+3e-6):raise RuntimeError(('hard',NAMES[tid],e,eps))
  rows.append({'tid':tid,'bytes':len(b),'blob':b,'maxerr':e,'diag':d})
 return min(rows,key=lambda q:(q['bytes'],q['tid'])),rows

def sanity():
 rng=np.random.default_rng(5603);ny,nx,nt=7,13,257;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
 for y in range(ny):
  for x in range(nx):X[y,x]=(80*np.sin((t+2*x+3*y)/22)+30*np.sin((t-x+y)/9)+rng.normal(0,2,nt)).astype(np.float32)
 eps=3.;best,rows=compete(X,eps);print('MV3D_SANITY_OK',NAMES[best['tid']],best['bytes'],[(NAMES[r['tid']],r['bytes']) for r in rows])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('cmd',choices=['sanity']);a=ap.parse_args();sanity()
if __name__=='__main__':main()
