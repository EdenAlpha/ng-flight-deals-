#!/usr/bin/env python3
"""Extract deterministic native-geometry tiles across migrated SEG-Y objects.

Locations come only from fixed fractional positions and header-derived geometry;
sample values never choose locations. The NPZ contains raw float32 tiles and
trace-index metadata for held-out compression-model transfer experiments.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_3d_runner as r
import migrated_volume_large_native_screen as large

FRACTIONS=tuple(np.linspace(.04,.96,16).tolist())
HEADER_WINDOW=14000


def extract(objects, stream_index=0):
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:
            raise RuntimeError('fixed-stride SEG-Y required')
        total=int(s.total_traces);tiles=[];meta=[];seen=set();skipped=[]
        for wi,frac in enumerate(FRACTIONS):
            center=int(round(frac*max(0,total-1)))
            st=max(0,min(max(0,total-HEADER_WINDOW),center-HEADER_WINDOW//2))
            n=min(HEADER_WINDOW,total-st)
            try:
                A=large.read_header_window(rr,s,st,n)
                geom,_=r.choose_geometry(A)
                seg=[(a+st,b+st) for a,b in geom['segments']]
                groups=r.groups_from_segments(seg,1)
                gi,block,minlen=groups[0]
                X,ids=r.read_tile(rr,s,block,minlen)
            except RuntimeError as ex:
                skipped.append({'fraction':float(frac),'window_start':int(st),'reason':str(ex)[:240]})
                print('CORPUS_SKIP',stream_index,wi,frac,str(ex)[:180],flush=True)
                continue
            key=(int(ids[0]),int(ids[-1]))
            if key in seen: continue
            seen.add(key);tiles.append(np.asarray(X,np.float32))
            meta.append({'stream_index':int(stream_index),'fraction':float(frac),'window_start':int(st),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':key[0],'trace_last':key[1],'shape':list(map(int,X.shape))})
            print('CORPUS_TILE',stream_index,wi,frac,key,X.shape,flush=True)
        if len(tiles)<8: raise RuntimeError(('too few distinct geometry-valid tiles',len(tiles),'skipped',len(skipped)))
        shapes={tuple(q.shape) for q in tiles}
        if len(shapes)!=1: raise RuntimeError(('nonuniform tile shapes',sorted(shapes)))
        return tiles,meta,total,skipped
    finally:
        rr.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    m=json.load(open(a.manifest));e=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(e['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    streams=[oo] if ds.get('assembly') else [[o] for o in oo]
    tiles=[];meta=[];totals=[];skipped=[]
    for si,stream in enumerate(streams):
        tt,mm,total,ss=extract(stream,si);tiles.extend(tt);meta.extend(mm);totals.append(int(total));skipped.extend([{'stream_index':si,**q} for q in ss])
    shapes={tuple(q.shape) for q in tiles}
    if len(shapes)!=1: raise RuntimeError(('nonuniform corpus tile shapes across streams',sorted(shapes)))
    tiles=np.stack(tiles)
    np.savez_compressed(a.out,tiles=tiles,epsilon=np.asarray([eps],np.float64),metadata_json=np.asarray([json.dumps(meta)]),total_traces=np.asarray([sum(totals)],np.int64),fractions=np.asarray(FRACTIONS,np.float64))
    Path(a.out+'.json').write_text(json.dumps({'dataset_id':a.dataset,'epsilon':eps,'tiles':len(tiles),'tile_shape':list(map(int,tiles.shape[1:])),'stream_trace_counts':totals,'total_traces':sum(totals),'positions':meta,'skipped_fixed_positions':skipped,'location_selection_uses_sample_values':False},indent=2))
    print('CORPUS_DONE',a.dataset,len(tiles),tiles.shape,'SKIPPED',len(skipped),flush=True)

if __name__=='__main__': main()
