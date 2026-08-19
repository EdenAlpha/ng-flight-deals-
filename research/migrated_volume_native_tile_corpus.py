#!/usr/bin/env python3
"""Extract deterministic native-geometry tiles across a migrated SEG-Y object.

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

# Fixed before reading any sample values; also serves as the corpus protocol ID.
FRACTIONS=tuple(np.linspace(.04,.96,16).tolist())
HEADER_WINDOW=14000
# PR gate marker: four-survey corpus extraction, 2026-08-19.


def extract(objects):
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:
            raise RuntimeError('fixed-stride SEG-Y required')
        total=int(s.total_traces);tiles=[];meta=[];seen=set()
        for wi,frac in enumerate(FRACTIONS):
            center=int(round(frac*max(0,total-1)))
            st=max(0,min(max(0,total-HEADER_WINDOW),center-HEADER_WINDOW//2))
            n=min(HEADER_WINDOW,total-st)
            A=large.read_header_window(rr,s,st,n)
            geom,_=r.choose_geometry(A)
            seg=[(a+st,b+st) for a,b in geom['segments']]
            groups=r.groups_from_segments(seg,1)
            gi,block,minlen=groups[0]
            X,ids=r.read_tile(rr,s,block,minlen)
            key=(int(ids[0]),int(ids[-1]))
            if key in seen: continue
            seen.add(key);tiles.append(np.asarray(X,np.float32))
            meta.append({'fraction':float(frac),'window_start':int(st),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':key[0],'trace_last':key[1],'shape':list(map(int,X.shape))})
            print('CORPUS_TILE',wi,frac,key,X.shape,flush=True)
        if len(tiles)<8: raise RuntimeError(('too few distinct tiles',len(tiles)))
        shapes={tuple(q.shape) for q in tiles}
        if len(shapes)!=1: raise RuntimeError(('nonuniform tile shapes',sorted(shapes)))
        return np.stack(tiles),meta,total
    finally:
        rr.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    m=json.load(open(a.manifest));e=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(e['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    tiles,meta,total=extract(oo)
    np.savez_compressed(a.out,tiles=tiles,epsilon=np.asarray([eps],np.float64),metadata_json=np.asarray([json.dumps(meta)]),total_traces=np.asarray([total],np.int64),fractions=np.asarray(FRACTIONS,np.float64))
    Path(a.out+'.json').write_text(json.dumps({'dataset_id':a.dataset,'epsilon':eps,'tiles':len(tiles),'tile_shape':list(map(int,tiles.shape[1:])),'total_traces':total,'positions':meta,'location_selection_uses_sample_values':False},indent=2))
    print('CORPUS_DONE',a.dataset,len(tiles),tiles.shape,flush=True)

if __name__=='__main__': main()
