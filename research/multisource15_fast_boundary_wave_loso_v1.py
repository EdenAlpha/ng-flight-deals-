#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_multisource15_replay_loso_v1 as base
import boundary_waveform_probability_v1 as bw

fr.CHUNK=1024

def main(a):
    bw.install(base)
    base.main(a)
    out=json.load(open(a.out));out['kind']='four-survey-multisource15-fast-boundary-waveform-loso-v1';out['adaptation_chunk']=fr.CHUNK;out['boundary_model']='source-trained causal boundary waveform MLP';out['boundary_hidden']=list(bw.HIDDEN);out['boundary_epochs']=bw.EPOCHS;out['same_rule_for_all_heldout_surveys']=True;out['heldout_survey_used_in_boundary_training']=False;out['note']='Each LOSO split trains both interior and boundary probability models only on the other three surveys. Same 1024-symbol target adaptation cadence for all targets. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('MULTI15_FAST_BOUNDARY_WAVE_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
