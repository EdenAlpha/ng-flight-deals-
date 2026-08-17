#!/usr/bin/env python3
"""Competing exact residual entropy coders for migrated_volume_3d_codec.

Modes 0-6 reproduce the original byte/ZigZag+Zstd packers. Mode 7 encodes
ZigZag integer bitplanes independently. Mode 8 splits zero mask, sign mask,
and magnitude-minus-one. Selection is solely by final serialized byte count.
"""
import struct
import numpy as np
import zstandard as zstd
CCTX=zstd.ZstdCompressor(level=12);DCTX=zstd.ZstdDecompressor()

def shuffle(a):
 a=np.ascontiguousarray(a);w=a.dtype.itemsize;return a.view(np.uint8).reshape(-1,w).T.copy().tobytes()
def unshuffle(raw,dt,n):
 dt=np.dtype(dt);w=dt.itemsize;u=np.frombuffer(raw,np.uint8)
 if u.size!=n*w:raise RuntimeError(('unshuffle',u.size,n,w))
 return u.reshape(w,n).T.copy().reshape(n*w).view(dt)
def zig(x):
 a=np.asarray(x,np.int64).reshape(-1);z=(a<<1)^(a>>63)
 if np.any((z<0)|(z>np.iinfo(np.uint32).max)):raise OverflowError('zigzag')
 return z.astype(np.uint32)
def unzig(z):
 z=np.asarray(z,np.uint32).astype(np.uint64);a=(z>>1).astype(np.int64)^-((z&1).astype(np.int64))
 if np.any((a<np.iinfo(np.int32).min)|(a>np.iinfo(np.int32).max)):raise OverflowError('unzig')
 return a.astype(np.int32)

def pack_bitplanes(a):
 z=zig(a);maxz=int(z.max()) if z.size else 0;nb=maxz.bit_length()
 blobs=[]
 for b in range(nb):
  bits=np.packbits(((z>>b)&1).astype(np.uint8),bitorder='little').tobytes();blobs.append(CCTX.compress(bits))
 return struct.pack('<B',nb)+b''.join(struct.pack('<I',len(q)) for q in blobs)+b''.join(blobs)
def unpack_bitplanes(body,n):
 if not body:raise RuntimeError('empty bitplane body')
 nb=body[0];p=1
 lens=[]
 for _ in range(nb):
  if p+4>len(body):raise RuntimeError('short bitplane lengths')
  lens.append(struct.unpack('<I',body[p:p+4])[0]);p+=4
 z=np.zeros(n,np.uint32);nbytes=(n+7)//8
 for b,L in enumerate(lens):
  if p+L>len(body):raise RuntimeError('short bitplane payload')
  raw=DCTX.decompress(body[p:p+L]);p+=L
  if len(raw)!=nbytes:raise RuntimeError(('bitplane raw',len(raw),nbytes))
  bits=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little',count=n).astype(np.uint32);z|=(bits<<b)
 if p!=len(body):raise RuntimeError(('bitplane trailing',p,len(body)))
 return unzig(z)

def pack_split(a):
 a=np.asarray(a,np.int32).reshape(-1);nz=(a!=0);nnz=int(nz.sum())
 mb=CCTX.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes())
 if nnz:
  vals=a[nz].astype(np.int64);neg=(vals<0);mag=np.abs(vals)-1;mx=int(mag.max())
  sb=CCTX.compress(np.packbits(neg.astype(np.uint8),bitorder='little').tobytes())
  if mx<=255:kind=1;q=mag.astype(np.uint8);raw=q.tobytes()
  elif mx<=65535:kind=2;q=mag.astype('<u2');raw=shuffle(q)
  else:kind=4;q=mag.astype('<u4');raw=shuffle(q)
  gb=CCTX.compress(raw)
 else:
  kind=1;sb=CCTX.compress(b'');gb=CCTX.compress(b'')
 return struct.pack('<BIII',kind,len(mb),len(sb),len(gb))+mb+sb+gb
