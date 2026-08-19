#!/usr/bin/env python3
"""Robust geometry wrapper for migrated_volume_quick_adapter_loso_v1.

Some migrated SEG-Y header segmentations contain one-trace separator runs between
long spatial rows.  For the probability-transfer gate, select rows using only
header-derived run length: keep runs long enough for a native 32-trace row and
choose four consecutive valid long rows nearest the middle of that fixed window.
No sample value or dataset-specific route participates.
"""
from __future__ import annotations
import argparse,json
import numpy as np
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_crosssurvey_prob_screen as b

NY=4
NX=32
WINDOW=15000


def extract_long_rows(ds,manifest,epsj,frac):
    large=b.large;r=large.r
    eps=float(epsj['datasets'][ds]['epsilon'])
    d=next(z for z in manifest['datasets'] if z['id']==ds)
    objects=[r.obj(u) for u in d['objects']]
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces)
        center=int(round(float(frac)*max(0,total-1)))
        st=max(0,min(max(0,total-WINDOW),center-WINDOW//2));n=min(WINDOW,total-st)
        H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H)
        seg=[(a+st,b0+st) for a,b0 in geom['segments']]
        long_rows=[z for z in seg if z[1]-z[0]>=NX]
        if len(long_rows)<NY:raise RuntimeError(('too few valid long rows',ds,frac,long_rows[:20]))
        starts=list(range(len(long_rows)-NY+1));i=starts[len(starts)//2]
        block=long_rows[i:i+NY];minlen=min(z-a for a,z in block)
        X,ids=r.read_tile(rr,s,block,minlen)
        return np.ascontiguousarray(X),eps,{
          'fraction':float(frac),'shape':list(map(int,X.shape)),
          'trace_first':int(ids[0]),'trace_last':int(ids[-1]),
          'geometry_mode':geom['mode'],'long_rows_available':int(len(long_rows)),
          'selection':'middle four header-derived rows with length >=32'}
    finally:rr.close()

q.b.extract=extract_long_rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);q.main(p.parse_args())
