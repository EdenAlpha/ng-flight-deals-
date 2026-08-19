#!/usr/bin/env python3
"""Combine fast main-model adaptation with causal adaptive boundary coding."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import waka_unseen_topology_boundary_v1 as tb
FROZEN_GAIN=1.9125539732547088
fr.CHUNK=1024

def main(a):
    tb.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-fast-adapt-plus-adaptive-boundary-v1';out['adaptation_chunk']=fr.CHUNK;out['combined_changes']=['held-out causal adaptation chunk 4096 -> 1024','44 source-initialized topology boundary contexts updated only after each charged boundary symbol'];out['frozen_stack_reference_gain']=FROZEN_GAIN
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['gain_improvement_over_frozen_stack']=float(out['full_replay_weighted_gain_vs_sz3']/FROZEN_GAIN);out['positions_crossing_2x']=int(sum(z['gain_vs_sz3_ideal']>=2 for z in out['adapt_rows']));out['note']='Combined gate: fast main-model adaptation plus source-initialized boundary tables that adapt strictly after charged boundary symbols. No Waka pretraining or side information. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('FAST_ADAPTIVE_BOUNDARY_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
