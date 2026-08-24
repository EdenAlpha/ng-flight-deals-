#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from typing import Any

import numpy as np

import compression_phenotype_probe_v1 as ph
import general_seismic_benchmark_runner as base
import general_seismic_sharded_runner as shardbase
import general_seismic_sharded_runner_v2 as execv2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--preflight', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--epsilon-map', required=True)
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--shard-count', type=int, default=8)
    ap.add_argument('--shards', default='0,2,5,7')
    ap.add_argument('--tiles-per-shard', type=int, default=2)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    manifest = shardbase.load(args.manifest)
    pre = shardbase.load(args.preflight)
    cfg = shardbase.load(args.config)
    em = shardbase.load(args.epsilon_map)
    ds = base.dataset_def(manifest, args.dataset)
    fullrow = base.dataset_row(pre, args.dataset)
    eps = float(em['datasets'][ds['id']]['epsilon'])
    shards = [int(x) for x in args.shards.split(',') if x.strip()]

    rows: list[dict[str, Any]] = []
    seen_panels = 0
    total_samples = 0
    with tempfile.TemporaryDirectory(prefix='blind_phenotype_') as tmp:
        for si in shards:
            row = execv2.shard_row(fullrow, ds, si, args.shard_count)
            taken = 0
            for P, meta0 in base.iter_panels(ds, row, cfg, tmp, os.environ.get('CUBE2MSEED')):
                X = np.asarray(P, dtype=np.float32)
                if X.ndim != 2:
                    X = X.reshape(X.shape[0], -1)
                sw = min(ph.TILE_SPACE, X.shape[0])
                tw = min(ph.TILE_TIME, X.shape[1])
                if sw < 2 or tw < 4:
                    continue
                # Deterministic central crop of the panel. No amplitude-dependent location choice.
                s0 = max(0, (X.shape[0] - sw) // 2)
                t0 = max(0, (X.shape[1] - tw) // 2)
                W = np.ascontiguousarray(X[s0:s0 + sw, t0:t0 + tw])
                m = ph.tile_metrics(W, eps)
                rows.append({
                    'blind_dataset_id': ds['id'],
                    'shard': int(si),
                    'logical_file': str(meta0.get('logical_file', '')),
                    'panel_shape': list(map(int, X.shape)),
                    'crop': [int(s0), int(t0), int(sw), int(tw)],
                    'metrics': m,
                })
                seen_panels += 1
                total_samples += int(W.size)
                taken += 1
                print('BLIND_TILE', ds['id'], si, json.dumps(m, sort_keys=True), flush=True)
                if taken >= args.tiles_per_shard:
                    break

    if not rows:
        raise RuntimeError(('no phenotype panels', ds['id']))
    summary = ph.summarize(rows)
    out = {
        'kind': 'seismic-compression-phenotype-blind-target-v2',
        'dataset': ds['id'],
        'category_metadata_not_used_by_classifier': ds.get('category'),
        'format_metadata_not_used_by_classifier': ds.get('format'),
        'eps': eps,
        'tiles': seen_panels,
        'samples_measured': total_samples,
        'sampling_rule': {
            'shard_count': args.shard_count,
            'shards': shards,
            'tiles_per_shard': args.tiles_per_shard,
            'crop': 'deterministic central <=128x1024 crop of each selected benchmark panel',
            'amplitude_selected': False,
        },
        'summary': summary,
        'rows': rows,
    }
    json.dump(out, open(args.out, 'w'), indent=2)
    print('BLIND_FINAL', json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
