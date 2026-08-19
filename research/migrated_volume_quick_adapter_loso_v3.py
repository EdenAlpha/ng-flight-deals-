#!/usr/bin/env python3
"""Header-only robust extraction wrapper for the four-survey quick-adapter gate.

Tile locations remain fixed by survey fraction before sample values are read.
For difficult local windows, expand the HEADER window deterministically and
recover row boundaries directly from SEG-Y header change/reset patterns.  Only
header fields and run lengths select geometry; amplitudes never participate.
"""
from __future__ import annotations
import argparse, math
import numpy as np
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_crosssurvey_prob_screen as b

NY=4; NX=32
WINDOWS=(15000, 60000, 120000)
VERSION='v3-expanding-header-geometry'


def _segments(n,bounds):
    bb=np.unique(np.r_[0,np.asarray(bounds,dtype=int),n]);bb=bb[(bb>=0)&(bb<=n)]
    return [(int(bb[i]),int(bb[i+1])) for i in range(len(bb)-1) if bb[i+1]>bb[i]]


def _score_segments(seg):
    lens=np.asarray([z-a for a,z in seg if z-a>=NX],dtype=float)
    if lens.size<NY:return -1e99
    med=float(np.median(lens));mad=float(np.median(np.abs(lens-med)))
    return float(lens.size/(1.+mad/max(1.,med))*math.log1p(med))


def _fallback_geometry(H,r):
    n=len(H);cands=[];names=list(r.FIELDS)
    for j,name in enumerate(names):
        x=np.asarray(H[:,j],dtype=np.int64);d=np.diff(x)
        seg=_segments(n,np.flatnonzero(d!=0)+1);sc=_score_segments(seg)
        if sc>-1e90:cands.append((sc,'fallback_change:'+name,seg))
        nz=d[d!=0]
        if nz.size<4:continue
        scale=max(1.,float(np.median(np.abs(nz))))
        reset=np.flatnonzero(np.abs(d)>8.*scale)+1
        seg=_segments(n,reset);sc=_score_segments(seg)
        if sc>-1e90:cands.append((sc,'fallback_reset:'+name,seg))
        sgn=np.sign(nz);dom=1 if np.sum(sgn>0)>=np.sum(sgn<0) else -1
        wrap=np.flatnonzero((np.sign(d)!=0)&(np.sign(d)!=dom)&(np.abs(d)>=scale))+1
        seg=_segments(n,wrap);sc=_score_segments(seg)
        if sc>-1e90:cands.append((sc,'fallback_wrap:'+name,seg))
    if not cands:return None
    sc,mode,seg=max(cands,key=lambda z:(z[0],z[1]))
    return {'score':float(sc),'mode':mode,'segments':seg}


def _geometry(H,r):
    try:
        g,_=r.choose_geometry(H);return g
    except RuntimeError:
        return _fallback_geometry(H,r)


def extract(ds,manifest,epsj,frac):
    large=b.large;r=large.r;eps=float(epsj['datasets'][ds]['epsilon'])
    d=next(z for z in manifest['datasets'] if z['id']==ds);objects=[r.obj(u) for u in d['objects']]
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces);target=int(round(float(frac)*max(0,total-1)))
        chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),target-window//2));n=min(window,total-st)
            H=large.read_header_window(rr,s,st,n);g=_geometry(H,r)
            if g is None:continue
            long_rows=[(a+st,z+st) for a,z in g['segments'] if z-a>=NX]
            if len(long_rows)<NY:continue
            choices=[]
            for i in range(len(long_rows)-NY+1):
                block=long_rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);choices.append((abs(mid-target),i,block))
            _,_,block=min(choices,key=lambda z:(z[0],z[1]));minlen=min(z-a for a,z in block)
            chosen=(window,g,long_rows,block,minlen);break
        if chosen is None:raise RuntimeError(('no header-derived 4x32 geometry after deterministic expansion',ds,frac,WINDOWS))
        window,g,long_rows,block,minlen=chosen;X,ids=r.read_tile(rr,s,block,minlen)
        return np.ascontiguousarray(X),eps,{
          'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),
          'geometry_mode':g['mode'],'header_window':int(window),'extractor_version':VERSION,'long_rows_available':int(len(long_rows)),
          'selection':'fixed fraction; nearest four header-derived rows length >=32; amplitudes unused'}
    finally:rr.close()

q.b.extract=extract
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);q.main(p.parse_args())
