#!/usr/bin/env python3
"""Fixed zero-bit time-spline basis on the unseen-Kahu hard-case engine.

The frozen predictor, residual representation, source surveys, source-trained
boundary model, 320/240/160 interior network, 10 source epochs, replay and
512-symbol post-charge adaptation remain unchanged. Based on the independently
measured strong absolute-time rate variation, append scalar tau=t/(nt-1) plus an
8-knot fixed triangular spline basis over tau. The basis is deterministic,
survey-independent, decoder-known and costs no transmitted bits.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_BASE=1.9023606738716896
REFERENCE_TIME=1.9255376298482818
KNOTS=np.linspace(0.0,1.0,8,dtype=np.float32)
H=float(KNOTS[1]-KNOTS[0])
_orig_build=q.b.build

def build_with_time_spline(X,eps):
    A,T,I,R=_orig_build(X,eps);nt=int(np.asarray(X).shape[-1])
    tau=I[:,2].astype(np.float32)/float(max(1,nt-1))
    B=np.maximum(0.0,1.0-np.abs(tau[:,None]-KNOTS[None,:])/H).astype(np.float32)
    C=np.concatenate([tau[:,None],B],axis=1)
    return np.concatenate([A,C],axis=1),T,I,R

def main(a):
    q.b.build=build_with_time_spline;k.fr.CHUNK=512;k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-time-spline-v1';out['main_feature_change']='append tau=t/(nt-1) plus fixed 8-knot triangular time spline basis';out['time_spline_knots']=KNOTS.tolist();out['extra_transmitted_bits']=0;out['reference_base_gain_vs_sz3']=REFERENCE_BASE;out['reference_time_only_gain_vs_sz3']=REFERENCE_TIME;out['gain_ratio_vs_time_only']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_TIME);out['note']='Fixed survey-independent time basis derived from the positive absolute-time mechanism; all codec machinery otherwise frozen. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_TIME_SPLINE_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
