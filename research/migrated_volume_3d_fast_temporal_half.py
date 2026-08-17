#!/usr/bin/env python3
"""Exact causal fast-axis predictor with half temporal mismatch correction.

For each native 3-D line y and fast trace x, quantization is unchanged. The
predictor is fully decoder-known and transmits no model or selector side-info:

  x == 0, t == 0: 0
  x == 0, t > 0 : Q[y,x,t-1]
  x > 0,  t == 0: Q[y,x-1,t]
  x > 0,  t > 0 : Q[y,x-1,t] + floor((Q[y,x,t-1]-Q[y,x-1,t-1])/2)

The correction tracks slowly evolving trace-to-trace mismatch while remaining
strictly causal. Integer floor division is part of the stream definition.
Residuals are encoded by whatever exact entropy backend is currently installed
(context entropy may compete automatically with the ordinary backend).
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c

TID=3000
NAME='fast_temporal_half'
_installed=False
_old_encode=None
_old_decode=None


def forward(Q):
    Q=np.asarray(Q,np.int32)
    if Q.ndim!=3: raise ValueError(Q.shape)
    ny,nx,nt=Q.shape
    R=np.empty_like(Q)
    for y in range(ny):
        # First trace is ordinary temporal DPCM so no raw trace is paid.
        R[y,0,0]=Q[y,0,0]
        if nt>1:
            d=Q[y,0,1:].astype(np.int64)-Q[y,0,:-1].astype(np.int64)
            if np.any((d<np.iinfo(np.int32).min)|(d>np.iinfo(np.int32).max)):
                raise OverflowError('ft-half first-trace residual')
            R[y,0,1:]=d.astype(np.int32)
        for x in range(1,nx):
            R[y,x,0]=np.int32(np.int64(Q[y,x,0])-np.int64(Q[y,x-1,0]))
            if nt>1:
                mismatch=Q[y,x,:-1].astype(np.int64)-Q[y,x-1,:-1].astype(np.int64)
                pred=Q[y,x-1,1:].astype(np.int64)+(mismatch//2)
                d=Q[y,x,1:].astype(np.int64)-pred
                if np.any((pred<np.iinfo(np.int32).min)|(pred>np.iinfo(np.int32).max)):
                    raise OverflowError('ft-half predictor')
                if np.any((d<np.iinfo(np.int32).min)|(d>np.iinfo(np.int32).max)):
                    raise OverflowError('ft-half residual')
                R[y,x,1:]=d.astype(np.int32)
    return R


def inverse(R):
    R=np.asarray(R,np.int32)
    if R.ndim!=3: raise ValueError(R.shape)
    ny,nx,nt=R.shape
    Q=np.empty_like(R)
    for y in range(ny):
        Q[y,0,0]=R[y,0,0]
        for t in range(1,nt):
            v=np.int64(R[y,0,t])+np.int64(Q[y,0,t-1])
            if v<np.iinfo(np.int32).min or v>np.iinfo(np.int32).max: raise OverflowError('ft-half inverse first trace')
            Q[y,0,t]=np.int32(v)
        for x in range(1,nx):
            v=np.int64(R[y,x,0])+np.int64(Q[y,x-1,0])
            if v<np.iinfo(np.int32).min or v>np.iinfo(np.int32).max: raise OverflowError('ft-half inverse t0')
            Q[y,x,0]=np.int32(v)
            for t in range(1,nt):
                mismatch=np.int64(Q[y,x,t-1])-np.int64(Q[y,x-1,t-1])
                pred=np.int64(Q[y,x-1,t])+(mismatch//2)
                v=np.int64(R[y,x,t])+pred
                if v<np.iinfo(np.int32).min or v>np.iinfo(np.int32).max: raise OverflowError('ft-half inverse')
                Q[y,x,t]=np.int32(v)
    return Q


def encode_new(X,eps):
    internal=float(eps)*c.MARGIN; step=2.0*internal
    q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):
        raise OverflowError('quantized int32')
    Q=q.astype(np.int32); R=forward(Q)
    pid,payload=c.pack(R); ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,TID,int(pid),0,len(payload))
    blob=h+payload
    return blob,{
        'transform':NAME,'pack_id':int(pid),'side_bytes':0,'payload_bytes':len(payload),
        'nonzero_fraction':float(np.mean(R!=0)),
        'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64))))
    }


def decode_new(blob):
    if len(blob)<c.HSZ: raise RuntimeError('short ft-half stream')
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or int(tid)!=TID or ns!=0 or len(blob)!=c.HSZ+npay:
        raise RuntimeError(('bad ft-half stream',magic,tid,ns,len(blob),npay))
    R=c.unpack(int(pid),blob[c.HSZ:],(int(ny),int(nx),int(nt)))
    Q=inverse(R)
    return Q.astype(np.float64)*(2.0*float(internal)),{'shape':[int(ny),int(nx),int(nt)],'transform':NAME,'eps':float(eps)}


def install():
    global _installed,_old_encode,_old_decode
    if _installed:return
    _old_encode=c.encode; _old_decode=c.decode
    c.NAMES[TID]=NAME
    def enc(X,eps,tid):
        return encode_new(X,eps) if int(tid)==TID else _old_encode(X,eps,tid)
    def dec(blob):
        if len(blob)>=c.HSZ:
            tid=struct.unpack(c.HDR,blob[:c.HSZ])[6]
            if int(tid)==TID:return decode_new(blob)
        return _old_decode(blob)
    c.encode=enc; c.decode=dec; _installed=True


def sanity():
    install(); rng=np.random.default_rng(300017); ny,nx,nt=4,11,257; t=np.arange(nt)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        base=80*np.sin((t+2*y)/21.0)+23*np.sin((t-y)/8.0)
        X[y,0]=(base+rng.normal(0,2,nt)).astype(np.float32)
        for x in range(1,nx):
            X[y,x]=(0.92*X[y,x-1]+8*np.sin((t+x)/35.0)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.0; b,d=encode_new(X,eps); Y,_=decode_new(b); me=c.hard(X,Y)
    if me>eps*(1+3e-6):raise RuntimeError(('ft-half sanity hard bound',me,eps))
    internal=eps*c.MARGIN; Q=np.rint(X.astype(np.float64)/(2*internal)).astype(np.int32)
    if not np.array_equal(Q,inverse(forward(Q))):raise RuntimeError('ft-half integer roundtrip')
    print('MV3D_FAST_TEMPORAL_HALF_SANITY_OK',len(b),me,d,flush=True)

if __name__=='__main__':sanity()
