#!/usr/bin/env python3
"""Context2 with traversal-optimized predictor side map.

Reuses the exact context2 residual arithmetic coder. Only predictor selector
serialization changes: all six causal-grid traversal orders compete by actual
zstd-19 bytes and the winning order is stored in one byte. No data labels.
"""
from __future__ import annotations
import itertools,struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as c
import migrated_volume_3d_adaptive_v2 as a
import migrated_volume_3d_context_entropy_v3 as cv3
import migrated_volume_3d_context_entropy_v4 as ctx2

PARAMS={32:(64,'bits'),33:(128,'l1')}
NAMES={32:'adaptive_block64_context2_arith_sideperm',33:'adaptive_block128_l1_context2_arith_sideperm'}
PERMS=tuple(itertools.permutations(range(3)));SC=zstd.ZstdCompressor(level=19);SD=zstd.ZstdDecompressor()
_old_encode=None;_old_decode=None;_installed=False

def pack_side(codes):
    best=None
    for pi,p in enumerate(PERMS):
        raw=np.ascontiguousarray(np.transpose(codes,p)).tobytes();b=SC.compress(raw);key=(len(b),pi)
        if best is None or key<best[0]:best=(key,pi,b)
    _,pi,b=best;return bytes([int(pi)])+b,int(pi)

def unpack_side(blob,shape,block):
    if not blob:raise RuntimeError('empty sideperm')
    pi=int(blob[0]);
    if pi>=len(PERMS):raise RuntimeError(('sideperm id',pi))
    ny,nx,nt=map(int,shape);nb=(nt+int(block)-1)//int(block);orig=(ny,nx,nb);p=PERMS[pi];pshape=tuple(orig[i] for i in p);raw=SD.decompress(blob[1:])
    if len(raw)!=ny*nx*nb:raise RuntimeError(('sideperm raw',len(raw),ny*nx*nb))
    A=np.frombuffer(raw,np.uint8).reshape(pshape);inv=np.argsort(np.asarray(p));codes=np.ascontiguousarray(np.transpose(A,tuple(inv)))
    return codes,codes.tobytes()

def encode_new(X,eps,tid):
    block,metric=PARAMS[int(tid)];internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
    if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('quantized int32')
    Q=q.astype(np.int32);R,side=a.forward(Q,block,metric);codes=cv3._codes(side,Q.shape,block);counts,nesc=ctx2.build_counts(R,codes,block);model=ctx2.pack_model(counts);arith,escape=ctx2.arithmetic_encode(R,codes,block,counts);body=struct.pack(ctx2.INNER,len(model),len(arith),len(escape))+model+arith+escape;sideb,pi=pack_side(codes);ny,nx,nt=Q.shape
    h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,int(tid),0,len(sideb),len(body));blob=h+sideb+body
    return blob,{'transform':NAMES[int(tid)],'pack_id':103,'block':block,'metric':metric,'side_bytes':len(sideb),'side_permutation':int(pi),'model_bytes':len(model),'arithmetic_bytes':len(arith),'escape_bytes':len(escape),'escape_symbols':int(nesc),'payload_bytes':len(body),'used_contexts':int(np.count_nonzero(counts.sum(axis=1))),'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64))))}

def decode_new(blob):
    magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
    if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay or int(tid) not in PARAMS:raise RuntimeError('bad sideperm stream')
    block,_=PARAMS[int(tid)];codes,side=unpack_side(blob[c.HSZ:c.HSZ+ns],(ny,nx,nt),block);body=blob[c.HSZ+ns:]
    if len(body)<ctx2.ISZ:raise RuntimeError('short sideperm payload')
    nm,na,ne=struct.unpack(ctx2.INNER,body[:ctx2.ISZ]);p=ctx2.ISZ
    if p+nm+na+ne!=len(body):raise RuntimeError(('sideperm lengths',len(body),nm,na,ne))
    counts=ctx2.unpack_model(body[p:p+nm]);p+=nm;arith=body[p:p+na];p+=na;escape=body[p:p+ne];R=ctx2.arithmetic_decode(arith,escape,codes,(ny,nx,nt),block,counts);Q=a.inverse(R,side,block)
    return Q.astype(np.float64)*(2*internal),{'shape':[ny,nx,nt],'transform':NAMES[int(tid)],'eps':eps,'model_bytes':nm,'arithmetic_bytes':na,'escape_bytes':ne}

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
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,11,277;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(75*np.sin((t+3*x+2*y)/19)+20*np.sin((t-x+y)/7)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.
    for tid in PARAMS:
        b,d=c.encode(X,eps,tid);Y,m=c.decode(b);e=c.hard(X,Y)
        if e>eps*(1+3e-6):raise RuntimeError(('sideperm sanity',tid,e,eps))
        print('MV3D_SIDEPERM_V8_SANITY',NAMES[tid],len(b),e,d,flush=True)
if __name__=='__main__':sanity()
