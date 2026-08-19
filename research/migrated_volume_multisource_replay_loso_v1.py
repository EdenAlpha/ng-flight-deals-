#!/usr/bin/env python3
"""Unseen-Waka 16-position causal adaptation stream diagnostic.

Train the universal probability model only on Kahu, Opunake and Tui, using the
same nine source tiles and eight source-training epochs as the frozen 1.8284x
four-survey gate. Then traverse 16 fixed Waka positions from 4% to 96% of the
volume. Every Waka tile/chunk is charged before the model learns from it; replay
between tiles uses only already-decoded Waka samples. Waka never participates in
base fitting or normalization.

This tests startup amortization over a realistic long unseen-survey stream.
Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401

TARGET='marine_waka_3d'
SOURCE_IDS=('marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
SOURCE_FRACS=(.15,.50,.85)
TARGET_FRACS=tuple(np.linspace(.04,.96,16).tolist())
MAX_TRAIN=720000
EPOCHS=8
PROTOCOL='waka-16position-unseen-causal-stream-v1'

def main(a):
    q.MAX_TRAIN=MAX_TRAIN;q.EPOCHS=EPOCHS
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in SOURCE_IDS:
        for frac in SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);source.append((q.crop(X),ep));print('WAKA16_SOURCE',ds,frac,q.crop(X).shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=q.b.extract(TARGET,m,e,float(frac));targets.append((q.crop(X),ep,md));print('WAKA16_RAW',frac,q.crop(X).shape,md.get('trace_first'),flush=True)
    # Fixed fractions must yield disjoint target regions; fail rather than silently
    # double-charge/reuse samples.
    rr=[(int(z[2].get('trace_first')) if z[2].get('trace_first') is not None else -1,int(z[2].get('trace_last')) if z[2].get('trace_last') is not None else -1) for z in targets]
    valid=[z for z in rr if z[0]>=0 and z[1]>=0]
    for i in range(len(valid)):
        for j in range(i):
            if max(valid[i][0],valid[j][0])<=min(valid[i][1],valid[j][1]):raise RuntimeError(('target overlap',i,j,valid[i],valid[j]))
    net,mu,sd,static=fr.fit_base(source,20261219);state,u1,u2=fr.new_adapter(97000);reservoir=[];rows=[];cum_sz3=0;cum_ours=0
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md.get('trace_first'),'trace_last':md.get('trace_last'),'geometry_mode':md.get('geometry_mode')}
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);cum_sz3+=row['sz3_bytes'];cum_ours+=row['ideal_bytes_plus_header'];row['cumulative_gain_vs_sz3']=float(cum_sz3/cum_ours);rows.append(row);print('WAKA16_STREAM',json.dumps(row),flush=True)
    out={'kind':'unseen-waka-16position-causal-adaptation-stream-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'training_datasets':list(SOURCE_IDS),'source_training_fractions':list(SOURCE_FRACS),'source_training_tiles':len(source),'source_training_epochs':EPOCHS,'max_train_examples':MAX_TRAIN,'test_dataset':TARGET,'target_fractions':list(TARGET_FRACS),'waka_used_in_base_training':False,'target_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_waka_samples':True,'rows':rows,'whole_stream_byte_weighted_gain_vs_sz3':float(cum_sz3/cum_ours),'first4_gain':float(sum(z['sz3_bytes'] for z in rows[:4])/sum(z['ideal_bytes_plus_header'] for z in rows[:4])),'last4_gain':float(sum(z['sz3_bytes'] for z in rows[-4:])/sum(z['ideal_bytes_plus_header'] for z in rows[-4:])),'median_position_gain':float(np.median([z['gain_vs_sz3_ideal'] for z in rows])),'min_position_gain':float(min(z['gain_vs_sz3_ideal'] for z in rows)),'max_position_gain':float(max(z['gain_vs_sz3_ideal'] for z in rows)),'note':'Waka is completely unseen during base training. All 16 target positions are charged in order; adaptation/replay uses only target samples after they were decoded. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('WAKA16_FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
