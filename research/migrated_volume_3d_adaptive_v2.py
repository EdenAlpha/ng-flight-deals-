#!/usr/bin/env python3
"""Blockwise causal migrated-volume predictor extension.

Installs four universal transforms into migrated_volume_3d_codec. Predictor
choice varies by time block and is fully serialized. No dataset labels route
or tune the codec.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c

T_B64 = 7
T_B128 = 8
T_B256 = 9
T_B128_L1 = 10
RADIUS = 12
PARAMS = {T_B64:(64,"bits"),T_B128:(128,"bits"),T_B256:(256,"bits"),T_B128_L1:(128,"l1")}
NAMES = {T_B64:"adaptive_block64_bits",T_B128:"adaptive_block128_bits",T_B256:"adaptive_block256_bits",T_B128_L1:"adaptive_block128_l1"}
_old_encode=None;_old_decode=None;_installed=False

def score_residual(cur,pred,metric):
 d=cur.astype(np.int64)-pred.astype(np.int64)
 return float(np.abs(d).sum()) if metric=="l1" else float(np.log2(1.0+2.0*np.abs(d).astype(np.float64)).sum())
def shifted(row,lag):return c.shift(row,int(lag))
def temporal_pred(cur,s,e):
 p=np.empty(e-s,np.int32)
 if s==0:
  p[0]=0
  if e-s>1:p[1:]=cur[s:e-1]
 else:p[:]=cur[s-1:e-1]
 return p

def choose_pred(Q,y,x,s,e,metric):
 cur=Q[y,x,s:e];cand=[];z=np.zeros(e-s,np.int32);cand.append((score_residual(cur,z,metric),0,z));pt=temporal_pred(Q[y,x],s,e);cand.append((score_residual(cur,pt,metric),1,pt))
 if y>0 and x>0:
  pp64=Q[y,x-1,s:e].astype(np.int64)+Q[y-1,x,s:e].astype(np.int64)-Q[y-1,x-1,s:e].astype(np.int64)
  if np.all((pp64>=np.iinfo(np.int32).min)&(pp64<=np.iinfo(np.int32).max)):
   pp=pp64.astype(np.int32);cand.append((score_residual(cur,pp,metric),2,pp))
 for lag in range(-RADIUS,RADIUS+1):
  k=lag+RADIUS
  if x>0:
   p=shifted(Q[y,x-1],lag)[s:e];cand.append((score_residual(cur,p,metric),16+k,p))
  if y>0:
   p=shifted(Q[y-1,x],lag)[s:e];cand.append((score_residual(cur,p,metric),48+k,p))
  if x>1:
   p64=2*shifted(Q[y,x-1],lag)[s:e].astype(np.int64)-shifted(Q[y,x-2],2*lag)[s:e].astype(np.int64)
   if np.all((p64>=np.iinfo(np.int32).min)&(p64<=np.iinfo(np.int32).max)):
    p=p64.astype(np.int32);cand.append((score_residual(cur,p,metric),80+k,p))
  if y>1:
   p64=2*shifted(Q[y-1,x],lag)[s:e].astype(np.int64)-shifted(Q[y-2,x],2*lag)[s:e].astype(np.int64)
   if np.all((p64>=np.iinfo(np.int32).min)&(p64<=np.iinfo(np.int32).max)):
    p=p64.astype(np.int32);cand.append((score_residual(cur,p,metric),112+k,p))
  if y>0 and x>0:
   p64=shifted(Q[y,x-1],lag)[s:e].astype(np.int64)+shifted(Q[y-1,x],lag)[s:e].astype(np.int64)-shifted(Q[y-1,x-1],2*lag)[s:e].astype(np.int64)
   if np.all((p64>=np.iinfo(np.int32).min)&(p64<=np.iinfo(np.int32).max)):
    p=p64.astype(np.int32);cand.append((score_residual(cur,p,metric),144+k,p))
 return min(cand,key=lambda q:(q[0],q[1]))[1:]

def forward(Q,block,metric):
 ny,nx,nt=Q.shape;nb=(nt+block-1)//block;R=np.empty_like(Q);codes=np.zeros((ny,nx,nb),np.uint8)
 for y in range(ny):
  for x in range(nx):
   for b in range(nb):
    s=b*block;e=min(nt,s+block);code,pred=choose_pred(Q,y,x,s,e,metric);codes[y,x,b]=np.uint8(code);R[y,x,s:e]=Q[y,x,s:e]-pred
 return R,codes.tobytes()

def decode_pred(Q,y,x,s,e,code):
 if code==0:return np.zeros(e-s,np.int32)
 if code==1:return None
 if code==2:
  if y==0 or x==0:raise RuntimeError(("plane edge",y,x))
  return (Q[y,x-1,s:e].astype(np.int64)+Q[y-1,x,s:e].astype(np.int64)-Q[y-1,x-1,s:e].astype(np.int64)).astype(np.int32)
 if 16<=code<=16+2*RADIUS:
  if x==0:raise RuntimeError(("left edge",code))
  return shifted(Q[y,x-1],code-16-RADIUS)[s:e]
 if 48<=code<=48+2*RADIUS:
  if y==0:raise RuntimeError(("up edge",code))
  return shifted(Q[y-1,x],code-48-RADIUS)[s:e]
 if 80<=code<=80+2*RADIUS:
  if x<2:raise RuntimeError(("left2 edge",code))
  lag=code-80-RADIUS;return (2*shifted(Q[y,x-1],lag)[s:e].astype(np.int64)-shifted(Q[y,x-2],2*lag)[s:e].astype(np.int64)).astype(np.int32)
 if 112<=code<=112+2*RADIUS:
  if y<2:raise RuntimeError(("up2 edge",code))
  lag=code-112-RADIUS;return (2*shifted(Q[y-1,x],lag)[s:e].astype(np.int64)-shifted(Q[y-2,x],2*lag)[s:e].astype(np.int64)).astype(np.int32)
 if 144<=code<=144+2*RADIUS:
  if y==0 or x==0:raise RuntimeError(("lagplane edge",code))
  lag=code-144-RADIUS;return (shifted(Q[y,x-1],lag)[s:e].astype(np.int64)+shifted(Q[y-1,x],lag)[s:e].astype(np.int64)-shifted(Q[y-1,x-1],2*lag)[s:e].astype(np.int64)).astype(np.int32)
 raise RuntimeError(("bad block code",code))

def inverse(R,side,block):
 ny,nx,nt=R.shape;nb=(nt+block-1)//block;codes=np.frombuffer(side,np.uint8)
 if codes.size!=ny*nx*nb:raise RuntimeError(("block side",codes.size,ny,nx,nb))
 codes=codes.reshape(ny,nx,nb);Q=np.empty_like(R)
 for y in range(ny):
  for x in range(nx):
   for b in range(nb):
    s=b*block;e=min(nt,s+block);code=int(codes[y,x,b])
    if code==1:
     for t in range(s,e):Q[y,x,t]=R[y,x,t]+(0 if t==0 else Q[y,x,t-1])
    else:Q[y,x,s:e]=R[y,x,s:e]+decode_pred(Q,y,x,s,e,code)
 return Q

def encode_new(X,eps,tid):
 block,metric=PARAMS[tid];internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
 if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError("quantized int32")
 Q=q.astype(np.int32);R,side=forward(Q,block,metric);sideb=c.CCTX.compress(side);pid,payload=c.pack(R);ny,nx,nt=Q.shape
 h=struct.pack(c.HDR,c.MAGIC,float(eps),internal,ny,nx,nt,tid,pid,len(sideb),len(payload));blob=h+sideb+payload
 return blob,{"transform":NAMES[tid],"pack_id":pid,"block":block,"metric":metric,"side_bytes":len(sideb),"payload_bytes":len(payload),"nonzero_fraction":float(np.mean(R!=0)),"mean_abs_residual":float(np.mean(np.abs(R.astype(np.int64))))}

def decode_new(blob):
 magic,eps,internal,ny,nx,nt,tid,pid,ns,npay=struct.unpack(c.HDR,blob[:c.HSZ])
 if magic!=c.MAGIC or len(blob)!=c.HSZ+ns+npay:raise RuntimeError("bad v2 stream")
 side=c.DCTX.decompress(blob[c.HSZ:c.HSZ+ns]) if ns else b"";R=c.unpack(pid,blob[c.HSZ+ns:],(ny,nx,nt));block,_=PARAMS[int(tid)];Q=inverse(R,side,block)
 return Q.astype(np.float64)*(2*internal),{"shape":[ny,nx,nt],"transform":NAMES[int(tid)],"eps":eps}

def install():
 global _old_encode,_old_decode,_installed
 if _installed:return
 _old_encode=c.encode;_old_decode=c.decode;c.NAMES.update(NAMES)
 def enc(X,eps,tid):return encode_new(X,eps,tid) if tid in PARAMS else _old_encode(X,eps,tid)
 def dec(blob):
  if len(blob)<c.HSZ:raise RuntimeError("short")
  tid=struct.unpack(c.HDR,blob[:c.HSZ])[6]
  return decode_new(blob) if tid in PARAMS else _old_decode(blob)
 c.encode=enc;c.decode=dec;_installed=True

def sanity():
 install();rng=np.random.default_rng(20260817);ny,nx,nt=5,9,301;t=np.arange(nt);X=np.empty((ny,nx,nt),np.float32)
 for y in range(ny):
  for x in range(nx):X[y,x]=(60*np.sin((t+3*x+2*y)/17)+20*np.sin((t-x+2*y)/7)+rng.normal(0,2,nt)).astype(np.float32)
 eps=3.0
 for tid in PARAMS:
  b,d=c.encode(X,eps,tid);Y,m=c.decode(b)
  if c.hard(X,Y)>eps*(1+3e-6):raise RuntimeError(("v2 sanity",tid,c.hard(X,Y)))
 print("MV3D_ADAPTIVE_V2_SANITY_OK",flush=True)
