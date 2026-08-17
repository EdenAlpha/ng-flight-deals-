#!/usr/bin/env python3
"""Exact ft-half predictor + multi-traversal Brotli bitplane stream.

This composes two independently reversible, dataset-agnostic mechanisms:
  1) the causal fast-axis half temporal-mismatch predictor, and
  2) the existing per-bitplane Brotli traversal selector.
No fitted parameter or predictor map is transmitted. The only per-bitplane
choice is the decoder-known traversal id already charged by the Brotli format.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_fast_temporal_half as ft
import migrated_volume_3d_brotli_bitplanes as br

MAGIC=b'MVBRFTH1'
HDR='<8sddIIIHHII'
HSZ=struct.calcsize(HDR)
TID=2001
VERSION=1
MARGIN=1.0-1e-4
NAME='fast_temporal_half_brotli_multitraversal'


def encode(X,eps):
    eps=float(eps); internal=eps*MARGIN; step=2.0*internal
    q64=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q64<np.iinfo(np.int32).min)|(q64>np.iinfo(np.int32).max)):
        raise OverflowError('ft-half Brotli quantized field exceeds int32')
    Q=q64.astype(np.int32); R=ft.forward(Q)
    body,choices=br.encode_residual(R)
    ny,nx,nt=map(int,Q.shape)
    hdr=struct.pack(HDR,MAGIC,eps,internal,ny,nx,nt,TID,VERSION,len(body),0)
    blob=hdr+body
    diag={
        'transform':NAME,'pack_id':TID,'payload_bytes':len(body),'header_bytes':HSZ,
        'nonzero_fraction':float(np.mean(R!=0)),
        'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),
        'bitplanes':choices,
    }
    return blob,diag


def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short ft-half Brotli stream')
    magic,eps,internal,ny,nx,nt,tid,version,body_n,reserved=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or tid!=TID or version!=VERSION or reserved!=0:
        raise RuntimeError(('bad ft-half Brotli header',magic,tid,version,reserved))
    if len(blob)!=HSZ+body_n:raise RuntimeError(('ft-half Brotli length',len(blob),HSZ,body_n))
    R=br.decode_residual(blob[HSZ:],(int(ny),int(nx),int(nt)))
    Q=ft.inverse(R)
    X=Q.astype(np.float64)*(2.0*float(internal))
    return X,{'shape':[int(ny),int(nx),int(nt)],'public_eps':float(eps),'internal_eps':float(internal),'transform':NAME}


def candidate(X,eps):
    blob,diag=encode(X,eps); Y,_=decode(blob); me=br.hard_error(X,Y)
    if me>float(eps)*(1+3e-6):raise RuntimeError(('ft-half Brotli hard bound',me,eps))
    return {'tid':TID,'bytes':len(blob),'blob':blob,'maxerr':me,'diag':diag}


def sanity():
    rng=np.random.default_rng(2001); ny,nx,nt=4,13,277; t=np.arange(nt); X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        X[y,0]=(60*np.sin((t+2*y)/19)+rng.normal(0,2,nt)).astype(np.float32)
        for x in range(1,nx):
            X[y,x]=(0.94*X[y,x-1]+7*np.sin((t+x)/29)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.; b,d=encode(X,eps); Y,_=decode(b); me=br.hard_error(X,Y)
    if me>eps*(1+3e-6):raise RuntimeError(('ft-half Brotli sanity',me,eps))
    internal=eps*MARGIN; Q=np.rint(X.astype(np.float64)/(2*internal)).astype(np.int32); R=ft.forward(Q); RR=br.decode_residual(br.encode_residual(R)[0],R.shape)
    if not np.array_equal(R,RR) or not np.array_equal(Q,ft.inverse(RR)):raise RuntimeError('ft-half Brotli exact integer roundtrip')
    print('MV3D_FT_HALF_BROTLI_SANITY_OK',len(b),me,d,flush=True)

if __name__=='__main__':sanity()
