#!/usr/bin/env python3
"""Model-free causal PPM entropy coder for native migrated 3-D residuals.

Uses the already decoder-visible adaptive predictor code plus two prior decoded
residuals as context.  Probability tables are learned causally by encoder and
decoder from the same decoded history; no per-tile frequency model is stored.
A three-level PPM hierarchy with symbol exclusion handles cold contexts. Novel
symbols fall through to a charged varint side stream. No survey identity or
external training state participates.
"""
from __future__ import annotations
import bisect,struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a
import migrated_volume_3d_context_entropy_v3 as v3

T_B64_PPM=15
T_B128L1_PPM=16
PARAMS={T_B64_PPM:(64,"bits"),T_B128L1_PPM:(128,"l1")}
NAMES={T_B64_PPM:"adaptive_block64_ppm2_arith",T_B128L1_PPM:"adaptive_block128_l1_ppm2_arith"}
N1=8*9
N2=N1*9
ALPH=127
INNER="<II"
ISZ=struct.calcsize(INNER)
_old_encode=None
_old_decode=None
_installed=False


def b1(v):return max(-4,min(4,int(v)))+4

def b2(v):return max(-4,min(4,int(v)))+4

def k1(code,p1):return v3.family(int(code))*9+b1(p1)

def k2(code,p1,p2):return k1(code,p1)*9+b2(p2)


def vu_put(out,n):
    n=int(n)
    if n<0:raise ValueError(n)
    while n>=128:out.append((n&127)|128);n>>=7
    out.append(n)


def vu_get(raw,pos):
    n=0;sh=0
    while True:
        if pos>=len(raw):raise RuntimeError("ppm raw varint eof")
        q=raw[pos];pos+=1;n|=(q&127)<<sh
        if not(q&128):return n,pos
        sh+=7
        if sh>63:raise RuntimeError("ppm raw varint overflow")


class State:
    __slots__=("counts","symbols","total")
    def __init__(self):self.counts={};self.symbols=[];self.total=0
    def add(self,s):
        s=int(s);d=self.counts
        if s in d:d[s]+=1
        else:d[s]=1;bisect.insort(self.symbols,s)
        self.total+=1


