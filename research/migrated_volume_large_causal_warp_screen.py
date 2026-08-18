#!/usr/bin/env python3
"""Hostile large native-3D screen for self-derived causal warp prediction.

Integer and half-sample warp candidates compete on identical large blocks
against the strongest existing monolithic v4/context/Brotli family and matched
whole-block SZ3. Every stream is decoder-validated and fully charged.
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
OVERHEAD=8

def screen_stream(objects,tag,eps):
    r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
        for wi,frac in enumerate(large.FRACTIONS):
            center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
            A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']]
            _,block,minlen,ny,nx=large.choose_large_group(seg);X,ids=large.read_tile(rr,s,block,minlen,nx)
            oldbest,oldcands=base.compete(X,eps);oldbytes=int(oldbest['bytes']);wc=[]
            for mod,fam in ((warp,'integer'),(fwarp,'fractional')):
                for tid in sorted(mod.PARAMS):
                    d,b=mod.candidate(X,eps,tid);q=dict(d);q['family']=fam;q['bytes_charged']=int(len(b)+OVERHEAD);wc.append(q)
                    shift=q.get('lag_mean_abs',q.get('delay_mean_abs_samples',0.0));fracdel=q.get('fractional_delay_fraction',0.0)
                    print('WARP',tag,wi,fam,tid,'NZ',q['nonzero_fraction'],'BYTES',q['bytes_charged'],'SHIFTABS',shift,'FRAC',fracdel,flush=True)
            wbest=min(wc,key=lambda q:(q['bytes_charged'],q['tid']));sb,sme=matched_sz3(X,eps)
            winner=min([{'name':oldbest['name'],'bytes':oldbytes,'kind':'incumbent'}]+[{'name':q['name'],'bytes':q['bytes_charged'],'kind':q['family'],'tid':q['tid']} for q in wc],key=lambda q:(q['bytes'],q['name']))
            row={'window_index':wi,'window_fraction':frac,'shape':list(map(int,X.shape)),'samples':int(X.size),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),
                 'incumbent_name':oldbest['name'],'incumbent_bytes':oldbytes,'incumbent_gain_vs_sz3':float(sb/oldbytes),
                 'best_warp_name':wbest['name'],'best_warp_family':wbest['family'],'best_warp_tid':int(wbest['tid']),'best_warp_bytes':int(wbest['bytes_charged']),
                 'best_warp_gain_vs_sz3':float(sb/wbest['bytes_charged']),'warp_gain_vs_incumbent':float(oldbytes/wbest['bytes_charged']),
                 'best_warp_nonzero_fraction':float(wbest['nonzero_fraction']),'best_warp_mean_abs_residual':float(wbest['mean_abs_residual']),
                 'winner':winner,'sz3_bytes':int(sb),'sz3_maxerr':float(sme),'warp_candidates':wc,'incumbent_candidates':{q['name']:int(q['bytes']) for q in oldcands}}
            if float(sme)>eps*(1+3e-6):raise RuntimeError(('sz3 hard',tag,wi,sme,eps))
            rows.append(row);print('WARP_GATE',tag,wi,'SZ3',sb,'OLD',oldbytes,'WARP',wbest['bytes_charged'],'WG',row['best_warp_gain_vs_sz3'],'REL',row['warp_gain_vs_incumbent'],'NZ',wbest['nonzero_fraction'],'FAM',wbest['family'],'WIN',winner['name'],flush=True)
        return {'logical_file':tag,'windows':rows}
    finally:rr.close()

def run(a):
    r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    ss=[screen_stream(oo,'assembled',eps)] if ds.get('assembly') else [screen_stream([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
    out={'kind':'migrated-volume-causal-warp-large-v2','dataset_id':a.dataset,'epsilon':eps,'positions':len(rows),
         'warp_beats_incumbent':int(sum(q['warp_gain_vs_incumbent']>1 for q in rows)),'warp_beats_sz3':int(sum(q['best_warp_gain_vs_sz3']>1 for q in rows)),
         'warp_weighted_gain_vs_sz3':float(sum(q['sz3_bytes'] for q in rows)/sum(q['best_warp_bytes'] for q in rows)),
         'warp_weighted_gain_vs_incumbent':float(sum(q['incumbent_bytes'] for q in rows)/sum(q['best_warp_bytes'] for q in rows)),
         'median_warp_nonzero_fraction':float(np.median([q['best_warp_nonzero_fraction'] for q in rows])),'min_warp_nonzero_fraction':float(min(q['best_warp_nonzero_fraction'] for q in rows)),
         'fractional_wins':int(sum(q['best_warp_family']=='fractional' for q in rows)),'all_valid':True,'zero_transmitted_warp_map':True,'streams':ss}
    Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
