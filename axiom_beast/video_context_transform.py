#!/usr/bin/env python3
# AXIOM v0.7 reversible raw-YUV420 local-motion law.
# Non-AI: integer block matching + causal spatial/temporal predictors + exact residuals.
import math, numpy as np
import axiom3_common as C
MAGIC=b'VID7'

def vi(n):return C.vi(n)
def uv(b,p=0):return C.uv(b,p)

def _entropy(a):
 h=np.bincount(a.ravel(),minlength=256).astype(np.float64);h=h[h>0]
 if not len(h):return 0.0
 p=h/h.sum();return float(-(p*np.log2(p)).sum())
def _zzmod(x):
 s=np.where(x<128,x.astype(np.int16),x.astype(np.int16)-256)
 return np.where(s>=0,2*s,-2*s-1).astype(np.uint8)
def _sample_entropy_diff(a,s,count=32768):
 n=len(a)
 if s<=0 or s>=n:return 99.0
 idx=np.linspace(s,n-1,min(count,n-s),dtype=np.int64)
 q=((a[idx].astype(np.int16)-a[idx-s].astype(np.int16))&255).astype(np.uint8)
 return _entropy(q)
def _factors(n):
 out=[]
 r=int(math.isqrt(n))
 for a in range(1,r+1):
  if n%a==0:
   b=n//a;out.append((a,b))
   if a!=b:out.append((b,a))
 return out

