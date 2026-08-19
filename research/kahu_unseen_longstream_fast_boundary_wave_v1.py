#!/usr/bin/env python3
"""16-position unseen-Kahu long-stream diagnostic.

Uses exactly the already-generalized hard-case rules: 15 source tiles from Waka,
Opunake and Tui; 320/240/160 interior probability model; source-trained causal
boundary waveform model; and 1024-symbol post-charge full-model adaptation.
Kahu is absent from all fitting and normalization. All 16 fixed target positions
are charged and adaptation/replay uses already-decoded Kahu only.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json,gc
from pathlib import Path
import numpy as np
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import boundary_waveform_probability_v1 as bw

TARGET='marine_kahu_3d'
TARGET_FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))
fr.CHUNK=1024


def main(a):
    bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    train_ids=tuple(s for s in q.SURVEYS if s!=TARGET)
    for ds in train_ids:
        for frac in base.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=q.crop(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':md.get('trace_first')});print('KAHU_LONG_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);targets.append((X,ep,md));print('KAHU_LONG_TARGET',frac,X.shape,md.get('trace_first'),flush=True)
    net,mu,sd,static=fr.fit_base(source,20261919);state,u1,u2=fr.new_adapter(99100);reservoir=[];base_rows=[];adapt_rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode'),'shape':list(map(int,X.shape))}
        base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('KAHU_LONG_REPLAY',json.dumps(row),flush=True)
    bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows);samples=sum(z['samples'] for z in adapt_rows);sz=sum(z['sz3_bytes'] for z in adapt_rows);ours=sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
    out={'kind':'unseen-kahu-longstream-fast-boundary-wave-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','training_datasets':list(train_ids),'source_training_tiles':len(source),'source_training_fractions':list(base.SOURCE_FRACS),'interior_hidden':list(base.HIDDEN),'source_training_epochs':base.EPOCHS,'boundary_hidden':list(bw.HIDDEN),'boundary_epochs':bw.EPOCHS,'test_dataset':TARGET,'target_fractions':list(TARGET_FRACS),'target_position_count':len(TARGET_FRACS),'kahu_used_in_training_or_normalization':False,'all_positions_charged':True,'adaptation_chunk':fr.CHUNK,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_kahu_samples':True,'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'weighted_gap_to_2x_bps':float((ours-.5*sz)*8/samples),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in adapt_rows)),'first4_weighted_gain':float(sum(z['sz3_bytes'] for z in adapt_rows[:4])/sum(z['ideal_bytes_plus_header'] for z in adapt_rows[:4])),'last4_weighted_gain':float(sum(z['sz3_bytes'] for z in adapt_rows[-4:])/sum(z['ideal_bytes_plus_header'] for z in adapt_rows[-4:])),'source_meta':source_meta,'note':'Same general hard-case rule already validated in four-survey LOSO, extended to a 16-position held-out Kahu stream. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_LONG_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
