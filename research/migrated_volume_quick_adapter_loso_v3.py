#!/usr/bin/env python3
"""Header-only object-aware geometry helper for LOSO gates."""
from __future__ import annotations
import math
import numpy as np
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_crosssurvey_prob_screen as b
NY=4;NX=32;WINDOWS=(15000,60000,120000);VERSION='v3-object-aware-header-geometry'
def _segments(n,bounds):
 bb=np.unique(np.r_[0,np.asarray(bounds,dtype=int),n]);bb=bb[(bb>=0)&(bb<=n)];return [(int(bb[i]),int(bb[i+1])) for i in range(len(bb)-1) if bb[i+1]>bb[i]]
def _score(seg):
 L=np.asarray([z-a for a,z in seg if z-a>=NX],float)
 if L.size<NY:return -1e99
 m=float(np.median(L));mad=float(np.median(np.abs(L-m)));return float(L.size/(1+mad/max(1,m))*math.log1p(m))
def _fallback(H,r):
 n=len(H);out=[]
 for j,name in enumerate(r.FIELDS):
  x=np.asarray(H[:,j],np.int64);d=np.diff(x);seg=_segments(n,np.flatnonzero(d!=0)+1);sc=_score(seg)
  if sc>-1e90:out.append((sc,f'fallback_change:{name}',seg))
  nz=d[d!=0]
  if nz.size<4:continue
  scale=max(1.,float(np.median(np.abs(nz))));dom=1 if np.sum(nz>0)>=np.sum(nz<0) else -1
  for mode,bounds in [('reset',np.flatnonzero(np.abs(d)>8*scale)+1),('wrap',np.flatnonzero((np.sign(d)!=0)&(np.sign(d)!=dom)&(np.abs(d)>=scale))+1)]:
   seg=_segments(n,bounds);sc=_score(seg)
   if sc>-1e90:out.append((sc,f'fallback_{mode}:{name}',seg))
 if not out:return None
 sc,mode,seg=max(out,key=lambda z:(z[0],z[1]));return {'score':float(sc),'mode':mode,'segments':seg}
def _geom(H,r):
 try:g,_=r.choose_geometry(H);return g
 except RuntimeError:return _fallback(H,r)
def _stream_for_fraction(d,objects,frac):
 if d.get('assembly') or len(objects)==1:return objects,float(frac),0
 sizes=np.asarray([int(o['size']) for o in objects],np.int64);cum=np.cumsum(sizes);target=float(frac)*float(cum[-1]);oi=int(np.searchsorted(cum,target,side='right'));oi=min(oi,len(objects)-1);before=0 if oi==0 else int(cum[oi-1]);local=(target-before)/max(1,int(sizes[oi]));return [objects[oi]],min(1.,max(0.,float(local))),oi
