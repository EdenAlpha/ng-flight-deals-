#!/usr/bin/env python3
"""Long-range-context ablation for the frozen Waka 16x32 vs 16x128 gate.

Preserves the exact paired extraction, residual predictor, training locations,
network hidden widths, training budget and held-out test from the frozen 16x128
scale diagnostic. The only modeling change is additional probability context
from already-decoded traces 4, 8, 16 and 32 fast-axis positions behind the
current trace. No future trace/sample is used. Ideal probability rate only.
"""
from __future__ import annotations
import argparse,json
import numpy as np
import waka_tall16_probability_scale_base_v1 as base

OFFSETS=(4,8,16,32)
_ORIG_FEATURE_BATCH=base.feature_batch

def longrange_feature_batch(S,R,flat):
    F,T=_ORIG_FEATURE_BATCH(S,R,flat)
    ny,nx,nt=S.shape;ntm=nt-base.b.RAD-15
    flat=np.asarray(flat,np.int64);q0=flat//ntm;t=14+(flat%ntm);x=1+(q0%(nx-1));y=q0//(nx-1)
    local=S[y,x-1,t];local_prev=S[y,x-1,t-1];extra=[]
    for d in OFFSETS:
        has=(x>=d).astype(np.float32);xd=np.maximum(0,x-d);c=S[y,xd,t]
        extra.append(has)
        for o in range(-base.b.RAD,base.b.RAD+1):extra.append((S[y,xd,t+o]-c)*has)
        for o in range(-base.b.RAD,base.b.RAD+1):extra.append(R[y,xd,t+o].astype(np.float32)*has)
        extra.append((c-local)*has)
        extra.append((S[y,xd,t-1]-local_prev)*has)
    E=np.stack(extra,axis=1).astype(np.float32,copy=False)
    return np.concatenate([F,E],axis=1),T

base.feature_batch=longrange_feature_batch

def main(a):
    base.main(a)
    out=json.load(open(a.out));out['kind']='waka-paired-learned-probability-scale-16x32-vs-16x128-longrange-v1';out['long_range_context_offsets']=list(OFFSETS);out['long_range_context_is_decoder_available']=True;out['only_change_from_frozen_16x128_gate']='probability features from previously decoded distant traces';out['note']='Ideal probability-rate diagnostic; same residual representation and held-out locations as frozen 16x128 scale gate.'
    with open(a.out,'w') as f:json.dump(out,f,indent=2)
    print('LONGRANGE_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
