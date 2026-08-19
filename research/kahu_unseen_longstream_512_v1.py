#!/usr/bin/env python3
"""Cadence-only Kahu ablation: 1024 -> 512 decoded interior symbols.

Everything else is the frozen unseen-Kahu long-stream fast-boundary-wave gate.
Every 512-symbol chunk is charged before it updates the model. Kahu remains
absent from source fitting/normalization. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import kahu_unseen_longstream_fast_boundary_wave_v1 as k

REFERENCE_GAIN=1.8940804770327848
k.fr.CHUNK=512


def main(a):
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-longstream-fast-boundary-wave-512-v1';out['adaptation_chunk']=512;out['only_change_from_reference']='post-charge adaptation cadence 1024 -> 512 interior symbols';out['reference_1024_gain_vs_sz3']=REFERENCE_GAIN;out['gain_ratio_vs_1024']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_GAIN);out['note']='Cadence-only ablation on the same 16 held-out Kahu positions. Every target symbol remains charged before adaptation; ideal probability rate only.';Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_512_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