def unpack_split(body,n):
 if len(body)<13:raise RuntimeError('short split body')
 kind,lm,ls,lg=struct.unpack('<BIII',body[:13]);p=13
 if p+lm+ls+lg!=len(body):raise RuntimeError(('split lengths',len(body),lm,ls,lg))
 mb=body[p:p+lm];p+=lm;sb=body[p:p+ls];p+=ls;gb=body[p:p+lg]
 mr=DCTX.decompress(mb);nz=np.unpackbits(np.frombuffer(mr,np.uint8),bitorder='little',count=n).astype(bool);nnz=int(nz.sum())
 sr=DCTX.decompress(sb);neg=np.unpackbits(np.frombuffer(sr,np.uint8),bitorder='little',count=nnz).astype(bool) if nnz else np.zeros(0,bool)
 gr=DCTX.decompress(gb)
 if kind==1:
  mag=np.frombuffer(gr,np.uint8,count=nnz).astype(np.int64)
 elif kind==2:
  mag=unshuffle(gr,'<u2',nnz).astype(np.int64)
 elif kind==4:
  mag=unshuffle(gr,'<u4',nnz).astype(np.int64)
 else:raise RuntimeError(('split kind',kind))
 if mag.size!=nnz:raise RuntimeError(('split mag',mag.size,nnz))
 vals=mag+1;vals[neg]*=-1
 if np.any((vals<np.iinfo(np.int32).min)|(vals>np.iinfo(np.int32).max)):raise OverflowError('split reconstruction')
 out=np.zeros(n,np.int32);out[nz]=vals.astype(np.int32);return out

def pack(R):
 a=np.asarray(R,np.int32).reshape(-1);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;tr=[]
 if -128<=mn and mx<=127:tr.append((0,CCTX.compress(a.astype(np.int8).tobytes())))
 if -32768<=mn and mx<=32767:
  q=a.astype('<i2');tr.extend([(1,CCTX.compress(q.tobytes())),(2,CCTX.compress(shuffle(q)))])
 q=a.astype('<i4');tr.extend([(3,CCTX.compress(q.tobytes())),(4,CCTX.compress(shuffle(q)))])
 z=zig(a)
 if z.size==0 or int(z.max())<=65535:tr.append((5,CCTX.compress(shuffle(z.astype('<u2')))))
 tr.append((6,CCTX.compress(shuffle(z.astype('<u4')))))
 tr.append((7,pack_bitplanes(a)))
 tr.append((8,pack_split(a)))
 return min(tr,key=lambda q:(len(q[1]),q[0]))
def unpack(pid,body,shape):
 n=int(np.prod(shape))
 if pid==7:a=unpack_bitplanes(body,n)
 elif pid==8:a=unpack_split(body,n)
 else:
  raw=DCTX.decompress(body)
  if pid==0:a=np.frombuffer(raw,np.int8,count=n).astype(np.int32)
  elif pid==1:a=np.frombuffer(raw,'<i2',count=n).astype(np.int32)
  elif pid==2:a=unshuffle(raw,'<i2',n).astype(np.int32)
  elif pid==3:a=np.frombuffer(raw,'<i4',count=n).astype(np.int32)
  elif pid==4:a=unshuffle(raw,'<i4',n).astype(np.int32)
  elif pid==5:a=unzig(unshuffle(raw,'<u2',n).astype(np.uint32))
  elif pid==6:a=unzig(unshuffle(raw,'<u4',n).astype(np.uint32))
  else:raise RuntimeError(('pack id',pid))
 if a.size!=n:raise RuntimeError(('unpack size',a.size,n))
 return a.reshape(shape)

def sanity():
 rng=np.random.default_rng(917);tests=[np.zeros(1001,np.int32),rng.integers(-3,4,5003,dtype=np.int32),rng.integers(-300,301,7001,dtype=np.int32)]
 for a in tests:
  for pid,b in [(7,pack_bitplanes(a)),(8,pack_split(a))]:
   r=unpack(pid,b,a.shape)
   if not np.array_equal(a,r):raise RuntimeError(('entropy sanity',pid))
  pid,b=pack(a);r=unpack(pid,b,a.shape)
  if not np.array_equal(a,r):raise RuntimeError(('selected entropy sanity',pid))
  print('MV3D_ENTROPY_SANITY',a.size,'pid',pid,'bytes',len(b),flush=True)
if __name__=='__main__':sanity()
