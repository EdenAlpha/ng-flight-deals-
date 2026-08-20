#!/usr/bin/env python3
"""Attribute the positive unseen-Kahu causal scale/roughness gain.

PR #735 showed that 12 fixed, decoder-known causal summaries improve the strict
held-out Kahu line beyond the y/x/t coordinate control. This experiment keeps
that entire protocol frozen and exposes only one physically interpretable group
of summaries at a time:

  current_wave    : current-trace causal-past mean-absolute + RMS
  neighbor_wave   : RMS of four already-decoded neighbor waveform windows
  neighbor_resid  : mean-absolute of four already-decoded neighbor residual windows
  current_resid   : current-trace residual-history mean-absolute + RMS
  all12           : exact PR #735 control

No future current-trace samples, target statistics, target fitting, selector
bits, predictor changes, quantizer changes or boundary-model changes are
introduced. The purpose is causal attribution: identify the minimal explicit
statistic that explains the neural probe's gain so the discovery can be
compiled into a simpler codec context law rather than left as an opaque feature
bundle. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import kahu_unseen_yxt_coordinate_v1 as yxt

REFERENCE_512 = 1.9023606738716896
REFERENCE_TIME = 1.9255376298482818
REFERENCE_YXT = 1.9321423201209738
REFERENCE_ALL12 = 1.9473577357821565

GROUPS = {
    'current_wave': (0, 1),
    'neighbor_wave': (2, 3, 4, 5),
    'neighbor_resid': (6, 7, 8, 9),
    'current_resid': (10, 11),
    'all12': tuple(range(12)),
}
GROUP = 'all12'
_base_build = yxt._orig_build


def _meanabs(z):
    return np.mean(np.abs(z), axis=1)


def _rms(z):
    return np.sqrt(np.mean(np.asarray(z, np.float64) ** 2, axis=1))


def _lg(z):
    return np.log1p(np.asarray(z, np.float64)).astype(np.float32)


def build_group_yxt(X, eps):
    A, T, I, R = _base_build(X, eps)
    A = np.asarray(A, np.float32)
    w = 2 * q.b.RAD + 1
    expected = 10 + 8 * w + q.b.HIST + 8
    if A.shape[1] != expected:
        raise RuntimeError(('base feature layout drift', A.shape[1], expected))

    p = 0
    cur = A[:, p:p + 10]; p += 10
    waves = [A[:, p + i*w:p + (i+1)*w] for i in range(4)]; p += 4*w
    res = [A[:, p + i*w:p + (i+1)*w] for i in range(4)]; p += 4*w
    crh = A[:, p:p + q.b.HIST]; p += q.b.HIST

    extra = [_lg(_meanabs(cur)), _lg(_rms(cur))]
    extra += [_lg(_rms(z)) for z in waves]
    extra += [_lg(_meanabs(z)) for z in res]
    extra += [_lg(_meanabs(crh)), _lg(_rms(crh))]
    E = np.stack(extra, axis=1).astype(np.float32)
    ids = GROUPS[GROUP]
    E = E[:, ids]

    ny, nx, nt = np.asarray(X).shape
    C = np.stack([
        I[:, 0].astype(np.float32) / float(max(1, ny - 1)),
        I[:, 1].astype(np.float32) / float(max(1, nx - 1)),
        I[:, 2].astype(np.float32) / float(max(1, nt - 1)),
    ], axis=1)
    return np.concatenate([A, E, C], axis=1), T, I, R


def main(a):
    global GROUP
    if a.group not in GROUPS:
        raise RuntimeError(('unknown group', a.group, sorted(GROUPS)))
    GROUP = a.group
    q.b.build = build_group_yxt
    fr.CHUNK = 512
    k.main(a)

    out = json.load(open(a.out))
    out['kind'] = 'unseen-kahu-causal-scale-group-ablation-v1'
    out['scale_group'] = GROUP
    out['scale_feature_indices'] = list(GROUPS[GROUP])
    out['scale_feature_count'] = len(GROUPS[GROUP])
    out['retains_yxt_coordinates'] = True
    out['extra_transmitted_bits'] = 0
    out['features_use_future_current_trace_samples'] = False
    out['heldout_kahu_used_to_choose_group_or_feature_form'] = False
    out['reference_512_gain_vs_sz3'] = REFERENCE_512
    out['reference_time_gain_vs_sz3'] = REFERENCE_TIME
    out['reference_yxt_gain_vs_sz3'] = REFERENCE_YXT
    out['reference_all12_gain_vs_sz3'] = REFERENCE_ALL12
    out['gain_delta_vs_yxt'] = float(out['full_replay_weighted_gain_vs_sz3'] - REFERENCE_YXT)
    out['gain_delta_vs_all12'] = float(out['full_replay_weighted_gain_vs_sz3'] - REFERENCE_ALL12)
    out['note'] = ('Controlled attribution of PR #735. Predictor, quantizer, source surveys, '
                   'boundary waveform model, 320/240/160 network, 10 source epochs, replay, '
                   '512-symbol post-charge adaptation and y/x/t coordinates are frozen; only '
                   'the selected explicit causal scale/roughness feature group changes.')
    Path(a.out).write_text(json.dumps(out, indent=2))
    print('KAHU_SCALE_GROUP_FINAL', json.dumps({x:y for x,y in out.items()
          if x not in ('base_rows','adapt_rows','source_meta')}, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--eps', required=True)
    p.add_argument('--group', required=True, choices=sorted(GROUPS))
    p.add_argument('--out', required=True)
    main(p.parse_args())
