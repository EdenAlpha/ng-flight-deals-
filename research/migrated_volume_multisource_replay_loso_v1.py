#!/usr/bin/env python3
"""Nine-source-tile LOSO capacity scaling + full causal replay.

Same nine source tiles, 720k deterministic training examples, eight epochs,
held-out target fractions and strict causal replay as the frozen 1.8284x gate.
Only probability-model capacity changes from 160/112/64 to 320/240/160.
Every target chunk is charged before adaptation. Ideal probability rate only.
"""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401

SOURCE_FRACS=(.15,.50,.85);TARGET_FRACS=(.15,.50,.85);MAX_TRAIN=720000;EPOCHS=8;HIDDEN=(320,240,160);PROTOCOL='multisource-9tile-capacity-v1'

def wide_fit(train_tiles,seed):
    AA=[];TT=[];RR=[]
    for X,eps in train_tiles:
        A,T,_,R=q.b.build(q.crop(X),eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR);A,T=q.deterministic_subsample(A,T,MAX_TRAIN)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=q.b.cls(T)
    sh=np.bincount(q.b.cls(fullR),minlength=q.b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh);h1,h2,h3=HIDDEN
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();self.trunk=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU());self.head=nn.Linear(h3,q.b.NCLASS)
        def latent(self,x):return self.trunk(x)
        def forward(self,x):return self.head(self.latent(x))
    torch.manual_seed(seed);np.random.seed(seed);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=1.5e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('CAPACITY_FIT',seed,ep,tot/len(Xt),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    print('CAPACITY_PARAMS',sum(p.numel() for p in net.parameters()),flush=True);return net,mu,sd,static

def main(a):
    fr._orig_fit=wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw={}
    for ds in q.SURVEYS:
        raw[ds]={}
        for frac in SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);raw[ds][frac]=(q.crop(X),ep,md);print('CAPACITY_RAW',ds,frac,q.crop(X).shape,flush=True)
    targets=[]
    for ti,target in enumerate(q.SURVEYS):
        train_ids=tuple(s for s in q.SURVEYS if s!=target);train=[(raw[s][f][0],raw[s][f][1]) for s in train_ids for f in SOURCE_FRACS]
        net,mu,sd,static=fr.fit_base(train,20261119+ti);state,u1,u2=fr.new_adapter(96000+ti);reservoir=[];base_rows=[];adapt_rows=[]
        for pi,frac in enumerate(TARGET_FRACS):
            X,ep,md=raw[target][frac];meta={'dataset':target,'fraction':frac,'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode')};base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
            if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
            row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('CAPACITY_REPLAY',json.dumps(row),flush=True)
        bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
        targets.append({'test_dataset':target,'training_datasets':list(train_ids),'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'gain_ratio_full_replay_over_base':float(ag/bg)})
        del net,mu,sd,static,state;gc.collect()
    allb=[r for t in targets for r in t['base_rows']];alla=[r for t in targets for r in t['adapt_rows']]
    out={'kind':'four-survey-multisource-capacity-full-replay-loso-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'hidden':list(HIDDEN),'source_tiles_per_loso_split':9,'max_train_examples':MAX_TRAIN,'source_training_epochs':EPOCHS,'held_out_survey_used_in_base_training':False,'test_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_target_samples':True,'targets':targets,'base_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in allb)/sum(z['ideal_bytes_plus_header'] for z in allb)),'full_replay_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in alla)/sum(z['ideal_bytes_plus_header'] for z in alla)),'all_full_replay_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in alla)),'note':'Capacity-only scaling from frozen 9-tile 8-epoch gate. All target surveys remain held out. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('MULTISOURCE_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
