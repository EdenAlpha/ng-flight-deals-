#!/usr/bin/env python3
"""Second-order causal context arithmetic for native migrated 3-D residuals.

Extends the proven v3 block predictor without changing reconstruction.  Entropy
context uses only decoder-known state: predictor family, previous residual
clipped to nine states, and residual two samples back quantized to five states.
The static frequency model is fully serialized as sparse varints and zstd-19
compressed.  No survey identity or encoder-only state participates.
"""
from __future__ import annotations
import struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a
import migrated_volume_3d_context_entropy_v3 as v3

T_B64_CTX2=13
T_B128L1_CTX2=14
PARAMS={T_B64_CTX2:(64,"bits"),T_B128L1_CTX2:(128,"l1")}
NAMES={T_B64_CTX2:"adaptive_block64_context2_arith",T_B128L1_CTX2:"adaptive_block128_l1_context2_arith"}
NCTX=8*9*5
NSYM=128
INNER="<III"
ISZ=struct.calcsize(INNER)
MODEL_C=zstd.ZstdCompressor(level=19)
MODEL_D=zstd.ZstdDecompressor()
_old_encode=None
_old_decode=None
_installed=False


def prev1_bucket(v):
    return max(-4,min(4,int(v)))+4


def prev2_bucket(v):
    v=int(v)
    if v<=-2:return 0
    if v==-1:return 1
    if v==0:return 2
    if v==1:return 3
    return 4


def context(code,p1,p2):
    return (v3.family(int(code))*9+prev1_bucket(p1))*5+prev2_bucket(p2)


def vu_put(out,n):
    n=int(n)
    if n<0:raise ValueError(n)
    while n>=128:
        out.append((n&127)|128);n>>=7
    out.append(n)


def vu_get(raw,pos):
    n=0;sh=0
    while True:
        if pos>=len(raw):raise RuntimeError("sparse model varint eof")
        b=raw[pos];pos+=1;n|=(b&127)<<sh
        if not (b&128):return n,pos
        sh+=7
        if sh>35:raise RuntimeError("sparse model varint overflow")


def pack_model(counts):
    counts=np.asarray(counts,np.uint32)
    used=np.flatnonzero(counts.sum(axis=1));raw=bytearray();vu_put(raw,len(used));pc=-1
    for ci in used:
        vu_put(raw,int(ci)-pc-1);pc=int(ci);nz=np.flatnonzero(counts[ci]);vu_put(raw,len(nz));ps=-1
        for si in nz:
            vu_put(raw,int(si)-ps-1);ps=int(si);vu_put(raw,int(counts[ci,si]))
    return MODEL_C.compress(bytes(raw))


def unpack_model(blob):
    raw=MODEL_D.decompress(blob);p=0;nused,p=vu_get(raw,p);counts=np.zeros((NCTX,NSYM),np.uint32);pc=-1
    for _ in range(nused):
        gap,p=vu_get(raw,p);ci=pc+1+gap;pc=ci
        if ci<0 or ci>=NCTX:raise RuntimeError(("sparse model context",ci))
        nnz,p=vu_get(raw,p);ps=-1
        for _ in range(nnz):
            sg,p=vu_get(raw,p);si=ps+1+sg;ps=si;cnt,p=vu_get(raw,p)
            if si<0 or si>=NSYM or cnt<=0:raise RuntimeError(("sparse model symbol",ci,si,cnt))
            counts[ci,si]=np.uint32(cnt)
    if p!=len(raw):raise RuntimeError(("sparse model trailing",p,len(raw)))
    return counts


