#!/usr/bin/env python3
"""Stack the positive main t-coordinate with zero-bit boundary x/t coordinates."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import kahu_unseen_time_coordinate_v1 as tc

REFERENCE_TIME=1.9255376298482818

def main(a):
    tc.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-main-time-plus-boundary-xt-coordinate-v1';out['boundary_feature_change']='append absolute normalized t/(nt-1) and x/(nx-1) to source-trained boundary waveform model';out['reference_time_only_gain_vs_sz3']=REFERENCE_TIME;out['gain_ratio_vs_time_only']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_TIME);out['note']='Stacks two zero-bit structural-coordinate changes: main interior gets normalized t; boundary waveform model gets normalized t and x. All source/target protocols otherwise unchanged; ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_TIME_BOUNDARY_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
