#!/usr/bin/env python3
"""Compute and freeze Parihaka's benchmark epsilon before any learned-codec test.

Uses the same General Seismic Benchmark V1 reservoir/statistics machinery and
seed convention used by the existing marine benchmark path. This script performs
no compression experiment. Its only product is survey std and epsilon=0.10*std.

Parihaka exposed an IBM-float SEG-Y decoding hazard in the generic streaming
reader's optional segyio fast path. For this preflight only, force a direct
byte-level IBM32 decoder and validate it against exact known IBM words before
reading target data. No compression result is consulted.
"""
from __future__ import annotations
import argparse,hashlib,json,tempfile
from pathlib import Path
import numpy as np
import general_seismic_benchmark_runner as br
import general_seismic_all_engines_gauntlet as gg
import general_seismic_streaming_segy as gs

DATASET='marine_parihaka_3d'


def audited_ibm32_to_float(raw,endian='>'):
    """Decode IBM hexadecimal float directly from its on-disk 32-bit word."""
    u=np.frombuffer(raw,dtype=np.dtype(endian+'u4')).astype(np.uint32,copy=False)
    sign=np.where((u>>31)!=0,-1.0,1.0)
    exp=((u>>24)&0x7f).astype(np.int32)-64
    frac=(u&0x00ffffff).astype(np.float64)/float(1<<24)
    y=sign*frac*np.power(16.0,exp)
    y[u==0]=0.0
    if not np.all(np.isfinite(y)):
        raise RuntimeError('non-finite value produced by audited IBM32 decoder')
    return gs._flush_subnormal32(y.astype(np.float32))


def validate_ibm_decoder():
    # Canonical IBM hexadecimal floating-point words:
    # 0x41100000 = +1, 0xC1100000 = -1, 0x40800000 = +0.5, 0 = 0.
    raw=bytes.fromhex('41100000c11000004080000000000000')
    got=audited_ibm32_to_float(raw,'>').astype(np.float64)
    want=np.asarray([1.0,-1.0,0.5,0.0],np.float64)
    if not np.array_equal(got,want):
        raise RuntimeError(('IBM32 self-test failed',got.tolist(),want.tolist()))
    return {'words':['0x41100000','0xC1100000','0x40800000','0x00000000'],'decoded':got.tolist()}


def main(a):
    ibm_test=validate_ibm_decoder()
    # Monkey-patch only the IBM conversion primitive. Framing, endian detection,
    # trace selection and all benchmark statistics machinery remain unchanged.
    gs.ibm32_to_float=audited_ibm32_to_float

    manifest=br.load_json(a.manifest);pre=br.load_json(a.preflight);cfg=br.load_json(a.config)
    ds=br.dataset_def(manifest,DATASET);row=br.dataset_row(pre,DATASET)
    seed=int.from_bytes(hashlib.sha256(('GAUNTLET-V1:'+ds['id']).encode()).digest()[:8],'little')

    # Independent first-panel sanity probe before the full statistics pass.
    with tempfile.TemporaryDirectory(prefix='parihaka_probe_') as tmp:
        it=br.iter_panels(ds,row,cfg,tmp,None)
        P,meta=next(it)
        probe={'format_code':int(meta.get('format_code',-1)),'endian':meta.get('endian'),
               'shape':list(map(int,P.shape)),'min':float(np.min(P)),'max':float(np.max(P)),
               'mean':float(np.mean(P,dtype=np.float64)),'std':float(np.std(P.astype(np.float64)))}
    if not np.all(np.isfinite([probe['min'],probe['max'],probe['mean'],probe['std']])):
        raise RuntimeError(('non-finite Parihaka sanity probe',probe))
    # Guard against the previously observed ~1e34 garbage while leaving broad
    # room for legitimate seismic amplitudes. This is a corruption guard, not
    # a compression-driven threshold.
    if max(abs(probe['min']),abs(probe['max']))>1e12:
        raise RuntimeError(('Parihaka decode still implausible after audited IBM decoder',probe))
    print('PARIHAKA_DECODE_PROBE',json.dumps(probe),flush=True)

    with tempfile.TemporaryDirectory(prefix='parihaka_eps_') as tmp:
        st,panels=gg.reservoir_stats_and_panels(ds,row,cfg,tmp,None,1,seed)
    std=float(st['std']);eps=.10*std
    if not np.isfinite(eps) or eps<=0 or eps>1e12:raise RuntimeError(('invalid Parihaka epsilon',std,eps))
    out={'kind':'parihaka-benchmark-epsilon-preflight-v1','dataset':DATASET,'std':std,'epsilon':eps,
         'definition':'epsilon = 0.10 * survey standard deviation under frozen General Seismic Benchmark V1 statistics path',
         'reservoir_seed':int(seed),'statistics_panels':int(st['panels']),
         'sample_panels_materialized_for_preflight':len(panels),'compression_experiment_run':False,
         'compression_results_seen_before_epsilon':False,'ibm_decoder':'direct audited IBM hexadecimal float32',
         'ibm_decoder_self_test':ibm_test,'first_panel_decode_probe':probe}
    Path(a.out).write_text(json.dumps(out,indent=2));print('PARIHAKA_EPS_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--preflight',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True);main(p.parse_args())
