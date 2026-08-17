#!/usr/bin/env python3
"""Predictive-quantization v3 candidate for migrated seismic volumes.

The key change from the earlier migrated-volume codecs is that prediction happens
BEFORE quantization. Each sample is predicted from already reconstructed causal
neighbors, only the prediction error is quantized, and the decoder reconstructs
the identical float64 state. This preserves the hard epsilon contract while
allowing highly coherent migrated reflectors to collapse to small integer codes.

A universal 8-value spatial-scale menu is selected independently per 128-sample
time block. Selector codes are serialized at exactly 3 bits each. Residual
zig-zag bitplanes independently choose one of six 3-D traversal orders and are
zstd-compressed at level 19. No survey id or category participates.
"""
from __future__ import annotations
import itertools, math, struct
import numpy as np
import zstandard as zstd
import migrated_volume_3d_codec as c

T_PQ128 = 20
NAME = "predictive_q_block128_scaled_bitplanes"
BLOCK = 128
COEFFS = np.asarray([0.75,0.8125,0.875,0.90625,0.9375,0.96875,1.0,1.03125], np.float64)
BITS_PER_CODE = 3
MAGIC = b"MVPQ3\0\0\0"
HDR = "<8sddIIIHHII"
HSZ = struct.calcsize(HDR)
PERMS = tuple(itertools.permutations(range(3)))
CCTX = zstd.ZstdCompressor(level=19)
DCTX = zstd.ZstdDecompressor()
_old_encode = None
_old_decode = None
_installed = False

def _score(q):
    a=np.abs(np.asarray(q,np.int64)).astype(np.float64)
    return float(np.log2(1.0+2.0*a).sum())

def _pack_codes(codes):
    flat=np.asarray(codes,np.uint8).reshape(-1)
    nbits=int(flat.size)*BITS_PER_CODE
    out=np.zeros((nbits+7)//8,np.uint8)
    bit=0
    for v in flat:
        q=int(v)
        if q<0 or q>=len(COEFFS): raise RuntimeError(("bad coeff code",q))
        for b in range(BITS_PER_CODE):
            if (q>>b)&1: out[(bit+b)>>3] |= np.uint8(1<<((bit+b)&7))
        bit += BITS_PER_CODE
    return out.tobytes()

def _unpack_codes(raw,n):
    need=(int(n)*BITS_PER_CODE+7)//8
    if len(raw)!=need: raise RuntimeError(("coeff side length",len(raw),need))
    u=np.frombuffer(raw,np.uint8); out=np.zeros(int(n),np.uint8); bit=0
    for i in range(int(n)):
        v=0
        for b in range(BITS_PER_CODE):
            v |= ((int(u[(bit+b)>>3])>>((bit+b)&7))&1)<<b
        if v>=len(COEFFS): raise RuntimeError(("bad coeff code",v))
        out[i]=v; bit+=BITS_PER_CODE
    return out

def _zig(a):
    x=np.asarray(a,np.int64).reshape(-1)
    z=(x<<1)^(x>>63)
    if z.size and np.any((z<0)|(z>np.iinfo(np.uint32).max)): raise OverflowError("pq zigzag")
    return z.astype(np.uint32)

def _unzig(z):
    q=np.asarray(z,np.uint32).astype(np.uint64)
    a=(q>>1).astype(np.int64)^-((q&1).astype(np.int64))
    if a.size and np.any((a<np.iinfo(np.int32).min)|(a>np.iinfo(np.int32).max)): raise OverflowError("pq unzig")
    return a.astype(np.int32)

def _pack_bitplanes(R):
    R=np.asarray(R,np.int32)
    base=_zig(R)
    maxz=int(base.max()) if base.size else 0
    nb=maxz.bit_length()
    parts=[]
    for b in range(nb):
        best=None
        for pi,p in enumerate(PERMS):
            z=_zig(np.transpose(R,p).reshape(-1))
            bits=np.packbits(((z>>b)&1).astype(np.uint8),bitorder="little").tobytes()
            comp=CCTX.compress(bits)
            key=(len(comp),pi)
            if best is None or key<best[0]: best=(key,pi,comp)
        _,pi,comp=best
        parts.append(struct.pack("<BI",int(pi),len(comp))+comp)
    return struct.pack("<B",nb)+b"".join(parts), nb

def _unpack_bitplanes(body,shape):
    if not body: raise RuntimeError("empty pq bitplane body")
    ny,nx,nt=map(int,shape); n=ny*nx*nt
    nb=int(body[0]); off=1
    zcanonical=np.zeros((ny,nx,nt),np.uint32)
    nbytes=(n+7)//8
    for b in range(nb):
        if off+5>len(body): raise RuntimeError("short pq plane header")
        pi,L=struct.unpack("<BI",body[off:off+5]); off+=5
        if pi>=len(PERMS) or off+L>len(body): raise RuntimeError(("bad pq plane",pi,L,off,len(body)))
        raw=DCTX.decompress(body[off:off+L]); off+=L
        if len(raw)!=nbytes: raise RuntimeError(("pq plane raw",len(raw),nbytes))
        bits=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder="little",count=n).astype(np.uint32)
        p=PERMS[int(pi)]
        tshape=tuple(shape[i] for i in p)
        plane=bits.reshape(tshape)
        inv=np.argsort(np.asarray(p))
        zcanonical |= (np.transpose(plane,tuple(inv))<<b)
    if off!=len(body): raise RuntimeError(("pq trailing bytes",off,len(body)))
    return _unzig(zcanonical.reshape(-1)).reshape((ny,nx,nt))

