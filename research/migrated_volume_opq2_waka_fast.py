#!/usr/bin/env python3
"""Waka-only fast native 4x32 gate for operator quotient v1/v2."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_large_context_v4_screen as base
import migrated_volume_3d_operator_quotient as op1
import migrated_volume_3d_operator_quotient_v2 as op2
from general_seismic_numeric_io import matched_sz3
NY,NX,OVERHEAD=4,32,8

def small(segabs):
    seg=list(segabs)
    if len(seg)>2:seg=seg[1:-1]
    good=[]
    for i in range(len(seg)-NY+1):
        b=seg[i:i+NY];lens=[z-a for a,z in b]
        if min(lens)>=NX:good.append((b,min(lens)))
    if not good:raise RuntimeError('no native 4x32')
    return good[len(good)//2]

def main():
    r=large.r;m=json.load(open('frozen_manifest.json'));ej=json.load(open('benchmarks/migrated_volume_global_eps_v1.json'));ds=next(d for d in m['datasets'] if d['id']=='marine_waka_3d');eps=float(ej['datasets']['marine_waka_3d']['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
      s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
      for wi,frac in enumerate(large.FRACTIONS):
        center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
        A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']];block,minlen=small(seg);X,ids=large.read_tile(rr,s,block,minlen,NX)
        incumbent,_=base.compete(X,eps);ib=int(incumbent['bytes']);cand=[]
        for mod,fam in ((op1,'opq1'),(op2,'opq2')):
          for tid in sorted(mod.PARAMS):
            d,b=mod.candidate(X,eps,tid);q=dict(d);q['family']=fam;q['charged']=len(b)+OVERHEAD;cand.append(q);print('OPQ',wi,fam,tid,q['charged'],q['nonzero_fraction'],flush=True)
        best=min(cand,key=lambda q:(q['charged'],q['tid']));sb,sme=matched_sz3(X,eps)
        row={'position':wi,'fraction':frac,'shape':list(X.shape),'incumbent':incumbent['name'],'incumbent_bytes':ib,'sz3_bytes':int(sb),'op_name':best['name'],'op_family':best['family'],'op_tid':int(best['tid']),'op_bytes':int(best['charged']),'op_nonzero_fraction':float(best['nonzero_fraction']),'gain_vs_incumbent':float(ib/best['charged']),'gain_vs_sz3':float(sb/best['charged']),'candidates':cand}
        if sme>eps*(1+3e-6):raise RuntimeError(('sz3 hard',sme,eps))
        rows.append(row);print('WAKA_OPQ2_GATE',json.dumps({k:v for k,v in row.items() if k!='candidates'}),flush=True)
      out={'dataset_id':'marine_waka_3d','epsilon':eps,'rows':rows,'weighted_gain_vs_incumbent':sum(x['incumbent_bytes'] for x in rows)/sum(x['op_bytes'] for x in rows),'weighted_gain_vs_sz3':sum(x['sz3_bytes'] for x in rows)/sum(x['op_bytes'] for x in rows),'median_nonzero_fraction':float(np.median([x['op_nonzero_fraction'] for x in rows])),'all_valid':True,'zero_transmitted_operator_map':True}
      Path('waka_opq2_fast.json').write_text(json.dumps(out,indent=2));print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='rows'}),flush=True)
    finally:rr.close()
if __name__=='__main__':main()
