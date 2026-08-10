#!/usr/bin/env python3
import os, subprocess, lzma, shutil, zlib
try:
 import brotli as _pybrotli
except Exception:
 _pybrotli=None

def vi(n):
    if n < 0: raise ValueError('negative varint')
    o=bytearray()
    while True:
        b=n & 127; n >>= 7
        if n: o.append(b|128)
        else: o.append(b); return bytes(o)

def uv(b,p=0):
    n=0; s=0
    while True:
        if p>=len(b): raise ValueError('truncated varint')
        x=b[p]; p+=1; n |= (x&127)<<s
        if not x&128: return n,p
        s += 7
        if s>70: raise ValueError('varint too long')

def zz(n): return (n<<1) ^ (n>>63)
def uz(n): return (n>>1) ^ -(n&1)
def enc_svar(n): return vi(zz(n))
def dec_svar(b,p):
    x,p=uv(b,p); return uz(x),p

def _run(args,d): return subprocess.run(args,input=d,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
def zc(d,level=22): return _run(['zstd',f'-{level}','--ultra','-q','-c'],d)
def zd(d): return _run(['zstd','-d','-q','-c'],d)
def bc(d):
    if shutil.which('brotli'): return _run(['brotli','-q','11','-c'],d)
    if _pybrotli is not None: return _pybrotli.compress(d,quality=11)
    raise FileNotFoundError('brotli')
def bd(d):
    if shutil.which('brotli'): return _run(['brotli','-d','-c'],d)
    if _pybrotli is not None: return _pybrotli.decompress(d)
    raise FileNotFoundError('brotli')
def bestc(d,allow_brotli=True):
    if not d:return 0,b''
    cand=[(1,zc(d)),(2,lzma.compress(d,preset=9|lzma.PRESET_EXTREME))]
    if allow_brotli:
        try:cand.append((3,bc(d)))
        except Exception:pass
    return min(cand,key=lambda x:len(x[1]))
def fast_score(d):return len(zlib.compress(d,6))
def dec(cid,d):
    if cid==0:return b''
    if cid==1:return zd(d)
    if cid==2:return lzma.decompress(d)
    if cid==3:return bd(d)
    raise ValueError('unknown backend')
