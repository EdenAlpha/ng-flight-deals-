#!/usr/bin/env python3
"""Predictive-quantization + context arithmetic hybrid for migrated 3-D seismic.

Prediction happens before quantization (v3).  The resulting small integer error
is then arithmetic-coded with a decoder-visible context formed from the current
predictive scale code and the previous decoded residual in the same trace.
Static per-tile frequency tables are fully serialized.  No survey identity,
file name, or hidden encoder state participates.
"""
from __future__ import annotations
import struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq
import migrated_volume_3d_context_entropy_v3 as ac

PARAMS={27:32,28:64}
NAMES={27:'predictive_q_context_arith_s32',28:'predictive_q_context_arith_s64'}
MAGIC=b'MVPQ6\0\0\0'
HDR='<8sddIIIHBBIIII'
HSZ=struct.calcsize(HDR)
NCTX=72
CCTX=zstd.ZstdCompressor(level=19)
DCTX=zstd.ZstdDecompressor()
_old_encode=None;_old_decode=None;_installed=False

def prev_bucket(v):
    v=int(v)
    if v < -3:return 0
    if v > 3:return 8
    return v+4

def zig(v):
    v=int(v);return (v<<1)^(v>>63)

def unzig(z):
    z=int(z);return (z>>1)^-(z&1)

