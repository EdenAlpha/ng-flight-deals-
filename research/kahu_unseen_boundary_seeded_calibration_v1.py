#!/usr/bin/env python3
"""Boundary-seeded causal prior calibration for the unseen-Kahu hard-case engine.

The strongest 4x24 Kahu engine is unchanged except for a tiny decoder-side
19-class calibration state. Before the interior stream of each target tile, the
codec has already decoded the tile's mandatory boundary/startup residuals. Their
class histogram is compared with the source-survey boundary histogram to infer a
survey-local prior shift. That shift seeds the interior class prior before the
first charged 512-symbol chunk. After each interior chunk is charged, its decoded
classes update the calibration posterior and the normal full-model adaptation
runs exactly as before.

No side information, current-chunk selection, future target samples or Kahu
pretraining are used. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_GAIN=1.9023606738716896
CHUNK=512
SOURCE_PSEUDO=float(q.b.NCLASS)
INTERIOR_PRIOR_STRENGTH=float(CHUNK)
fr.CHUNK=CHUNK
_SOURCE_BOUND=None
_SOURCE_INTERIOR=None
_orig_fit=fr.fit_base


def _classes_for_source(train_tiles):
    bc=np.ones(q.b.NCLASS,np.float64);ic=np.ones(q.b.NCLASS,np.float64)
    for X,eps in train_tiles:
        X=q.crop(X);A,T,I,R=q.b.build(X,eps);ic+=np.bincount(q.b.cls(T),minlength=q.b.NCLASS)
        mask=np.zeros(R.shape,bool)
        for y,x,t in I:mask[int(y),int(x),int(t)]=True
        rb=R[~mask];bc+=np.bincount(q.b.cls(rb),minlength=q.b.NCLASS)
    return bc/bc.sum(),ic/ic.sum()


def calibrated_fit(train_tiles,seed):
    global _SOURCE_BOUND,_SOURCE_INTERIOR
    _SOURCE_BOUND,_SOURCE_INTERIOR=_classes_for_source(train_tiles)
    print('KAHU_CAL_SOURCE_PRIORS',json.dumps({'boundary':_SOURCE_BOUND.tolist(),'interior':_SOURCE_INTERIOR.tolist()}),flush=True)
    return _orig_fit(train_tiles,seed)


def _boundary_seed(R,I):
    mask=np.zeros(R.shape,bool)
    for y,x,t in I:mask[int(y),int(x),int(t)]=True
    z=q.b.cls(R[~mask]);cnt=np.bincount(z,minlength=q.b.NCLASS).astype(np.float64)
    # Dirichlet smoothing around the source boundary prior prevents zero/rare
    # classes from producing extreme corrections.
    pt=(cnt+SOURCE_PSEUDO*_SOURCE_BOUND)/(cnt.sum()+SOURCE_PSEUDO)
    ratio=pt/np.maximum(_SOURCE_BOUND,1e-12)
    prior=_SOURCE_INTERIOR*ratio;prior/=prior.sum()
    return prior,cnt


def calibration_bias(decoded_counts,prior):
    p=(decoded_counts+INTERIOR_PRIOR_STRENGTH*prior)/(decoded_counts.sum()+INTERIOR_PRIOR_STRENGTH)
    b=np.log(np.maximum(p,1e-12))-np.log(np.maximum(_SOURCE_INTERIOR,1e-12))
    # A common additive constant is irrelevant to softmax; center for numerical stability.
    b-=b.mean();return torch.from_numpy(b.astype(np.float32))


def calibrated_score_and_adapt(net,mu,sd,static,X,eps,meta,state,_u1,_u2,reservoir,first_tile):
    X=q.crop(X);A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;Y=q.b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=q.boundary_bits(static,R,I);chunk_bits=[]
    prior,bound_counts=_boundary_seed(R,I);decoded=np.zeros(q.b.NCLASS,np.float64);initial_bias=calibration_bias(decoded,prior)
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        e=min(len(XE),s+CHUNK);xx=XE[s:e];yy=YY[s:e];bias=calibration_bias(decoded,prior)
        net.eval()
        with torch.no_grad():
            lp=F.log_softmax(net(xx)+bias,1)/math.log(2);idx=torch.arange(len(yy));cb=float((-lp[idx,yy]).sum())
        bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
        # Calibration and network both learn only after this chunk has been charged.
        decoded+=np.bincount(yy.numpy(),minlength=q.b.NCLASS)
        fr._update(net,xx,yy,state,fr.FIRST_CHUNK_STEPS if (first_tile and ci==0) else fr.LATER_CHUNK_STEPS)
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    take=min(fr.REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>fr.REPLAY_CAP:reservoir.pop(0)
    sb,sme=q.matched_sz3(X,eps);ours=int(math.ceil(bits/8))+q.HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None,'boundary_seed_samples':int(bound_counts.sum()),'initial_calibration_bias_linf':float(initial_bias.abs().max())}


def main(a):
    fr.CHUNK=CHUNK;fr.fit_base=calibrated_fit;fr.score_and_adapt=calibrated_score_and_adapt
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-boundary-seeded-prior-calibration-v1';out['adaptation_chunk']=CHUNK;out['calibration_classes']=q.b.NCLASS;out['calibration_seed']='already-decoded target boundary residuals versus source boundary prior';out['calibration_updates']='after each charged interior chunk';out['interior_prior_strength']=INTERIOR_PRIOR_STRENGTH;out['reference_512_gain_vs_sz3']=REFERENCE_GAIN;out['gain_ratio_vs_512']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_GAIN);out['note']='Boundary-seeded decoder-synchronized class-prior calibration. No extra bits or target pretraining; ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_CAL_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
