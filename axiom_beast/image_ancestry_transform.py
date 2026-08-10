#!/usr/bin/env python3
"""AXIOM codec-ancestry basis for raw RGB24 images.

The transform searches a small family of canonical JPEG generator states, decodes each
with a pinned FFmpeg decoder law, and stores the basis plus an exact modular correction.
No AI; reconstruction is byte exact. This is an experimental law requiring ffmpeg.
"""
import os,io,math,tempfile,subprocess,zlib,lzma,shutil
import numpy as np
from PIL import Image
from axiom3_common import vi,uv
MAGIC=b'JBA1'

def _ffsig():
    q=subprocess.run(['ffmpeg','-version'],check=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True).stdout.splitlines()[0]
    return q.encode()

def _ffdecode(jpg,w,h):
    fd,jp=tempfile.mkstemp(suffix='.jpg');os.close(fd);rp=jp+'.raw'
    try:
        open(jp,'wb').write(jpg)
        subprocess.run(['ffmpeg','-loglevel','error','-y','-i',jp,'-f','rawvideo','-pix_fmt','rgb24',rp],check=True)
        b=open(rp,'rb').read()
        if len(b)!=w*h*3:raise ValueError('decoder geometry mismatch')
        return b
    finally:
        for p in (jp,rp):
            try:os.unlink(p)
            except OSError:pass

def _shape(raw):
    if len(raw)%3:return None
    n=len(raw)//3
    fac=[]
    for w in range(32,min(4096,n)+1):
        if n%w:continue
        h=n//w
        if not 32<=h<=4096:continue
        fac.append((w,h))
    if not fac:return None
    a=np.frombuffer(raw,dtype=np.uint8).astype(np.int16)
    best=None
    for w,h in fac:
        lag=3*w
        lim=min(len(a)-lag,300000)
        if lim<=0:continue
        idx=np.arange(0,lim,3)
        score=float(np.mean(np.abs(a[idx+lag]-a[idx])))+abs(math.log2(max(w,h)/min(w,h)))*0.15
        if best is None or score<best[0]:best=(score,w,h)
    return (best[1],best[2]) if best else None

def _zig_channel(raw,basis,w,h,bias):
    a=np.frombuffer(raw,dtype=np.uint8).reshape(h,w,3).astype(np.int16)
    b=np.frombuffer(basis,dtype=np.uint8).reshape(h,w,3).astype(np.int16)
    r=((a-b+128)&255)-128-bias
    # ensure mapping stays within signed byte after bias; use int16 zigzag then byte if legal
    z=np.where(r>=0,2*r,-2*r-1)
    if z.max(initial=0)>255:return None
    return np.transpose(z.astype(np.uint8),(2,0,1)).tobytes()

def _unzig_channel(z,w,h,bias):
    q=np.frombuffer(z,dtype=np.uint8).reshape(3,h,w).transpose(1,2,0).astype(np.int16)
    r=np.where((q&1)==0,q//2,-((q+1)//2))+bias
    return r

def _encres(b):
    cand=[]
    try:cand.append((2,lzma.compress(b,preset=9|lzma.PRESET_EXTREME)))
    except Exception:pass
    try:
        import brotli;cand.append((3,brotli.compress(b,quality=11)))
    except Exception:pass
    return min(cand,key=lambda x:len(x[1]))

def _decres(cid,b):
    if cid==2:return lzma.decompress(b)
    if cid==3:
        import brotli;return brotli.decompress(b)
    raise ValueError('residual codec')

def pack(raw):
    if not shutil.which('ffmpeg'):return None
    sh=_shape(raw)
    if not sh:return None
    w,h=sh
    if w*h*3!=len(raw):return None
    im=Image.frombytes('RGB',(w,h),raw)
    proxy=[]
    # Coarse MDL search. Exact decoder output, not visual distortion, is the objective.
    for samp in (0,1,2):
        for q in (88,90,91,92,93,94,96,98,100):
            bio=io.BytesIO()
            try:im.save(bio,'JPEG',quality=q,subsampling=samp,optimize=True)
            except Exception:continue
            jpg=bio.getvalue()
            try:bas=_ffdecode(jpg,w,h)
            except Exception:continue
            for bias in (0,1):
                z=_zig_channel(raw,bas,w,h,bias)
                if z is None:continue
                score=len(jpg)+len(zlib.compress(z,3))
                proxy.append((score,jpg,z,bias,q,samp))
    if not proxy:return None
    proxy.sort(key=lambda x:x[0]);best=None
    for _,jpg,z,bias,q,samp in proxy[:4]:
        cid,c=_encres(z);cost=len(jpg)+len(c)
        if best is None or cost<best[0]:best=(cost,jpg,c,cid,bias,q,samp)
    _,jpg,c,cid,bias,q,samp=best;sig=_ffsig()
    o=bytearray(MAGIC)+vi(w)+vi(h)+vi(len(sig))+sig+bytes([cid,bias,q,samp])+vi(len(jpg))+jpg+vi(len(c))+c
    return bytes(o)

def unpack(rep):
    if rep[:4]!=MAGIC:raise ValueError('image ancestry magic')
    p=4;w,p=uv(rep,p);h,p=uv(rep,p);sl,p=uv(rep,p);sig=rep[p:p+sl];p+=sl
    if _ffsig()!=sig:raise RuntimeError('FFmpeg decoder law signature mismatch')
    cid,bias,q,samp=rep[p:p+4];p+=4;jl,p=uv(rep,p);jpg=rep[p:p+jl];p+=jl;cl,p=uv(rep,p);c=rep[p:p+cl];p+=cl
    if p!=len(rep):raise ValueError('trailing image ancestry data')
    bas=np.frombuffer(_ffdecode(jpg,w,h),dtype=np.uint8).reshape(h,w,3).astype(np.int16)
    z=_decres(cid,c);r=_unzig_channel(z,w,h,bias)
    out=((bas+r)&255).astype(np.uint8).tobytes()
    return out