def build_counts(R,codes,nsym):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape
    counts=np.zeros((NCTX,int(nsym)),np.uint32);escapes=0
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=int(codes[y,x,t//pq.BLOCK])*9+prev_bucket(prev)
                v=int(R[y,x,t]);z=zig(v);sym=z if z<int(nsym)-1 else int(nsym)-1
                counts[ctx,sym]+=1
                if sym==int(nsym)-1:escapes+=1
                prev=v
    return counts,escapes

def pack_model(counts):
    q=np.ascontiguousarray(counts.astype('<u4',copy=False)).reshape(-1)
    raw=q.view(np.uint8).reshape(-1,4).T.copy().tobytes()
    return CCTX.compress(raw)

def unpack_model(blob,nsym):
    raw=DCTX.decompress(blob);n=NCTX*int(nsym);u=np.frombuffer(raw,np.uint8)
    if u.size!=n*4:raise RuntimeError(('pqctx model size',u.size,n*4))
    q=u.reshape(4,n).T.copy().reshape(n*4).view('<u4').copy()
    return q.reshape(NCTX,int(nsym))

def arithmetic_encode(R,codes,counts,nsym):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;nsym=int(nsym)
    pref=np.zeros((NCTX,nsym+1),np.uint64);pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    low=0;high=ac.TOP;pending=0;bw=ac.BitWriter();escape=bytearray()
    def emit(bit):
        nonlocal pending
        bw.bit(bit)
        while pending:
            bw.bit(1-int(bit));pending-=1
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=int(codes[y,x,t//pq.BLOCK])*9+prev_bucket(prev)
                v=int(R[y,x,t]);z=zig(v);sym=z if z<nsym-1 else nsym-1
                total=int(pref[ctx,nsym]);lo=int(pref[ctx,sym]);hi=int(pref[ctx,sym+1])
                if total<=0 or hi<=lo:raise RuntimeError(('pqctx model',ctx,sym,total,lo,hi))
                rng=high-low+1;high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<ac.HALF:emit(0)
                    elif low>=ac.HALF:
                        emit(1);low-=ac.HALF;high-=ac.HALF
                    elif low>=ac.Q1 and high<ac.Q3:
                        pending+=1;low-=ac.Q1;high-=ac.Q1
                    else:break
                    low=(low<<1)&ac.TOP;high=((high<<1)&ac.TOP)|1
                if sym==nsym-1:
                    q=z
                    while q>=128:
                        escape.append((q&127)|128);q>>=7
                    escape.append(q)
                prev=v
    pending+=1;emit(0 if low<ac.Q1 else 1)
    return bw.finish(),bytes(escape)

def arithmetic_decode(arith,escape,codes,shape,counts,nsym):
    ny,nx,nt=map(int,shape);nsym=int(nsym)
    pref=np.zeros((NCTX,nsym+1),np.uint64);pref[:,1:]=np.cumsum(counts.astype(np.uint64),axis=1)
    br=ac.BitReader(arith);code=0
    for _ in range(32):code=((code<<1)|br.bit())&ac.TOP
    low=0;high=ac.TOP;ep=0;R=np.empty((ny,nx,nt),np.int32)
    for y in range(ny):
        for x in range(nx):
            prev=0
            for t in range(nt):
                ctx=int(codes[y,x,t//pq.BLOCK])*9+prev_bucket(prev);total=int(pref[ctx,nsym])
                if total<=0:raise RuntimeError(('pqctx empty context',ctx))
                rng=high-low+1;scaled=((code-low+1)*total-1)//rng;row=pref[ctx]
                sym=int(np.searchsorted(row,scaled,side='right')-1)
                if sym<0 or sym>=nsym or int(counts[ctx,sym])<=0:raise RuntimeError(('pqctx symbol',ctx,sym,scaled,total))
                lo=int(row[sym]);hi=int(row[sym+1]);high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<ac.HALF:pass
                    elif low>=ac.HALF:
                        low-=ac.HALF;high-=ac.HALF;code-=ac.HALF
                    elif low>=ac.Q1 and high<ac.Q3:
                        low-=ac.Q1;high-=ac.Q1;code-=ac.Q1
                    else:break
                    low=(low<<1)&ac.TOP;high=((high<<1)&ac.TOP)|1;code=((code<<1)&ac.TOP)|br.bit()
                if sym<nsym-1:z=sym
                else:
                    z=0;sh=0
                    while True:
                        if ep>=len(escape):raise RuntimeError('pqctx escape eof')
                        b=escape[ep];ep+=1;z|=(b&127)<<sh
                        if not (b&128):break
                        sh+=7
                        if sh>63:raise RuntimeError('pqctx escape overflow')
                v=unzig(z)
                if v<np.iinfo(np.int32).min or v>np.iinfo(np.int32).max:raise OverflowError('pqctx residual')
                R[y,x,t]=v;prev=v
    if ep!=len(escape):raise RuntimeError(('pqctx escape trailing',ep,len(escape)))
    return R

def encode_new(X,eps,tid):
    nsym=PARAMS[int(tid)]
    R,Y,codes,internal=pq._forward(X,eps)
    side=pq._pack_codes(codes)
    counts,nesc=build_counts(R,codes,nsym);model=pack_model(counts);arith,escape=arithmetic_encode(R,codes,counts,nsym)
    ny,nx,nt=R.shape
    hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,pq.BLOCK,int(tid),int(nsym),len(side),len(model),len(arith),len(escape))
    blob=hdr+side+model+arith+escape
    return blob,{'transform':NAMES[int(tid)],'block':pq.BLOCK,'symbols':int(nsym),'side_bytes':len(side),'model_bytes':len(model),'arithmetic_bytes':len(arith),'escape_bytes':len(escape),'escape_symbols':int(nesc),'payload_bytes':len(model)+len(arith)+len(escape),'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),'encoder_reconstruction_maxerr':float(c.hard(X,Y))}

def decode_new(blob):
    if len(blob)<HSZ:raise RuntimeError('short pqctx stream')
    magic,eps,internal,ny,nx,nt,block,tid,nsym,ns,nm,na,ne=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or int(tid) not in PARAMS or int(nsym)!=PARAMS[int(tid)] or int(block)!=pq.BLOCK:raise RuntimeError('bad pqctx header')
    if len(blob)!=HSZ+ns+nm+na+ne:raise RuntimeError(('pqctx length',len(blob),HSZ,ns,nm,na,ne))
    p=HSZ;side=blob[p:p+ns];p+=ns;model=blob[p:p+nm];p+=nm;arith=blob[p:p+na];p+=na;escape=blob[p:p+ne]
    nb=(int(nt)+pq.BLOCK-1)//pq.BLOCK
    codes=pq._unpack_codes(side,int(ny)*int(nx)*nb).reshape(int(ny),int(nx),nb)
    counts=unpack_model(model,int(nsym));R=arithmetic_decode(arith,escape,codes,(int(ny),int(nx),int(nt)),counts,int(nsym))
    Y=pq._inverse(R,codes,float(internal))
    return Y,{'shape':[int(ny),int(nx),int(nt)],'transform':NAMES[int(tid)],'eps':float(eps),'model_bytes':int(nm),'arithmetic_bytes':int(na),'escape_bytes':int(ne)}

def install():
    global _old_encode,_old_decode,_installed
    if _installed:return
    pq.install();_old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
    def enc(X,eps,tid):return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):return decode_new(blob) if len(blob)>=8 and blob[:8]==MAGIC else _old_decode(blob)
    c.encode=enc;c.decode=dec;_installed=True

def sanity():
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,9,301;t=np.arange(nt,dtype=np.float64);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(80*np.sin((t+2*x+3*y)/21)+20*np.sin((t-x+y)/8)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.0
    for tid in PARAMS:
        b,d=encode_new(X,eps,tid);Y,m=decode_new(b);me=c.hard(X,Y)
        if me>eps*(1+3e-6):raise RuntimeError(('pqctx sanity',tid,me,eps))
        print('MV3D_PQCTX_V6_SANITY',NAMES[tid],len(b),me,d,flush=True)

if __name__=='__main__':sanity()
