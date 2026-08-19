#!/usr/bin/env python3
"""Faster causal adaptation cadence on the frozen 1.9126x unseen-Waka stack.

Imports the strongest stacked 16x32 gate unchanged and reduces only the held-out
adaptation chunk from 4096 to 1024 modeled samples. The source model, source data,
Waka targets, probability architecture, learning rate, replay reservoir and every
bit-accounting rule stay fixed. Each 1024-sample target chunk is still scored
before the model learns from it, so decoder/encoder adaptation remains causal and
requires no side information.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr

FROZEN_GAIN=1.9125539732547088
fr.CHUNK=1024

def main(a):
    s.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-stacked-fast-adapt-v1';out['adaptation_chunk']=fr.CHUNK;out['only_change_vs_frozen_stack']='held-out causal adaptation chunk 4096 -> 1024';out['frozen_stack_reference_gain']=FROZEN_GAIN;sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['gain_improvement_over_frozen_stack']=float(out['full_replay_weighted_gain_vs_sz3']/FROZEN_GAIN);out['note']='Cadence-only ablation. Every target chunk is charged before adaptation; no target sample is used early. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('FAST_ADAPT_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
