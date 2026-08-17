#!/usr/bin/env python3
"""Exact blockwise causal dip predictor for native 3-D migrated seismic tiles.

This is a competing stream, not an oracle. Each time block chooses from a fixed
set of decoder-known predictors using only already decoded spatial neighbours:
zero, temporal DPCM, left/up trace with small lag, left/up linear spatial
extrapolation, an unshifted spatial plane, or a JPEG-LS-style median predictor.
Every predictor code is serialized and charged.
"""
from __future__ import annotations
import struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as base
import migrated_volume_3d_entropy as entropy

MAGIC=b'MVBLK01\0';HDR='<8sddIIIHHII';HSZ=struct.calcsize(HDR);RADIUS=8
CCTX=zstd.ZstdCompressor(level=12);DCTX=zstd.ZstdDecompressor()

# codes
ZERO=0;TEMP=1;LEFT0=16;UP0=48;PLANE=80;LEX0=96;UEX0=128;MED=160

def _shift_block(row,s,e,lag):
 n=e-s;out=np.zeros(n,np.int32);a=max(s,-lag);b=min(e,row.size-lag)
 if b>a:out[a-s:b-s]=row[a+lag:b+lag]
 return out

def _med_predict(a,b,c):
 # JPEG-LS median edge detector: median(a,b,a+b-c), fully integer/reversible.
 p=a.astype(np.int64)+b.astype(np.int64)-c.astype(np.int64)
 lo=np.minimum(a,b).astype(np.int64);hi=np.maximum(a,b).astype(np.int64)
 p=np.minimum(np.maximum(p,lo),hi)
 return p.astype(np.int32)

def _candidate(cur,pred,code):
 d=cur.astype(np.int64)-pred.astype(np.int64)
 # Entropy-aware deterministic proxy: nonzero count first, then L1 magnitude.
 return (int(np.count_nonzero(d)),int(np.abs(d).sum()),int(code)),pred,int(code)

def forward(Q,block):
 Q=np.asarray(Q,np.int32);ny,nx,nt=Q.shape;nb=(nt+block-1)//block
 R=np.empty_like(Q);codes=np.zeros((ny,nx,nb),np.uint8)
 for y in range(ny):
  for x in range(nx):
   for bi in range(nb):
    s=bi*block;e=min(nt,s+block);cur=Q[y,x,s:e];cands=[]
    z=np.zeros(e-s,np.int32);cands.append(_candidate(cur,z,ZERO))
    # Temporal DPCM predictor is causal inside the current trace.
    pt=np.empty(e-s,np.int32)
    for j in range(e-s):pt[j]=0 if s+j==0 else Q[y,x,s+j-1]
    cands.append(_candidate(cur,pt,TEMP))
    if x>0:
     for lag in range(-RADIUS,RADIUS+1):
      p=_shift_block(Q[y,x-1],s,e,lag);cands.append(_candidate(cur,p,LEFT0+lag+RADIUS))
     if x>1:
      for lag in range(-RADIUS,RADIUS+1):
       a=_shift_block(Q[y,x-1],s,e,lag).astype(np.int64);b=_shift_block(Q[y,x-2],s,e,2*lag).astype(np.int64);p=2*a-b
       if np.all((p>=np.iinfo(np.int32).min)&(p<=np.iinfo(np.int32).max)):cands.append(_candidate(cur,p.astype(np.int32),LEX0+lag+RADIUS))
    if y>0:
     for lag in range(-RADIUS,RADIUS+1):
      p=_shift_block(Q[y-1,x],s,e,lag);cands.append(_candidate(cur,p,UP0+lag+RADIUS))
     if y>1:
      for lag in range(-RADIUS,RADIUS+1):
       a=_shift_block(Q[y-1,x],s,e,lag).astype(np.int64);b=_shift_block(Q[y-2,x],s,e,2*lag).astype(np.int64);p=2*a-b
       if np.all((p>=np.iinfo(np.int32).min)&(p<=np.iinfo(np.int32).max)):cands.append(_candidate(cur,p.astype(np.int32),UEX0+lag+RADIUS))
    if x>0 and y>0:
     l=Q[y,x-1,s:e];u=Q[y-1,x,s:e];d=Q[y-1,x-1,s:e]
     p64=l.astype(np.int64)+u.astype(np.int64)-d.astype(np.int64)
     if np.all((p64>=np.iinfo(np.int32).min)&(p64<=np.iinfo(np.int32).max)):cands.append(_candidate(cur,p64.astype(np.int32),PLANE))
     cands.append(_candidate(cur,_med_predict(l,u,d),MED))
    key,pred,code=min(cands,key=lambda q:q[0]);codes[y,x,bi]=np.uint8(code);R[y,x,s:e]=cur-pred
 return R,codes.tobytes()

