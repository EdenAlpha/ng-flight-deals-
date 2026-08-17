#!/usr/bin/env python3
"""Export the exact width-adaptive native Waka tiles used by current v2+ screens."""
import argparse,json
import numpy as np
import migrated_volume_3d_runner_v2 as rv2
r=rv2.runner

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',default='waka_native_tiles_v2.npz');a=ap.parse_args()
    m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']=='marine_waka_3d');eps=float(ej['datasets']['marine_waka_3d']['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);A=r.read_header_matrix(rr,s,r.SCAN);geom,ranked=r.choose_geometry(A);groups=r.groups_from_segments(geom['segments'],2);arrays={};meta=[]
        for k,(gi,block,minlen) in enumerate(groups):
            X,ids=r.read_tile(rr,s,block,minlen);arrays[f'tile{k}']=X
            meta.append({'tile':k,'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape))})
        arrays['epsilon']=np.asarray([eps],np.float64);arrays['metadata_json']=np.asarray([json.dumps({'geometry':geom,'ranked':ranked,'selected_fast_width':int(r.NX),'tiles':meta})]);np.savez_compressed(a.out,**arrays)
        print(json.dumps({'dataset_id':'marine_waka_3d','epsilon':eps,'selected_fast_width':int(r.NX),'geometry_mode':geom['mode'],'geometry_score':geom['score'],'tiles':meta,'out':a.out},indent=2))
    finally:rr.close()
if __name__=='__main__':main()
