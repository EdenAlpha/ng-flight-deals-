#!/usr/bin/env python3
"""Exact multiscale spatial lifting codec for migrated/poststack 3-D seismic.

After the standard hard-error scalar quantizer, the integer field is transformed
reversibly with CDF 5/3 lifting across the two native spatial axes.  The coarse
LL field and each detail band are entropy-coded independently, so large-scale
reflector structure is represented explicitly rather than only through local
DPCM.  Optional temporal delta or temporal 5/3 lifting is exact.  Every band
header and payload byte is serialized and charged.
"""
from __future__ import annotations
import math,struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_context_entropy as ent

MAGIC=b'MVSP53V1'
HDR='<8sddIIIHHHH'
HSZ=struct.calcsize(HDR)
BHDR='<IIIIIBI'
BHSZ=struct.calcsize(BHDR)
T_NONE=0;T_DELTA=1;T_WAVELET=2
TLEVELS=3
LEVEL_MENU=((2,4),(3,5))
TMODES=(T_NONE,T_DELTA,T_WAVELET)
MARGIN=c.MARGIN


def hard(a,b):return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))

def _fwd53_last(a):
 a=np.asarray(a,np.int64);n=a.shape[-1]
 if n<2:return a.copy()
 e=a[...,::2].copy();d=a[...,1::2].copy();no=d.shape[-1];ne=e.shape[-1]
 er=np.concatenate([e[...,1:],e[...,-1:]],axis=-1)
 d=d-np.floor_divide(e[...,:no]+er[...,:no],2)
 dl=np.concatenate([d[...,:1],d],axis=-1)[...,:ne]
 dr=np.concatenate([d,d[...,-1:]],axis=-1)[...,:ne]
 s=e+np.floor_divide(dl+dr+2,4)
 return np.concatenate([s,d],axis=-1)

def _inv53_last(a,n):
 a=np.asarray(a,np.int64);n=int(n)
 if n<2:return a.copy()
 ne=(n+1)//2;no=n//2;s=a[...,:ne].copy();d=a[...,ne:ne+no].copy()
 dl=np.concatenate([d[...,:1],d],axis=-1)[...,:ne]
 dr=np.concatenate([d,d[...,-1:]],axis=-1)[...,:ne]
 e=s-np.floor_divide(dl+dr+2,4)
 er=np.concatenate([e[...,1:],e[...,-1:]],axis=-1)
 o=d+np.floor_divide(e[...,:no]+er[...,:no],2)
 out=np.empty(a.shape[:-1]+(n,),np.int64);out[...,::2]=e;out[...,1::2]=o
 return out

def _fwd_axis_prefix(A,axis,n):
 B=np.asarray(A,np.int64).copy();sl=[slice(None)]*B.ndim;sl[axis]=slice(0,int(n));q=np.moveaxis(B[tuple(sl)],axis,-1);q=_fwd53_last(q);B[tuple(sl)]=np.moveaxis(q,-1,axis);return B

def _inv_axis_prefix(A,axis,n):
 B=np.asarray(A,np.int64).copy();sl=[slice(None)]*B.ndim;sl[axis]=slice(0,int(n));q=np.moveaxis(B[tuple(sl)],axis,-1);q=_inv53_last(q,int(n));B[tuple(sl)]=np.moveaxis(q,-1,axis);return B

def spatial_forward(Q,ly,lx):
 A=np.asarray(Q,np.int64).copy();ny,nx,_=A.shape;ys=[];xs=[];cy=ny;cx=nx
 for lev in range(max(int(ly),int(lx))):
  ys.append(cy);xs.append(cx)
  if lev<int(lx) and cx>1:A=_fwd_axis_prefix(A,1,cx);cx=(cx+1)//2
  if lev<int(ly) and cy>1:A=_fwd_axis_prefix(A,0,cy);cy=(cy+1)//2
 return A,ys,xs,cy,cx

def spatial_inverse(A,ly,lx,ys,xs):
 B=np.asarray(A,np.int64).copy()
 for lev in range(max(int(ly),int(lx))-1,-1,-1):
  if lev<int(ly) and ys[lev]>1:B=_inv_axis_prefix(B,0,ys[lev])
  if lev<int(lx) and xs[lev]>1:B=_inv_axis_prefix(B,1,xs[lev])
 return B

def band_rects(ny,nx,ly,lx):
 rect=[];cy=int(ny);cx=int(nx)
 for lev in range(max(int(ly),int(lx))):
  py,px=cy,cx;nylo=(cy+1)//2 if lev<int(ly) else cy;nxlo=(cx+1)//2 if lev<int(lx) else cx
  if lev<int(lx) and nxlo<px:rect.append((0,nylo,nxlo,px,lev,1))
  if lev<int(ly) and nylo<py:rect.append((nylo,py,0,nxlo,lev,2))
  if lev<int(ly) and lev<int(lx) and nylo<py and nxlo<px:rect.append((nylo,py,nxlo,px,lev,3))
  cy,cx=nylo,nxlo
 rect.append((0,cy,0,cx,max(int(ly),int(lx)),0))
 return rect

def temporal_forward(B,mode):
 A=np.asarray(B,np.int64)
 if mode==T_NONE:return A.copy()
 if mode==T_DELTA:
  R=np.empty_like(A);R[...,0]=A[...,0];R[...,1:]=A[...,1:]-A[...,:-1];return R
 if mode==T_WAVELET:
  R=A.copy();n=R.shape[-1]
  for _ in range(TLEVELS):
   if n<2:break
   R[...,:n]=_fwd53_last(R[...,:n]);n=(n+1)//2
  return R
 raise ValueError(mode)

