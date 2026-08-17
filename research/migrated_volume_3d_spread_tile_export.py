#!/usr/bin/env python3
"""Export one deterministic native-3D spread tile for offline codec R&D.

The location algorithm is exactly the spread benchmark's header-only rule. This
is a research fixture exporter only; production codecs never receive dataset or
window identities.
"""
import argparse,json
import numpy as np
import migrated_volume_3d_spread_screen as sp
import migrated_volume_3d_runner as r


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--window-index',type=int,required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    m=json.load(open(a.manifest)); ej=json.load(open(a.eps)); ds=next(d for d in m['datasets'] if d['id']==a.dataset); eps=float(ej['datasets'][a.dataset]['epsilon']); oo=[r.obj(u) for u in ds['objects']]
    if not ds.get('assembly'): raise RuntimeError('exporter currently requires assembled logical stream')
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr); total=int(s.total_traces); wi=int(a.window_index)
        if wi<0 or wi>=len(sp.FRACTIONS): raise ValueError(wi)
        frac=sp.FRACTIONS[wi]; center=int(round(frac*max(0,total-1)))
        st=max(0,min(total-sp.WINDOW_TRACES,center-sp.WINDOW_TRACES//2)) if total>sp.WINDOW_TRACES else 0
        n=min(sp.WINDOW_TRACES,total-st); A=sp.read_header_window(rr,s,st,n); geom,ranked=r.choose_geometry(A); segabs=[(x+st,y+st) for x,y in geom['segments']]; gi,block,minlen=sp.middle_group(segabs); X,ids=r.read_tile(rr,s,block,minlen)
        meta={'dataset_id':a.dataset,'window_index':wi,'window_fraction':float(frac),'window_trace_start':int(st),'geometry_mode':geom['mode'],'geometry_score':float(geom['score']),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'epsilon':eps}
        np.savez_compressed(a.out,tile=np.asarray(X,np.float32),epsilon=np.asarray([eps],np.float64),metadata_json=np.asarray([json.dumps(meta)])); print(json.dumps(meta,indent=2),flush=True)
    finally: rr.close()

if __name__=='__main__':main()
