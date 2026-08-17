#!/usr/bin/env python3
"""Causal context entropy extension for migrated 3-D residuals.

The residual value at time t is assigned to a stream using only the already
reconstructed residual at t-1 from the same trace. Streams are traversed in a
decoder-known time-major native-grid order, then each is encoded by the existing
exact entropy packer. This exposes strong conditional structure without oracle
information. K and scan order are stored and every substream/framing byte is
charged. The ordinary entropy stream remains an automatic fallback.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_entropy as base

PID_CONTEXT=9
VERSION=1
SCAN_TXY=0
SCAN_TYX=1
K_MENU=(3,4,5)
SCAN_MENU=(SCAN_TXY,SCAN_TYX)
HEAD='<BBBB'
SUB='<BII'
HSZ=struct.calcsize(HEAD);SSZ=struct.calcsize(SUB)

def _iter_indices(shape,scan):
 ny,nx,nt=map(int,shape)
 if scan==SCAN_TXY:
  for t in range(nt):
   for x in range(nx):
    for y in range(ny):yield y,x,t
 elif scan==SCAN_TYX:
  for t in range(nt):
   for y in range(ny):
    for x in range(nx):yield y,x,t
 else:raise RuntimeError(('bad context scan',scan))

def _ctx(prev,K):
 v=max(-K,min(K,int(prev)))
 return 1+v+K

def encode_context(R,K,scan):
 A=np.asarray(R,np.int32)
 if A.ndim!=3:raise ValueError(('context entropy requires 3D residual',A.shape))
 nctx=2*int(K)+2
 streams=[[] for _ in range(nctx)]
 for y,x,t in _iter_indices(A.shape,scan):
  ci=0 if t==0 else _ctx(A[y,x,t-1],K)
  streams[ci].append(int(A[y,x,t]))
 desc=[];payloads=[]
 for s in streams:
  a=np.asarray(s,np.int32)
  if a.size:
   pid,payload=base.pack(a)
  else:
   pid,payload=0,b''
  desc.append((int(pid),int(a.size),len(payload)));payloads.append(payload)
 out=bytearray(struct.pack(HEAD,VERSION,int(K),int(scan),int(nctx)))
 for q in desc:out.extend(struct.pack(SUB,*q))
 for p in payloads:out.extend(p)
 return bytes(out)

def decode_context(body,shape):
 if len(body)<HSZ:raise RuntimeError('short context entropy')
 ver,K,scan,nctx=struct.unpack(HEAD,body[:HSZ])
 if ver!=VERSION or nctx!=2*K+2:raise RuntimeError(('context header',ver,K,scan,nctx))
 p=HSZ;desc=[]
 for _ in range(nctx):
  if p+SSZ>len(body):raise RuntimeError('short context descriptors')
  desc.append(struct.unpack(SUB,body[p:p+SSZ]));p+=SSZ
 streams=[]
 for pid,count,L in desc:
  if p+L>len(body):raise RuntimeError('short context payload')
  payload=body[p:p+L];p+=L
  if count:
   a=base.unpack(int(pid),payload,(int(count),)).reshape(-1)
  else:
   if L:raise RuntimeError(('nonempty zero-count context',L))
   a=np.zeros(0,np.int32)
  streams.append(a)
 if p!=len(body):raise RuntimeError(('context trailing',p,len(body)))
 pos=np.zeros(nctx,np.int64);A=np.empty(tuple(map(int,shape)),np.int32)
 for y,x,t in _iter_indices(A.shape,int(scan)):
  ci=0 if t==0 else _ctx(A[y,x,t-1],int(K))
  j=int(pos[ci])
  if j>=streams[ci].size:raise RuntimeError(('context underflow',ci,j,streams[ci].size))
  A[y,x,t]=streams[ci][j];pos[ci]+=1
 if any(int(pos[i])!=int(streams[i].size) for i in range(nctx)):
  raise RuntimeError(('context unused symbols',pos,[q.size for q in streams]))
 return A

def pack(R):
 pid0,b0=base.pack(R);best=(len(b0),int(pid0),b0,('base',int(pid0)))
 A=np.asarray(R)
 if A.ndim==3 and A.size:
  for scan in SCAN_MENU:
   for K in K_MENU:
    b=encode_context(A,K,scan)
    cand=(len(b),PID_CONTEXT,b,('context',scan,K))
    if cand[:2]<best[:2]:best=cand
 return best[1],best[2]

def unpack(pid,body,shape):
 if int(pid)==PID_CONTEXT:return decode_context(body,shape)
 return base.unpack(int(pid),body,shape)

def sanity():
 rng=np.random.default_rng(20260817)
 A=rng.integers(-5,6,size=(4,7,211),dtype=np.int32)
 # inject first-order persistence typical of predictive residuals
 for t in range(1,A.shape[2]):
  m=rng.random(A.shape[:2])<.6;A[:,:,t][m]=A[:,:,t-1][m]
 for scan in SCAN_MENU:
  for K in K_MENU:
   b=encode_context(A,K,scan);R=decode_context(b,A.shape)
   if not np.array_equal(A,R):raise RuntimeError(('context sanity',scan,K))
 pid,b=pack(A);R=unpack(pid,b,A.shape)
 if not np.array_equal(A,R):raise RuntimeError(('selected context sanity',pid))
 print('MV3D_CONTEXT_ENTROPY_SANITY_OK','pid',pid,'bytes',len(b),flush=True)
if __name__=='__main__':sanity()
