#!/usr/bin/env python3
"""Slope-aware exact error-bounded codec for migrated seismic image panels.

Quantize once to an epsilon-valid integer lattice, then predict that lattice
along local reflector dip. Each trace/time block selects a decoder-visible lag
and one of three causal spatial predictors. Residual integers are zig-zag
mapped, byte-shuffled, and zstd compressed. No dataset label participates.
"""
from __future__ import annotations
import struct
import numpy as np
import zstandard as zstd

MAGIC=b"MVGEO1\0\0"
HDR="<8sddIIHBBII"
HSZ=struct.calcsize(HDR)
LAGS=tuple(range(-8,9))
MODES=(0,1,2)
BLOCKS=(64,128,256)

def _hard_error(a,b):
    return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64)))) if np.size(a) else 0.0

def _predict_block(Q,r,t0,t1,mode,lag):
    nt=Q.shape[1]
    idx=np.clip(np.arange(t0,t1,dtype=np.int64)+int(lag),0,nt-1)
    p1=Q[r-1,idx].astype(np.int64,copy=False)
    if mode==0 or r<2: return p1
    if mode==1:
        idx2=np.clip(np.arange(t0,t1,dtype=np.int64)+2*int(lag),0,nt-1)
        return 2*p1-Q[r-2,idx2].astype(np.int64,copy=False)
    out=np.empty(t1-t0,dtype=np.int64)
    for j,t in enumerate(range(t0,t1)):
        if t==0: out[j]=p1[j]
        else:
            ip=max(0,min(nt-1,t-1+int(lag)))
            out[j]=int(p1[j])+int(Q[r,t-1])-int(Q[r-1,ip])
    return out

def _cost(x):
    return float(np.log2(np.abs(np.asarray(x,np.int64))+1.0).sum())

def _choose_map(Q,block):
    nr,nt=Q.shape; nb=(nt+block-1)//block
    codes=np.zeros((max(0,nr-1),nb),dtype=np.uint8)
    for r in range(1,nr):
        for bi,t0 in enumerate(range(0,nt,block)):
            t1=min(nt,t0+block); target=Q[r,t0:t1].astype(np.int64,copy=False); best=None
            for mode in MODES:
                if mode==1 and r<2: continue
                for lag in LAGS:
                    residual=target-_predict_block(Q,r,t0,t1,mode,lag)
                    key=(_cost(residual),mode,abs(lag),lag)
                    if best is None or key<best[0]: best=(key,mode,lag)
            _,mode,lag=best; codes[r-1,bi]=np.uint8(mode*17+(lag+8))
    return codes

def _residual_from_map(Q,block,codes):
    nr,nt=Q.shape; R=np.empty_like(Q,dtype=np.int64)
    R[0,0]=int(Q[0,0])
    if nt>1: R[0,1]=int(Q[0,1])-int(Q[0,0])
    if nt>2: R[0,2:]=Q[0,2:].astype(np.int64)-2*Q[0,1:-1].astype(np.int64)+Q[0,:-2].astype(np.int64)
    for r in range(1,nr):
        for bi,t0 in enumerate(range(0,nt,block)):
            t1=min(nt,t0+block); code=int(codes[r-1,bi]); mode=code//17; lag=(code%17)-8
            R[r,t0:t1]=Q[r,t0:t1].astype(np.int64)-_predict_block(Q,r,t0,t1,mode,lag)
    return R

def _zigzag32(x):
    a=np.asarray(x,np.int64)
    if np.any(a<np.iinfo(np.int32).min) or np.any(a>np.iinfo(np.int32).max): raise OverflowError("residual exceeds int32")
    s=a.astype(np.int32); return ((s.astype(np.uint32)<<1)^(s>>31).astype(np.uint32)).astype(np.uint32)

def _unzigzag32(z):
    z=np.asarray(z,np.uint32); return ((z>>1).astype(np.int64)^-((z&1).astype(np.int64))).astype(np.int32)

def _pack(z,shuffle):
    b=np.asarray(z,np.uint32).reshape(-1).view(np.uint8).reshape(-1,4)
    return (b.T if shuffle else b).tobytes(order='C')

def _unpack(buf,n,shuffle):
    b=np.frombuffer(buf,dtype=np.uint8)
    if b.size!=4*n: raise RuntimeError(("bad residual length",b.size,4*n))
    b=b.reshape(4,n).T.copy() if shuffle else b.reshape(n,4)
    return b.reshape(-1).view(np.uint32).copy()

