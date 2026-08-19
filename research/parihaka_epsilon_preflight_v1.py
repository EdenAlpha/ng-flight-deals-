#!/usr/bin/env python3
"""Compute and freeze Parihaka's benchmark epsilon before any learned-codec test.

Uses the same General Seismic Benchmark V1 reservoir/statistics machinery and
seed convention used by the existing marine benchmark path. This script performs
no compression experiment. Its only product is survey std and epsilon=0.10*std.
"""
from __future__ import annotations
import argparse,hashlib,json,tempfile
from pathlib import Path
import numpy as np
import general_seismic_benchmark_runner as br
import general_seismic_all_engines_gauntlet as gg

DATASET='marine_parihaka_3d'

def main(a):
    manifest=br.load_json(a.manifest);pre=br.load_json(a.preflight);cfg=br.load_json(a.config)
    ds=br.dataset_def(manifest,DATASET);row=br.dataset_row(pre,DATASET)
    seed=int.from_bytes(hashlib.sha256(('GAUNTLET-V1:'+ds['id']).encode()).digest()[:8],'little')
    with tempfile.TemporaryDirectory(prefix='parihaka_eps_') as tmp:
        st,panels=gg.reservoir_stats_and_panels(ds,row,cfg,tmp,None,1,seed)
    std=float(st['std']);eps=.10*std
    if not np.isfinite(eps) or eps<=0 or eps>1e12:raise RuntimeError(('invalid Parihaka epsilon',std,eps))
    out={'kind':'parihaka-benchmark-epsilon-preflight-v1','dataset':DATASET,'std':std,'epsilon':eps,'definition':'epsilon = 0.10 * survey standard deviation under frozen General Seismic Benchmark V1 statistics path','reservoir_seed':int(seed),'statistics_panels':int(st['panels']),'sample_panels_materialized_for_preflight':len(panels),'compression_experiment_run':False,'compression_results_seen_before_epsilon':False}
    Path(a.out).write_text(json.dumps(out,indent=2));print('PARIHAKA_EPS_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--preflight',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);main(p.parse_args())
