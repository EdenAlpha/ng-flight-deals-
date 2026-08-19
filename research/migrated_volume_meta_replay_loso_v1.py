#!/usr/bin/env python3
"""Four-survey LOSO meta-initialization + full causal replay diagnostic.

The held-out survey is never used in base fitting or meta-training. On the other
three surveys, first train the ordinary probability model, then meta-train its
initialization so a few gradient steps on an already-decoded support segment
improve a disjoint query segment from the same source survey. Finally evaluate
exactly the full causal replay gate: every held-out chunk is charged before it
updates the model; replay uses already-decoded samples only.

This is an ideal probability-rate diagnostic, not a serialized codec claim.
"""
from __future__ import annotations
import argparse, copy, json, math
import numpy as np
import torch
import torch.nn.functional as F
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
# object-aware, header-only extraction
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401

META_EPOCHS=4
INNER_STEPS=2
INNER_LR=7e-4
META_LR=2e-4
SUPPORT_CAP=16000
QUERY_CAP=16000
PLAIN_FIT=fr._orig_fit
# Protocol marker: v1 is frozen before any held-out meta-replay result is read.
PROTOCOL='meta-replay-v1-source-only-fast-adaptation'

def _subsample(X,Y,cap):
    if len(Y)<=cap:return X,Y
    ii=np.linspace(0,len(Y)-1,cap,dtype=np.int64)
    return X[ii],Y[ii]

def meta_fit(train_tiles,seed):
    net,mu,sd,static=PLAIN_FIT(train_tiles,seed)
    episodes=[]
    for X,eps in train_tiles:
        A,T,I,R=q.b.build(q.crop(X),eps);A=(A-mu)/sd;Y=q.b.cls(T)
        mid=int(np.median(I[:,2]));sm=I[:,2] <= mid;qm=I[:,2] > mid
        SX,SY=_subsample(A[sm],Y[sm],SUPPORT_CAP);QX,QY=_subsample(A[qm],Y[qm],QUERY_CAP)
        episodes.append((torch.from_numpy(SX),torch.from_numpy(SY),torch.from_numpy(QX),torch.from_numpy(QY)))
    for p in net.parameters():p.requires_grad_(True)
    meta_opt=torch.optim.AdamW(net.parameters(),lr=META_LR,weight_decay=1e-5)
    torch.manual_seed(seed+7000)
    for me in range(META_EPOCHS):
        order=torch.randperm(len(episodes)).tolist();losses=[]
        for ei in order:
            SX,SY,QX,QY=episodes[ei];fast=copy.deepcopy(net);fast.train();inner=torch.optim.SGD(fast.parameters(),lr=INNER_LR)
            for st in range(INNER_STEPS):
                a=(st*4096)%max(1,len(SX));b=min(len(SX),a+4096)
                if b-a<1024:a=0;b=min(len(SX),4096)
                inner.zero_grad(set_to_none=True);loss=F.cross_entropy(fast(SX[a:b]),SY[a:b]);loss.backward();inner.step()
            fast.zero_grad(set_to_none=True);qloss=F.cross_entropy(fast(QX),QY);qloss.backward();losses.append(float(qloss.detach()))
            meta_opt.zero_grad(set_to_none=True)
            for p,pf in zip(net.parameters(),fast.parameters()):
                if pf.grad is not None:p.grad=pf.grad.detach().clone()
            meta_opt.step()
        print('META_EPOCH',me,'query_nats',float(np.mean(losses)),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    return net,mu,sd,static

def main(a):
    fr._orig_fit=meta_fit;fr.main(a)
    out=json.load(open(a.out));out['kind']='four-survey-meta-initialized-causal-full-replay-loso-v1';out['meta_training_uses_heldout_survey']=False;out['meta_epochs']=META_EPOCHS;out['meta_inner_steps']=INNER_STEPS;out['meta_inner_lr']=INNER_LR;out['meta_lr']=META_LR;out['meta_support_cap']=SUPPORT_CAP;out['meta_query_cap']=QUERY_CAP;out['meta_protocol']=PROTOCOL;out['meta_rule']='source-survey temporal support/query episodes; first-order MAML initialization; same rule for every LOSO split';out['note']='Meta-initialized full causal replay diagnostic. Held-out target never participates in base or meta fitting. Every target chunk is scored before target adaptation. Ideal probability rate only.'
    with open(a.out,'w') as f:json.dump(out,f,indent=2)
    print('META_REPLAY_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',required=True);main(ap.parse_args())