def _encode_candidate(X,eps,block):
    X=np.ascontiguousarray(X,dtype=np.float32)
    if X.ndim!=2: raise ValueError(X.shape)
    internal=float(eps)*(1.0-2e-6); step=2.0*internal
    q64=np.rint(X.astype(np.float64)/step)
    if np.any(q64<np.iinfo(np.int32).min) or np.any(q64>np.iinfo(np.int32).max): raise OverflowError("quantized lattice exceeds int32")
    Q=q64.astype(np.int32); codes=_choose_map(Q,int(block)); resid=_residual_from_map(Q,int(block),codes); zz=_zigzag32(resid)
    zc=zstd.ZstdCompressor(level=19,threads=0); map_blob=zc.compress(codes.tobytes())
    reps=[]
    for shuffle in (0,1):
        rb=zc.compress(_pack(zz,bool(shuffle))); reps.append((len(rb),shuffle,rb))
    _,shuffle,res_blob=min(reps,key=lambda x:(x[0],x[1]))
    hdr=struct.pack(HDR,MAGIC,float(eps),internal,int(Q.shape[0]),int(Q.shape[1]),int(block),int(shuffle),0,len(map_blob),len(res_blob))
    blob=hdr+map_blob+res_blob
    return blob,{"block":int(block),"shuffle":int(shuffle),"map_bytes":len(map_blob),"residual_bytes":len(res_blob),"mode_counts":np.bincount((codes//17).reshape(-1),minlength=3).tolist(),"lag_mean_abs":float(np.mean(np.abs((codes%17).astype(np.int16)-8))) if codes.size else 0.0}

def decode_stream(blob):
    magic,eps,internal,nr,nt,block,shuffle,_flags,map_n,res_n=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC: raise RuntimeError("bad migrated-volume magic")
    off=HSZ; zd=zstd.ZstdDecompressor(); nb=(int(nt)+int(block)-1)//int(block)
    map_raw=zd.decompress(blob[off:off+map_n],max_output_size=max(1,(int(nr)-1)*nb)); off+=map_n
    codes=np.frombuffer(map_raw,dtype=np.uint8).copy().reshape(max(0,int(nr)-1),nb)
    raw=zd.decompress(blob[off:off+res_n],max_output_size=int(nr)*int(nt)*4)
    resid=_unzigzag32(_unpack(raw,int(nr)*int(nt),bool(shuffle))).reshape(int(nr),int(nt)).astype(np.int64)
    Q=np.empty((int(nr),int(nt)),dtype=np.int64); Q[0,0]=resid[0,0]
    if nt>1: Q[0,1]=resid[0,1]+Q[0,0]
    if nt>2:
        for t in range(2,int(nt)): Q[0,t]=resid[0,t]+2*Q[0,t-1]-Q[0,t-2]
    for r in range(1,int(nr)):
        for bi,t0 in enumerate(range(0,int(nt),int(block))):
            t1=min(int(nt),t0+int(block)); code=int(codes[r-1,bi]); mode=code//17; lag=(code%17)-8
            for t in range(t0,t1):
                ip=max(0,min(int(nt)-1,t+lag)); p1=int(Q[r-1,ip])
                if mode==1 and r>=2:
                    ip2=max(0,min(int(nt)-1,t+2*lag)); pred=2*p1-int(Q[r-2,ip2])
                elif mode==2 and t>0:
                    ipp=max(0,min(int(nt)-1,t-1+lag)); pred=p1+int(Q[r,t-1])-int(Q[r-1,ipp])
                else: pred=p1
                Q[r,t]=int(resid[r,t])+pred
    return Q.astype(np.float64)*(2.0*float(internal)),{"epsilon":float(eps),"shape":[int(nr),int(nt)],"block":int(block),"shuffle":int(shuffle),"map_bytes":int(map_n),"residual_bytes":int(res_n)}

def encode_array(X,eps,blocks=BLOCKS):
    rows=[]
    for b in blocks:
        blob,meta=_encode_candidate(X,eps,int(b)); R,dmeta=decode_stream(blob); me=_hard_error(X,R)
        if me>float(eps)*(1.0+3e-6): raise RuntimeError(("hard-bound",b,me,eps))
        rows.append((len(blob),int(b),blob,meta,me,dmeta))
    nb,b,blob,meta,me,dmeta=min(rows,key=lambda x:(x[0],x[1]))
    return blob,{"bytes":int(nb),"block":int(b),"maxerr":float(me),**meta,"decoded_meta":dmeta,"candidates":[{"block":x[1],"bytes":x[0],"maxerr":x[4]} for x in rows]}