def _trial_block(src,left,up,prev_rec,s,e,a,step):
    q=np.empty(e-s,np.int32); rec=np.empty(e-s,np.float64)
    for j,t in enumerate(range(s,e)):
        if left is not None:
            pred=float(a)*float(left[t])
            if t>0:
                rp=float(rec[j-1]) if j>0 else float(prev_rec)
                pred += rp-float(a)*float(left[t-1])
        elif up is not None:
            pred=float(a)*float(up[t])
        elif t>0:
            pred=float(rec[j-1]) if j>0 else float(prev_rec)
        else:
            pred=0.0
        qi=int(np.rint((float(src[t])-pred)/step))
        if qi<np.iinfo(np.int32).min or qi>np.iinfo(np.int32).max: raise OverflowError("pq residual int32")
        q[j]=qi; rec[j]=pred+float(qi)*step
    return q,rec

def _forward(X,eps):
    X=np.asarray(X,np.float64)
    if X.ndim!=3: raise ValueError(X.shape)
    ny,nx,nt=X.shape; internal=float(eps)*float(c.MARGIN); step=2.0*internal
    nb=(nt+BLOCK-1)//BLOCK
    Q=np.empty((ny,nx,nt),np.int32)
    Y=np.empty((ny,nx,nt),np.float64)
    codes=np.zeros((ny,nx,nb),np.uint8)
    for y in range(ny):
        for x in range(nx):
            left=Y[y,x-1] if x>0 else None
            up=Y[y-1,x] if y>0 else None
            for bi,s in enumerate(range(0,nt,BLOCK)):
                e=min(nt,s+BLOCK)
                prev=Y[y,x,s-1] if s>0 else 0.0
                best=None
                for ci,a in enumerate(COEFFS):
                    qb,rb=_trial_block(X[y,x],left,up,prev,s,e,float(a),step)
                    key=(_score(qb),ci)
                    if best is None or key<best[0]: best=(key,ci,qb,rb)
                _,ci,qb,rb=best
                codes[y,x,bi]=np.uint8(ci); Q[y,x,s:e]=qb; Y[y,x,s:e]=rb
    return Q,Y,codes,internal

