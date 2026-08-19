#!/usr/bin/env python3
"""Stack only independently positive unseen-Waka mechanisms.

Frozen baseline: the 1.91255x unseen-Waka 16x32 stack. This experiment combines
three changes that each improved that frozen gate independently:
- topology-specific source-only boundary probability contexts,
- causal adaptation cadence 4096 -> 1024 modeled samples,
- stronger post-charge full-model optimization/replay.

Waka remains absent from source fitting and normalization. Every target chunk is
scored before any update from that chunk. Replay uses only already-decoded Waka
samples. No target selector/oracle information is introduced.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import waka_unseen_topology_boundary_v1 as boundary

FROZEN_GAIN=1.9125539732547088

# Independently positive adaptation mechanisms.
fr.CHUNK=1024
fr.FIRST_CHUNK_STEPS=4
fr.LATER_CHUNK_STEPS=2
fr.REPLAY_CAP=48000
fr.REPLAY_STEPS_BETWEEN_TILES=4


def main(a):
    boundary.main(a)
    out=json.load(open(a.out))
    out['kind']='unseen-waka-16x32-proven-stack-v1'
    out['stacked_positive_mechanisms']={
        'topology_boundary_contexts':int(out.get('boundary_contexts',44)),
        'adaptation_chunk':int(fr.CHUNK),
        'first_chunk_steps':int(fr.FIRST_CHUNK_STEPS),
        'later_chunk_steps':int(fr.LATER_CHUNK_STEPS),
        'replay_cap':int(fr.REPLAY_CAP),
        'replay_steps_between_tiles':int(fr.REPLAY_STEPS_BETWEEN_TILES),
    }
    out['only_independently_positive_changes_stacked']=True
    out['frozen_stack_reference_gain']=FROZEN_GAIN
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows'])
    ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'])
    samples=sum(z['samples'] for z in out['adapt_rows'])
    out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples)
    out['crosses_weighted_2x']=bool(out['full_replay_weighted_gain_vs_sz3']>=2.0)
    out['gain_improvement_over_frozen_stack']=float(out['full_replay_weighted_gain_vs_sz3']/FROZEN_GAIN)
    out['note']='Combined gate of three independently positive, decoder-reproducible mechanisms. Waka remains fully held out until charged decoding begins. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2))
    print('PROVEN_STACK_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
