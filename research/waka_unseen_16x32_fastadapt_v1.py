#!/usr/bin/env python3
"""Aggressive causal-adaptation extension of the frozen stacked Waka gate.

Uses exactly the same 15 non-Waka source tiles, 320/240/160 model, 10 source
training epochs, three 16x32 Waka target positions and held-out protocol as the
frozen 1.91255x result. Only decoder-reproducible adaptation effort changes:
4 gradient steps after the first charged chunk, 2 after later charged chunks,
and a 48k-sample decoded-target replay reservoir with 4 replay passes between
positions. This changes compute, not compressed bits or target visibility.
Ideal probability rate only.
"""
from __future__ import annotations
import argparse,json
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_multisource_replay_loso_v1 as stacked

fr.FIRST_CHUNK_STEPS=4
fr.LATER_CHUNK_STEPS=2
fr.REPLAY_CAP=48000
fr.REPLAY_STEPS_BETWEEN_TILES=4

def main(a):
    stacked.PROTOCOL='unseen-waka-16x32-stacked-fastadapt-v1'
    stacked.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-stacked-fastadapt-v1';out['protocol']=stacked.PROTOCOL;out['fast_adaptation']={'first_chunk_steps':fr.FIRST_CHUNK_STEPS,'later_chunk_steps':fr.LATER_CHUNK_STEPS,'replay_cap':fr.REPLAY_CAP,'replay_steps_between_tiles':fr.REPLAY_STEPS_BETWEEN_TILES};out['only_change_from_frozen_1p91255x_gate']='more decoder-reproducible optimization on already charged/decoded Waka samples';out['note']='Compute-only adaptation-strength ablation; Waka remains absent from source fitting/normalization and every Waka chunk is charged before it updates the model. Ideal rate only.'
    with open(a.out,'w') as f:json.dump(out,f,indent=2)
    print('WAKA_FASTADAPT_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
