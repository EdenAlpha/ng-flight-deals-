#!/usr/bin/env python3
"""No-side-information two-axis predictive-quantization candidates.

These candidates keep the v3 prediction-before-quantization principle but
replace its per-block coefficient map with a tiny fixed universal menu. On
interior traces the spatial predictor blends the already reconstructed fast-
and slow-axis neighbors, then applies the causal temporal correction. Each
candidate is a complete independently decodable stream and competes by bytes.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

PARAMS = {
    21:(0.9375,0.875),
    22:(0.96875,0.8125),
    23:(0.9375,0.7500),
    24:(1.0000,0.875),
}
NAMES = {k:f"predictive_q_blend_a{a:g}_w{w:g}" for k,(a,w) in PARAMS.items()}
MAGIC=b"MVPQ4\0\0\0"
HDR="<8sddIIIHHII"
HSZ=struct.calcsize(HDR)
_old_encode=None
_old_decode=None
_installed=False

def _forward(X,eps,a,w):
    X=np.asarray(X,np.float64)
    if X.ndim!=3: raise ValueError(X.shape)
    ny,nx,nt=X.shape
    internal=float(eps)*float(c.MARGIN); step=2.0*internal
    R=np.empty((ny,nx,nt),np.int32); Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        spatial=w*float(Y[y,x-1,t])+(1.0-w)*float(Y[y-1,x,t])
                        if t>0:
                            prevsp=w*float(Y[y,x-1,t-1])+(1.0-w)*float(Y[y-1,x,t-1])
                    else:
                        spatial=float(Y[y,x-1,t])
                        if t>0: prevsp=float(Y[y,x-1,t-1])
                    pred=a*spatial
                    if t>0: pred += float(Y[y,x,t-1])-a*prevsp
                elif y>0:
                    pred=a*float(Y[y-1,x,t])
                    if t>0: pred += float(Y[y,x,t-1])-a*float(Y[y-1,x,t-1])
                elif t>0:
                    pred=float(Y[y,x,t-1])
                else:
                    pred=0.0
                q=int(np.rint((float(X[y,x,t])-pred)/step))
                if q<np.iinfo(np.int32).min or q>np.iinfo(np.int32).max: raise OverflowError("blend residual int32")
                R[y,x,t]=q; Y[y,x,t]=pred+float(q)*step
    return R,Y,internal

def _inverse(R,internal,a,w):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;step=2.0*float(internal)
    Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        spatial=w*float(Y[y,x-1,t])+(1.0-w)*float(Y[y-1,x,t])
                        if t>0: prevsp=w*float(Y[y,x-1,t-1])+(1.0-w)*float(Y[y-1,x,t-1])
                    else:
                        spatial=float(Y[y,x-1,t])
                        if t>0: prevsp=float(Y[y,x-1,t-1])
                    pred=a*spatial
                    if t>0: pred += float(Y[y,x,t-1])-a*prevsp
                elif y>0:
                    pred=a*float(Y[y-1,x,t])
                    if t>0: pred += float(Y[y,x,t-1])-a*float(Y[y-1,x,t-1])
                elif t>0:
                    pred=float(Y[y,x,t-1])
                else:
                    pred=0.0
                Y[y,x,t]=pred+float(R[y,x,t])*step
    return Y

def encode_new(X,eps,tid):
    a,w=PARAMS[int(tid)]
    R,Y,internal=_forward(X,eps,float(a),float(w))
    payload,nbp=pq._pack_bitplanes(R)
    ny,nx,nt=R.shape
    hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),0,0,len(payload))
    blob=hdr+payload
    return blob,{
        "transform":NAMES[int(tid)],"a":float(a),"w_fast":float(w),
        "payload_bytes":len(payload),"side_bytes":0,"bitplanes":int(nbp),
        "nonzero_fraction":float(np.mean(R!=0)),
        "mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64)))),
        "encoder_reconstruction_maxerr":float(c.hard(X,Y))
    }

def decode_new(blob):
    if len(blob)<HSZ: raise RuntimeError("short blend stream")
    magic,eps,internal,ny,nx,nt,tid,_flags,ns,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or ns!=0 or int(tid) not in PARAMS: raise RuntimeError("bad blend header")
    if len(blob)!=HSZ+npay: raise RuntimeError(("blend length",len(blob),HSZ,npay))
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)))
    a,w=PARAMS[int(tid)]
    Y=_inverse(R,float(internal),float(a),float(w))
    return Y,{"shape":[int(ny),int(nx),int(nt)],"transform":NAMES[int(tid)],"eps":float(eps)}

def install():
    global _old_encode,_old_decode,_installed
    if _installed:return
    pq.install()
    _old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
    def enc(X,eps,tid):
        return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):
        return decode_new(blob) if len(blob)>=8 and blob[:8]==MAGIC else _old_decode(blob)
    c.encode=enc;c.decode=dec;_installed=True

def sanity():
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,9,257;t=np.arange(nt,dtype=np.float64)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):
            X[y,x]=(70*np.sin((t+2*x+3*y)/19)+18*np.sin((t-x+y)/7)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.
    for tid in PARAMS:
        b,d=encode_new(X,eps,tid);Y,m=decode_new(b);me=c.hard(X,Y)
        if me>eps*(1+3e-6):raise RuntimeError(("blend sanity",tid,me))
    print("MV3D_PQ_BLEND_V4_SANITY_OK",flush=True)

if __name__=="__main__":sanity()
