#!/usr/bin/env python3
"""Four-survey LOSO ablation adding one zero-bit absolute trace-time feature.

Starts from the frozen 15-source-tile, 320/240/160, source-trained boundary
waveform, 1024-symbol post-charge four-survey gate. The only change is appending
t/(nt-1) to every modeled interior residual feature. The coordinate is structural,
decoder-known and costs no transmitted bits. Same rule is used for each held-out
Waka/Kahu/Opunake/Tui split.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_quick_adapter_loso_v1 as q
import multisource15_fast_boundary_wave_loso_v1 as h

_orig_build=q.b.build

def build_with_time(X,eps):
    A,T,I,R=_orig_build(X,eps)
    nt=int(np.asarray(X).shape[-1]);tau=(I[:,2].astype(np.float32)/float(max(1,nt-1))).reshape(-1,1)
    return np.concatenate([A,tau],axis=1),T,I,R

def main(a):
    q.b.build=build_with_time
    h.main(a)
    out=json.load(open(a.out));out['kind']='four-survey-multisource15-fast-boundary-time-loso-v1';out['main_feature_change']='append normalized sample coordinate t/(nt-1)';out['extra_transmitted_bits']=0;out['same_rule_for_all_heldout_surveys']=True;out['note']='Generalization ablation of the positive Kahu time-coordinate feature. Same source-only LOSO protocol and target adaptation; ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('MULTI15_TIME_LOSO_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