def _inverse(Q,codes,internal):
    Q=np.asarray(Q,np.int32); ny,nx,nt=Q.shape; step=2.0*float(internal)
    nb=(nt+BLOCK-1)//BLOCK
    if tuple(codes.shape)!=(ny,nx,nb): raise RuntimeError(("pq code shape",codes.shape,(ny,nx,nb)))
    Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
        for x in range(nx):
            left=Y[y,x-1] if x>0 else None
            up=Y[y-1,x] if y>0 else None
            for bi,s in enumerate(range(0,nt,BLOCK)):
                e=min(nt,s+BLOCK); a=float(COEFFS[int(codes[y,x,bi])])
                for t in range(s,e):
                    if left is not None:
                        pred=a*float(left[t])
                        if t>0: pred += float(Y[y,x,t-1])-a*float(left[t-1])
                    elif up is not None:
                        pred=a*float(up[t])
                    elif t>0:
                        pred=float(Y[y,x,t-1])
                    else:
                        pred=0.0
                    Y[y,x,t]=pred+float(Q[y,x,t])*step
    return Y

def encode_new(X,eps):
    R,Y,codes,internal=_forward(X,eps)
    side=_pack_codes(codes)
    payload,nbp=_pack_bitplanes(R)
    ny,nx,nt=R.shape
    hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,BLOCK,BITS_PER_CODE,len(side),len(payload))
    blob=hdr+side+payload
    me=c.hard(X,Y)
    return blob,{
        "transform":NAME,"block":BLOCK,"coeff_count":len(COEFFS),
        "side_bytes":len(side),"payload_bytes":len(payload),"bitplanes":int(nbp),
        "nonzero_fraction":float(np.mean(R!=0)),
        "mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64)))),
        "encoder_reconstruction_maxerr":float(me)
    }

def decode_new(blob):
    if len(blob)<HSZ: raise RuntimeError("short pq stream")
    magic,eps,internal,ny,nx,nt,block,bpc,ns,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or block!=BLOCK or bpc!=BITS_PER_CODE: raise RuntimeError("bad pq header")
    if len(blob)!=HSZ+ns+npay: raise RuntimeError(("pq stream length",len(blob),HSZ,ns,npay))
    nb=(int(nt)+BLOCK-1)//BLOCK
    flat=_unpack_codes(blob[HSZ:HSZ+ns],int(ny)*int(nx)*nb)
    codes=flat.reshape(int(ny),int(nx),nb)
    R=_unpack_bitplanes(blob[HSZ+ns:],(int(ny),int(nx),int(nt)))
    Y=_inverse(R,codes,float(internal))
    return Y,{"shape":[int(ny),int(nx),int(nt)],"transform":NAME,"eps":float(eps)}

def install():
    global _old_encode,_old_decode,_installed
    if _installed: return
    _old_encode=c.encode; _old_decode=c.decode
    c.NAMES[T_PQ128]=NAME
    def enc(X,eps,tid):
        return encode_new(X,eps) if int(tid)==T_PQ128 else _old_encode(X,eps,tid)
    def dec(blob):
        if len(blob)>=8 and blob[:8]==MAGIC: return decode_new(blob)
        return _old_decode(blob)
    c.encode=enc; c.decode=dec; _installed=True

def sanity():
    install()
    rng=np.random.default_rng(20260817)
    ny,nx,nt=4,10,321; t=np.arange(nt,dtype=np.float64)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):
            X[y,x]=(90*np.sin((t+1.5*x+2*y)/20.0)+25*np.sin((t-x+y)/8.0)+rng.normal(0,3,nt)).astype(np.float32)
    eps=4.0
    b,d=encode_new(X,eps); Y,m=decode_new(b); me=c.hard(X,Y)
    if me>eps*(1+3e-6): raise RuntimeError(("pq sanity hard",me,eps))
    print("MV3D_PQ_V3_SANITY_OK",len(b),me,d,flush=True)

if __name__=="__main__":
    sanity()
