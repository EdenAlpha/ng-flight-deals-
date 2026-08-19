#!/usr/bin/env python3
"""Controlled adaptation-intensity sweep on the 16-position unseen-Kahu stream.

Keeps the proven general hard-case engine fixed: 15 non-Kahu source tiles,
320/240/160 interior probability model, source-trained boundary waveform model,
16 fixed held-out Kahu positions, 512-symbol causal cadence, predictor, quantizer,
replay reservoir and bit accounting. Every target chunk is scored before any
update. Only the post-charge optimizer learning rate / update-count is varied.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,copy,json
from pathlib import Path
import numpy as np
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import boundary_waveform_probability_v1 as bw

TARGET='marine_kahu_3d'
TARGET_FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))
CHUNK=512
CONFIGS=(
    ('control_lr3e4_2x1',3e-4,2,1),
    ('lr6e4_2x1',6e-4,2,1),
    ('lr3e4_3x2',3e-4,3,2),
    ('lr6e4_3x2',6e-4,3,2),
)

def run_config(base_net,mu,sd,static,targets,name,lr,first_steps,later_steps):
    fr.CHUNK=CHUNK;fr.FULL_LR=float(lr);fr.FIRST_CHUNK_STEPS=int(first_steps);fr.LATER_CHUNK_STEPS=int(later_steps)
    net=copy.deepcopy(base_net);state,u1,u2=fr.new_adapter(99100);reservoir=[];rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode'),'shape':list(map(int,X.shape))}
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);rows.append(row)
        print('KAHU_INTENSITY_ROW',name,json.dumps(row),flush=True)
    sz=sum(z['sz3_bytes'] for z in rows);ours=sum(z['ideal_bytes_plus_header'] for z in rows);samples=sum(z['samples'] for z in rows)
    return {'name':name,'lr':float(lr),'first_chunk_steps':int(first_steps),'later_chunk_steps':int(later_steps),'weighted_gain_vs_sz3':float(sz/ours),'weighted_gap_to_2x_bps':float((ours-.5*sz)*8/samples),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in rows)),'first4_weighted_gain':float(sum(z['sz3_bytes'] for z in rows[:4])/sum(z['ideal_bytes_plus_header'] for z in rows[:4])),'last4_weighted_gain':float(sum(z['sz3_bytes'] for z in rows[-4:])/sum(z['ideal_bytes_plus_header'] for z in rows[-4:])),'rows':rows}

def main(a):
    bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    train_ids=tuple(s for s in q.SURVEYS if s!=TARGET)
    for ds in train_ids:
        for frac in base.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=q.crop(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':md.get('trace_first')});print('KAHU_INTENSITY_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);targets.append((X,ep,md));print('KAHU_INTENSITY_TARGET',frac,X.shape,md.get('trace_first'),flush=True)
    base_net,mu,sd,static=fr.fit_base(source,20261919)
    results=[]
    for cfg in CONFIGS:
        results.append(run_config(base_net,mu,sd,static,targets,*cfg))
    best=max(results,key=lambda z:z['weighted_gain_vs_sz3'])
    out={'kind':'unseen-kahu-longstream-adaptation-intensity-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','training_datasets':list(train_ids),'source_training_tiles':len(source),'target_position_count':len(TARGET_FRACS),'target_fractions':list(TARGET_FRACS),'kahu_used_in_training_or_normalization':False,'all_positions_charged':True,'adaptation_chunk':CHUNK,'only_ablation':'post-charge full-model learning rate and optimizer steps','reference_512_gain_vs_sz3':1.9023606738716896,'configs':results,'best_config':best['name'],'best_weighted_gain_vs_sz3':best['weighted_gain_vs_sz3'],'best_weighted_gap_to_2x_bps':best['weighted_gap_to_2x_bps'],'source_meta':source_meta,'note':'Every target chunk is charged before update; same general hard-case representation and boundary model. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_INTENSITY_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('configs','source_meta')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
