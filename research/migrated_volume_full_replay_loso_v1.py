#!/usr/bin/env python3
"""Four-survey LOSO diagnostic with full decoder-reproducible replay adaptation.

The base probability model is trained only on the other three surveys. For the
held-out survey each modeled chunk is scored first, then the full model is
updated from that decoded chunk. A deterministic reservoir of already-decoded
samples is replayed between charged positions. No held-out sample participates
in fitting before its own rate is charged.

Diagnostic ideal arithmetic rate only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse, copy, json, math
import numpy as np
import torch
import torch.nn.functional as F
import migrated_volume_quick_adapter_loso_v1 as q
# Import installs the object-aware/header-only extractor into q.b.extract.
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401

CHUNK=4096
FULL_LR=3e-4
WEIGHT_DECAY=1e-5
FIRST_CHUNK_STEPS=2
LATER_CHUNK_STEPS=1
REPLAY_PER_TILE=6000
REPLAY_CAP=12000
REPLAY_STEPS_BETWEEN_TILES=2
_BASE_STATE={}
_PARAM_COUNT={}

_orig_fit=q.fit_base
_orig_score_base=q.score_base


def fit_base(train_tiles,seed):
    net,mu,sd,static=_orig_fit(train_tiles,seed)
    _BASE_STATE[id(net)]={k:v.detach().clone() for k,v in net.state_dict().items()}
    _PARAM_COUNT[id(net)]=sum(p.numel() for p in net.parameters())
    return net,mu,sd,static


def score_base(net,mu,sd,static,X,eps,meta):
    # Always score the pristine cross-survey model, even after replay mutated net.
    current={k:v.detach().clone() for k,v in net.state_dict().items()}
    net.load_state_dict(_BASE_STATE[id(net)])
    out=_orig_score_base(net,mu,sd,static,X,eps,meta)
    net.load_state_dict(current)
    return out


def new_adapter(seed):
    # q.main expects three objects; the dict lazily holds optimizer state.
    return {'seed':int(seed),'opt':None},None,None


def _ensure_opt(net,state):
    if state['opt'] is None:
        for p in net.parameters():p.requires_grad_(True)
        state['opt']=torch.optim.AdamW(net.parameters(),lr=FULL_LR,weight_decay=WEIGHT_DECAY)
    return state['opt']


def _update(net,X,Y,state,steps):
    if len(X)==0:return
    opt=_ensure_opt(net,state);net.train()
    for _ in range(int(steps)):
        opt.zero_grad(set_to_none=True);loss=F.cross_entropy(net(X),Y);loss.backward();opt.step()
    net.eval()


def score_and_adapt(net,mu,sd,static,X,eps,meta,state,_unused1,_unused2,reservoir,first_tile):
    X=q.crop(X);A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;Y=q.b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=q.boundary_bits(static,R,I);chunk_bits=[]
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        e=min(len(XE),s+CHUNK);xx=XE[s:e];yy=YY[s:e]
        net.eval()
        with torch.no_grad():
            lp=F.log_softmax(net(xx),1)/math.log(2);cb=float((-lp[torch.arange(len(yy)),yy]).sum())
        bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
        _update(net,xx,yy,state,FIRST_CHUNK_STEPS if (first_tile and ci==0) else LATER_CHUNK_STEPS)
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    take=min(REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>REPLAY_CAP:reservoir.pop(0)
    sb,sme=q.matched_sz3(X,eps);ours=int(math.ceil(bits/8))+q.HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None}


def replay_adapter(net,state,_unused1,_unused2,reservoir):
    if not reservoir:return
    X=torch.cat([z[0] for z in reservoir],0);Y=torch.cat([z[1] for z in reservoir],0)
    for _ in range(REPLAY_STEPS_BETWEEN_TILES):
        for s in range(0,len(X),4096):_update(net,X[s:s+4096],Y[s:s+4096],state,1)


def main(a):
    q.fit_base=fit_base;q.score_base=score_base;q.new_adapter=new_adapter;q.score_and_adapt=score_and_adapt;q.replay_adapter=replay_adapter
    q.main(a)
    p=a.out;out=json.load(open(p));out['kind']='four-survey-causal-full-replay-loso-v1';out['adaptation']='all base-model parameters updated only after scoring decoded chunks';out['full_replay_lr']=FULL_LR;out['full_replay_weight_decay']=WEIGHT_DECAY;out['first_chunk_steps']=FIRST_CHUNK_STEPS;out['later_chunk_steps']=LATER_CHUNK_STEPS;out['replay_cap']=REPLAY_CAP;out['replay_steps_between_tiles']=REPLAY_STEPS_BETWEEN_TILES;out.pop('adapter_rank',None);out.pop('adapter_trainable_parameters',None);out.pop('adapter_lr',None);out['note']='Full-model causal replay diagnostic. Base scores are always recomputed from the pristine other-three-survey state. Ideal probability rate only.'
    for t in out['targets']:
        t['full_replay_weighted_gain_vs_sz3']=t.pop('quick_adapter_weighted_gain_vs_sz3');t['gain_ratio_full_replay_over_base']=t.pop('gain_ratio_adapter_over_base')
    out['full_replay_overall_byte_weighted_gain_vs_sz3']=out.pop('quick_adapter_overall_byte_weighted_gain_vs_sz3');out['all_full_replay_positions_beat_sz3']=out.pop('all_quick_adapter_positions_beat_sz3')
    with open(p,'w') as f:json.dump(out,f,indent=2)
    print('FULL_REPLAY_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',required=True);main(ap.parse_args())
