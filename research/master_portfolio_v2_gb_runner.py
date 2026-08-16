#!/usr/bin/env python3
"""GB-scale Master Portfolio V2 runner.

Execution reuses the frozen V1 benchmark selection and survey-global epsilon.
For each deterministic compression shard it first runs the exact frozen V1
portfolio.  On complete SEG-Y records that are safe to materialize in CI, every
structurally compatible recovered native engine is then raced against the exact
V1 encoding of the same numeric object.  Only a byte-smaller, decoder-verified,
hard-error-valid candidate may replace that object's V1 bytes.

Dataset names never participate in codec eligibility or winner selection.
Large/unsupported objects simply retain the immutable V1 fallback.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import json
import os
from pathlib import Path
import tempfile

import numpy as np

import general_seismic_sharded_runner_v2 as execv2
import general_seismic_sharded_runner as shardbase
import general_seismic_benchmark_runner as base


def _v1_object_stats(obj, cfg, eps):
    """Encode one SEG-Y source object exactly as the frozen streaming V1 path."""
    import general_seismic_codec_portfolio as g
    from general_seismic_fast_backend import install
    from general_seismic_portfolio_optimized import encode_portfolio
    from general_seismic_streaming_segy import s3_panels

    install(g)
    channels, time_samples = base.panel_dims(cfg)
    total = samples = panels = 0
    maxerr = 0.0
    engines = Counter()
    for P, meta0 in s3_panels(base.S3, [obj], channels=channels, time_samples=time_samples):
        pcfg = base.short_cfg(cfg, P.shape[1])
        blob, meta = encode_portfolio(g, P, eps, pcfg, bool(meta0.get('source_integer', False)))
        if float(meta['maxerr']) > eps:
            raise RuntimeError(('V1 object hard bound failure', obj.get('key'), meta['maxerr'], eps))
        total += len(blob)
        samples += int(P.size)
        panels += 1
        maxerr = max(maxerr, float(meta['maxerr']))
        engines[str(meta['selected_engine'])] += 1
    if samples <= 0:
        raise RuntimeError(('V1 object contained no samples', obj))
    return {'bytes': int(total), 'samples': int(samples), 'panels': int(panels),
            'maxerr': float(maxerr), 'engine_panel_counts': dict(engines)}


def _native_competitions(path, eps):
    """Attempt all recovered native families; incompatibility is fail-closed."""
    import master_portfolio_v2_compete as compete

    trials = []
    funcs = [
        ('soda_record_run_lattice_pr169', lambda: compete.compete_soda(path, eps)),
        ('forge_wholefile_lattice_pr203', lambda: compete.compete_forge(path, eps)),
        ('marine_anchor_carrier_pr6', lambda: compete.compete_marine(path, eps)),
    ]
    for engine, fn in funcs:
        try:
            r = fn()
            if not bool(r.get('selected_is_no_worse_than_v1')):
                raise RuntimeError('native/V1 selector regression')
            trials.append({'engine': engine, 'eligible': True, 'result': r})
        except Exception as e:
            trials.append({'engine': engine, 'eligible': False,
                           'reason': f'{type(e).__name__}: {e}'[:1000]})
    return trials


def _augment_complete_segy_records(ds, row, cfg, eps, tmp, fallback_bytes):
    """Replace V1 bytes only where an identical-object native race proves smaller."""
    result = {
        'v1_fallback_bytes': int(fallback_bytes),
        'v2_bytes': int(fallback_bytes),
        'native_saved_bytes': 0,
        'native_records': [],
        'native_skipped_large_records': [],
    }
    ex = row.get('execution_shard', {})
    if ds.get('format') != 'SEG-Y' or ds.get('assembly') or ex.get('mode') != 'complete_records':
        return result

    max_source = int(os.environ.get('V2_NATIVE_MAX_OBJECT_BYTES', str(256 * 1024 * 1024)))
    for oi, obj in enumerate(base.records(row)):
        source_bytes = int(obj.get('size', 0))
        key = str(obj.get('key', ''))
        if source_bytes <= 0 or source_bytes > max_source or obj.get('member'):
            result['native_skipped_large_records'].append({
                'key': key, 'source_bytes': source_bytes,
                'reason': 'CI materialization limit or non-direct object; immutable V1 fallback retained'
            })
            continue

        local = os.path.join(tmp, f'native_{oi:05d}.segy')
        base.download_object(obj, local)
        v1obj = _v1_object_stats(obj, cfg, eps)
        trials = _native_competitions(local, eps)
        valid = []
        for t in trials:
            if not t['eligible']:
                continue
            r = t['result']
            # Critical equivalence guard: recovered native loader must expose the
            # same numeric object/partition as the frozen streaming V1 path.
            candidate_samples = int(np.prod(r.get('shape', [])))
            if candidate_samples != v1obj['samples']:
                t['eligible'] = False
                t['reason'] = f'numeric sample-count mismatch native={candidate_samples} streamingV1={v1obj["samples"]}'
                t.pop('result', None)
                continue
            if int(r['v1_fallback_bytes']) != int(v1obj['bytes']):
                t['eligible'] = False
                t['reason'] = f'V1 byte-equivalence mismatch native-view={r["v1_fallback_bytes"]} streaming={v1obj["bytes"]}'
                t.pop('result', None)
                continue
            valid.append(r)

        winner_bytes = int(v1obj['bytes'])
        winner = 'general_seismic_portfolio_v1_panel_fallback'
        for r in valid:
            if int(r['winner_bytes']) < winner_bytes:
                winner_bytes = int(r['winner_bytes'])
                winner = str(r['winner'])

        saved = int(v1obj['bytes']) - winner_bytes
        if saved < 0:
            raise RuntimeError(('V2 object regression', key, v1obj['bytes'], winner_bytes))
        result['v2_bytes'] -= saved
        result['native_saved_bytes'] += saved
        result['native_records'].append({
            'key': key,
            'source_bytes': source_bytes,
            'numeric_samples': int(v1obj['samples']),
            'v1_bytes': int(v1obj['bytes']),
            'winner': winner,
            'winner_bytes': winner_bytes,
            'saved_bytes': saved,
            'trials': trials,
        })
        os.remove(local)

    if result['v2_bytes'] > result['v1_fallback_bytes']:
        raise RuntimeError(('V2 shard monotonicity failure', result))
    return result


def run_compress_shard(args):
    manifest = shardbase.load(args.manifest)
    pre = shardbase.load(args.preflight)
    cfg = shardbase.load(args.config)
    em = shardbase.load(args.epsilon_map)
    ds = base.dataset_def(manifest, args.dataset)
    row = execv2.shard_row(base.dataset_row(pre, args.dataset), ds, args.shard_index, args.shard_count)
    eps = float(em['datasets'][ds['id']]['epsilon'])

    if not base.records(row):
        out = shardbase.empty_compression(ds['id'], args.shard_index, args.shard_count, row['selected_bytes'], eps)
        out.update({'benchmark': 'general-seismic-master-portfolio-v2-gb',
                    'v1_fallback_bytes': 0, 'native_saved_bytes': 0,
                    'native_records': [], 'native_skipped_large_records': []})
    else:
        with tempfile.TemporaryDirectory(prefix='master_v2_gb_') as tmp:
            co = base.compression_pass(ds, row, cfg, eps, tmp, args.cube2mseed)
            aug = _augment_complete_segy_records(ds, row, cfg, eps, tmp, co['ours_bytes'])
        out = {'kind': 'compression-shard', 'benchmark': 'general-seismic-master-portfolio-v2-gb',
               'dataset_id': ds['id'], 'shard_index': int(args.shard_index),
               'shard_count': int(args.shard_count),
               'selected_source_bytes': int(row['selected_bytes']), 'epsilon': eps, 'empty': False}
        out.update(co)
        out['v1_fallback_bytes'] = int(aug['v1_fallback_bytes'])
        out['ours_bytes'] = int(aug['v2_bytes'])
        out['native_saved_bytes'] = int(aug['native_saved_bytes'])
        out['native_records'] = aug['native_records']
        out['native_skipped_large_records'] = aug['native_skipped_large_records']
        out['gain_sz3_over_ours'] = float(out['sz3_bytes'] / out['ours_bytes'])
        out['reduction_percent_vs_sz3'] = float(100.0 * (1.0 - out['ours_bytes'] / out['sz3_bytes']))
        out['ours_bps'] = float(8.0 * out['ours_bytes'] / out['samples'])
        out['v2_gain_over_v1'] = float(out['v1_fallback_bytes'] / out['ours_bytes'])
        out['dataset_label_used_for_routing'] = False
        if out['ours_bytes'] > out['v1_fallback_bytes']:
            raise RuntimeError(('V2 shard regression', out['dataset_id'], out['ours_bytes'], out['v1_fallback_bytes']))

    shardbase.dump(out, args.out)
    print(json.dumps(out, indent=2))
    return out


def aggregate_compression(args):
    manifest = shardbase.load(args.manifest)
    em = shardbase.load(args.epsilon_map)
    rows = []
    for f in sorted(glob.glob(os.path.join(args.results, '**', '*.json'), recursive=True)):
        try:
            r = shardbase.load(f)
        except Exception:
            continue
        if isinstance(r, dict) and r.get('kind') == 'compression-shard' and r.get('benchmark') == 'general-seismic-master-portfolio-v2-gb':
            rows.append(r)
    groups = defaultdict(list)
    for r in rows:
        groups[r['dataset_id']].append(r)

    surveys = []
    for ds in manifest['datasets']:
        did = ds['id']
        rr = groups.get(did, [])
        collapsed = shardbase.collapse_dataset(ds, rr, em['datasets'][did], args.shard_count)
        v1 = int(sum(int(r.get('v1_fallback_bytes', r.get('ours_bytes', 0))) for r in rr))
        saved = int(sum(int(r.get('native_saved_bytes', 0)) for r in rr))
        native_records = [x for r in rr for x in r.get('native_records', [])]
        collapsed.update({
            'benchmark': 'general-seismic-master-portfolio-v2-gb',
            'portfolio': 'master-portfolio-v2-hierarchical',
            'v1_fallback_bytes': v1,
            'native_saved_bytes': saved,
            'v2_gain_over_v1': float(v1 / collapsed['ours_bytes']),
            'native_record_count': len(native_records),
            'native_winner_counts': dict(Counter(x['winner'] for x in native_records if x.get('saved_bytes', 0) > 0)),
            'dataset_label_used_for_routing': False,
        })
        if collapsed['ours_bytes'] > v1:
            raise RuntimeError(('collapsed V2 regression', did, collapsed['ours_bytes'], v1))
        surveys.append(collapsed)

    h, groups_out = shardbase.headline_from_surveys(surveys)
    total_v1 = int(sum(r['v1_fallback_bytes'] for r in surveys))
    total_v2 = int(sum(r['ours_bytes'] for r in surveys))
    out = {
        'benchmark': 'general-seismic-master-portfolio-v2-gb',
        'portfolio': 'master-portfolio-v2-hierarchical',
        'source_frozen_benchmark': 'PR490 frozen selection + exact survey-global epsilon artifacts',
        'execution': {'mode': 'deterministic 8-way shards; native complete-record races where structurally eligible; V1 immutable fallback elsewhere',
                      'shard_count_per_survey': int(args.shard_count),
                      'dataset_label_routing': False},
        'headline': h,
        'v2_monotonicity': {'total_v1_fallback_bytes': total_v1, 'total_v2_bytes': total_v2,
                            'saved_bytes': total_v1 - total_v2,
                            'gain_v1_over_v2': float(total_v1 / total_v2),
                            'no_regression': bool(total_v2 <= total_v1)},
        'groups': groups_out,
        'surveys': sorted(surveys, key=lambda r: r['dataset_id']),
    }
    shardbase.dump(out, args.out)
    print(json.dumps(out, indent=2))
    return out


def common(p):
    p.add_argument('--manifest', required=True)
    p.add_argument('--preflight', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--dataset', required=True)
    p.add_argument('--shard-index', type=int, required=True)
    p.add_argument('--shard-count', type=int, required=True)
    p.add_argument('--epsilon-map', required=True)
    p.add_argument('--cube2mseed', default=os.environ.get('CUBE2MSEED'))
    p.add_argument('--out', required=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    common(sub.add_parser('compress-shard'))
    a = sub.add_parser('aggregate-compression')
    a.add_argument('--manifest', required=True)
    a.add_argument('--epsilon-map', required=True)
    a.add_argument('--results', required=True)
    a.add_argument('--shard-count', type=int, required=True)
    a.add_argument('--out', required=True)
    args = ap.parse_args()
    if args.cmd == 'compress-shard':
        run_compress_shard(args)
    else:
        aggregate_compression(args)


if __name__ == '__main__':
    main()
