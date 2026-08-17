#!/usr/bin/env python3
"""Measure SZ3's whole-block advantage over regular 4x64 native cells."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
from general_seismic_numeric_io import matched_sz3
TY,TX=4,64

def stream(objects,tag,eps):
 r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
  for wi,frac in enumerate(large.FRACTIONS):
   center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
   A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']]
   gi,block,minlen,ny,nx=large.choose_large_group(seg);X,_=large.read_tile(rr,s,block,minlen,nx)
   ny2=(X.shape[0]//TY)*TY;nx2=(X.shape[1]//TX)*TX;X=np.ascontiguousarray(X[:ny2,:nx2]);whole,we=matched_sz3(X,eps);tile_sum=0
   for y in range(0,ny2,TY):
    for x in range(0,nx2,TX):
     b,e=matched_sz3(np.ascontiguousarray(X[y:y+TY,x:x+TX]),eps);tile_sum+=int(b)
   adv=float(tile_sum/whole)
   row={'window_index':wi,'window_fraction':frac,'shape':list(map(int,X.shape)),'whole_sz3_bytes':int(whole),'sum_4x64_sz3_bytes':int(tile_sum),'whole_block_advantage':adv,'whole_maxerr':float(we)};rows.append(row)
   print('SZ3_SCALE',tag,wi,X.shape,whole,tile_sum,adv,flush=True)
  return {'logical_file':tag,'windows':rows}
 finally:rr.close()
def run(a):
 r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
 ss=[stream(oo,'assembled',eps)] if ds.get('assembly') else [stream([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
 out={'kind':'migrated-volume-sz3-scale-diag','compression_class':'migrated_poststack_3d','dataset_id':a.dataset,'tile_shape':[TY,TX],'positions':len(rows),'median_whole_block_advantage':float(np.median([q['whole_block_advantage'] for q in rows])),'weighted_whole_block_advantage':sum(q['sum_4x64_sz3_bytes'] for q in rows)/sum(q['whole_sz3_bytes'] for q in rows),'streams':ss};Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
