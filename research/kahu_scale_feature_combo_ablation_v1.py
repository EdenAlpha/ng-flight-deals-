#!/usr/bin/env python3
"""Second-stage attribution of the unseen-Kahu scale/roughness discovery.

PR #736 isolated four physically interpretable groups and showed decoded-neighbor
residual roughness to be the strongest single group. This wrapper tests a few
predeclared combinations, without changing any other codec/model setting, to
identify the smallest bundle that recovers essentially all of PR #735's gain.

The combinations are fixed before this run; they are not selected on Kahu
results. All features are deterministic functions of already-decoded causal
state and cost zero transmitted bits. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse
import kahu_scale_feature_group_ablation_v1 as g

COMBOS = {
    # All residual-scale summaries: four decoded-neighbor residual mean-absolute
    # values plus current residual-history mean-absolute/RMS.
    'residual6': (6,7,8,9,10,11),
    # All waveform-energy summaries only.
    'waveform6': (0,1,2,3,4,5),
    # Everything available from fully decoded neighboring traces.
    'neighbor8': (2,3,4,5,6,7,8,9),
    # Strong residual bundle plus current-wave causal scale.
    'residual_plus_currentwave8': (0,1,6,7,8,9,10,11),
    # Drop only current-wave scale from the full 12-feature result.
    'no_currentwave10': (2,3,4,5,6,7,8,9,10,11),
}


def main(a):
    g.GROUPS.update(COMBOS)
    g.main(a)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--eps',required=True)
    p.add_argument('--group',required=True,choices=sorted(COMBOS))
    p.add_argument('--out',required=True)
    main(p.parse_args())
