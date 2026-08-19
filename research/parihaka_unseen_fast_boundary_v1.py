#!/usr/bin/env python3
"""True fifth-survey transfer gate: completely unseen Parihaka 3D.

Train the established hard migrated-volume probability engine only on Waka,
Kahu, Opunake and Tui. Parihaka is absent from all source fitting and
normalization. The source rule is otherwise unchanged: five fixed source regions
per training survey, 320/240/160 interior model, source-trained causal boundary
waveform model, 10 source epochs and 1024-symbol post-charge target adaptation.

Three deterministic Parihaka positions are selected through the existing
object-aware/header-only extractor. Every target chunk is charged before it can
update the model; replay uses only already-decoded Parihaka samples. Ideal
probability-rate diagnostic only; not yet a serialized codec claim.
"""
from __future__ import annotations
import argparse,json,gc
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401
import boundary_waveform_probability_v1 as bw

TARGET='marine_parihaka_3d'
SOURCE_IDS=('marine_waka_3d','marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
TARGET_FRACS=(.15,.50,.85)
fr.CHUNK=1024


def main(a):
    bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    for ds in SOURCE_IDS:
        for frac in base.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=q.crop(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':md.get('trace_first'),'object_index':md.get('object_index')});print('PARIHAKA_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);targets.append((X,ep,md));print('PARIHAKA_TARGET',frac,X.shape,md.get('object_index'),md.get('trace_first'),flush=True)
    net,mu,sd,static=fr.fit_base(source,20262119);state,u1,u2=fr.new_adapter(99300);reservoir=[];base_rows=[];adapt_rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'object_index':md.get('object_index'),'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode'),'shape':list(map(int,X.shape))}
        base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('PARIHAKA_REPLAY',json.dumps(row),flush=True)
    bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows);samples=sum(z['samples'] for z in adapt_rows);sz=sum(z['sz3_bytes'] for z in adapt_rows);ours=sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
    out={'kind':'unseen-parihaka-fifth-survey-fast-boundary-wave-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','training_datasets':list(SOURCE_IDS),'source_training_tiles':len(source),'source_training_fractions':list(base.SOURCE_FRACS),'source_training_shape':'4x24 native crop','interior_hidden':list(base.HIDDEN),'source_training_epochs':base.EPOCHS,'boundary_hidden':list(bw.HIDDEN),'boundary_epochs':bw.EPOCHS,'test_dataset':TARGET,'target_fractions':list(TARGET_FRACS),'parihaka_used_in_training_or_normalization':False,'all_target_positions_charged':True,'adaptation_chunk':fr.CHUNK,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_parihaka_samples':True,'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'weighted_gap_to_2x_bps':float((ours-.5*sz)*8/samples),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in adapt_rows)),'all_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in adapt_rows)),'source_meta':source_meta,'note':'First fifth-survey transfer gate for the learned migrated-volume hard-case engine. Parihaka is absent until its charged target stream begins. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('PARIHAKA_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True);gc.collect()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
