#!/usr/bin/env python3
"""Correct inverse implementation for migrated_volume_3d_block_codec."""
import numpy as np
import migrated_volume_3d_block_codec as m

def inverse(R,side,block):
 R=np.asarray(R,np.int32);ny,nx,nt=R.shape;nb=(nt+block-1)//block
 codes=np.frombuffer(side,np.uint8)
 if codes.size!=ny*nx*nb:raise RuntimeError(('block side size',codes.size,ny*nx*nb))
 codes=codes.reshape(ny,nx,nb);Q=np.empty_like(R)
 for y in range(ny):
  for x in range(nx):
   for bi in range(nb):
    s=bi*block;e=min(nt,s+block);code=int(codes[y,x,bi])
    if code==m.ZERO:
     Q[y,x,s:e]=R[y,x,s:e];continue
    if code==m.TEMP:
     for j in range(e-s):
      pred=0 if s+j==0 else Q[y,x,s+j-1]
      Q[y,x,s+j]=R[y,x,s+j]+pred
     continue
    if m.LEFT0<=code<=m.LEFT0+2*m.RADIUS:
     if x==0:raise RuntimeError(('left edge',code))
     lag=code-m.LEFT0-m.RADIUS
     pred=m._shift_block(Q[y,x-1],s,e,lag)
    elif m.UP0<=code<=m.UP0+2*m.RADIUS:
     if y==0:raise RuntimeError(('up edge',code))
     lag=code-m.UP0-m.RADIUS
     pred=m._shift_block(Q[y-1,x],s,e,lag)
    elif code==m.PLANE:
     if x==0 or y==0:raise RuntimeError(('plane edge',code))
     p64=Q[y,x-1,s:e].astype(np.int64)+Q[y-1,x,s:e].astype(np.int64)-Q[y-1,x-1,s:e].astype(np.int64)
     pred=p64.astype(np.int32)
    elif m.LEX0<=code<=m.LEX0+2*m.RADIUS:
     if x<2:raise RuntimeError(('lex edge',code))
     lag=code-m.LEX0-m.RADIUS
     pred=(2*m._shift_block(Q[y,x-1],s,e,lag).astype(np.int64)-m._shift_block(Q[y,x-2],s,e,2*lag).astype(np.int64)).astype(np.int32)
    elif m.UEX0<=code<=m.UEX0+2*m.RADIUS:
     if y<2:raise RuntimeError(('uex edge',code))
     lag=code-m.UEX0-m.RADIUS
     pred=(2*m._shift_block(Q[y-1,x],s,e,lag).astype(np.int64)-m._shift_block(Q[y-2,x],s,e,2*lag).astype(np.int64)).astype(np.int32)
    elif code==m.MED:
     if x==0 or y==0:raise RuntimeError(('med edge',code))
     pred=m._med_predict(Q[y,x-1,s:e],Q[y-1,x,s:e],Q[y-1,x-1,s:e])
    else:
     raise RuntimeError(('bad block predictor code',code))
    Q[y,x,s:e]=R[y,x,s:e]+pred
 return Q

def install():
 m.inverse=inverse
 return m

if __name__=='__main__':
 install();m.sanity()
