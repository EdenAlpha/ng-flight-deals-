#!/usr/bin/env python3
"""Header-only robust extraction wrapper for the four-survey quick-adapter gate.

Locations are fixed from survey fractions before amplitudes are read. Split
objects that form one SEG-Y (assembly=true) are concatenated. Multiple standalone
SEG-Y objects are selected by cumulative object bytes, then parsed independently.
Geometry uses only SEG-Y headers and deterministic expanding windows.
"""
from __future__ import annotations
import argparse, math
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
  x=np.asarray(H[:,j],np.int64);d=np.diff(x)
  seg=_segments(n,np.flatnonzero(d!=0)+1);sc=_score(seg)
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
def extract(ds,manifest,epsj,frac):
 large=b.large;r=large.r;eps=float(epsj['datasets'][ds]['epsilon']);d=next(z for z in manifest['datasets'] if z['id']==ds);objects=[r.obj(u) for u in d['objects']];stream,local_frac,oi=_stream_for_fraction(d,objects,frac);rr=r.S3ConcatSequential(r.S3,stream,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr)
  if s.total_traces is None:raise RuntimeError(('selected SEG-Y stream lacks fixed trace count',ds,frac,oi))
  total=int(s.total_traces);target=int(round(local_frac*max(0,total-1)));chosen=None
  for window in WINDOWS:
   st=max(0,min(max(0,total-window),target-window//2));n=min(window,total-st);H=large.read_header_window(rr,s,st,n);g=_geom(H,r)
   if g is None:continue
   rows=[(a+st,z+st) for a,z in g['segments'] if z-a>=NX]
   if len(rows)<NY:continue
   choices=[]
   for i in range(len(rows)-NY+1):
    block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);choices.append((abs(mid-target),i,block))
   _,_,block=min(choices,key=lambda z:(z[0],z[1]));chosen=(window,g,rows,block,min(z-a for a,z in block));break
  if chosen is None:raise RuntimeError(('no header-derived 4x32 geometry',ds,frac,oi,WINDOWS))
  window,g,rows,block,minlen=chosen;X,ids=r.read_tile(rr,s,block,minlen)
  return np.ascontiguousarray(X),eps,{'fraction':float(frac),'local_fraction':float(local_frac),'object_index':int(oi),'shape':list(map(int,X.shape)),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'geometry_mode':g['mode'],'header_window':int(window),'extractor_version':VERSION,'long_rows_available':int(len(rows)),'selection':'fixed survey fraction; object by cumulative bytes; header-only geometry; amplitudes unused'}
 finally:rr.close()
q.b.extract=extract
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);q.main(p.parse_args())
