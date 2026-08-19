#!/usr/bin/env python3
"""Strict trace-causal residual-prior calibration on unseen Kahu.

This is the corrected successor to the invalid whole-tile boundary-seeding idea.
It follows the predictor's actual decode order. Before a modeled trace interior,
only residuals that have genuinely already been decoded may affect calibration:
- all completed earlier traces,
- the current trace's startup residuals t < 14.
After each charged interior chunk its classes become available; after the trace's
interior, its terminal boundary residuals become available before the next trace.

A 19-class Dirichlet posterior over target residual frequencies multiplicatively
calibrates the neural class probabilities. The source residual prior comes from
the already-fitted source static table. No side information, target pretraining,
future trace residuals, current-chunk selection or predictor changes are used.
The normal 512-symbol full-model adaptation remains unchanged.

Ideal probability-rate diagnostic only; not a serialized codec claim.
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
PRIOR_STRENGTH=float(CHUNK)
fr.CHUNK=CHUNK


def _source_prior(static):
    p=np.exp2(-np.asarray(static,np.float64));p/=p.sum();return p


def _bias(counts,source):
    p=(np.asarray(counts,np.float64)+PRIOR_STRENGTH*source)/(float(np.sum(counts))+PRIOR_STRENGTH)
    b=np.log(np.maximum(p,1e-12))-np.log(np.maximum(source,1e-12));b-=b.mean()
    return torch.from_numpy(b.astype(np.float32))


def _add_classes(counts,z):
    if np.size(z):counts+=np.bincount(q.b.cls(np.asarray(z)),minlength=q.b.NCLASS)


def causal_score_and_adapt(net,mu,sd,static,X,eps,meta,state,_u1,_u2,reservoir,first_tile):
    X=q.crop(X);A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;Y=q.b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=q.boundary_bits(static,R,I);chunk_bits=[]
    source=_source_prior(static);counts=np.zeros(q.b.NCLASS,np.float64);ny,nx,nt=R.shape
    # I/A/T are emitted contiguously in y,x,t order by q.b.build. Walk the
    # same trace order and only expose residual classes after their decode point.
    pos=0;first_bias_linf=None;first_main_seen=False
    for y in range(ny):
        # x=0 is entirely a boundary trace and is decoded before x=1.
        _add_classes(counts,R[y,0,:])
        for x in range(1,nx):
            # Current-trace causal startup: exactly the samples excluded from the
            # main model before t=14. These are decoded before this trace interior.
            _add_classes(counts,R[y,x,:14])
            start=pos
            while pos<len(I) and int(I[pos,0])==y and int(I[pos,1])==x:pos+=1
            end=pos
            if end>start:
                xxall=XE[start:end];yyall=YY[start:end]
                for s in range(0,len(xxall),CHUNK):
                    xx=xxall[s:s+CHUNK];yy=yyall[s:s+CHUNK];bias=_bias(counts,source)
                    if not first_main_seen:first_bias_linf=float(bias.abs().max());first_main_seen=True
                    net.eval()
                    with torch.no_grad():
                        lp=F.log_softmax(net(xx)+bias,1)/math.log(2);idx=torch.arange(len(yy));cb=float((-lp[idx,yy]).sum())
                    bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
                    # Only now are these labels decoder-visible.
                    counts+=np.bincount(yy.numpy(),minlength=q.b.NCLASS)
                    fr._update(net,xx,yy,state,fr.FIRST_CHUNK_STEPS if (first_tile and start==0 and s==0) else fr.LATER_CHUNK_STEPS)
            # The terminal temporal boundary is decoded after this trace's main
            # interior and is therefore available before the next trace.
            _add_classes(counts,R[y,x,nt-q.b.RAD-1:])
    if pos!=len(I):raise RuntimeError(('trace-causal modeled index walk mismatch',pos,len(I)))
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    take=min(fr.REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>fr.REPLAY_CAP:reservoir.pop(0)
    sb,sme=q.matched_sz3(X,eps);ours=int(math.ceil(bits/8))+q.HEADER_BYTES
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None,'initial_trace_causal_bias_linf':first_bias_linf,'calibration_decoded_residuals_final':int(counts.sum())}


def main(a):
    fr.CHUNK=CHUNK;fr.score_and_adapt=causal_score_and_adapt
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-trace-causal-prior-calibration-v1';out['adaptation_chunk']=CHUNK;out['calibration']='19-class Dirichlet prior shift from already-decoded residuals in exact y,x,t trace order';out['prior_strength']=PRIOR_STRENGTH;out['future_boundary_information_used']=False;out['reference_512_gain_vs_sz3']=REFERENCE_GAIN;out['gain_ratio_vs_reference']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_GAIN);out['note']='Strict causal successor to invalid whole-tile boundary seeding. Only residuals decoded before the current trace/chunk enter calibration. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_TRACE_CAL_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
