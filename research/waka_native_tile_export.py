#!/usr/bin/env python3
"""Export exact Waka native-geometry 4x64 screening tiles for rapid local codec R&D.

Research fixture only. Geometry is inferred by the same generic detector used by
the benchmark screen; no sample values influence geometry or tile selection.
"""
import argparse,json
import numpy as np
import migrated_volume_3d_runner as r
import migrated_volume_3d_geometry_v2 as gv2


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',default='waka_native_tiles.npz');a=ap.parse_args()
 m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']=='marine_waka_3d');eps=float(ej['datasets']['marine_waka_3d']['epsilon']);oo=[r.obj(u) for u in ds['objects']]
 # Match the successful native-3D v2 Waka screen exactly: four spatial lines,
 # 64 traces along the fast spatial axis. This is a research export only;
 # production codec selection remains structural and dataset-name independent.
 r.NY=4; r.NX=64
 rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr);A=r.read_header_matrix(rr,s,40000);base=r.geometry_candidates;cc=gv2.geometry_candidates(base,r,A)
  for q in cc:q['score']=r.score_geometry(q,A.shape[0])
  geom=max(cc,key=lambda z:(z['score'],z['mode']));groups=r.groups_from_segments(geom['segments'],2);arrays={};meta=[]
  for k,(gi,block,minlen) in enumerate(groups):
   X,ids=r.read_tile(rr,s,block,minlen);arrays[f'tile{k}']=X
   meta.append({'tile':k,'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape))})
  arrays['epsilon']=np.asarray([eps],np.float64);arrays['metadata_json']=np.asarray([json.dumps({'geometry_mode':geom['mode'],'geometry_score':geom['score'],'tiles':meta})])
  np.savez_compressed(a.out,**arrays)
  print(json.dumps({'dataset_id':'marine_waka_3d','epsilon':eps,'geometry_mode':geom['mode'],'geometry_score':geom['score'],'tiles':meta,'out':a.out},indent=2))
 finally:rr.close()
if __name__=='__main__':main()
