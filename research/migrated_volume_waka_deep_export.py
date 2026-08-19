#!/usr/bin/env python3
"""Export a deeper deterministic Waka native block for steady-state diagnostics.

Location is fixed by the same 5-percent spread window and SEG-Y header geometry.
No sample amplitudes choose the block.  Unlike the standard 4x32 fixture this
exports 16 consecutive geometry rows x 32 centered fast traces so startup cost
can be separated from steady-state behavior.
"""
from __future__ import annotations
import argparse,json
import numpy as np
import migrated_volume_3d_runner as r
import migrated_volume_3d_spread_screen as sp

NY=16
NX=32
# PR execution marker; does not affect block selection or sample values.


def choose_group(segments, target_trace):
    valid=[]
    for i in range(0,len(segments)-NY+1):
        block=segments[i:i+NY]
        lens=[int(b-a) for a,b in block]
        if min(lens) < NX: continue
        lo=int(block[0][0]); hi=int(block[-1][1]); mid=(lo+hi)/2.0
        valid.append((abs(mid-float(target_trace)),i,block,min(lens)))
    if not valid: raise RuntimeError(('no 16x32 native group',segments[:30]))
    return min(valid,key=lambda q:(q[0],q[1]))


def read_deep_tile(reader,segy,block,minlen):
    fast0=max(0,(int(minlen)-NX)//2); rows=[]; indices=[]
    for a,b in block:
        st=int(a)+fast0
        reader.seek(segy.trace_start+st*segy.binary_stride);segy.trace_index=st
        line=[]
        for x in range(NX):
            q=segy.next_trace()
            if q is None: raise RuntimeError(('unexpected eof',st,x))
            arr,_=q;line.append(np.asarray(arr,np.float32));indices.append(st+x)
        rows.append(np.asarray(line,np.float32))
    X=np.asarray(rows,np.float32)
    if X.ndim!=3 or X.shape[0]!=NY or X.shape[1]!=NX: raise RuntimeError(('bad deep tile',X.shape))
    return np.ascontiguousarray(X),indices


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    m=json.load(open(a.manifest));e=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']=='marine_waka_3d');eps=float(e['datasets']['marine_waka_3d']['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    if not ds.get('assembly'): raise RuntimeError('Waka manifest assembly expected')
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces);wi=0;frac=float(sp.FRACTIONS[wi]);center=int(round(frac*max(0,total-1)))
        window=max(int(sp.WINDOW_TRACES),120000);st=max(0,min(total-window,center-window//2)) if total>window else 0;n=min(window,total-st)
        A=sp.read_header_window(rr,s,st,n);geom,ranked=r.choose_geometry(A);segabs=[(x+st,y+st) for x,y in geom['segments']]
        _,gi,block,minlen=choose_group(segabs,center);X,ids=read_deep_tile(rr,s,block,minlen)
        meta={'kind':'waka-deep-native-steady-state-v1','dataset_id':'marine_waka_3d','window_fraction':frac,'window_trace_start':int(st),'target_trace_center':int(center),'geometry_mode':geom['mode'],'geometry_score':float(geom['score']),'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'epsilon':eps,'location_uses_sample_values':False}
        np.savez_compressed(a.out,tile=X,epsilon=np.asarray([eps],np.float64),metadata_json=np.asarray([json.dumps(meta)]));print(json.dumps(meta,indent=2),flush=True)
    finally: rr.close()

if __name__=='__main__': main()
