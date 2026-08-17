#!/usr/bin/env python3
"""3-D boundary refinement of the exact ft-half + Brotli stream.

Interior traces use the fast-axis half temporal-mismatch predictor. The first
trace of each subsequent slow-axis line uses the identical causal rule against
the previous slow-axis line. Only the very first trace uses temporal DPCM.
There is no model/selector side stream; this is a fixed decoder-known transform.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_brotli_bitplanes as br

MAGIC=b'MVBRFH3D'
HDR='<8sddIIIHHII'; HSZ=struct.calcsize(HDR)
TID=2002; VERSION=1; MARGIN=1.0-1e-4
NAME='fast_temporal_half_3d_boundary_brotli'


def forward(Q):
    Q=np.asarray(Q,np.int32); ny,nx,nt=Q.shape; R=np.empty_like(Q)
    lo=np.iinfo(np.int32).min; hi=np.iinfo(np.int32).max
    for y in range(ny):
        if y==0:
            R[0,0,0]=Q[0,0,0]
            if nt>1:
                d=Q[0,0,1:].astype(np.int64)-Q[0,0,:-1].astype(np.int64)
                if np.any((d<lo)|(d>hi)):raise OverflowError('fh3d first temporal residual')
                R[0,0,1:]=d.astype(np.int32)
        else:
            d0=np.int64(Q[y,0,0])-np.int64(Q[y-1,0,0])
            if d0<lo or d0>hi:raise OverflowError('fh3d slow boundary t0')
            R[y,0,0]=np.int32(d0)
            if nt>1:
                mm=Q[y,0,:-1].astype(np.int64)-Q[y-1,0,:-1].astype(np.int64)
                pred=Q[y-1,0,1:].astype(np.int64)+(mm//2)
                d=Q[y,0,1:].astype(np.int64)-pred
                if np.any((pred<lo)|(pred>hi)) or np.any((d<lo)|(d>hi)):raise OverflowError('fh3d slow boundary')
                R[y,0,1:]=d.astype(np.int32)
        for x in range(1,nx):
            d0=np.int64(Q[y,x,0])-np.int64(Q[y,x-1,0])
            if d0<lo or d0>hi:raise OverflowError('fh3d fast t0')
            R[y,x,0]=np.int32(d0)
            if nt>1:
                mm=Q[y,x,:-1].astype(np.int64)-Q[y,x-1,:-1].astype(np.int64)
                pred=Q[y,x-1,1:].astype(np.int64)+(mm//2)
                d=Q[y,x,1:].astype(np.int64)-pred
                if np.any((pred<lo)|(pred>hi)) or np.any((d<lo)|(d>hi)):raise OverflowError('fh3d fast')
                R[y,x,1:]=d.astype(np.int32)
    return R


def inverse(R):
    R=np.asarray(R,np.int32); ny,nx,nt=R.shape; Q=np.empty_like(R)
    lo=np.iinfo(np.int32).min; hi=np.iinfo(np.int32).max
    for y in range(ny):
        if y==0:
            Q[0,0,0]=R[0,0,0]
            for t in range(1,nt):
                v=np.int64(R[0,0,t])+np.int64(Q[0,0,t-1])
                if v<lo or v>hi:raise OverflowError('fh3d inverse first')
                Q[0,0,t]=np.int32(v)
        else:
            v=np.int64(R[y,0,0])+np.int64(Q[y-1,0,0])
            if v<lo or v>hi:raise OverflowError('fh3d inverse slow t0')
            Q[y,0,0]=np.int32(v)
            for t in range(1,nt):
                mm=np.int64(Q[y,0,t-1])-np.int64(Q[y-1,0,t-1])
                pred=np.int64(Q[y-1,0,t])+(mm//2); v=np.int64(R[y,0,t])+pred
                if pred<lo or pred>hi or v<lo or v>hi:raise OverflowError('fh3d inverse slow')
                Q[y,0,t]=np.int32(v)
        for x in range(1,nx):
            v=np.int64(R[y,x,0])+np.int64(Q[y,x-1,0])
            if v<lo or v>hi:raise OverflowError('fh3d inverse fast t0')
            Q[y,x,0]=np.int32(v)
            for t in range(1,nt):
                mm=np.int64(Q[y,x,t-1])-np.int64(Q[y,x-1,t-1])
                pred=np.int64(Q[y,x-1,t])+(mm//2); v=np.int64(R[y,x,t])+pred
                if pred<lo or pred>hi or v<lo or v>hi:raise OverflowError('fh3d inverse fast')
                Q[y,x,t]=np.int32(v)
    return Q


def encode(X,eps):
    eps=float(eps); internal=eps*MARGIN; step=2.0*internal
    q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('fh3d quantized int32')
    Q=q.astype(np.int32); R=forward(Q); body,choices=br.encode_residual(R); ny,nx,nt=map(int,Q.shape)
    blob=struct.pack(HDR,MAGIC,eps,internal,ny,nx,nt,TID,VERSION,len(body),0)+body
    return blob,{'transform':NAME,'pack_id':TID,'payload_bytes':len(body),'header_bytes':HSZ,'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),'bitplanes':choices}


def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short fh3d stream')
    magic,eps,internal,ny,nx,nt,tid,ver,n,res=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or tid!=TID or ver!=VERSION or res!=0 or len(blob)!=HSZ+n:raise RuntimeError(('bad fh3d stream',magic,tid,ver,res,len(blob),n))
    R=br.decode_residual(blob[HSZ:],(int(ny),int(nx),int(nt))); Q=inverse(R)
    return Q.astype(np.float64)*(2.0*float(internal)),{'shape':[int(ny),int(nx),int(nt)],'transform':NAME,'eps':float(eps)}


def candidate(X,eps):
    b,d=encode(X,eps); Y,_=decode(b); me=br.hard_error(X,Y)
    if me>float(eps)*(1+3e-6):raise RuntimeError(('fh3d hard bound',me,eps))
    return {'tid':TID,'bytes':len(b),'blob':b,'maxerr':me,'diag':d}


def sanity():
    rng=np.random.default_rng(2002); ny,nx,nt=5,11,271; t=np.arange(nt); X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        X[y,0]=(65*np.sin((t+2*y)/21)+rng.normal(0,2,nt)).astype(np.float32)
        for x in range(1,nx):X[y,x]=(0.94*X[y,x-1]+5*np.sin((t+x+y)/27)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.; b,d=encode(X,eps); Y,_=decode(b); me=br.hard_error(X,Y)
    if me>eps*(1+3e-6):raise RuntimeError(('fh3d sanity hard',me,eps))
    q=np.rint(X.astype(np.float64)/(2*eps*MARGIN)).astype(np.int32)
    if not np.array_equal(q,inverse(forward(q))):raise RuntimeError('fh3d integer roundtrip')
    print('MV3D_FT_HALF3D_BROTLI_SANITY_OK',len(b),me,d,flush=True)

if __name__=='__main__':sanity()
