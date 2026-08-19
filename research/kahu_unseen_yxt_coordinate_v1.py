#!/usr/bin/env python3
"""Add deterministic normalized y/x/t coordinates to the unseen-Kahu model.

Direct extension of the positive t/(nt-1) ablation. The predictor, residual
representation, source data, source-trained boundary waveform model, 320/240/160
interior model, 10 source epochs, replay and 512-symbol post-charge adaptation
remain unchanged. The only change is appending three structural, decoder-known,
zero-bit features for each modeled residual: y/(ny-1), x/(nx-1), t/(nt-1).

These coordinates expose causal topology explicitly: early x traces and y=0 have
less decoded spatial context than later positions. Kahu remains absent from
fitting/normalization. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_BASE=1.9023606738716896
REFERENCE_TIME=1.9255376298482818
_orig_build=q.b.build

def build_with_yxt(X,eps):
    A,T,I,R=_orig_build(X,eps);ny,nx,nt=np.asarray(X).shape
    den_y=float(max(1,ny-1));den_x=float(max(1,nx-1));den_t=float(max(1,nt-1))
    C=np.stack([I[:,0].astype(np.float32)/den_y,I[:,1].astype(np.float32)/den_x,I[:,2].astype(np.float32)/den_t],axis=1)
    return np.concatenate([A,C],axis=1),T,I,R

def main(a):
    q.b.build=build_with_yxt;k.fr.CHUNK=512;k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-yxt-coordinate-v1';out['main_feature_change']='append normalized structural coordinates y/(ny-1), x/(nx-1), t/(nt-1)';out['extra_transmitted_bits']=0;out['reference_base_gain_vs_sz3']=REFERENCE_BASE;out['reference_time_only_gain_vs_sz3']=REFERENCE_TIME;out['gain_ratio_vs_time_only']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_TIME);out['note']='Three-coordinate zero-bit topology ablation; everything else frozen. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_YXT_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
