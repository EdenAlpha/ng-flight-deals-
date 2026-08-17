#!/usr/bin/env python3
"""Model-free adaptive second-order context arithmetic for migrated 3-D residuals.

Uses the proven block predictor and the same causal context as context2:
predictor family + previous residual + residual two samples back.  Unlike the
static context2 stream, encoder and decoder learn symbol frequencies online from
identical initial counts, so no per-tile probability table is transmitted.
Rare large zig-zag residuals use a varint escape.  No survey identity is used.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a
import migrated_volume_3d_context_entropy_v3 as ac
import migrated_volume_3d_context_entropy_v4 as ctx2

PARAMS={29:(64,'bits',12),30:(64,'bits',14),31:(64,'bits',16)}
NAMES={29:'adaptive_block64_context2_online_s12',30:'adaptive_block64_context2_online_s14',31:'adaptive_block64_context2_online_s16'}
INNER='<II';ISZ=struct.calcsize(INNER)
_old_encode=None;_old_decode=None;_installed=False

def _codes(side,shape,block):return ac._codes(side,shape,block)

def _zig(v):return ac.zig_value(v)
def _unzig(z):return ac.unzig_value(z)

def arithmetic_encode(R,codes,block,nsym):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;nsym=int(nsym)
    counts=np.ones((ctx2.NCTX,nsym),np.uint32)
    low=0;high=ac.TOP;pending=0;bw=ac.BitWriter();escape=bytearray()
    def emit(bit):
        nonlocal pending
        bw.bit(bit)
        while pending:bw.bit(1-int(bit));pending-=1
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                ci=ctx2.context(codes[y,x,t//block],p1,p2);val=int(R[y,x,t]);z=_zig(val);sym=z if z<nsym-1 else nsym-1
                row=counts[ci];total=int(row.sum());lo=int(row[:sym].sum()) if sym else 0;hi=lo+int(row[sym])
                rng=high-low+1;high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<ac.HALF:emit(0)
                    elif low>=ac.HALF:emit(1);low-=ac.HALF;high-=ac.HALF
                    elif low>=ac.Q1 and high<ac.Q3:pending+=1;low-=ac.Q1;high-=ac.Q1
                    else:break
                    low=(low<<1)&ac.TOP;high=((high<<1)&ac.TOP)|1
                if sym==nsym-1:
                    q=z
                    while q>=128:escape.append((q&127)|128);q>>=7
                    escape.append(q)
                row[sym]+=1;p2,p1=p1,val
    pending+=1;emit(0 if low<ac.Q1 else 1)
    return bw.finish(),bytes(escape)

def arithmetic_decode(arith,escape,codes,shape,block,nsym):
    ny,nx,nt=map(int,shape);nsym=int(nsym);counts=np.ones((ctx2.NCTX,nsym),np.uint32)
    br=ac.BitReader(arith);code=0
    for _ in range(32):code=((code<<1)|br.bit())&ac.TOP
    low=0;high=ac.TOP;ep=0;R=np.empty((ny,nx,nt),np.int32)
    for y in range(ny):
        for x in range(nx):
            p1=p2=0
            for t in range(nt):
                ci=ctx2.context(codes[y,x,t//block],p1,p2);row=counts[ci];total=int(row.sum());rng=high-low+1;scaled=((code-low+1)*total-1)//rng
                pref=np.cumsum(row,dtype=np.uint64);sym=int(np.searchsorted(pref,scaled,side='right'))
                if sym<0 or sym>=nsym:raise RuntimeError(('online ctx symbol',ci,sym,scaled,total))
                lo=int(pref[sym-1]) if sym else 0;hi=int(pref[sym]);high=low+(rng*hi//total)-1;low=low+(rng*lo//total)
                while True:
                    if high<ac.HALF:pass
                    elif low>=ac.HALF:low-=ac.HALF;high-=ac.HALF;code-=ac.HALF
                    elif low>=ac.Q1 and high<ac.Q3:low-=ac.Q1;high-=ac.Q1;code-=ac.Q1
                    else:break
                    low=(low<<1)&ac.TOP;high=((high<<1)&ac.TOP)|1;code=((code<<1)&ac.TOP)|br.bit()
                if sym<nsym-1:z=sym
                else:
                    z=0;sh=0
                    while True:
                        if ep>=len(escape):raise RuntimeError('online ctx escape eof')
                        b=escape[ep];ep+=1;z|=(b&127)<<sh
                        if not (b&128):break
                        sh+=7
                        if sh>63:raise RuntimeError('online ctx escape overflow')
                val=_unzig(z)
                if val<np.iinfo(np.int32).min or val>np.iinfo(np.int32).max:raise OverflowError('online residual')
                R[y,x,t]=val;row[sym]+=1;p2,p1=p1,val
    if ep!=len(escape):raise RuntimeError(('online escape trailing',ep,len(escape)))
    return R

def encode_new(X,eps,tid):
    block,metric,nsym=PARAMS[int(tid)];internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('quantized int32')
    Q=q.astype(np.int32);R,side=a.forward(Q,block,metric);codes=_codes(side,Q.shape,block);arith,escape=arithmetic_encode(R,codes,block,nsym);body=struct.pack(INNER,len(arith),len(escape))+arith+escape;sideb=c.CCTX.compress(side);ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body));blob=h+sideb+body
    return blob,{'transform':NAMES[int(tid)],'pack_id':102,'block':block,'metric':metric,'symbols':int(nsym),'side_bytes':len(sideb),'model_bytes':0,'arithmetic_bytes':len(arith),'escape_bytes':len(escape),'payload_bytes':len(body),'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64))))}

def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay or int(tid) not in PARAMS:raise RuntimeError('bad online context stream')
    block,metric,nsym=PARAMS[int(tid)];side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b'';codes=_codes(side,(ny,nx,nt),block);body=blob[c.HSZ+ns:]
    if len(body)<ISZ:raise RuntimeError('short online context payload')
    na,ne=struct.unpack(INNER,body[:ISZ]);p=ISZ
    if p+na+ne!=len(body):raise RuntimeError(('online lengths',len(body),na,ne))
    R=arithmetic_decode(body[p:p+na],body[p+na:p+na+ne],codes,(ny,nx,nt),block,nsym);Q=a.inverse(R,side,block)
    return Q.astype(np.float64)*(2*internal),{'shape':[ny,nx,nt],'transform':NAMES[int(tid)],'eps':eps,'arithmetic_bytes':na,'escape_bytes':ne}

def install():
    global _old_encode,_old_decode,_installed
    if _installed:return
    _old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
    def enc(X,eps,tid):return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):
        if len(blob)<c.HSZ:raise RuntimeError('short')
        tid=struct.unpack(c.HDR,blob[:c.HSZ])[6]
        return decode_new(blob) if int(tid) in PARAMS else _old_decode(blob)
    c.encode=enc;c.decode=dec;_installed=True

def sanity():
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,10,257;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(70*np.sin((t+2*x+2*y)/17)+25*np.sin((t-x+y)/8)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid);Y,m=c.decode(b);e=c.hard(X,Y)
        if e>eps*(1+3e-6):raise RuntimeError(('online ctx sanity',tid,e,eps))
        print('MV3D_ONLINE_CTX_V7_SANITY',NAMES[tid],len(b),e,d,flush=True)

if __name__=='__main__':sanity()