def temporal_inverse(B,mode):
 A=np.asarray(B,np.int64)
 if mode==T_NONE:return A.copy()
 if mode==T_DELTA:return np.cumsum(A,axis=-1,dtype=np.int64)
 if mode==T_WAVELET:
  R=A.copy();lengths=[];n=R.shape[-1]
  for _ in range(TLEVELS):
   if n<2:break
   lengths.append(n);n=(n+1)//2
  for q in reversed(lengths):R[...,:q]=_inv53_last(R[...,:q],q)
  return R
 raise ValueError(mode)

def _levels(shape,req):
 ny,nx,_=shape;ly=min(int(req[0]),int(math.floor(math.log2(max(1,ny)))));lx=min(int(req[1]),int(math.floor(math.log2(max(1,nx)))));return ly,lx

def encode_config(X,eps,req_levels,tmode):
 eps=float(eps);internal=eps*MARGIN;step=2*internal;q=np.rint(np.asarray(X,np.float64)/step)
 if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('sp53 quantized int32')
 Q=q.astype(np.int32);ly,lx=_levels(Q.shape,req_levels);A,ys,xs,cy,cx=spatial_forward(Q,ly,lx)
 if np.any((A<np.iinfo(np.int32).min)|(A>np.iinfo(np.int32).max)):raise OverflowError('sp53 coefficient int32')
 rects=band_rects(Q.shape[0],Q.shape[1],ly,lx);bands=[]
 for y0,y1,x0,x1,lev,kind in rects:
  B=temporal_forward(np.ascontiguousarray(A[y0:y1,x0:x1,:]),int(tmode))
  if np.any((B<np.iinfo(np.int32).min)|(B>np.iinfo(np.int32).max)):raise OverflowError('sp53 temporal coefficient int32')
  Bi=B.astype(np.int32);pid,payload=ent.pack(Bi);bands.append((y0,y1,x0,x1,lev,kind,int(pid),payload))
 ny,nx,nt=Q.shape;out=bytearray(struct.pack(HDR,MAGIC,eps,internal,ny,nx,nt,ly,lx,int(tmode),len(bands)))
 for y0,y1,x0,x1,lev,kind,pid,payload in bands:
  out.extend(struct.pack(BHDR,y0,y1,x0,x1,lev,kind,pid,len(payload)));out.extend(payload)
 return bytes(out),{'levels':[ly,lx],'temporal_mode':int(tmode),'bands':len(bands),'payload_bytes':sum(len(q[-1]) for q in bands)}

def decode(blob):
 if len(blob)<HSZ:raise RuntimeError('short sp53')
 magic,eps,internal,ny,nx,nt,ly,lx,tmode,nb=struct.unpack(HDR,blob[:HSZ])
 if magic!=MAGIC:raise RuntimeError(('sp53 magic',magic))
 A=np.zeros((ny,nx,nt),np.int64);p=HSZ
 for _ in range(nb):
  if p+BHSZ>len(blob):raise RuntimeError('short sp53 band header')
  y0,y1,x0,x1,lev,kind,pid,L=struct.unpack(BHDR,blob[p:p+BHSZ]);p+=BHSZ
  if p+L>len(blob):raise RuntimeError('short sp53 band payload')
  shape=(y1-y0,x1-x0,nt);B=ent.unpack(int(pid),blob[p:p+L],shape);p+=L;A[y0:y1,x0:x1,:]=temporal_inverse(B,int(tmode))
 if p!=len(blob):raise RuntimeError(('sp53 trailing',p,len(blob)))
 # Recreate exact prefix lengths used by the forward transform.
 ys=[];xs=[];cy=int(ny);cx=int(nx)
 for lev in range(max(int(ly),int(lx))):
  ys.append(cy);xs.append(cx)
  if lev<int(lx):cx=(cx+1)//2
  if lev<int(ly):cy=(cy+1)//2
 Q=spatial_inverse(A,int(ly),int(lx),ys,xs)
 if np.any((Q<np.iinfo(np.int32).min)|(Q>np.iinfo(np.int32).max)):raise OverflowError('sp53 inverse int32')
 return Q.astype(np.float64)*(2*float(internal)),{'shape':[ny,nx,nt],'levels':[ly,lx],'temporal_mode':int(tmode),'eps':float(eps)}

def compete(X,eps):
 rows=[]
 seen=set()
 for req in LEVEL_MENU:
  ly,lx=_levels(np.asarray(X).shape,req)
  for tm in TMODES:
   key=(ly,lx,tm)
   if key in seen:continue
   seen.add(key);b,d=encode_config(X,eps,(ly,lx),tm);Y,_=decode(b);me=hard(X,Y)
   if me>float(eps)*(1+3e-6):raise RuntimeError(('sp53 hard',key,me,eps))
   rows.append({'name':f'spatial53_l{ly}x{lx}_t{tm}','bytes':len(b),'blob':b,'maxerr':me,'diag':d})
 return min(rows,key=lambda q:(q['bytes'],q['name'])),rows

def sanity():
 rng=np.random.default_rng(20260817);t=np.arange(259);X=np.empty((8,64,259),np.float32)
 for y in range(8):
  for x in range(64):X[y,x]=(75*np.sin((t+2*x+3*y)/22)+21*np.sin((t-x+y)/9)+rng.normal(0,2,t.size)).astype(np.float32)
 b,rows=compete(X,3.0);print('MV_SPATIAL53_SANITY_OK',b['name'],b['bytes'],b['maxerr'],[(q['name'],q['bytes']) for q in rows],flush=True)
if __name__=='__main__':sanity()
