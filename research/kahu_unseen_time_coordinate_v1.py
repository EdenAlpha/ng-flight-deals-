#!/usr/bin/env python3
"""Add one deterministic normalized time/depth coordinate to the Kahu hard-case model.

The direct residual representation, source surveys, source-trained boundary model,
network widths, training schedule, 512-symbol post-charge adaptation, replay,
predictor, quantizer and bit accounting remain unchanged. The only change is one
extra main-model feature for every modeled residual: t/(nt-1). This coordinate is
known identically to encoder and decoder and costs zero transmitted bits.

Kahu remains absent from all source fitting/normalization. Ideal probability-rate
diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_GAIN=1.9023606738716896
_orig_build=q.b.build


def build_with_time(X,eps):
    A,T,I,R=_orig_build(X,eps)
    nt=int(np.asarray(X).shape[-1]);den=float(max(1,nt-1))
    tau=(I[:,2].astype(np.float32)/den).reshape(-1,1)
    A=np.concatenate([A,tau],axis=1)
    return A,T,I,R


def main(a):
    q.b.build=build_with_time
    k.fr.CHUNK=512
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-longstream-time-coordinate-v1';out['main_feature_change']='append normalized sample coordinate t/(nt-1)';out['extra_transmitted_bits']=0;out['reference_512_gain_vs_sz3']=REFERENCE_GAIN;out['gain_ratio_vs_reference']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_GAIN);out['note']='Single-feature causal ablation. Everything except normalized trace time/depth is unchanged; ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_TIME_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
