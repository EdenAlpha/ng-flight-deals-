#!/usr/bin/env python3
"""Additional generic geometry inference for serpentine SEG-Y trace ordering."""
import numpy as np

def geometry_candidates(base,A):
 out=list(base.geometry_candidates(A));n=A.shape[0];names=list(base.FIELDS)
 for j,name in enumerate(names):
  x=A[:,j].astype(np.int64);d=np.diff(x)
  # Coordinate fields often traverse one line forward and the next backward.
  # Ignore zeros, then flag boundaries where the sign of the local step reverses.
  s=np.sign(d).astype(np.int8)
  # Carry nearest nonzero direction through short plateaus.
  last=0
  for i in range(s.size):
   if s[i]!=0:last=int(s[i])
   elif last:s[i]=last
  first=0
  for i in range(s.size-1,-1,-1):
   if s[i]!=0:first=int(s[i])
   elif first:s[i]=first
  flip=np.flatnonzero(s[1:]*s[:-1]<0)+1
  if 2<=flip.size<=n//max(4,base.NX//2):
   seg=base.segments_from_boundaries(n,flip);lens=np.asarray([b-a for a,b in seg],float)
   if np.sum(lens>=base.NX)>=base.NY:
    out.append({'mode':'direction_flip:'+name,'segments':seg})
  # Also detect sharp curvature even when the coordinate does not fully reverse.
  nz=np.abs(d[d!=0])
  if nz.size:
   med=float(np.median(nz));dd=np.abs(np.diff(d.astype(np.int64)))
   bend=np.flatnonzero(dd>max(1.,6.*med))+1
   if 2<=bend.size<=n//max(4,base.NX//2):
    seg=base.segments_from_boundaries(n,bend);lens=np.asarray([b-a for a,b in seg],float)
    if np.sum(lens>=base.NX)>=base.NY:
     out.append({'mode':'sharp_bend:'+name,'segments':seg})
 seen=set();ded=[]
 for q in out:
  key=tuple(q['segments'])
  if key not in seen:seen.add(key);ded.append(q)
 return ded