class AEnc:
    __slots__=("low","high","pending","bw")
    def __init__(self):self.low=0;self.high=v3.TOP;self.pending=0;self.bw=v3.BitWriter()
    def _emit(self,b):
        self.bw.bit(b)
        while self.pending:self.bw.bit(1-int(b));self.pending-=1
    def update(self,lo,hi,total):
        lo=int(lo);hi=int(hi);total=int(total)
        if not(0<=lo<hi<=total):raise RuntimeError(("ppm interval",lo,hi,total))
        rng=self.high-self.low+1;self.high=self.low+(rng*hi//total)-1;self.low=self.low+(rng*lo//total)
        while True:
            if self.high<v3.HALF:self._emit(0)
            elif self.low>=v3.HALF:self._emit(1);self.low-=v3.HALF;self.high-=v3.HALF
            elif self.low>=v3.Q1 and self.high<v3.Q3:self.pending+=1;self.low-=v3.Q1;self.high-=v3.Q1
            else:break
            self.low=(self.low<<1)&v3.TOP;self.high=((self.high<<1)&v3.TOP)|1
    def finish(self):
        self.pending+=1;self._emit(0 if self.low<v3.Q1 else 1);return self.bw.finish()


class ADec:
    __slots__=("low","high","code","br")
    def __init__(self,data):
        self.low=0;self.high=v3.TOP;self.br=v3.BitReader(data);self.code=0
        for _ in range(32):self.code=((self.code<<1)|self.br.bit())&v3.TOP
    def scaled(self,total):
        rng=self.high-self.low+1;return ((self.code-self.low+1)*int(total)-1)//rng
    def update(self,lo,hi,total):
        rng=self.high-self.low+1;self.high=self.low+(rng*int(hi)//int(total))-1;self.low=self.low+(rng*int(lo)//int(total))
        while True:
            if self.high<v3.HALF:pass
            elif self.low>=v3.HALF:self.low-=v3.HALF;self.high-=v3.HALF;self.code-=v3.HALF
            elif self.low>=v3.Q1 and self.high<v3.Q3:self.low-=v3.Q1;self.high-=v3.Q1;self.code-=v3.Q1
            else:break
            self.low=(self.low<<1)&v3.TOP;self.high=((self.high<<1)&v3.TOP)|1;self.code=((self.code<<1)&v3.TOP)|self.br.bit()


def allowed(state,excluded):
    if not excluded:return state.symbols
    return [s for s in state.symbols if s not in excluded]


def encode_level(enc,state,target,excluded,force_escape=False):
    syms=allowed(state,excluded);sf=sum(state.counts[s] for s in syms);ef=max(1,len(syms));total=sf+ef
    if not force_escape and target in state.counts and target not in excluded:
        cum=0
        for s in syms:
            n=state.counts[s]
            if s==target:enc.update(cum,cum+n,total);return False,set(state.symbols)
            cum+=n
        raise RuntimeError("ppm target vanished")
    enc.update(sf,total,total);return True,set(state.symbols)


def decode_level(dec,state,excluded):
    syms=allowed(state,excluded);sf=sum(state.counts[s] for s in syms);ef=max(1,len(syms));total=sf+ef;z=dec.scaled(total)
    if z>=sf:
        dec.update(sf,total,total);return None,True,set(state.symbols)
    cum=0
    for s in syms:
        n=state.counts[s]
        if z<cum+n:dec.update(cum,cum+n,total);return s,False,set(state.symbols)
        cum+=n
    raise RuntimeError(("ppm decode selection",z,sf,total))


def ppm_encode(R,codes,block):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;l2=[State() for _ in range(N2)];l1=[State() for _ in range(N1)];g=State();enc=AEnc();raw=bytearray();novel=0
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                code=int(codes[y,x,t//block]);z=v3.zig_value(int(R[y,x,t]));target=int(z) if z<ALPH else None;force=target is None;i1=k1(code,p1);i2=k2(code,p1,p2);excluded=set()
                esc,seen=encode_level(enc,l2[i2],target,excluded,force);excluded|=seen
                if esc:
                    esc,seen=encode_level(enc,l1[i1],target,excluded,force);excluded|=seen
                    if esc:
                        esc,seen=encode_level(enc,g,target,excluded,force)
                        if esc:vu_put(raw,z);novel+=1
                if target is not None:
                    l2[i2].add(target);l1[i1].add(target);g.add(target)
                p2,p1=p1,int(R[y,x,t])
    return enc.finish(),bytes(raw),novel


def ppm_decode(arith,raw,codes,shape,block):
    ny,nx,nt=map(int,shape);l2=[State() for _ in range(N2)];l1=[State() for _ in range(N1)];g=State();dec=ADec(arith);rp=0;R=np.empty((ny,nx,nt),np.int32)
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                code=int(codes[y,x,t//block]);i1=k1(code,p1);i2=k2(code,p1,p2);excluded=set();sym,esc,seen=decode_level(dec,l2[i2],excluded);excluded|=seen
                if esc:
                    sym,esc,seen=decode_level(dec,l1[i1],excluded);excluded|=seen
                    if esc:
                        sym,esc,seen=decode_level(dec,g,excluded)
                        if esc:z,rp=vu_get(raw,rp);sym=int(z) if z<ALPH else None
                z=int(sym) if sym is not None else int(z);val=v3.unzig_value(z);R[y,x,t]=val
                if z<ALPH:
                    l2[i2].add(z);l1[i1].add(z);g.add(z)
                p2,p1=p1,val
    if rp!=len(raw):raise RuntimeError(("ppm raw trailing",rp,len(raw)))
    return R


def encode_new(X,eps,tid):
    block,metric=PARAMS[int(tid)];internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError("ppm quantized int32")
    Q=q.astype(np.int32);R,side=a.forward(Q,block,metric);codes=v3._codes(side,Q.shape,block);arith,raw,novel=ppm_encode(R,codes,block);body=struct.pack(INNER,len(arith),len(raw))+arith+raw;sideb=c.CCTX.compress(side);ny,nx,nt=Q.shape;h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body));blob=h+sideb+body
    return blob,{"transform":NAMES[int(tid)],"pack_id":102,"block":block,"metric":metric,"side_bytes":len(sideb),"model_bytes":0,"arithmetic_bytes":len(arith),"raw_novel_bytes":len(raw),"novel_symbols":int(novel),"payload_bytes":len(body),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64))))}


def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay:raise RuntimeError("bad ppm stream")
    block,_=PARAMS[int(tid)];side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b'';codes=v3._codes(side,(ny,nx,nt),block);body=blob[c.HSZ+ns:]
    if len(body)<ISZ:raise RuntimeError("short ppm body")
    na,nr=struct.unpack(INNER,body[:ISZ]);p=ISZ
    if p+na+nr!=len(body):raise RuntimeError(("ppm lengths",len(body),na,nr))
    R=ppm_decode(body[p:p+na],body[p+na:p+na+nr],codes,(ny,nx,nt),block);Q=a.inverse(R,side,block)
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
    install();rng=np.random.default_rng(5172026);ny,nx,nt=3,8,257;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(65*np.sin((t+2*x+3*y)/17)+21*np.sin((t-x+y)/7)+rng.normal(0,2.7,nt)).astype(np.float32)
    X[0,0,0]+=5000.;eps=3.
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid);Y,m=c.decode(b);e=c.hard(X,Y)
        if e>eps*(1+3e-6):raise RuntimeError(("ppm sanity",tid,e,eps))
        print("MV3D_PPM_V5_SANITY",NAMES[tid],len(b),e,d,flush=True)

if __name__=='__main__':sanity()
