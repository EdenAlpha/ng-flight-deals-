#!/usr/bin/env python3
"""Fast real-data gate for the self-derived local-operator quotient.

Uses native 4x32 tiles at the same deterministic 10/50/90% positions. This is
not a scale claim: it asks whether a zero-side-map local convolutional operator
can materially reduce fully coded bytes and innovation versus the incumbent.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_large_context_v4_screen as base
import migrated_volume_3d_operator_quotient as opq
from general_seismic_numeric_io import matched_sz3
OVERHEAD=8;NY=4;NX=32

def choose_small(segabs):
    seg=list(segabs)
    if len(seg)>2:seg=seg[1:-1]
    good=[]
    for i in range(len(seg)-NY+1):
        block=seg[i:i+NY];lens=[b-a for a,b in block]
        if min(lens)>=NX:good.append((block,min(lens)))
    if not good:raise RuntimeError(('no native 4x32 block',segabs[:20]))
    return good[len(good)//2]

def screen(objects,tag,eps):
    r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
        for wi,frac in enumerate(large.FRACTIONS):
            center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
            A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']]
            block,minlen=choose_small(seg);X,ids=large.read_tile(rr,s,block,minlen,NX)
            incumbent,_=base.compete(X,eps);ib=int(incumbent['bytes']);cands=[]
            for tid in sorted(opq.PARAMS):
                d,b=opq.candidate(X,eps,tid);q=dict(d);q['bytes_charged']=len(b)+OVERHEAD;cands.append(q)
                print('OPQ',tag,wi,tid,'NZ',q['nonzero_fraction'],'BYTES',q['bytes_charged'],'JOINT',q['joint_model_fraction'],flush=True)
            best=min(cands,key=lambda q:(q['bytes_charged'],q['tid']));sb,sme=matched_sz3(X,eps)
            row={'window_index':wi,'fraction':frac,'shape':list(X.shape),'samples':int(X.size),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),
                 'incumbent_name':incumbent['name'],'incumbent_bytes':ib,'incumbent_gain_vs_sz3':float(sb/ib),
                 'operator_name':best['name'],'operator_tid':int(best['tid']),'operator_bytes':int(best['bytes_charged']),
                 'operator_gain_vs_incumbent':float(ib/best['bytes_charged']),'operator_gain_vs_sz3':float(sb/best['bytes_charged']),
                 'operator_nonzero_fraction':float(best['nonzero_fraction']),'operator_mean_abs_residual':float(best['mean_abs_residual']),
                 'operator_joint_fraction':float(best['joint_model_fraction']),'sz3_bytes':int(sb),'sz3_maxerr':float(sme),'operator_candidates':cands}
            if sme>eps*(1+3e-6):raise RuntimeError(('sz3 hard',tag,wi,sme,eps))
            rows.append(row);print('OPQ_GATE',tag,wi,'OLD',ib,'OPQ',best['bytes_charged'],'SZ3',sb,'REL',row['operator_gain_vs_incumbent'],'GAIN',row['operator_gain_vs_sz3'],'NZ',row['operator_nonzero_fraction'],flush=True)
        return {'logical_file':tag,'windows':rows}
    finally:rr.close()

def run(a):
    r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    ss=[screen(oo,'assembled',eps)] if ds.get('assembly') else [screen([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
    out={'kind':'migrated-volume-operator-quotient-fast-v1','dataset_id':a.dataset,'epsilon':eps,'positions':len(rows),
         'operator_beats_incumbent':sum(q['operator_gain_vs_incumbent']>1 for q in rows),'operator_beats_sz3':sum(q['operator_gain_vs_sz3']>1 for q in rows),
         'weighted_operator_vs_incumbent':sum(q['incumbent_bytes'] for q in rows)/sum(q['operator_bytes'] for q in rows),
         'weighted_operator_vs_sz3':sum(q['sz3_bytes'] for q in rows)/sum(q['operator_bytes'] for q in rows),
         'median_nonzero_fraction':float(np.median([q['operator_nonzero_fraction'] for q in rows])),'min_nonzero_fraction':float(min(q['operator_nonzero_fraction'] for q in rows)),
         'all_valid':True,'zero_transmitted_operator_map':True,'streams':ss}
    Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
