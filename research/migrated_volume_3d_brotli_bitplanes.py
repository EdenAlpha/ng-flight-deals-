#!/usr/bin/env python3
"""Exact fast-delta + multi-traversal Brotli bitplane codec for 3-D seismic.

The codec is dataset-agnostic. After the public error-bounded scalar
quantization, it takes an exact integer fast-spatial delta. Each ZigZag
bitplane independently selects the smallest actual Brotli stream among a fixed
set of decoder-known 3-D traversal orders. Traversal ids and byte lengths are
serialized and charged. The decoder reconstructs the exact quantized integer
field before dequantization.
"""
from __future__ import annotations

import struct
import numpy as np
import brotli

MAGIC=b'MVBRBP1\0'
HDR='<8sddIIIHHII'
HSZ=struct.calcsize(HDR)  # deliberately 48 bytes
TID=2000
VERSION=1
MARGIN=1.0-1e-4

TRAVERSALS=('bxyt4','bxyt8','xty')
TRAV_ID={s:i for i,s in enumerate(TRAVERSALS)}


def hard_error(a,b):
    return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))


def _perm_indices(shape,spec):
    ny,nx,nt=map(int,shape)
    I=np.arange(ny*nx*nt,dtype=np.int64).reshape((ny,nx,nt))
    if spec=='xty':
        return np.transpose(I,(1,2,0)).reshape(-1)
    if spec.startswith('bxyt'):
        bt=int(spec[4:]); nb=(nt+bt-1)//bt; pad=nb*bt-nt
        A=np.pad(I,((0,0),(0,0),(0,pad)),constant_values=-1).reshape(ny,nx,nb,bt)
        return np.transpose(A,(2,1,0,3)).reshape(-1)  # time-block,x,y,t-within-block
    raise ValueError(spec)


def _zigzag32(a):
    a=np.asarray(a,np.int64).reshape(-1)
    z=(a<<1)^(a>>63)
    if np.any((z<0)|(z>np.iinfo(np.uint32).max)):
        raise OverflowError('zigzag32 overflow')
    return z.astype(np.uint32)


def _unzigzag32(z):
    z=np.asarray(z,np.uint32).astype(np.uint64)
    a=(z>>1).astype(np.int64)^-((z&1).astype(np.int64))
    if np.any((a<np.iinfo(np.int32).min)|(a>np.iinfo(np.int32).max)):
        raise OverflowError('unzigzag32 overflow')
    return a.astype(np.int32)


def _fast_delta(Q):
    Q=np.asarray(Q,np.int32)
    R=np.empty_like(Q)
    R[:,0,:]=Q[:,0,:]
    if Q.shape[1]>1:
        d=Q[:,1:,:].astype(np.int64)-Q[:,:-1,:].astype(np.int64)
        if np.any((d<np.iinfo(np.int32).min)|(d>np.iinfo(np.int32).max)):
            raise OverflowError('fast-delta int32 overflow')
        R[:,1:,:]=d.astype(np.int32)
    return R


def _fast_inverse(R):
    # Use int64 for the accumulation and explicitly prove the reconstructed
    # quantized field remains representable before returning int32.
    q=np.cumsum(np.asarray(R,np.int32).astype(np.int64),axis=1,dtype=np.int64)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):
        raise OverflowError('fast-inverse int32 overflow')
    return q.astype(np.int32)


def encode_residual(R):
    shape=tuple(map(int,R.shape)); flat=_zigzag32(R)
    maxz=int(flat.max()) if flat.size else 0
    nb=maxz.bit_length()
    perms={s:_perm_indices(shape,s) for s in TRAVERSALS}
    chosen=[]
    for bit in range(nb):
        best=None
        for spec,idx in perms.items():
            valid=idx>=0
            vals=np.zeros(idx.size,dtype=np.uint8)
            vals[valid]=((flat[idx[valid]]>>bit)&1).astype(np.uint8)
            raw=np.packbits(vals,bitorder='little').tobytes()
            comp=brotli.compress(raw,quality=11)
            cand=(len(comp),TRAV_ID[spec],comp)
            if best is None or cand[:2]<best[:2]:
                best=cand
        chosen.append(best)
    body=bytearray([nb])
    for L,sid,comp in chosen:
        body += struct.pack('<BI',sid,L)
    for L,sid,comp in chosen:
        body += comp
    choices=[{'bitplane':i,'traversal':TRAVERSALS[sid],'bytes':int(L)} for i,(L,sid,_) in enumerate(chosen)]
    return bytes(body),choices


