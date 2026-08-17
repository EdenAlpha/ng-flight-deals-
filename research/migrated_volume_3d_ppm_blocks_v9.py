#!/usr/bin/env python3
"""Compact additional PPM block scales for migrated 3-D seismic.

Extends the proven model-free PPM2 residual coder with two decoder-visible
causal predictor block sizes selected from exact native Waka screening: 80 and
112 samples. The existing portfolio already provides 64-bit-metric and
128-L1 modes. No dataset identity participates; actual serialized bytes choose.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a
import migrated_volume_3d_context_entropy_v3 as v3
import migrated_volume_3d_context_entropy_v5 as ppm

T_B80_PPM=34
T_B112_PPM=35
PARAMS={T_B80_PPM:(80,"bits"),T_B112_PPM:(112,"bits")}
NAMES={T_B80_PPM:"adaptive_block80_ppm2_arith",T_B112_PPM:"adaptive_block112_ppm2_arith"}
_old_encode=None
_old_decode=None
_installed=False

def encode_new(X,eps,tid):
    block,metric=PARAMS[int(tid)]
    internal=float(eps)*c.MARGIN;step=2*internal
    q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):
        raise OverflowError("ppm block quantized int32")
    Q=q.astype(np.int32)
    R,side=a.forward(Q,block,metric)
    codes=v3._codes(side,Q.shape,block)
    arith,raw,novel=ppm.ppm_encode(R,codes,block)
    body=struct.pack(ppm.INNER,len(arith),len(raw))+arith+raw
    sideb=c.CCTX.compress(side)
    ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body))
    blob=h+sideb+body
    return blob,{"transform":NAMES[int(tid)],"pack_id":104,"block":block,"metric":metric,"side_bytes":len(sideb),"model_bytes":0,"arithmetic_bytes":len(arith),"raw_novel_bytes":len(raw),"novel_symbols":int(novel),"payload_bytes":len(body),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64))))}

def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay or int(tid) not in PARAMS:
        raise RuntimeError("bad ppm block stream")
    block,_=PARAMS[int(tid)]
    side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b''
    codes=v3._codes(side,(ny,nx,nt),block)
    body=blob[c.HSZ+ns:]
    if len(body)<ppm.ISZ:raise RuntimeError("short ppm block body")
    na,nr=struct.unpack(ppm.INNER,body[:ppm.ISZ]);p=ppm.ISZ
    if p+na+nr!=len(body):raise RuntimeError(("ppm block lengths",len(body),na,nr))
    R=ppm.ppm_decode(body[p:p+na],body[p+na:p+na+nr],codes,(ny,nx,nt),block)
    Q=a.inverse(R,side,block)
    return Q.astype(np.float64)*(2*internal),{"shape":[ny,nx,nt],"transform":NAMES[int(tid)],"eps":eps,"arithmetic_bytes":na,"raw_novel_bytes":nr}

def install():
    global _old_encode,_old_decode,_installed
    if _installed:return
    _old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
    def enc(X,eps,tid):return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):
        if len(blob)<c.HSZ:raise RuntimeError("short")
        tid=struct.unpack(c.HDR,blob[:c.HSZ])[6]
        return decode_new(blob) if int(tid) in PARAMS else _old_decode(blob)
    c.encode=enc;c.decode=dec;_installed=True

def sanity():
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,10,347;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(70*np.sin((t+2*x+3*y)/18)+20*np.sin((t-x+y)/7)+rng.normal(0,2.5,nt)).astype(np.float32)
    eps=3.
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid);Y,m=c.decode(b);e=c.hard(X,Y)
        if e>eps*(1+3e-6):raise RuntimeError(("ppm block sanity",tid,e,eps))
        print("MV3D_PPM_BLOCK_V9_SANITY",NAMES[tid],len(b),e,d,flush=True)
if __name__=='__main__':sanity()
