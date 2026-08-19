#!/usr/bin/env python3
"""Four-survey leave-one-out diagnostic with a tiny causal quick-adapter.

For each held-out migrated survey, train the same base probability model only on
the other three surveys.  The held-out survey starts with a zeroed 95-parameter
adapter (rank-4 logit correction + class bias).  Each held-out chunk is scored
BEFORE its symbols update the adapter.  Adapter state persists across the three
charged held-out positions; between positions it may replay a small deterministic
reservoir made only from already-decoded samples.  No held-out sample, statistic,
or identity participates in base fitting or normalization.

Diagnostic ideal arithmetic rate only.  This does not materialize an arithmetic
stream and does not establish a production-codec or throughput claim.
"""
from __future__ import annotations
import argparse, gc, json, math
from pathlib import Path
import numpy as np
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

SURVEYS=('marine_waka_3d','marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
TRAIN_FRAC=.50
TEST_FRACS=(.15,.50,.85)
MAX_TRAIN=220000
EPOCHS=3
XKEEP=24
HEADER_BYTES=128
CHUNK=4096
RANK=4
ADAPTER_LR=.08
FIRST_CHUNK_STEPS=4
LATER_CHUNK_STEPS=1
REPLAY_PER_TILE=6000
REPLAY_CAP=12000
REPLAY_STEPS_BETWEEN_TILES=2


def crop(X):
    X=np.asarray(X)
    if X.shape[1] <= XKEEP:return np.ascontiguousarray(X)
    x0=(X.shape[1]-XKEEP)//2
    return np.ascontiguousarray(X[:,x0:x0+XKEEP,:])


def deterministic_subsample(A,T,cap):
    if len(T)<=cap:return A,T
    idx=np.linspace(0,len(T)-1,cap,dtype=np.int64)
    return A[idx],T[idx]


def fit_base(train_tiles,seed):
    import torch, torch.nn as nn, torch.nn.functional as F
    AA=[];TT=[];RR=[]
    for X,eps in train_tiles:
        A,T,_,R=b.build(crop(X),eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR)
    A,T=deterministic_subsample(A,T,MAX_TRAIN)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T)
    sh=np.bincount(b.cls(fullR),minlength=b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh)

    class Base(nn.Module):
        def __init__(self,d):
            super().__init__()
            self.trunk=nn.Sequential(
                nn.Linear(d,160),nn.SiLU(),nn.LayerNorm(160),
                nn.Linear(160,112),nn.SiLU(),
                nn.Linear(112,64),nn.SiLU())
            self.head=nn.Linear(64,b.NCLASS)
        def latent(self,x):return self.trunk(x)
        def forward(self,x):return self.head(self.latent(x))

    torch.manual_seed(seed);np.random.seed(seed)
    net=Base(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4)
    X=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(X));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(X[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('BASE_FIT',seed,'epoch',ep,'ce_nats',tot/len(X),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    return net,mu,sd,static


def new_adapter(seed):
    import torch
    g=torch.Generator().manual_seed(seed)
    P=torch.randn(64,RANK,generator=g,dtype=torch.float32)/math.sqrt(64.0)
    # Fixed random projection P is shared by encoder/decoder; only B and bias adapt.
    B=torch.zeros(RANK,b.NCLASS,dtype=torch.float32,requires_grad=True)
    bias=torch.zeros(b.NCLASS,dtype=torch.float32,requires_grad=True)
    return P,B,bias


def logits_with_adapter(net,x,P,B,bias):
    z=net.latent(x)
    return net.head(z)+(z@P)@B+bias


def adapter_update(net,X,Y,P,B,bias,steps,lr):
    import torch.nn.functional as F
    if len(X)==0:return
    for _ in range(int(steps)):
        logits=logits_with_adapter(net,X,P,B,bias)
        loss=F.cross_entropy(logits,Y)
        if B.grad is not None:B.grad.zero_()
        if bias.grad is not None:bias.grad.zero_()
        loss.backward()
        with __import__('torch').no_grad():
            B-=lr*B.grad;bias-=lr*bias.grad


def boundary_bits(static,R,I):
    mask=np.zeros(R.shape,bool)
    for y,x,t in I:mask[int(y),int(x),int(t)]=True
    rb=R[~mask]
    return float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum())


def score_base(net,mu,sd,static,X,eps,meta):
    import torch, torch.nn.functional as F
    X=crop(X);A,T,I,R=b.build(X,eps);A=(A-mu)/sd;Y=b.cls(T);bits=boundary_bits(static,R,I)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y)
    with torch.no_grad():
        for i in range(0,len(XE),16384):
            lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);yy=YY[i:i+16384]
            bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
    bits+=float(b.gamma_bits(np.maximum(np.abs(T)-b.LIM,0)).sum())
    sb,sme=matched_sz3(X,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme)}


