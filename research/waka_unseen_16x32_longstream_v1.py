#!/usr/bin/env python3
"""Long-stream extension of the frozen stacked unseen-Waka 16x32 gate.

Uses the identical source model/training/adaptation machinery as the frozen
three-position 1.91255x stacked diagnostic. The only change is evaluation length:
16 fixed Waka fractions spanning 4%..96% of the volume. Waka remains absent from
all source fitting/normalization. Every target chunk is charged before its data
updates the model; replay uses only already-decoded Waka samples. The inherited
extractor rejects target-block overlap. Ideal probability rate only.
"""
from __future__ import annotations
import argparse,json
import numpy as np
import migrated_volume_multisource_replay_loso_v1 as stacked

FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))

def main(a):
    stacked.TARGET_FRACS=FRACS
    stacked.PROTOCOL='unseen-waka-16x32-stacked-longstream-16pos-v1'
    stacked.main(a)
    out=json.load(open(a.out))
    out['kind']='unseen-waka-16x32-stacked-longstream-16pos-v1'
    out['protocol']=stacked.PROTOCOL
    out['target_fractions']=list(FRACS)
    out['longstream_position_count']=len(FRACS)
    out['purpose']='Measure whether legal causal adaptation/startup cost amortizes over a realistic longer unseen Waka stream.'
    out['note']='Same source training/model/16x32 target geometry and strict causal replay as frozen stacked Waka gate; only the number of charged target positions increases from 3 to 16. Ideal probability rate only.'
    with open(a.out,'w') as f:json.dump(out,f,indent=2)
    print('WAKA_LONGSTREAM_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
