#!/usr/bin/env python3
"""16-position unseen-Waka stack with source-trained boundary waveform coding."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_multisource_replay_loso_v1 as stacked
import waka_unseen_16x32_longstream_v1 as ls
import boundary_waveform_probability_v1 as bw

fr.CHUNK=1024

def main(a):
    stacked.TARGET_FRACS=ls.FRACS
    stacked.PROTOCOL='unseen-waka-16x32-longstream-fast-boundary-wave-v1'
    bw.install(stacked)
    stacked.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-longstream-fast-boundary-wave-v1';out['target_fractions']=list(ls.FRACS);out['longstream_position_count']=len(ls.FRACS);out['adaptation_chunk']=fr.CHUNK;out['boundary_model']='source-trained causal waveform MLP';out['boundary_hidden']=list(bw.HIDDEN);out['boundary_epochs']=bw.EPOCHS;out['boundary_training_uses_waka']=False
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['positions_crossing_2x']=int(sum(z['gain_vs_sz3_ideal']>=2 for z in out['adapt_rows']));out['first4_weighted_gain']=float(sum(z['sz3_bytes'] for z in out['adapt_rows'][:4])/sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'][:4]));out['last4_weighted_gain']=float(sum(z['sz3_bytes'] for z in out['adapt_rows'][-4:])/sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'][-4:]));out['note']='All 16 Waka positions charged; source-only boundary waveform model; main model adapts only after each 1024-symbol chunk is charged. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('LONGSTREAM_FAST_BOUNDARY_WAVE_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
