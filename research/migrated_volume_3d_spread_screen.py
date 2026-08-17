#!/usr/bin/env python3
"""Deterministic cross-volume native-3D migrated seismic screen.

Unlike the early native screen, this does not take all tiles from the beginning
of each SEG-Y stream. It opens five fixed trace windows centered at 5%, 27.5%,
50%, 72.5%, and 95% of every logical stream, rediscovers native line geometry
from trace headers inside each window, then tests one 4x32xT tile per window.
Tile locations depend only on trace count/header geometry, never sample values.
"""
from __future__ import annotations

import argparse,json,struct
from pathlib import Path
import numpy as np

# Importing this module installs the full current codec competition stack:
# original exact codecs + residual entropy + block predictor + Brotli bitplanes.
import migrated_volume_3d_runner_entropy  # noqa: F401
import migrated_volume_3d_runner as r
from general_seismic_numeric_io import matched_sz3

FRACTIONS=(0.05,0.275,0.50,0.725,0.95)
WINDOW_TRACES=36000
MODE_OVERHEAD=8


def read_header_window(reader,segy,start,count):
    if not segy.binary_stride_exact or segy.total_traces is None:
        raise RuntimeError(('spread screen needs fixed stride',segy.ns_policy))
    total=int(segy.total_traces); start=max(0,min(int(start),max(0,total-1))); count=min(int(count),total-start)
    reader.seek(segy.trace_start+start*segy.binary_stride)
    raw=reader.read(count*segy.binary_stride)
    if len(raw)!=count*segy.binary_stride:
        raise RuntimeError(('short spread header window',start,count,len(raw),count*segy.binary_stride))
    A=np.empty((count,len(r.FIELDS)),np.int64)
    for i in range(count):
        th=raw[i*segy.binary_stride:i*segy.binary_stride+240]
        for j,o in enumerate(r.FIELDS.values()):
            A[i,j]=struct.unpack(segy.endian+'i',th[o:o+4])[0]
    return A


def middle_group(segments_abs):
    # Window-edge segments are truncated by construction, so never use them.
    seg=list(segments_abs)
    if len(seg)>2: seg=seg[1:-1]
    valid=[]
    for i in range(0,len(seg)-r.NY+1):
        block=seg[i:i+r.NY]
        lens=[b-a for a,b in block]
        if min(lens)>=r.NX:
            valid.append((i,block,min(lens)))
    if not valid:
        raise RuntimeError(('no complete rectangular group in spread window',segments_abs[:12]))
    return valid[len(valid)//2]


def screen_stream(objects,tag,eps):
    rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:
            raise RuntimeError(('spread stream not fixed stride',tag,s.ns_policy))
        total=int(s.total_traces); starts=[]
        for frac in FRACTIONS:
            center=int(round(frac*max(0,total-1)))
            st=max(0,min(total-WINDOW_TRACES,center-WINDOW_TRACES//2)) if total>WINDOW_TRACES else 0
            if st not in starts: starts.append(st)
        rows=[]
        for wi,st in enumerate(starts):
            n=min(WINDOW_TRACES,total-st)
            A=read_header_window(rr,s,st,n)
            geom,ranked=r.choose_geometry(A)
            segabs=[(a+st,b+st) for a,b in geom['segments']]
            gi,block,minlen=middle_group(segabs)
            X,ids=r.read_tile(rr,s,block,minlen)
            best,cands=r.codec.compete(X,eps)
            sb,sme=matched_sz3(X,eps)
            ours=int(best['bytes'])+MODE_OVERHEAD
            gain=float(sb/ours)
            row={
                'window_index':wi,'window_fraction':float(FRACTIONS[wi]),'window_trace_start':int(st),
                'geometry_mode':geom['mode'],'geometry_score':float(geom['score']),
                'geometry_top':ranked[:5],'group_index_local':int(gi),
                'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),
                'samples':int(X.size),'winner':r.codec.NAMES[best['tid']],
                'ours_bytes':ours,'codec_bytes':int(best['bytes']),'geometry_mode_overhead':MODE_OVERHEAD,
                'sz3_bytes':int(sb),'gain_vs_sz3':gain,'maxerr':float(best['maxerr']),'sz3_maxerr':float(sme),
                'candidate_bytes':{r.codec.NAMES[c['tid']]:int(c['bytes'])+MODE_OVERHEAD for c in cands},
            }
            rows.append(row)
            print('MV3D_SPREAD',tag,wi,'F',FRACTIONS[wi],'TRACE',ids[0],ids[-1],'GEOM',geom['mode'],
                  'SZ3',sb,'OURS',ours,'GAIN',gain,'WIN',row['winner'],flush=True)
        return {'logical_file':tag,'total_traces':total,'windows':rows}
    finally:
        rr.close()


def run(args):
    m=json.load(open(args.manifest)); ej=json.load(open(args.eps))
    ds=next(d for d in m['datasets'] if d['id']==args.dataset)
    eps=float(ej['datasets'][args.dataset]['epsilon']); oo=[r.obj(u) for u in ds['objects']]
    if ds.get('assembly'):
        streams=[screen_stream(oo,'assembled',eps)]
    else:
        streams=[screen_stream([o],o['key'],eps) for o in oo]
    tiles=[q for s in streams for q in s['windows']]
    if not tiles: raise RuntimeError('no spread tiles')
    out={
        'kind':'migrated-volume-native-3d-spread-v1','dataset_id':args.dataset,'epsilon':eps,
        'fractions':list(FRACTIONS),'window_traces':WINDOW_TRACES,'streams':streams,'tile_count':len(tiles),
        'wins':int(sum(q['gain_vs_sz3']>1.0 for q in tiles)),
        'min_gain':float(min(q['gain_vs_sz3'] for q in tiles)),
        'p10_gain':float(np.percentile([q['gain_vs_sz3'] for q in tiles],10)),
        'median_gain':float(np.median([q['gain_vs_sz3'] for q in tiles])),
        'byte_weighted_gain':float(sum(q['sz3_bytes'] for q in tiles)/sum(q['ours_bytes'] for q in tiles)),
        'all_valid':bool(all(q['maxerr']<=eps*(1+3e-6) and q['sz3_maxerr']<=eps*(1+3e-6) for q in tiles)),
        'no_sample_value_location_selection':True,
    }
    Path(args.out).write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())

if __name__=='__main__':main()
