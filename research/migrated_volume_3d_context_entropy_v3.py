#!/usr/bin/env python3
"""Context arithmetic entropy extension for migrated-volume native 3-D codec.

The block predictor already serializes a decoder-visible predictor code.  This
extension uses only decoder-known information — predictor family and the
previous decoded residual in the same trace — as an entropy context.  A static
per-tile frequency model is fully serialized and compressed.  No survey label,
object identity, or hidden encoder state participates.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a

T_B64_CTX = 11
T_B128L1_CTX = 12
PARAMS = {T_B64_CTX:(64,"bits"), T_B128L1_CTX:(128,"l1")}
NAMES = {T_B64_CTX:"adaptive_block64_context_arith", T_B128L1_CTX:"adaptive_block128_l1_context_arith"}
INNER = "<III"
INNER_SIZE = struct.calcsize(INNER)
NCTX = 72
NSYM = 128
TOP = (1<<32)-1
HALF = 1<<31
Q1 = 1<<30
Q3 = 3<<30
_old_encode = None
_old_decode = None
_installed = False


def family(code):
    code=int(code)
    if code <= 2: return code
    if code < 48: return 3
    if code < 80: return 4
    if code < 112: return 5
    if code < 144: return 6
    return 7


def prev_bucket(v):
    v=int(v)
    if v < -3: return 0
    if v > 3: return 8
    return v + 4


def zig_value(v):
    v=int(v)
    return (v << 1) ^ (v >> 63)


def unzig_value(z):
    z=int(z)
    return (z >> 1) ^ -(z & 1)


class BitWriter:
    def __init__(self):
        self.out=bytearray(); self.cur=0; self.n=0
    def bit(self,b):
        self.cur=(self.cur<<1)|(int(b)&1); self.n+=1
        if self.n==8:
            self.out.append(self.cur); self.cur=0; self.n=0
    def finish(self):
        if self.n: self.out.append(self.cur << (8-self.n))
        return bytes(self.out)


class BitReader:
    def __init__(self,data): self.data=data; self.pos=0
    def bit(self):
        if self.pos >= len(self.data)*8: return 0
        b=(self.data[self.pos>>3] >> (7-(self.pos&7))) & 1
        self.pos += 1
        return b


def _codes(side,shape,block):
    ny,nx,nt=map(int,shape); nb=(nt+int(block)-1)//int(block)
    q=np.frombuffer(side,np.uint8)
    if q.size != ny*nx*nb: raise RuntimeError(("context code side",q.size,ny,nx,nb))
    return q.reshape(ny,nx,nb)


def build_counts(R,codes,block):
    R=np.asarray(R,np.int32); ny,nx,nt=R.shape
    counts=np.zeros((NCTX,NSYM),np.uint32)
    escapes=0
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=family(codes[y,x,t//block])*9 + prev_bucket(prev)
                v=int(R[y,x,t]); z=zig_value(v); sym=z if z < NSYM-1 else NSYM-1
                counts[ctx,sym]+=1
                if sym==NSYM-1: escapes+=1
                prev=v
    return counts,escapes


def pack_model(counts):
    q=np.ascontiguousarray(counts.astype('<u4',copy=False)).reshape(-1)
    raw=q.view(np.uint8).reshape(-1,4).T.copy().tobytes()
    return c.CCTX.compress(raw)


def unpack_model(blob):
    raw=c.DCTX.decompress(blob)
    n=NCTX*NSYM
    u=np.frombuffer(raw,np.uint8)
    if u.size != n*4: raise RuntimeError(("context model size",u.size,n*4))
    q=u.reshape(4,n).T.copy().reshape(n*4).view('<u4').copy()
    return q.reshape(NCTX,NSYM)


def arithmetic_encode(R,codes,block,counts):
    R=np.asarray(R,np.int32); ny,nx,nt=R.shape
    pref=np.zeros((NCTX,NSYM+1),np.uint64)
    pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    low=0; high=TOP; pending=0; bw=BitWriter(); escape=bytearray()
    def emit(bit):
        nonlocal pending
        bw.bit(bit)
        while pending:
            bw.bit(1-int(bit)); pending-=1
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=family(codes[y,x,t//block])*9 + prev_bucket(prev)
                v=int(R[y,x,t]); z=zig_value(v); sym=z if z < NSYM-1 else NSYM-1
                total=int(pref[ctx,NSYM]); lo=int(pref[ctx,sym]); hi=int(pref[ctx,sym+1])
                if total<=0 or hi<=lo: raise RuntimeError(("bad context model",ctx,sym,total,lo,hi))
                rng=high-low+1
                high=low+(rng*hi//total)-1
                low=low+(rng*lo//total)
                while True:
                    if high < HALF: emit(0)
                    elif low >= HALF:
                        emit(1); low-=HALF; high-=HALF
                    elif low >= Q1 and high < Q3:
                        pending+=1; low-=Q1; high-=Q1
                    else: break
                    low=(low<<1)&TOP; high=((high<<1)&TOP)|1
                if sym==NSYM-1:
                    q=z
                    while q>=128:
                        escape.append((q&127)|128); q>>=7
                    escape.append(q)
                prev=v
    pending+=1
    emit(0 if low < Q1 else 1)
    return bw.finish(),bytes(escape)


def arithmetic_decode(arith,escape,codes,shape,block,counts):
    ny,nx,nt=map(int,shape)
    pref=np.zeros((NCTX,NSYM+1),np.uint64)
    pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    br=BitReader(arith); code=0
    for _ in range(32): code=((code<<1)|br.bit())&TOP
    low=0; high=TOP; ep=0; R=np.empty((ny,nx,nt),np.int32)
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=family(codes[y,x,t//block])*9 + prev_bucket(prev)
                total=int(pref[ctx,NSYM])
                if total<=0: raise RuntimeError(("empty context used",ctx))
                rng=high-low+1
                scaled=((code-low+1)*total-1)//rng
                row=pref[ctx]
                sym=int(np.searchsorted(row,scaled,side='right')-1)
                if sym<0 or sym>=NSYM or int(counts[ctx,sym])<=0:
                    raise RuntimeError(("context symbol",ctx,sym,scaled,total))
                lo=int(row[sym]); hi=int(row[sym+1])
                high=low+(rng*hi//total)-1
                low=low+(rng*lo//total)
                while True:
                    if high < HALF: pass
                    elif low >= HALF:
                        low-=HALF; high-=HALF; code-=HALF
                    elif low >= Q1 and high < Q3:
                        low-=Q1; high-=Q1; code-=Q1
                    else: break
                    low=(low<<1)&TOP; high=((high<<1)&TOP)|1; code=((code<<1)&TOP)|br.bit()
                if sym < NSYM-1: z=sym
                else:
                    z=0; sh=0
                    while True:
                        if ep>=len(escape): raise RuntimeError("context escape eof")
                        b=escape[ep]; ep+=1; z|=(b&127)<<sh
                        if not (b&128): break
                        sh+=7
                        if sh>63: raise RuntimeError("context escape overflow")
                v=unzig_value(z); R[y,x,t]=v; prev=v
    if ep != len(escape): raise RuntimeError(("context escape trailing",ep,len(escape)))
    return R


def encode_new(X,eps,tid):
    block,metric=PARAMS[int(tid)]
    internal=float(eps)*c.MARGIN; step=2*internal
    q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)): raise OverflowError("quantized int32")
    Q=q.astype(np.int32); R,side=a.forward(Q,block,metric); codes=_codes(side,Q.shape,block)
    counts,nesc=build_counts(R,codes,block); modelb=pack_model(counts); arith,escape=arithmetic_encode(R,codes,block,counts)
    body=struct.pack(INNER,len(modelb),len(arith),len(escape))+modelb+arith+escape
    sideb=c.CCTX.compress(side); ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body))
    blob=h+sideb+body
    return blob,{"transform":NAMES[int(tid)],"pack_id":100,"block":block,"metric":metric,"side_bytes":len(sideb),"model_bytes":len(modelb),"arithmetic_bytes":len(arith),"escape_bytes":len(escape),"escape_symbols":int(nesc),"payload_bytes":len(body),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64))))}


def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay: raise RuntimeError("bad context stream")
    block,_=PARAMS[int(tid)]
    side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b''
    codes=_codes(side,(ny,nx,nt),block)
    body=blob[c.HSZ+ns:]
    if len(body)<INNER_SIZE: raise RuntimeError("short context payload")
    nm,na,ne=struct.unpack(INNER,body[:INNER_SIZE]); p=INNER_SIZE
    if p+nm+na+ne != len(body): raise RuntimeError(("context payload lengths",len(body),nm,na,ne))
    modelb=body[p:p+nm]; p+=nm; arith=body[p:p+na]; p+=na; escape=body[p:p+ne]
    counts=unpack_model(modelb); R=arithmetic_decode(arith,escape,codes,(ny,nx,nt),block,counts)
    Q=a.inverse(R,side,block)
    return Q.astype(np.float64)*(2*internal),{"shape":[ny,nx,nt],"transform":NAMES[int(tid)],"eps":eps,"model_bytes":nm,"arithmetic_bytes":na,"escape_bytes":ne}


def install():
    global _old_encode,_old_decode,_installed
    if _installed: return
    _old_encode=c.encode; _old_decode=c.decode; c.NAMES.update(NAMES)
    def enc(X,eps,tid): return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):
        if len(blob)<c.HSZ: raise RuntimeError("short")
        tid=struct.unpack(c.HDR,blob[:c.HSZ])[6]
        return decode_new(blob) if int(tid) in PARAMS else _old_decode(blob)
    c.encode=enc; c.decode=dec; _installed=True


def sanity():
    install(); rng=np.random.default_rng(20260817); ny,nx,nt=4,17,401; t=np.arange(nt); X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx): X[y,x]=(70*np.sin((t+3*x+2*y)/19)+22*np.sin((t-x+2*y)/8)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.0
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid); Y,m=c.decode(b); e=c.hard(X,Y)
        if e>eps*(1+3e-6): raise RuntimeError(("context sanity",tid,e,eps))
        print("MV3D_CONTEXT_SANITY",NAMES[tid],len(b),d,flush=True)

if __name__=='__main__': sanity()