def decode_residual(body,shape):
    if not body:
        raise RuntimeError('empty Brotli bitplane body')
    nb=int(body[0]); p=1; meta=[]
    for _ in range(nb):
        if p+5>len(body): raise RuntimeError('short bitplane descriptor')
        sid,L=struct.unpack('<BI',body[p:p+5]); p+=5
        if sid>=len(TRAVERSALS): raise RuntimeError(('bad traversal id',sid))
        meta.append((int(sid),int(L)))
    n=int(np.prod(shape)); zz=np.zeros(n,dtype=np.uint32)
    for bit,(sid,L) in enumerate(meta):
        if p+L>len(body): raise RuntimeError('short Brotli bitplane payload')
        comp=body[p:p+L]; p+=L
        spec=TRAVERSALS[sid]; idx=_perm_indices(shape,spec)
        raw=brotli.decompress(comp)
        need=(idx.size+7)//8
        if len(raw)!=need:
            raise RuntimeError(('bitplane raw length',len(raw),need,spec))
        bits=np.unpackbits(np.frombuffer(raw,dtype=np.uint8),bitorder='little',count=idx.size).astype(np.uint32)
        valid=idx>=0
        zz[idx[valid]] |= (bits[valid]<<bit)
    if p!=len(body): raise RuntimeError(('trailing Brotli bytes',p,len(body)))
    return _unzigzag32(zz).reshape(shape)


def encode(X,eps):
    eps=float(eps); internal=eps*MARGIN; step=2.0*internal
    q64=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q64<np.iinfo(np.int32).min)|(q64>np.iinfo(np.int32).max)):
        raise OverflowError('quantized field exceeds int32')
    Q=q64.astype(np.int32); R=_fast_delta(Q)
    body,choices=encode_residual(R)
    ny,nx,nt=map(int,Q.shape)
    hdr=struct.pack(HDR,MAGIC,eps,internal,ny,nx,nt,TID,VERSION,len(body),0)
    blob=hdr+body
    diag={
        'transform':'fast_delta_brotli_multitraversal',
        'pack_id':2000,
        'payload_bytes':len(body),
        'header_bytes':HSZ,
        'nonzero_fraction':float(np.mean(R!=0)),
        'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),
        'bitplanes':choices,
    }
    return blob,diag


def decode(blob):
    if len(blob)<HSZ: raise RuntimeError('short Brotli 3-D stream')
    magic,eps,internal,ny,nx,nt,tid,version,body_n,reserved=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or tid!=TID or version!=VERSION or reserved!=0:
        raise RuntimeError(('bad Brotli 3-D header',magic,tid,version,reserved))
    if len(blob)!=HSZ+body_n:
        raise RuntimeError(('Brotli 3-D stream length',len(blob),HSZ,body_n))
    R=decode_residual(blob[HSZ:],(int(ny),int(nx),int(nt)))
    Q=_fast_inverse(R)
    X=Q.astype(np.float64)*(2.0*float(internal))
    return X,{'shape':[int(ny),int(nx),int(nt)],'public_eps':float(eps),'internal_eps':float(internal),'transform':'fast_delta_brotli_multitraversal'}


def candidate(X,eps):
    blob,diag=encode(X,eps); Y,_=decode(blob); me=hard_error(X,Y)
    if me>float(eps)*(1+3e-6):
        raise RuntimeError(('Brotli 3-D hard bound',me,eps))
    return {'tid':TID,'bytes':len(blob),'blob':blob,'maxerr':me,'diag':diag}


def sanity():
    rng=np.random.default_rng(20260817); ny,nx,nt=5,11,259; t=np.arange(nt)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):
            X[y,x]=(60*np.sin((t+2*x+3*y)/21.0)+17*np.sin((t-x+y)/8.0)+rng.normal(0,1.4,nt)).astype(np.float32)
    eps=2.25; blob,diag=encode(X,eps); Y,_=decode(blob); me=hard_error(X,Y)
    if me>eps*(1+3e-6): raise RuntimeError(('sanity hard bound',me,eps))
    # Also verify the residual representation itself exactly.
    internal=eps*MARGIN; Q=np.rint(X.astype(np.float64)/(2*internal)).astype(np.int32); R=_fast_delta(Q)
    body,_=encode_residual(R); RR=decode_residual(body,R.shape)
    if not np.array_equal(R,RR): raise RuntimeError('residual roundtrip mismatch')
    print('MV3D_BROTLI_SANITY_OK',len(blob),me,diag,flush=True)

if __name__=='__main__':
    sanity()
