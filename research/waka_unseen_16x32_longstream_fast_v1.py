#!/usr/bin/env python3
"""16-position unseen-Waka long stream with proven 1024-symbol adaptation cadence.

Combines two independently positive mechanisms only: the frozen 16-position
long-stream protocol and the 1024-symbol causal adaptation cadence. Every target
chunk remains charged before update; Waka is absent from source fitting and
normalization. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import waka_unseen_16x32_longstream_v1 as ls

fr.CHUNK=1024

def main(a):
    ls.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-stacked-longstream-16pos-fastadapt-v1';out['adaptation_chunk']=fr.CHUNK;out['combined_positive_mechanisms']=['16-position startup amortization','1024-symbol causal adaptation cadence'];out['waka_used_in_source_training']=False
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['positions_crossing_2x']=int(sum(z['gain_vs_sz3_ideal']>=2 for z in out['adapt_rows']));out['first4_weighted_gain']=float(sum(z['sz3_bytes'] for z in out['adapt_rows'][:4])/sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'][:4]));out['last4_weighted_gain']=float(sum(z['sz3_bytes'] for z in out['adapt_rows'][-4:])/sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'][-4:]));out['note']='Stacks only independently positive long-stream amortization and faster causal adaptation. All 16 Waka positions are charged; no Waka sample is used before its own charge. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('WAKA_LONGSTREAM_FAST_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
