#!/usr/bin/env python3
"""Strict unseen-Kahu native-16x32 scale gate using the strongest general engine.

Purpose: isolate the repeated topology/startup penalty seen on 4x24 Kahu blocks.
The source-trained engine is unchanged: 15 non-Kahu 4x24 source tiles, the
320/240/160 interior probability model, source-only causal boundary-waveform
model, and decoder-reproducible post-charge adaptation. Only held-out target
geometry changes to native 16x32, with the current best 512-symbol cadence.

Kahu is absent from source fitting and normalization. Target locations are chosen
from fixed fractions and SEG-Y headers before amplitudes are inspected. Every
modeled target chunk is charged before it updates the model; replay uses only
already-decoded Kahu samples. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json,gc
from pathlib import Path
import numpy as np
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as g
import migrated_volume_large_native_screen as large
import boundary_waveform_probability_v1 as bw

TARGET='marine_kahu_3d'
TARGET_FRACS=(.15,.50,.85)
NY=16;NX=32;WINDOWS=(60000,120000,240000)
fr.CHUNK=512
REFERENCE_4X24_512_GAIN=1.9023606738716896


def extract16(ds,manifest,epsj,frac):
    r=large.r;eps=float(epsj['datasets'][ds]['epsilon']);d=next(z for z in manifest['datasets'] if z['id']==ds)
    objects=[r.obj(u) for u in d['objects']];stream,local_frac,oi=g._stream_for_fraction(d,objects,frac)
    rr=r.S3ConcatSequential(r.S3,stream,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if s.total_traces is None or not s.binary_stride_exact:raise RuntimeError(('fixed stride required',ds,frac,oi,s.ns_policy))
        total=int(s.total_traces);target=int(round(local_frac*max(0,total-1)));chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),target-window//2));n=min(window,total-st)
            H=large.read_header_window(rr,s,st,n);geom=g._geom(H,r)
            if geom is None:continue
            rows=[(a+st,z+st) for a,z in geom['segments'] if z-a>=NX]
            if len(rows)<NY:continue
            cand=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);cand.append((abs(mid-target),i,block))
            _,gi,block=min(cand,key=lambda z:(z[0],z[1]));chosen=(window,geom,gi,block,min(z-a for a,z in block),len(rows));break
        if chosen is None:raise RuntimeError(('no header-derived 16x32 block',ds,frac,oi,WINDOWS))
        window,geom,gi,block,minlen,nrows=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX)
        md={'dataset':ds,'fraction':float(frac),'local_fraction':float(local_frac),'object_index':int(oi),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(nrows),'selection_uses_sample_values':False}
        print('KAHU16_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()


def main(a):
    bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    train_ids=tuple(s for s in q.SURVEYS if s!=TARGET)
    for ds in train_ids:
        for frac in base.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=q.crop(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':md.get('trace_first')});print('KAHU16_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=extract16(TARGET,m,e,frac);targets.append((X,ep,md))
    for i in range(len(targets)):
        oi=targets[i][2]['object_index'];a0,a1=targets[i][2]['trace_first'],targets[i][2]['trace_last']
        for j in range(i):
            if targets[j][2]['object_index']!=oi:continue
            b0,b1=targets[j][2]['trace_first'],targets[j][2]['trace_last']
            if max(a0,b0)<=min(a1,b1):raise RuntimeError(('Kahu target overlap',i,j,oi,(a0,a1),(b0,b1)))
    # Source tiles are already frozen 4x24 crops. Preserve full target geometry
    # during scoring/adaptation and boundary-waveform evaluation.
    q.crop=lambda X: np.ascontiguousarray(X)
    net,mu,sd,static=fr.fit_base(source,20262019);state,u1,u2=fr.new_adapter(99200);reservoir=[];base_rows=[];adapt_rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'object_index':md['object_index'],'trace_first':md['trace_first'],'trace_last':md['trace_last'],'geometry_mode':md['geometry_mode'],'shape':list(map(int,X.shape))}
        base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('KAHU16_REPLAY',json.dumps(row),flush=True);gc.collect()
    bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows);samples=sum(z['samples'] for z in adapt_rows);sz=sum(z['sz3_bytes'] for z in adapt_rows);ours=sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
    out={'kind':'unseen-kahu-native16x32-fast-boundary-wave-512-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','training_datasets':list(train_ids),'source_training_tiles':len(source),'source_training_fractions':list(base.SOURCE_FRACS),'source_training_shape':'4x24 native crop','interior_hidden':list(base.HIDDEN),'source_training_epochs':base.EPOCHS,'boundary_hidden':list(bw.HIDDEN),'boundary_epochs':bw.EPOCHS,'test_dataset':TARGET,'target_shape':'16x32 native','target_fractions':list(TARGET_FRACS),'kahu_used_in_training_or_normalization':False,'all_positions_charged':True,'adaptation_chunk':fr.CHUNK,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_kahu_samples':True,'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'weighted_gap_to_2x_bps':float((ours-.5*sz)*8/samples),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in adapt_rows)),'reference_4x24_512_gain_vs_sz3':REFERENCE_4X24_512_GAIN,'gain_ratio_16x32_over_4x24_reference':float(ag/REFERENCE_4X24_512_GAIN),'source_meta':source_meta,'note':'Scale-only hard-case test: strongest Kahu engine moved from repeated 4x24 targets to native 16x32 targets. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU16_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