def inverse(R,side,block):
 R=np.asarray(R,np.int32);ny,nx,nt=R.shape;nb=(nt+block-1)//block;codes=np.frombuffer(side,np.uint8)
 if codes.size!=ny*nx*nb:raise RuntimeError(('block side size',codes.size,ny*nx*nb))
 codes=codes.reshape(ny,nx,nb);Q=np.empty_like(R)
 for y in range(ny):
  for x in range(nx):
   for bi in range(nb):
    s=bi*block;e=min(nt,s+block);code=int(codes[y,x,bi])
    if code==ZERO:Q[y,x,s:e]=R[y,x,s:e];continue
    if code==TEMP:
     for j in range(e-s):
      p=0 if s+j==0 else Q[y,x,s+j-1];Q[y,x,s+j]=R[y,x,s+j]+p
     continue
    if LEFT0<=code<=LEFT0+2*RADIUS:
     if x==0:raise RuntimeError(('left edge',code));lag=code-LEFT0-RADIUS;p=_shift_block(Q[y,x-1],s,e,lag)
    elif UP0<=code<=UP0+2*RADIUS:
     if y==0:raise RuntimeError(('up edge',code));lag=code-UP0-RADIUS;p=_shift_block(Q[y-1,x],s,e,lag)
    elif code==PLANE:
     if x==0 or y==0:raise RuntimeError(('plane edge',code));p64=Q[y,x-1,s:e].astype(np.int64)+Q[y-1,x,s:e].astype(np.int64)-Q[y-1,x-1,s:e].astype(np.int64);p=p64.astype(np.int32)
    elif LEX0<=code<=LEX0+2*RADIUS:
     if x<2:raise RuntimeError(('lex edge',code));lag=code-LEX0-RADIUS;p=(2*_shift_block(Q[y,x-1],s,e,lag).astype(np.int64)-_shift_block(Q[y,x-2],s,e,2*lag).astype(np.int64)).astype(np.int32)
    elif UEX0<=code<=UEX0+2*RADIUS:
     if y<2:raise RuntimeError(('uex edge',code));lag=code-UEX0-RADIUS;p=(2*_shift_block(Q[y-1,x],s,e,lag).astype(np.int64)-_shift_block(Q[y-2,x],s,e,2*lag).astype(np.int64)).astype(np.int32)
    elif code==MED:
     if x==0 or y==0:raise RuntimeError(('med edge',code));p=_med_predict(Q[y,x-1,s:e],Q[y-1,x,s:e],Q[y-1,x-1,s:e])
    else:raise RuntimeError(('bad block predictor code',code))
    Q[y,x,s:e]=R[y,x,s:e]+p
 return Q

def encode(X,eps,block):
 internal=float(eps)*base.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
 if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('quantized int32')
 Q=q.astype(np.int32);R,side=forward(Q,int(block));sideb=CCTX.compress(side);pid,payload=entropy.pack(R);ny,nx,nt=Q.shape
 h=struct.pack(HDR,MAGIC,float(eps),internal,ny,nx,nt,int(block),int(pid),len(sideb),len(payload));blob=h+sideb+payload
 return blob,{'transform':f'block_causal_b{block}','pack_id':int(pid),'block':int(block),'side_bytes':len(sideb),'payload_bytes':len(payload),'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64))))}
def decode(blob):
 if len(blob)<HSZ:raise RuntimeError('short block stream')
 magic,eps,internal,ny,nx,nt,block,pid,ns,npay=struct.unpack(HDR,blob[:HSZ])
 if magic!=MAGIC or len(blob)!=HSZ+ns+npay:raise RuntimeError('bad block stream')
 side=DCTX.decompress(blob[HSZ:HSZ+ns]);R=entropy.unpack(int(pid),blob[HSZ+ns:],(ny,nx,nt));Q=inverse(R,side,int(block));return Q.astype(np.float64)*(2*internal)
def compete_with_base(X,eps,base_compete):
 best0,rows0=base_compete(X,eps);rows=list(rows0);extra=[]
 for block in (64,128,256):
  blob,d=encode(X,eps,block);Y=decode(blob);me=base.hard(X,Y)
  if me>float(eps)*(1+3e-6):raise RuntimeError(('block hard bound',block,me,eps))
  extra.append({'tid':1000+block,'bytes':len(blob),'blob':blob,'maxerr':me,'diag':d})
 rows.extend(extra);best=min(rows,key=lambda r:(r['bytes'],r['tid']))
 return best,rows

def sanity():
 rng=np.random.default_rng(617);ny,nx,nt=5,9,383;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
 for y in range(ny):
  for x in range(nx):X[y,x]=(50*np.sin((t+3*x+2*y)/19)+18*np.sin((t-x+2*y)/8)+rng.normal(0,1.3,nt)).astype(np.float32)
 for b in (64,128,256):
  bb,d=encode(X,2.0,b);Y=decode(bb);me=base.hard(X,Y)
  if me>2.0*(1+3e-6):raise RuntimeError(('sanity',b,me))
  print('MV3D_BLOCK_SANITY',b,len(bb),me,d,flush=True)
if __name__=='__main__':sanity()