def build_counts(R,codes,block):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;counts=np.zeros((NCTX,NSYM),np.uint32);esc=0
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                ctx=context(codes[y,x,t//block],p1,p2);val=int(R[y,x,t]);z=v3.zig_value(val);sym=z if z<NSYM-1 else NSYM-1
                counts[ctx,sym]+=1
                if sym==NSYM-1:esc+=1
                p2,p1=p1,val
    return counts,esc


def arithmetic_encode(R,codes,block,counts):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape
    pref=np.zeros((NCTX,NSYM+1),np.uint64);pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    low=0;high=v3.TOP;pending=0;bw=v3.BitWriter();escape=bytearray()
    def emit(bit):
        nonlocal pending
        bw.bit(bit)
        while pending:bw.bit(1-int(bit));pending-=1
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                ctx=context(codes[y,x,t//block],p1,p2);val=int(R[y,x,t]);z=v3.zig_value(val);sym=z if z<NSYM-1 else NSYM-1
                total=int(pref[ctx,NSYM]);lo=int(pref[ctx,sym]);hi=int(pref[ctx,sym+1])
                if total<=0 or hi<=lo:raise RuntimeError(("bad ctx2 model",ctx,sym,total,lo,hi))
                rng=high-low+1;high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<v3.HALF:emit(0)
                    elif low>=v3.HALF:emit(1);low-=v3.HALF;high-=v3.HALF
                    elif low>=v3.Q1 and high<v3.Q3:pending+=1;low-=v3.Q1;high-=v3.Q1
                    else:break
                    low=(low<<1)&v3.TOP;high=((high<<1)&v3.TOP)|1
                if sym==NSYM-1:
                    q=z
                    while q>=128:escape.append((q&127)|128);q>>=7
                    escape.append(q)
                p2,p1=p1,val
    pending+=1;emit(0 if low<v3.Q1 else 1)
    return bw.finish(),bytes(escape)


def arithmetic_decode(arith,escape,codes,shape,block,counts):
    ny,nx,nt=map(int,shape);pref=np.zeros((NCTX,NSYM+1),np.uint64);pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    br=v3.BitReader(arith);code=0
    for _ in range(32):code=((code<<1)|br.bit())&v3.TOP
    low=0;high=v3.TOP;ep=0;R=np.empty((ny,nx,nt),np.int32)
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                ctx=context(codes[y,x,t//block],p1,p2);total=int(pref[ctx,NSYM])
                if total<=0:raise RuntimeError(("empty ctx2",ctx))
                rng=high-low+1;scaled=((code-low+1)*total-1)//rng;row=pref[ctx];sym=int(np.searchsorted(row,scaled,side="right")-1)
                if sym<0 or sym>=NSYM or int(counts[ctx,sym])<=0:raise RuntimeError(("ctx2 symbol",ctx,sym,scaled,total))
                lo=int(row[sym]);hi=int(row[sym+1]);high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<v3.HALF:pass
                    elif low>=v3.HALF:low-=v3.HALF;high-=v3.HALF;code-=v3.HALF
                    elif low>=v3.Q1 and high<v3.Q3:low-=v3.Q1;high-=v3.Q1;code-=v3.Q1
                    else:break
                    low=(low<<1)&v3.TOP;high=((high<<1)&v3.TOP)|1;code=((code<<1)&v3.TOP)|br.bit()
                if sym<NSYM-1:z=sym
                else:
                    z=0;sh=0
                    while True:
                        if ep>=len(escape):raise RuntimeError("ctx2 escape eof")
                        b=escape[ep];ep+=1;z|=(b&127)<<sh
                        if not (b&128):break
                        sh+=7
                        if sh>63:raise RuntimeError("ctx2 escape overflow")
                val=v3.unzig_value(z);R[y,x,t]=val;p2,p1=p1,val
    if ep!=len(escape):raise RuntimeError(("ctx2 escape trailing",ep,len(escape)))
    return R


def encode_new(X,eps,tid):
    block,metric=PARAMS[int(tid)];internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError("quantized int32")
    Q=q.astype(np.int32);R,side=a.forward(Q,block,metric);codes=v3._codes(side,Q.shape,block);counts,nesc=build_counts(R,codes,block)
    modelb=pack_model(counts);arith,escape=arithmetic_encode(R,codes,block,counts);body=struct.pack(INNER,len(modelb),len(arith),len(escape))+modelb+arith+escape;sideb=c.CCTX.compress(side);ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body));blob=h+sideb+body
    return blob,{"transform":NAMES[int(tid)],"pack_id":101,"block":block,"metric":metric,"side_bytes":len(sideb),"model_bytes":len(modelb),"arithmetic_bytes":len(arith),"escape_bytes":len(escape),"escape_symbols":int(nesc),"payload_bytes":len(body),"used_contexts":int(np.count_nonzero(counts.sum(axis=1))),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64))))}


def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay:raise RuntimeError("bad ctx2 stream")
    block,_=PARAMS[int(tid)];side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b'';codes=v3._codes(side,(ny,nx,nt),block);body=blob[c.HSZ+ns:]
    if len(body)<ISZ:raise RuntimeError("short ctx2 payload")
    nm,na,ne=struct.unpack(INNER,body[:ISZ]);p=ISZ
    if p+nm+na+ne!=len(body):raise RuntimeError(("ctx2 lengths",len(body),nm,na,ne))
    counts=unpack_model(body[p:p+nm]);p+=nm;arith=body[p:p+na];p+=na;escape=body[p:p+ne];R=arithmetic_decode(arith,escape,codes,(ny,nx,nt),block,counts);Q=a.inverse(R,side,block)
    return Q.astype(np.float64)*(2*internal),{"shape":[ny,nx,nt],"transform":NAMES[int(tid)],"eps":eps,"model_bytes":nm,"arithmetic_bytes":na,"escape_bytes":ne}


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
    install();rng=np.random.default_rng(4172026);ny,nx,nt=4,12,321;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(75*np.sin((t+3*x+2*y)/18)+24*np.sin((t-x+y)/8)+rng.normal(0,2.5,nt)).astype(np.float32)
    eps=3.0
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid);Y,m=c.decode(b);e=c.hard(X,Y)
        if e>eps*(1+3e-6):raise RuntimeError(("ctx2 sanity",tid,e,eps))
        print("MV3D_CONTEXT2_SANITY",NAMES[tid],len(b),e,d,flush=True)

if __name__=='__main__':sanity()
