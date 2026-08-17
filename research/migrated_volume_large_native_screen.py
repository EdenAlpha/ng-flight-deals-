#!/usr/bin/env python3
"""Larger coherent native-geometry validation for migrated seismic volumes.

This is deliberately a scale/transfer gate, not another tuning screen. Geometry
is rediscovered from SEG-Y trace headers in three deterministic windows. From a
fixed dataset-agnostic ladder it selects the largest rectangular line x fast
trace block supported by the discovered geometry, then compares a small frozen
exact codec portfolio against matched SZ3 on the identical samples/epsilon.

No sample value affects location, geometry selection, block shape, or codec
parameters. Codec selection itself is only by final serialized bytes.
"""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
import numpy as np

import migrated_volume_3d_runner as r
import migrated_volume_3d_geometry_v2 as gv2
import migrated_volume_3d_brotli_bitplanes as br
import migrated_volume_3d_ft_half_brotli as fh
import migrated_volume_3d_ft_half3d_brotli as fh3
from general_seismic_numeric_io import matched_sz3

FRACTIONS=(0.10,0.50,0.90)
WINDOW_TRACES=60000
# Descending sample-context ladder. First feasible shape wins; data values never
# participate. 16x128 is 64x the spatial context of the original 4x32 screen.
SHAPES=((16,128),(12,128),(8,128),(8,96),(8,64),(4,128),(4,64))
MODE_OVERHEAD=8

# Geometry discovery retains permissive small-run thresholds; block sizing is a
# separate deterministic step below.
r.NY=4; r.NX=32
_base_geom=r.geometry_candidates
r.geometry_candidates=lambda A: gv2.geometry_candidates(_base_geom,r,A)


def read_header_window(reader,segy,start,count):
    total=int(segy.total_traces);start=max(0,min(int(start),max(0,total-1)));count=min(int(count),total-start)
    reader.seek(segy.trace_start+start*segy.binary_stride);raw=reader.read(count*segy.binary_stride)
    if len(raw)!=count*segy.binary_stride:raise RuntimeError(('short header window',start,count,len(raw)))
    A=np.empty((count,len(r.FIELDS)),np.int64)
    for i in range(count):
        th=raw[i*segy.binary_stride:i*segy.binary_stride+240]
        for j,o in enumerate(r.FIELDS.values()):A[i,j]=struct.unpack(segy.endian+'i',th[o:o+4])[0]
    return A


def choose_large_group(segments_abs):
    seg=list(segments_abs)
    if len(seg)>2:seg=seg[1:-1]  # reject truncated window-edge runs
    for ny,nx in SHAPES:
        valid=[]
        for i in range(0,len(seg)-ny+1):
            block=seg[i:i+ny];lens=[b-a for a,b in block]
            if min(lens)>=nx:valid.append((i,block,min(lens),ny,nx))
        if valid:return valid[len(valid)//2]
    raise RuntimeError(('no large native block supported',segments_abs[:20]))


def read_tile(reader,segy,block,minlen,nx):
    fast0=max(0,(int(minlen)-int(nx))//2);tile=[];indices=[]
    for a,b in block:
        st=int(a)+fast0;reader.seek(segy.trace_start+st*segy.binary_stride);segy.trace_index=st;rows=[]
        for x in range(int(nx)):
            q=segy.next_trace()
            if q is None:raise RuntimeError(('unexpected eof',st,x,nx))
            arr,th=q;rows.append(np.asarray(arr,np.float32));indices.append(st+x)
        tile.append(np.asarray(rows,np.float32))
    X=np.asarray(tile,np.float32)
    if X.ndim!=3:raise RuntimeError(('bad large tile',X.shape))
    return np.ascontiguousarray(X),indices


def candidates(X,eps):
    # Frozen compact portfolio: baseline spatial bitplanes plus two causal
    # half-mismatch variants. All are self-contained exact streams.
    rows=[br.candidate(X,eps),fh.candidate(X,eps),fh3.candidate(X,eps)]
    return min(rows,key=lambda q:(q['bytes'],q['tid'])),rows


def screen_stream(objects,tag,eps):
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('large screen needs fixed stride',tag,s.ns_policy))
        total=int(s.total_traces);rows=[]
        for wi,frac in enumerate(FRACTIONS):
            center=int(round(frac*max(0,total-1)));st=max(0,min(total-WINDOW_TRACES,center-WINDOW_TRACES//2)) if total>WINDOW_TRACES else 0;n=min(WINDOW_TRACES,total-st)
            A=read_header_window(rr,s,st,n);geom,ranked=r.choose_geometry(A);segabs=[(a+st,b+st) for a,b in geom['segments']]
            gi,block,minlen,ny,nx=choose_large_group(segabs);X,ids=read_tile(rr,s,block,minlen,nx)
            best,cands=candidates(X,eps);sb,sme=matched_sz3(X,eps);ours=int(best['bytes'])+MODE_OVERHEAD;gain=float(sb/ours);me=float(best['maxerr'])
            row={'window_index':wi,'window_fraction':frac,'geometry_mode':geom['mode'],'geometry_score':float(geom['score']),'shape':list(map(int,X.shape)),'spatial_shape':[int(ny),int(nx)],'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'samples':int(X.size),'winner':{br.TID:'fast_delta_brotli_multitraversal',fh.TID:fh.NAME,fh3.TID:fh3.NAME}[best['tid']],'ours_bytes':ours,'codec_bytes':int(best['bytes']),'sz3_bytes':int(sb),'gain_vs_sz3':gain,'maxerr':me,'sz3_maxerr':float(sme),'candidate_bytes':{str(c['tid']):int(c['bytes'])+MODE_OVERHEAD for c in cands}}
            if me>eps*(1+3e-6) or float(sme)>eps*(1+3e-6):raise RuntimeError(('hard bound',tag,wi,me,sme,eps))
            rows.append(row);print('MV3D_LARGE',tag,wi,'F',frac,'SHAPE',X.shape,'SZ3',sb,'OURS',ours,'GAIN',gain,'WIN',row['winner'],flush=True)
        return {'logical_file':tag,'total_traces':total,'windows':rows}
    finally:rr.close()


def run(args):
    m=json.load(open(args.manifest));ej=json.load(open(args.eps));ds=next(d for d in m['datasets'] if d['id']==args.dataset);eps=float(ej['datasets'][args.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    streams=[screen_stream(oo,'assembled',eps)] if ds.get('assembly') else [screen_stream([o],o['key'],eps) for o in oo]
    tiles=[q for s in streams for q in s['windows']]
    out={'kind':'migrated-volume-large-native-v1','dataset_id':args.dataset,'epsilon':eps,'fractions':list(FRACTIONS),'shape_ladder':[list(q) for q in SHAPES],'streams':streams,'tile_count':len(tiles),'wins':int(sum(q['gain_vs_sz3']>1 for q in tiles)),'min_gain':float(min(q['gain_vs_sz3'] for q in tiles)),'median_gain':float(np.median([q['gain_vs_sz3'] for q in tiles])),'byte_weighted_gain':float(sum(q['sz3_bytes'] for q in tiles)/sum(q['ours_bytes'] for q in tiles)),'total_samples':int(sum(q['samples'] for q in tiles)),'all_valid':True,'no_sample_value_location_or_shape_selection':True}
    Path(args.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
