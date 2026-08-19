#!/usr/bin/env python3
"""Four-survey LOSO with 15 diverse source tiles + full causal replay.

For each held-out survey, train the same probability model on five fixed regions
from each of the other three surveys (15 source tiles total). The target survey
is absent from fitting and normalization. Every held-out target chunk is charged
before full-model adaptation; replay uses only already-decoded target samples.

This follows the positive 3->9 source-tile scaling result. Same model family and
same target fractions; only source diversity/training budget increase.
Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401

SOURCE_FRACS=(.08,.29,.50,.71,.92)
TARGET_FRACS=(.15,.50,.85)
MAX_TRAIN=1200000
EPOCHS=6
PROTOCOL='multisource-15tile-full-replay-v1'

def main(a):
    q.MAX_TRAIN=MAX_TRAIN;q.EPOCHS=EPOCHS
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw={}
    allfr=tuple(sorted(set(SOURCE_FRACS+TARGET_FRACS)))
    for ds in q.SURVEYS:
        raw[ds]={}
        for frac in allfr:
            X,ep,md=q.b.extract(ds,m,e,frac);raw[ds][frac]=(q.crop(X),ep,md);print('MULTI15_RAW',ds,frac,q.crop(X).shape,flush=True)
    targets=[]
    for ti,target in enumerate(q.SURVEYS):
        train_ids=tuple(s for s in q.SURVEYS if s!=target)
        train=[(raw[s][f][0],raw[s][f][1]) for s in train_ids for f in SOURCE_FRACS]
        net,mu,sd,static=fr.fit_base(train,20260919+ti)
        state,u1,u2=fr.new_adapter(94000+ti);reservoir=[];base_rows=[];adapt_rows=[]
        for pi,frac in enumerate(TARGET_FRACS):
            X,ep,md=raw[target][frac];meta={'dataset':target,'fraction':frac,'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode')}
            base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
            if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
            row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('MULTI15_REPLAY',json.dumps(row),flush=True)
        bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
        targets.append({'test_dataset':target,'training_datasets':list(train_ids),'source_training_fractions':list(SOURCE_FRACS),'source_training_tiles':len(train),'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'gain_ratio_full_replay_over_base':float(ag/bg)})
        del net,mu,sd,static,state;gc.collect()
    allb=[r for t in targets for r in t['base_rows']];alla=[r for t in targets for r in t['adapt_rows']]
    out={'kind':'four-survey-multisource15-causal-full-replay-loso-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'surveys':list(q.SURVEYS),'source_training_fractions':list(SOURCE_FRACS),'source_tiles_per_loso_split':15,'max_train_examples':MAX_TRAIN,'source_training_epochs':EPOCHS,'held_out_survey_used_in_base_training':False,'test_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_target_samples':True,'targets':targets,'base_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in allb)/sum(z['ideal_bytes_plus_header'] for z in allb)),'full_replay_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in alla)/sum(z['ideal_bytes_plus_header'] for z in alla)),'all_full_replay_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in alla)),'note':'15 source tiles per split, all from the other three surveys. Same target fractions and causal replay protocol as prior gates. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('MULTISOURCE15_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
