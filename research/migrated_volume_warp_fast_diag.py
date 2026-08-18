#!/usr/bin/env python3
"""Fast diagnostic for the causal quotient/warp hypothesis on native 4x32 tiles.

This is not a scale claim. It asks a more fundamental question at three frozen
positions: after self-derived integer/fractional alignment, does innovation
activity and fully coded size collapse relative to the incumbent predictor?
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_large_context_v4_screen as base
import migrated_volume_3d_causal_warp as warp
import migrated_volume_3d_fractional_warp as fwarp
from general_seismic_numeric_io import matched_sz3
OVERHEAD=8; NY=4; NX=32

def choose_small(segabs):
    seg=list(segabs)
    if len(seg)>2:seg=seg[1:-1]
    valid=[]
    for i in range(0,len(seg)-NY+1):
        block=seg[i:i+NY];lens=[b-a for a,b in block]
        if min(lens)>=NX:valid.append((block,min(lens)))
    if not valid:raise RuntimeError(('no 4x32 native block',segabs[:20]))
    return valid[len(valid)//2]

def screen(objects,tag,eps):
    r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
        for wi,frac in enumerate(large.FRACTIONS):
            center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
            A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']];block,minlen=choose_small(seg);X,ids=large.read_tile(rr,s,block,minlen,NX)
            old,_=base.compete(X,eps);oldbytes=int(old['bytes']);wc=[]
            for mod,fam in ((warp,'integer'),(fwarp,'fractional')):
                for tid in sorted(mod.PARAMS):
                    d,b=mod.candidate(X,eps,tid);q=dict(d);q['family']=fam;q['bytes_charged']=len(b)+OVERHEAD;wc.append(q)
            wb=min(wc,key=lambda q:(q['bytes_charged'],q['tid']));sb,sme=matched_sz3(X,eps)
            row={'window_index':wi,'fraction':frac,'shape':list(X.shape),'incumbent_name':old['name'],'incumbent_bytes':oldbytes,
                 'sz3_bytes':int(sb),'incumbent_gain_vs_sz3':float(sb/oldbytes),'warp_name':wb['name'],'warp_family':wb['family'],'warp_tid':wb['tid'],
                 'warp_bytes':int(wb['bytes_charged']),'warp_gain_vs_sz3':float(sb/wb['bytes_charged']),'warp_gain_vs_incumbent':float(oldbytes/wb['bytes_charged']),
                 'warp_nonzero_fraction':float(wb['nonzero_fraction']),'warp_mean_abs_residual':float(wb['mean_abs_residual']),'warp_candidates':wc}
            if sme>eps*(1+3e-6):raise RuntimeError(('sz3 hard',tag,wi,sme,eps))
            rows.append(row);print('FAST_WARP',tag,wi,'OLD',oldbytes,'WARP',wb['bytes_charged'],'SZ3',sb,'REL',row['warp_gain_vs_incumbent'],'WG',row['warp_gain_vs_sz3'],'NZ',row['warp_nonzero_fraction'],'FAM',wb['family'],flush=True)
        return {'logical_file':tag,'windows':rows}
    finally:rr.close()

def run(a):
    r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    ss=[screen(oo,'assembled',eps)] if ds.get('assembly') else [screen([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
    out={'kind':'migrated-volume-warp-fast-diagnostic-v1','dataset_id':a.dataset,'epsilon':eps,'positions':len(rows),'shape':[NY,NX,'native_nt'],
         'warp_beats_incumbent':sum(q['warp_gain_vs_incumbent']>1 for q in rows),'warp_beats_sz3':sum(q['warp_gain_vs_sz3']>1 for q in rows),
         'weighted_warp_vs_incumbent':sum(q['incumbent_bytes'] for q in rows)/sum(q['warp_bytes'] for q in rows),
         'weighted_warp_vs_sz3':sum(q['sz3_bytes'] for q in rows)/sum(q['warp_bytes'] for q in rows),
         'median_nonzero_fraction':float(np.median([q['warp_nonzero_fraction'] for q in rows])),'fractional_wins':sum(q['warp_family']=='fractional' for q in rows),'streams':ss}
    Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