def score_and_adapt(net,mu,sd,static,X,eps,meta,P,B,bias,reservoir,first_tile):
    import torch, torch.nn.functional as F
    X=crop(X);A,T,I,R=b.build(X,eps);A=(A-mu)/sd;Y=b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=boundary_bits(static,R,I)
    chunk_bits=[]
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        e=min(len(XE),s+CHUNK);xx=XE[s:e];yy=YY[s:e]
        # Strict causality: score before updating on this chunk.
        with torch.no_grad():
            lp=F.log_softmax(logits_with_adapter(net,xx,P,B,bias),1)/math.log(2)
            cb=float((-lp[torch.arange(len(yy)),yy]).sum())
        bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
        steps=FIRST_CHUNK_STEPS if (first_tile and ci==0) else LATER_CHUNK_STEPS
        adapter_update(net,xx,yy,P,B,bias,steps,ADAPTER_LR)
    bits+=float(b.gamma_bits(np.maximum(np.abs(T)-b.LIM,0)).sum())

    # Deterministic reservoir from already decoded modeled samples only.
    take=min(REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long()
        reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(q[0]) for q in reservoir)>REPLAY_CAP:reservoir.pop(0)

    sb,sme=matched_sz3(X,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None}


def replay_adapter(net,P,B,bias,reservoir):
    import torch
    if not reservoir:return
    X=torch.cat([q[0] for q in reservoir],0);Y=torch.cat([q[1] for q in reservoir],0)
    for _ in range(REPLAY_STEPS_BETWEEN_TILES):
        # Fixed contiguous order; all samples are already decoded.
        for s in range(0,len(X),4096):adapter_update(net,X[s:s+4096],Y[s:s+4096],P,B,bias,1,ADAPTER_LR)


def main(a):
    import torch
    m=json.load(open(a.manifest));e=json.load(open(a.eps))
    raw={}
    for ds in SURVEYS:
        raw[ds]={}
        for frac in sorted(set((TRAIN_FRAC,)+TEST_FRACS)):
            X,ep,md=b.extract(ds,m,e,frac);raw[ds][frac]=(crop(X),ep,md)
            print('RAW',ds,frac,crop(X).shape,flush=True)

    targets=[]
    for ti,target in enumerate(SURVEYS):
        train_ids=tuple(q for q in SURVEYS if q!=target)
        train=[(raw[q][TRAIN_FRAC][0],raw[q][TRAIN_FRAC][1]) for q in train_ids]
        net,mu,sd,static=fit_base(train,20260819+ti)
        P,B,bias=new_adapter(91000+ti);reservoir=[];base_rows=[];adapt_rows=[]
        for pi,frac in enumerate(TEST_FRACS):
            X,ep,md=raw[target][frac];meta={'dataset':target,'fraction':frac,'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode')}
            base_rows.append(score_base(net,mu,sd,static,X,ep,meta))
            if pi>0:replay_adapter(net,P,B,bias,reservoir)
            row=score_and_adapt(net,mu,sd,static,X,ep,meta,P,B,bias,reservoir,pi==0);adapt_rows.append(row)
            print('QUICK_ADAPT',json.dumps(row),flush=True)
        base_gain=sum(q['sz3_bytes'] for q in base_rows)/sum(q['ideal_bytes_plus_header'] for q in base_rows)
        adapt_gain=sum(q['sz3_bytes'] for q in adapt_rows)/sum(q['ideal_bytes_plus_header'] for q in adapt_rows)
        targets.append({'test_dataset':target,'training_datasets':list(train_ids),'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(base_gain),'quick_adapter_weighted_gain_vs_sz3':float(adapt_gain),'gain_ratio_adapter_over_base':float(adapt_gain/base_gain)})
        del net,mu,sd,static,P,B,bias;gc.collect()

    allb=[r for t in targets for r in t['base_rows']];alla=[r for t in targets for r in t['adapt_rows']]
    out={
      'kind':'four-survey-causal-quick-adapter-loso-v1',
      'status':'diagnostic_ideal_probability_rate_not_serialized_codec',
      'surveys':list(SURVEYS),
      'held_out_survey_used_in_base_training':False,
      'test_positions_all_charged':True,
      'adapter_updates_only_after_scoring_decoded_chunks':True,
      'adapter_state_persists_across_heldout_positions':True,
      'adapter_replay_uses_only_already_decoded_samples':True,
      'adapter_rank':RANK,
      'adapter_trainable_parameters':int(RANK*b.NCLASS+b.NCLASS),
      'chunk':CHUNK,
      'adapter_lr':ADAPTER_LR,
      'first_chunk_steps':FIRST_CHUNK_STEPS,
      'later_chunk_steps':LATER_CHUNK_STEPS,
      'replay_cap':REPLAY_CAP,
      'replay_steps_between_tiles':REPLAY_STEPS_BETWEEN_TILES,
      'targets':targets,
      'base_overall_byte_weighted_gain_vs_sz3':float(sum(q['sz3_bytes'] for q in allb)/sum(q['ideal_bytes_plus_header'] for q in allb)),
      'quick_adapter_overall_byte_weighted_gain_vs_sz3':float(sum(q['sz3_bytes'] for q in alla)/sum(q['ideal_bytes_plus_header'] for q in alla)),
      'all_quick_adapter_positions_beat_sz3':bool(all(q['gain_vs_sz3_ideal']>=1 for q in alla)),
      'note':'Base model weights are separately trained on the other three surveys for each LOSO split. Adapter has only 95 trainable numbers and begins at zero on the held-out survey. Ideal rate only; production determinism/serialization/throughput remain future gates.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
