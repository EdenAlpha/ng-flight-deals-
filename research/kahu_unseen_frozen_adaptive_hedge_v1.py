#!/usr/bin/env python3
"""Causal frozen/adaptive probability hedge on the 16-position unseen-Kahu stream.

Starts from the frozen 512-symbol Kahu hard-case engine. The residual predictor,
quantizer, source data, source-only boundary waveform model, target positions,
replay rule and error accounting remain unchanged.

For interior symbols only, keep two probability experts:
  1. a frozen copy of the source-trained universal model;
  2. the normal target-adapting model.
Before each charged chunk, combine their probabilities using weights derived only
from exponentially-smoothed per-symbol losses on PREVIOUS charged chunks. After
the chunk is charged, update the loss memory and then adapt expert (2) normally.
No selector bits, Kahu pretraining or future target information are used.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse, copy, json, math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_GAIN=1.9023606738716896
CHUNK=512
EMA_DECAY=0.85
BETA=8.0
fr.CHUNK=CHUNK


def _ensure_hedge(net,state):
    if 'hedge_frozen' not in state:
        frozen=copy.deepcopy(net)
        frozen.load_state_dict(fr._BASE_STATE[id(net)])
        frozen.eval()
        for p in frozen.parameters():p.requires_grad_(False)
        state['hedge_frozen']=frozen
        state['hedge_ema']=None
        state['hedge_weight_sum']=np.zeros(2,np.float64)
        state['hedge_chunks']=0
    return state['hedge_frozen']


def _weights(state):
    ema=state.get('hedge_ema')
    if ema is None:return np.array([0.5,0.5],np.float64)
    z=-BETA*(np.asarray(ema,np.float64)-float(np.min(ema)))
    z-=float(np.max(z));w=np.exp(z);w/=w.sum();return w


def hedge_score_and_adapt(net,mu,sd,static,X,eps,meta,state,_u1,_u2,reservoir,first_tile):
    X=q.crop(X);A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;Y=q.b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=q.boundary_bits(static,R,I);chunk_bits=[]
    frozen=_ensure_hedge(net,state)
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        e=min(len(XE),s+CHUNK);xx=XE[s:e];yy=YY[s:e]
        net.eval();frozen.eval();w=_weights(state)
        with torch.no_grad():
            la=F.log_softmax(net(xx),1);lf=F.log_softmax(frozen(xx),1)
            lm=torch.logaddexp(la+math.log(max(w[0],1e-12)),lf+math.log(max(w[1],1e-12)))
            idx=torch.arange(len(yy));cb=float((-lm[idx,yy]).sum()/math.log(2))
            abl=float((-la[idx,yy]).mean()/math.log(2));fbl=float((-lf[idx,yy]).mean()/math.log(2))
        bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
        cur=np.array([abl,fbl],np.float64)
        if state['hedge_ema'] is None:state['hedge_ema']=cur
        else:state['hedge_ema']=EMA_DECAY*np.asarray(state['hedge_ema'])+(1-EMA_DECAY)*cur
        state['hedge_weight_sum']+=w;state['hedge_chunks']+=1
        fr._update(net,xx,yy,state,fr.FIRST_CHUNK_STEPS if (first_tile and ci==0) else fr.LATER_CHUNK_STEPS)
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    take=min(fr.REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>fr.REPLAY_CAP:reservoir.pop(0)
    sb,sme=q.matched_sz3(X,eps);ours=int(math.ceil(bits/8))+q.HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None,'hedge_last_adaptive_weight':float(_weights(state)[0])}


def main(a):
    fr.CHUNK=CHUNK
    fr.score_and_adapt=hedge_score_and_adapt
    k.main(a)
    out=json.load(open(a.out))
    out['kind']='unseen-kahu-longstream-frozen-adaptive-hedge-v1'
    out['adaptation_chunk']=CHUNK
    out['hedge_experts']=['target_adaptive','frozen_universal']
    out['hedge_weight_source']='previous charged chunks only'
    out['hedge_ema_decay']=EMA_DECAY
    out['hedge_beta']=BETA
    out['reference_512_gain_vs_sz3']=REFERENCE_GAIN
    out['gain_ratio_vs_512']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_GAIN)
    out['note']='Causal frozen/adaptive probability hedge; current chunk never chooses its own weight. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2))
    print('KAHU_HEDGE_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
