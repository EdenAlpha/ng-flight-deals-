#!/usr/bin/env python3
"""Split-symbol entropy backend for predictive migrated-volume residuals.

The predictor is the no-side two-axis predictive quantizer from v4. The new
backend represents its small integer residuals as a nonzero mask, sign stream,
and magnitude-minus-one bitplanes. All six 3-D traversal orders compete by
actual serialized bytes. No survey labels participate.
"""
from __future__ import annotations
import itertools, struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v4 as v4

PARAMS={25:(0.9375,0.875),26:(0.96875,0.8125)}
NAMES={k:f"predictive_q_split_a{a:g}_w{w:g}" for k,(a,w) in PARAMS.items()}
MAGIC=b"MVPQ5\0\0\0"
HDR="<8sddIIIHHII";HSZ=struct.calcsize(HDR)
PERMS=tuple(itertools.permutations(range(3)))
CCTX=zstd.ZstdCompressor(level=19);DCTX=zstd.ZstdDecompressor()
_old_encode=None;_old_decode=None;_installed=False

def _pack_split(R):
    R=np.asarray(R,np.int32)
    best=None
    for pi,p in enumerate(PERMS):
        A=np.transpose(R,p).reshape(-1).astype(np.int64)
        nz=A!=0; nnz=int(nz.sum())
        nz_raw=np.packbits(nz.astype(np.uint8),bitorder="little").tobytes()
        nz_blob=CCTX.compress(nz_raw)
        vals=A[nz]
        neg=vals<0
        sign_raw=np.packbits(neg.astype(np.uint8),bitorder="little").tobytes()
        sign_blob=CCTX.compress(sign_raw)
        mag=(np.abs(vals)-1).astype(np.uint32)
        maxm=int(mag.max()) if mag.size else 0; nb=maxm.bit_length()
        planes=[]
        for b in range(nb):
            bits=np.packbits(((mag>>b)&1).astype(np.uint8),bitorder="little").tobytes()
            planes.append(CCTX.compress(bits))
        meta=struct.pack("<BBIII",int(pi),int(nb),nnz,len(nz_blob),len(sign_blob))
        meta+=b"".join(struct.pack("<I",len(q)) for q in planes)
        body=meta+nz_blob+sign_blob+b"".join(planes)
        key=(len(body),pi)
        if best is None or key<best[0]:best=(key,body,pi,nnz,nb,len(nz_blob),len(sign_blob),[len(q) for q in planes])
    _,body,pi,nnz,nb,nzb,sb,pls=best
    return body,{"traversal":int(pi),"nnz":int(nnz),"magnitude_bitplanes":int(nb),"nonzero_mask_bytes":int(nzb),"sign_bytes":int(sb),"magnitude_plane_bytes":pls}

def _unpack_split(body,shape):
    if len(body)<14:raise RuntimeError("short split-v5 payload")
    pi,nb,nnz,lnz,lsign=struct.unpack("<BBIII",body[:14]);off=14
    if pi>=len(PERMS):raise RuntimeError(("bad split perm",pi))
    lens=[]
    for _ in range(int(nb)):
        if off+4>len(body):raise RuntimeError("short split plane lengths")
        lens.append(struct.unpack("<I",body[off:off+4])[0]);off+=4
    if off+lnz+lsign+sum(lens)!=len(body):raise RuntimeError(("split lengths",off,lnz,lsign,lens,len(body)))
    n=int(np.prod(shape));nmask=(n+7)//8
    nzraw=DCTX.decompress(body[off:off+lnz]);off+=lnz
    if len(nzraw)!=nmask:raise RuntimeError(("split nz raw",len(nzraw),nmask))
    nz=np.unpackbits(np.frombuffer(nzraw,np.uint8),bitorder="little",count=n).astype(bool)
    if int(nz.sum())!=int(nnz):raise RuntimeError(("split nnz",int(nz.sum()),nnz))
    sraw=DCTX.decompress(body[off:off+lsign]);off+=lsign
    nsbytes=(int(nnz)+7)//8
    if len(sraw)!=nsbytes:raise RuntimeError(("split sign raw",len(sraw),nsbytes))
    neg=np.unpackbits(np.frombuffer(sraw,np.uint8),bitorder="little",count=int(nnz)).astype(bool)
    mag=np.zeros(int(nnz),np.uint32)
    for b,L in enumerate(lens):
        raw=DCTX.decompress(body[off:off+L]);off+=L
        need=(int(nnz)+7)//8
        if len(raw)!=need:raise RuntimeError(("split mag raw",b,len(raw),need))
        bits=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder="little",count=int(nnz)).astype(np.uint32)
        mag|=(bits<<b)
    vals=mag.astype(np.int64)+1;vals[neg]*=-1
    if vals.size and np.any((vals<np.iinfo(np.int32).min)|(vals>np.iinfo(np.int32).max)):raise OverflowError("split vals")
    flat=np.zeros(n,np.int32);flat[nz]=vals.astype(np.int32)
    p=PERMS[int(pi)];tshape=tuple(shape[i] for i in p)
    A=flat.reshape(tshape);inv=np.argsort(np.asarray(p))
    return np.ascontiguousarray(np.transpose(A,tuple(inv)))

def encode_new(X,eps,tid):
    a,w=PARAMS[int(tid)]
    R,Y,internal=v4._forward(X,eps,float(a),float(w))
    payload,diag=_pack_split(R);ny,nx,nt=R.shape
    hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),0,0,len(payload))
    blob=hdr+payload
    return blob,{"transform":NAMES[int(tid)],"a":float(a),"w_fast":float(w),"side_bytes":0,"payload_bytes":len(payload),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64)))),"encoder_reconstruction_maxerr":float(c.hard(X,Y)),**diag}

def decode_new(blob):
    if len(blob)<HSZ:raise RuntimeError("short split-v5 stream")
    magic,eps,internal,ny,nx,nt,tid,_flags,ns,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or ns!=0 or int(tid) not in PARAMS:raise RuntimeError("bad split-v5 header")
    if len(blob)!=HSZ+npay:raise RuntimeError(("split-v5 length",len(blob),HSZ,npay))
    R=_unpack_split(blob[HSZ:],(int(ny),int(nx),int(nt)))
    a,w=PARAMS[int(tid)];Y=v4._inverse(R,float(internal),float(a),float(w))
    return Y,{"shape":[int(ny),int(nx),int(nt)],"transform":NAMES[int(tid)],"eps":float(eps)}

def install():
    global _old_encode,_old_decode,_installed
    if _installed:return
    v4.install();_old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
    def enc(X,eps,tid):return encode_new(X,eps,tid) if int(tid) in PARAMS else _old_encode(X,eps,tid)
    def dec(blob):return decode_new(blob) if len(blob)>=8 and blob[:8]==MAGIC else _old_decode(blob)
    c.encode=enc;c.decode=dec;_installed=True

def sanity():
    install();rng=np.random.default_rng(20260817);ny,nx,nt=4,8,259;t=np.arange(nt,dtype=np.float64)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):X[y,x]=(75*np.sin((t+2*x+2*y)/18)+15*np.sin((t-x+y)/6)+rng.normal(0,2,nt)).astype(np.float32)
    eps=3.
    for tid in PARAMS:
        b,d=encode_new(X,eps,tid);Y,m=decode_new(b);me=c.hard(X,Y)
        if me>eps*(1+3e-6):raise RuntimeError(("split-v5 sanity",tid,me))
    print("MV3D_PQ_SPLIT_V5_SANITY_OK",flush=True)

if __name__=="__main__":sanity()
