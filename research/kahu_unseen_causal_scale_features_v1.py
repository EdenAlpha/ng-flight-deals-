#!/usr/bin/env python3
"""Expose causal local energy/roughness summaries to the unseen-Kahu model.

The established migrated-volume feature vector contains raw causal waveform and
residual windows, but asks the MLP to infer useful scale/roughness statistics
implicitly. Kahu's remaining cost is concentrated in highly variable early
trace regimes. This ablation appends fixed nonlinear summaries computed only
from feature values that are already decoder-known at the current symbol.

Added summaries (all log1p-scaled): current-trace past mean-absolute and RMS;
RMS of each of four decoded-neighbor waveform-difference windows; mean-absolute
of each of four decoded-neighbor residual windows; and mean-absolute/RMS of the
current-trace residual history. The positive y/x/t structural coordinates are
retained. No future current-trace value, target statistic, selector or side bit
is introduced. Kahu remains absent from fitting/normalization. Ideal
probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import kahu_unseen_yxt_coordinate_v1 as yxt

REFERENCE_512=1.9023606738716896
REFERENCE_TIME=1.9255376298482818
REFERENCE_YXT=1.9321423201209738
_base_build=yxt._orig_build


def _meanabs(z):return np.mean(np.abs(z),axis=1)
def _rms(z):return np.sqrt(np.mean(np.asarray(z,np.float64)**2,axis=1))
def _lg(z):return np.log1p(np.asarray(z,np.float64)).astype(np.float32)


def build_with_scale_yxt(X,eps):
    A,T,I,R=_base_build(X,eps)
    A=np.asarray(A,np.float32)
    w=2*q.b.RAD+1
    expected=10+8*w+q.b.HIST+8
    if A.shape[1]!=expected:raise RuntimeError(('base feature layout drift',A.shape[1],expected))
    p=0
    cur=A[:,p:p+10];p+=10
    waves=[A[:,p+i*w:p+(i+1)*w] for i in range(4)];p+=4*w
    res=[A[:,p+i*w:p+(i+1)*w] for i in range(4)];p+=4*w
    crh=A[:,p:p+q.b.HIST];p+=q.b.HIST
    # Remaining eight base scalars are left untouched in A.
    extra=[_lg(_meanabs(cur)),_lg(_rms(cur))]
    extra += [_lg(_rms(z)) for z in waves]
    extra += [_lg(_meanabs(z)) for z in res]
    extra += [_lg(_meanabs(crh)),_lg(_rms(crh))]
    E=np.stack(extra,axis=1).astype(np.float32)
    ny,nx,nt=np.asarray(X).shape
    C=np.stack([I[:,0].astype(np.float32)/float(max(1,ny-1)),I[:,1].astype(np.float32)/float(max(1,nx-1)),I[:,2].astype(np.float32)/float(max(1,nt-1))],axis=1)
    return np.concatenate([A,E,C],axis=1),T,I,R


def main(a):
    q.b.build=build_with_scale_yxt;fr.CHUNK=512;k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-causal-scale-yxt-v1';out['main_feature_change']='append 12 zero-bit causal local-scale/roughness summaries plus y/x/t coordinates';out['causal_scale_feature_count']=12;out['extra_transmitted_bits']=0;out['features_use_future_current_trace_samples']=False;out['reference_512_gain_vs_sz3']=REFERENCE_512;out['reference_time_gain_vs_sz3']=REFERENCE_TIME;out['reference_yxt_gain_vs_sz3']=REFERENCE_YXT;out['gain_ratio_vs_yxt']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_YXT);out['note']='Fixed analytic summaries of already-decoded causal windows; predictor, quantizer, source surveys, boundary waveform model, network widths, training schedule, replay and 512-symbol post-charge adaptation otherwise frozen. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_SCALE_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