def infer_yuv420(data):
 n=len(data)
 if n<65536:return None
 a=np.frombuffer(data,dtype=np.uint8)
 fc=[]
 for nf in range(4,min(600,n//1536)+1):
  if n%nf:continue
  fs=n//nf
  if (fs*2)%3:continue
  yp=fs*2//3
  if yp<64*64:continue
  te=_sample_entropy_diff(a,fs,16384)
  fc.append((te,nf,fs,yp))
 if not fc:return None
 fc.sort();best=None
 ratios=(16/9,4/3,3/2,5/4,1.0,9/16,3/4)
 for te,nf,fs,yp in fc[:8]:
  # score row stride on luma only; favor conventional aspect ratios only as a weak tie-breaker.
  y=np.frombuffer(data[:min(nf,3)*fs],dtype=np.uint8)
  # pull only the Y part of first frames into one band
  ys=[]
  for t in range(min(nf,3)):
   s=t*fs;ys.append(a[s:s+yp])
  yy=np.concatenate(ys)
  for h,w in _factors(yp):
   if w<64 or h<64 or w>4096 or h>4096 or (w&1) or (h&1):continue
   re=_sample_entropy_diff(yy,w,16384)
   ratio=w/h;ap=min(abs(math.log(max(ratio,1e-9)/r)) for r in ratios)
   score=te+0.70*re+0.06*ap
   if best is None or score<best[0]:best=(score,w,h,nf,fs,te,re)
 if best is None:return None
 score,w,h,nf,fs,te,re=best
 # Natural video should have useful same-position temporal correlation.
 if te>7.75:return None
 return {'w':w,'h':h,'frames':nf,'frame_size':fs,'temporal_entropy':te,'row_entropy':re,'score':score}

def _split(raw,w,h):
 fs=w*h*3//2
 if len(raw)%fs:raise ValueError('size')
 nf=len(raw)//fs;a=np.frombuffer(raw,dtype=np.uint8);Y=[];U=[];V=[];p=0
 for _ in range(nf):
  Y.append(a[p:p+w*h].reshape(h,w));p+=w*h
  U.append(a[p:p+w*h//4].reshape(h//2,w//2));p+=w*h//4
  V.append(a[p:p+w*h//4].reshape(h//2,w//2));p+=w*h//4
 return np.stack(Y),np.stack(U),np.stack(V)
def _join(ps):
 Y,U,V=ps;o=bytearray()
 for t in range(len(Y)):o+=Y[t].tobytes()+U[t].tobytes()+V[t].tobytes()
 return bytes(o)
def _paeth(a,b,c):
 p=a.astype(np.int16)+b.astype(np.int16)-c.astype(np.int16);pa=np.abs(p-a);pb=np.abs(p-b);pc=np.abs(p-c)
 return np.where((pa<=pb)&(pa<=pc),a,np.where(pb<=pc,b,c)).astype(np.uint8)
def _spatial(cur):
 l=np.zeros_like(cur);l[:,1:]=cur[:,:-1];u=np.zeros_like(cur);u[1:]=cur[:-1];ul=np.zeros_like(cur);ul[1:,1:]=cur[:-1,:-1]
 return _paeth(l,u,ul)
def _tx(cur,prev):
 l=np.zeros_like(cur);l[:,1:]=cur[:,:-1];pl=np.zeros_like(prev);pl[:,1:]=prev[:,:-1]
 return ((prev.astype(np.int16)+l.astype(np.int16)-pl.astype(np.int16))&255).astype(np.uint8)
def _ty(cur,prev):
 u=np.zeros_like(cur);u[1:]=cur[:-1];pu=np.zeros_like(prev);pu[1:]=prev[:-1]
 return ((prev.astype(np.int16)+u.astype(np.int16)-pu.astype(np.int16))&255).astype(np.uint8)
def _motion_block(prev,cur,y0,x0,bs=16,rad=16):
 y1=min(cur.shape[0],y0+bs);x1=min(cur.shape[1],x0+bs);cb=cur[y0:y1,x0:x1];pad=np.pad(prev,rad,mode='edge');best=(10**30,0,0)
 for dy in range(-rad,rad+1,4):
  for dx in range(-rad,rad+1,4):
   pb=pad[y0+rad+dy:y1+rad+dy,x0+rad+dx:x1+rad+dx]
   sc=np.abs(cb[::2,::2].astype(np.int16)-pb[::2,::2].astype(np.int16)).sum()
   if sc<best[0]:best=(int(sc),dx,dy)
 _,bx,by=best;best=(10**30,bx,by)
 for dy in range(max(-rad,by-3),min(rad,by+3)+1):
  for dx in range(max(-rad,bx-3),min(rad,bx+3)+1):
   pb=pad[y0+rad+dy:y1+rad+dy,x0+rad+dx:x1+rad+dx]
   sc=np.abs(cb.astype(np.int16)-pb.astype(np.int16)).sum()
   if sc<best[0]:best=(int(sc),dx,dy)
 return best[1],best[2]
def _encode_y(frames,bs=16,rad=16):
 nf,h,w=frames.shape;res=np.empty_like(frames);modes=[];dxs=[];dys=[]
 for t in range(nf):
  cur=frames[t];sp=_spatial(cur);prev=frames[t-1] if t else None;xx=_tx(cur,prev) if t else None;yy=_ty(cur,prev) if t else None;pad=np.pad(prev,rad,mode='edge') if t else None
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);cb=cur[y0:y1,x0:x1];cand=[sp[y0:y1,x0:x1]];dx=dy=0
    if t:
     dx,dy=_motion_block(prev,cur,y0,x0,bs,rad);mb=pad[y0+rad+dy:y1+rad+dy,x0+rad+dx:x1+rad+dx]
     cand += [prev[y0:y1,x0:x1],xx[y0:y1,x0:x1],yy[y0:y1,x0:x1],mb]
    rr=[_zzmod(((cb.astype(np.int16)-q.astype(np.int16))&255).astype(np.uint8)) for q in cand];k=int(np.argmin([_entropy(q) for q in rr]));modes.append(k);dxs.append(dx+rad);dys.append(dy+rad);res[t,y0:y1,x0:x1]=rr[k]
 return res,bytes(modes),bytes(dxs),bytes(dys)
def _decode_plane(res,modes,dxs,dys,bs,rad,scale=1):
 nf,h,w=res.shape;out=np.empty_like(res);mi=0
 for t in range(nf):
  fr=np.zeros((h,w),dtype=np.uint8);prev=out[t-1] if t else None;pad=np.pad(prev,max(1,rad//scale),mode='edge') if t else None;prad=max(1,rad//scale)
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);k=modes[mi];dx=int(round((dxs[mi]-rad)/scale));dy=int(round((dys[mi]-rad)/scale));mi+=1
    for y in range(y0,y1):
     for x in range(x0,x1):
      l=int(fr[y,x-1]) if x else 0;u=int(fr[y-1,x]) if y else 0;ul=int(fr[y-1,x-1]) if x and y else 0;p=l+u-ul;pa=abs(p-l);pb=abs(p-u);pc=abs(p-ul);sp=l if pa<=pb and pa<=pc else u if pb<=pc else ul
      if k==0:pred=sp
      elif k==1:pred=int(prev[y,x])
      elif k==2:
       pl=int(prev[y,x-1]) if x else 0;pred=(int(prev[y,x])+l-pl)&255
      elif k==3:
       pu=int(prev[y-1,x]) if y else 0;pred=(int(prev[y,x])+u-pu)&255
      elif k==4:pred=int(pad[y+prad+dy,x+prad+dx])
      else:raise ValueError('mode')
      z=int(res[t,y,x]);e=z//2 if not z&1 else -((z+1)//2);fr[y,x]=(pred+e)&255
  out[t]=fr
 return out
def _shift(a,dx,dy):
 h,w=a.shape;xs=np.clip(np.arange(w)-dx,0,w-1);ys=np.clip(np.arange(h)-dy,0,h-1)
 return a[np.ix_(ys,xs)]
def _find_global_shift(prev,cur,rad=8):
 a=prev[::4,::4].astype(np.int16);b=cur[::4,::4].astype(np.int16);best=(10**30,0,0)
 for dy in range(-rad,rad+1):
  for dx in range(-rad,rad+1):
   sx=int(round(dx/4));sy=int(round(dy/4));x0=max(0,sx);x1=min(a.shape[1],a.shape[1]+sx);y0=max(0,sy);y1=min(a.shape[0],a.shape[0]+sy);qx=max(0,-sx);qy=max(0,-sy)
   if x1-x0<8 or y1-y0<8:continue
   sc=np.abs(b[y0:y1,x0:x1]-a[qy:qy+y1-y0,qx:qx+x1-x0]).sum()
   if sc<best[0]:best=(int(sc),dx,dy)
 return best[1],best[2]
def _encode_global_plane(frames,motions,bs=8,scale=2):
 nf,h,w=frames.shape;res=np.empty_like(frames);modes=[]
 for t in range(nf):
  cur=frames[t];sp=_spatial(cur);prev=frames[t-1] if t else None;cands=[sp]
  if t:
   dx=int(round(motions[t][0]/scale));dy=int(round(motions[t][1]/scale));mp=_shift(prev,dx,dy)
   cands += [prev,_tx(cur,prev),_ty(cur,prev),mp]
  rr=[_zzmod(((cur.astype(np.int16)-q.astype(np.int16))&255).astype(np.uint8)) for q in cands]
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);k=int(np.argmin([_entropy(q[y0:y1,x0:x1]) for q in rr]));modes.append(k);res[t,y0:y1,x0:x1]=rr[k][y0:y1,x0:x1]
 return res,bytes(modes)
def _decode_global_plane(res,modes,motions,bs=8,scale=2):
 nf,h,w=res.shape;out=np.empty_like(res);mi=0
 for t in range(nf):
  fr=np.zeros((h,w),dtype=np.uint8);prev=out[t-1] if t else None;dx=dy=0
  if t:dd=motions[t];dx=int(round(dd[0]/scale));dy=int(round(dd[1]/scale));mp=_shift(prev,dx,dy)
  else:mp=None
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);k=modes[mi];mi+=1
    for y in range(y0,y1):
     for x in range(x0,x1):
      l=int(fr[y,x-1]) if x else 0;u=int(fr[y-1,x]) if y else 0;ul=int(fr[y-1,x-1]) if x and y else 0;p=l+u-ul;pa=abs(p-l);pb=abs(p-u);pc=abs(p-ul);sp=l if pa<=pb and pa<=pc else u if pb<=pc else ul
      if k==0:pred=sp
      elif k==1:pred=int(prev[y,x])
      elif k==2:
       pl=int(prev[y,x-1]) if x else 0;pred=(int(prev[y,x])+l-pl)&255
      elif k==3:
       pu=int(prev[y-1,x]) if y else 0;pred=(int(prev[y,x])+u-pu)&255
      elif k==4:pred=int(mp[y,x])
      else:raise ValueError('unknown global mode')
      z=int(res[t,y,x]);e=z//2 if not z&1 else -((z+1)//2);fr[y,x]=(pred+e)&255
  out[t]=fr
 return out

# ============== AXIOM v0.10 causal-context override ==============
# Later definitions intentionally replace the v0.7 pack/unpack above.
import zlib as _zlib
import lzma as _lzma
try:
    import cv2 as _cv2
except Exception:
    _cv2=None
try:
    from numba import njit as _njit
except Exception:
    _njit=None

MAGIC_CTX=b'VC10