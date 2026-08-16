#!/usr/bin/env python3
"""Per-file all-engine bake-off for Master Portfolio V2.

Every currently executable compressor family is measured independently instead
of only allowing the portfolio selector to expose the winner.  The frozen V1
panel families (AR32-ZSM and Spectral Top-N) are forced across every numeric
panel. Recovered native-scope SEG-Y families (Soda lattice, FORGE lattice,
marine anchor carrier) are attempted on each direct complete record when it can
be materialized safely on a hosted runner.  Incompatibility/failure is recorded,
never converted into a fake compression score.

All methods use the exact frozen PR490 survey-global epsilon. Dataset labels do
not select engines.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import json
import os
import tempfile

import numpy as np

import general_seismic_benchmark_runner as base
import general_seismic_sharded_runner as shardbase
import general_seismic_sharded_runner_v2 as execv2


def _new_family():
    return {
        'bytes': 0,
        'panels_attempted': 0,
        'panels_valid': 0,
        'valid': True,
        'max_abs_error': 0.0,
        'best_config_counts': {},
        'errors': [],
    }


def _add_error(fam, exc):
    fam['valid'] = False
    if len(fam['errors']) < 8:
        fam['errors'].append(f'{type(exc).__name__}: {exc}'[:1000])


def _force_panel_families(P, eps, cfg, source_integer):
    """Encode one panel independently with both frozen V1 architecture families."""
    import general_seismic_codec_portfolio as g
    import general_seismic_portfolio_optimized as opt
    from general_seismic_fast_backend import install
    install(g)

    X = np.asarray(P)
    out = {}

    # Family 1: AR32 predictor + ZSM entropy coder. Predictor work is shared
    # across its W variants; the smallest fully decoded charged stream wins.
    rows = []
    ar_cache = {}
    for cand in [c for c in cfg['candidates'] if c['engine'] == 'ar32_zsm']:
        try:
            key = opt._ar_key(cand)
            if key not in ar_cache:
                ar_cache[key] = opt._prepare_ar(g, X, eps, cand, source_integer)
            body, _ = opt._ar_blob(g, ar_cache[key], int(cand['zsm_window']))
            blob = bytes([int(cand['id'])]) + body
            R = g.decode_portfolio(blob)
            me = float(np.max(np.abs(X.astype(np.float64) - np.asarray(R, np.float64))))
            if me > float(eps):
                raise RuntimeError(('AR32-ZSM hard bound', me, eps))
            rows.append({'id': int(cand['id']), 'bytes': len(blob), 'maxerr': me,
                         'zsm_window': int(cand['zsm_window'])})
        except Exception as e:
            rows.append({'id': int(cand['id']), 'bytes': None, 'error': f'{type(e).__name__}: {e}'[:500]})
    valid = [r for r in rows if r.get('bytes') is not None]
    out['ar32_zsm'] = ({'valid': True, 'best': min(valid, key=lambda r: (r['bytes'], r['id'])), 'trials': rows}
                       if valid else {'valid': False, 'trials': rows, 'error': 'no valid AR32-ZSM configuration'})

    # Family 2: spectral Top-N + exact correction. Every frozen spectral menu
    # point is tried; the smallest valid stream represents the family on panel.
    rows = []
    for cand in [c for c in cfg['candidates'] if c['engine'] == 'spectral_topn']:
        try:
            body, _ = g.encode_spectral_topn(X, eps, int(cand['time_block']), float(cand['fraction']))
            blob = bytes([int(cand['id'])]) + body
            R = g.decode_portfolio(blob)
            me = float(np.max(np.abs(X.astype(np.float64) - np.asarray(R, np.float64))))
            if me > float(eps):
                raise RuntimeError(('Spectral Top-N hard bound', me, eps))
            rows.append({'id': int(cand['id']), 'bytes': len(blob), 'maxerr': me,
                         'time_block': int(cand['time_block']), 'fraction': float(cand['fraction'])})
        except Exception as e:
            rows.append({'id': int(cand['id']), 'bytes': None, 'error': f'{type(e).__name__}: {e}'[:500]})
    valid = [r for r in rows if r.get('bytes') is not None]
    out['spectral_topn'] = ({'valid': True, 'best': min(valid, key=lambda r: (r['bytes'], r['id'])), 'trials': rows}
                           if valid else {'valid': False, 'trials': rows, 'error': 'no valid Spectral Top-N configuration'})
    return out


def _attempt_native(path, eps):
    """Attempt all recovered native SEG-Y families on the same direct file."""
    import master_portfolio_v2 as native
    import marine_carrier_pr6_v2 as marine

    trials = []
    funcs = [
        ('soda_record_run_lattice_pr169', lambda: native.soda_record_codec(path, eps)),
        ('forge_wholefile_lattice_pr203', lambda: native.forge_whole_gather_codec(path, eps)),
        ('marine_anchor_carrier_pr6', lambda: marine.run_fixture(path, None, eps, None)),
    ]
    for name, fn in funcs:
        try:
            r = fn()
            if name == 'marine_anchor_carrier_pr6':
                b = int(r['best']['bytes']); me = float(r['best']['max_abs_error']); shape = r['shape']
            else:
                b = int(r['ours_bytes']); me = float(r['ours_maxerr']); shape = r['shape']
            if me > float(eps) * (1.0 + 3e-6):
                raise RuntimeError(('native hard bound', me, eps))
            trials.append({'engine': name, 'status': 'valid', 'bytes': b,
                           'max_abs_error': me, 'shape': list(map(int, shape)), 'details': r})
        except Exception as e:
            trials.append({'engine': name, 'status': 'ineligible_or_failed',
                           'reason': f'{type(e).__name__}: {e}'[:1200]})
    return trials


def _source_size_map(row):
    return {str(o.get('key', '')): int(o.get('size', 0)) for o in base.records(row)}


def run_shard(args):
    from general_seismic_numeric_io import matched_sz3
    import general_seismic_codec_portfolio as g
    from general_seismic_fast_backend import install
    from general_seismic_portfolio_optimized import encode_portfolio
    install(g)

    manifest = shardbase.load(args.manifest)
    pre = shardbase.load(args.preflight)
    cfg = shardbase.load(args.config)
    em = shardbase.load(args.epsilon_map)
    ds = base.dataset_def(manifest, args.dataset)
    fullrow = base.dataset_row(pre, args.dataset)
    row = execv2.shard_row(fullrow, ds, args.shard_index, args.shard_count)
    eps = float(em['datasets'][ds['id']]['epsilon'])
    source_sizes = _source_size_map(fullrow)

    files = {}
    def getf(name):
        if name not in files:
            files[name] = {
                'logical_file': name,
                'source_bytes': int(source_sizes.get(name, 0)),
                'samples': 0, 'panels': 0,
                'sz3_bytes': 0, 'sz3_max_abs_error': 0.0,
                'v1_portfolio_bytes': 0, 'v1_portfolio_max_abs_error': 0.0,
                'families': {'ar32_zsm': _new_family(), 'spectral_topn': _new_family()},
                'native_trials': [],
            }
        return files[name]

    with tempfile.TemporaryDirectory(prefix='all_engine_bakeoff_') as tmp:
        for i, (P, meta0) in enumerate(base.iter_panels(ds, row, cfg, tmp, args.cube2mseed), 1):
            name = str(meta0.get('logical_file', f'unknown:{i}'))
            f = getf(name)
            f['samples'] += int(P.size); f['panels'] += 1
            sb, sme = matched_sz3(P, eps)
            f['sz3_bytes'] += int(sb)
            f['sz3_max_abs_error'] = max(f['sz3_max_abs_error'], float(sme))
            vb, vm = encode_portfolio(g, P, eps, base.short_cfg(cfg, P.shape[1]), bool(meta0.get('source_integer', False)))
            f['v1_portfolio_bytes'] += len(vb)
            f['v1_portfolio_max_abs_error'] = max(f['v1_portfolio_max_abs_error'], float(vm['maxerr']))

            fams = _force_panel_families(P, eps, base.short_cfg(cfg, P.shape[1]), bool(meta0.get('source_integer', False)))
            for fam_name, r in fams.items():
                a = f['families'][fam_name]
                a['panels_attempted'] += 1
                if r['valid']:
                    b = r['best']
                    a['panels_valid'] += 1
                    a['bytes'] += int(b['bytes'])
                    a['max_abs_error'] = max(a['max_abs_error'], float(b['maxerr']))
                    k = str(b['id']); a['best_config_counts'][k] = int(a['best_config_counts'].get(k, 0)) + 1
                else:
                    a['valid'] = False
                    if len(a['errors']) < 8:
                        a['errors'].append(r.get('error', 'family failed'))

            if i % 25 == 0:
                print('ALL_ENGINE_PROGRESS', ds['id'], args.shard_index, i,
                      sum(x['samples'] for x in files.values()), flush=True)

        # Native families operate on whole direct SEG-Y records. For panel-sharded
        # single/assembled files only shard 0 owns the one whole-file attempt.
        ex = row.get('execution_shard', {})
        native_owner = ex.get('mode') == 'complete_records' or int(args.shard_index) == 0
        if ds.get('format') == 'SEG-Y' and not ds.get('assembly') and native_owner:
            max_source = int(os.environ.get('ALL_ENGINE_NATIVE_MAX_OBJECT_BYTES', str(768 * 1024 * 1024)))
            seen = set()
            objects = base.records(row) if ex.get('mode') == 'complete_records' else base.records(fullrow)
            for oi, obj in enumerate(objects):
                key = str(obj.get('key', ''))
                if not key or key in seen or obj.get('member'):
                    continue
                seen.add(key)
                f = getf(key)
                n = int(obj.get('size', 0))
                if n <= 0 or n > max_source:
                    f['native_trials'] = [
                        {'engine': x, 'status': 'resource_ineligible', 'source_bytes': n,
                         'reason': f'whole-file native test exceeds hosted-runner materialization limit {max_source} bytes'}
                        for x in ('soda_record_run_lattice_pr169','forge_wholefile_lattice_pr203','marine_anchor_carrier_pr6')
                    ]
                    continue
                local = os.path.join(tmp, f'native_{oi:05d}.segy')
                base.download_object(obj, local)
                f['native_trials'] = _attempt_native(local, eps)
                os.remove(local)

    # Finalize family comparability and per-file rankings for this shard piece.
    for f in files.values():
        for fam in f['families'].values():
            fam['valid'] = bool(fam['valid'] and fam['panels_attempted'] > 0 and fam['panels_valid'] == fam['panels_attempted'])
            if fam['valid'] and f['sz3_bytes'] > 0:
                fam['gain_sz3_over_family'] = float(f['sz3_bytes'] / fam['bytes'])
        f['v1_gain_sz3_over_ours'] = float(f['sz3_bytes'] / f['v1_portfolio_bytes']) if f['v1_portfolio_bytes'] else None

    out = {
        'kind': 'all-engine-bakeoff-shard',
        'benchmark': 'master-portfolio-v2-all-engine-per-file',
        'dataset_id': ds['id'], 'category': ds['category'], 'format': ds['format'],
        'shard_index': int(args.shard_index), 'shard_count': int(args.shard_count),
        'epsilon': eps,
        'engine_families': [
            'ar32_zsm','spectral_topn','soda_record_run_lattice_pr169',
            'forge_wholefile_lattice_pr203','marine_anchor_carrier_pr6'
        ],
        'files': sorted(files.values(), key=lambda x: x['logical_file']),
        'dataset_label_used_for_routing': False,
    }
    shardbase.dump(out, args.out)
    print(json.dumps(out, indent=2))


def _merge_family(parts, name):
    rr = [p['families'][name] for p in parts if name in p.get('families', {})]
    if not rr:
        return {'valid': False, 'reason': 'no panel results'}
    out = _new_family()
    out['bytes'] = int(sum(int(x.get('bytes', 0)) for x in rr))
    out['panels_attempted'] = int(sum(int(x.get('panels_attempted', 0)) for x in rr))
    out['panels_valid'] = int(sum(int(x.get('panels_valid', 0)) for x in rr))
    out['valid'] = bool(all(bool(x.get('valid')) for x in rr) and out['panels_attempted'] > 0 and out['panels_valid'] == out['panels_attempted'])
    out['max_abs_error'] = float(max([float(x.get('max_abs_error', 0.0)) for x in rr] or [0.0]))
    c = Counter()
    for x in rr: c.update({str(k): int(v) for k, v in x.get('best_config_counts', {}).items()})
    out['best_config_counts'] = dict(c)
    out['errors'] = [e for x in rr for e in x.get('errors', [])][:12]
    return out


def aggregate(args):
    rows = []
    for fn in glob.glob(os.path.join(args.results, '**', '*.json'), recursive=True):
        try: r = shardbase.load(fn)
        except Exception: continue
        if isinstance(r, dict) and r.get('kind') == 'all-engine-bakeoff-shard': rows.append(r)
    by_file = defaultdict(list)
    for r in rows:
        for f in r.get('files', []):
            by_file[(r['dataset_id'], f['logical_file'])].append(f)

    files = []
    for (did, name), pp in sorted(by_file.items()):
        sz3 = int(sum(int(x.get('sz3_bytes', 0)) for x in pp))
        v1 = int(sum(int(x.get('v1_portfolio_bytes', 0)) for x in pp))
        samples = int(sum(int(x.get('samples', 0)) for x in pp))
        panels = int(sum(int(x.get('panels', 0)) for x in pp))
        fams = {n: _merge_family(pp, n) for n in ('ar32_zsm','spectral_topn')}
        for v in fams.values():
            if v.get('valid') and sz3 > 0: v['gain_sz3_over_family'] = float(sz3 / v['bytes'])

        # Native whole-file result should appear on at most one shard. Deduplicate
        # by engine and prefer a valid result over an ineligible/failure record.
        nt = {}
        for p in pp:
            for t in p.get('native_trials', []):
                e = t['engine']
                if e not in nt or (t.get('status') == 'valid' and nt[e].get('status') != 'valid'):
                    nt[e] = t

        ranking = []
        if sz3 > 0: ranking.append({'engine': 'SZ3', 'bytes': sz3, 'kind': 'external_baseline'})
        if v1 > 0: ranking.append({'engine': 'V1_portfolio', 'bytes': v1, 'kind': 'portfolio'})
        for n, v in fams.items():
            if v.get('valid'): ranking.append({'engine': n, 'bytes': int(v['bytes']), 'kind': 'forced_panel_family'})
        for e, t in nt.items():
            if t.get('status') == 'valid': ranking.append({'engine': e, 'bytes': int(t['bytes']), 'kind': 'native_whole_file'})
        ranking.sort(key=lambda x: (x['bytes'], x['engine']))
        best = ranking[0] if ranking else None
        for q in ranking:
            q['gain_vs_sz3'] = float(sz3 / q['bytes']) if sz3 else None

        files.append({
            'dataset_id': did, 'logical_file': name,
            'source_bytes': max(int(x.get('source_bytes', 0)) for x in pp),
            'samples': samples, 'panels': panels,
            'sz3_bytes': sz3, 'v1_portfolio_bytes': v1,
            'families': fams, 'native_trials': list(nt.values()),
            'ranking': ranking, 'best_engine': best,
        })

    by_dataset = defaultdict(list)
    for f in files: by_dataset[f['dataset_id']].append(f)
    datasets = {}
    for did, ff in sorted(by_dataset.items()):
        datasets[did] = {
            'file_count': len(ff),
            'complete_ranked_files': sum(1 for x in ff if x['ranking']),
            'best_engine_counts': dict(Counter(x['best_engine']['engine'] for x in ff if x['best_engine'])),
        }

    out = {
        'benchmark': 'master-portfolio-v2-all-engine-per-file',
        'purpose': 'measure every currently executable compressor family independently on every frozen benchmark file/panel domain',
        'family_semantics': {
            'ar32_zsm': 'best frozen AR32-ZSM configuration per panel, forced family',
            'spectral_topn': 'best frozen Spectral Top-N configuration per panel, forced family',
            'soda_record_run_lattice_pr169': 'native whole SEG-Y record attempt',
            'forge_wholefile_lattice_pr203': 'native whole SEG-Y gather attempt',
            'marine_anchor_carrier_pr6': 'native regular-receiver whole SEG-Y attempt',
        },
        'note': 'Native whole-file families can be resource_ineligible on very large single files until streaming/scalable adapters exist; that is reported explicitly rather than scored.',
        'datasets': datasets,
        'files': files,
    }
    shardbase.dump(out, args.out)
    print(json.dumps(out, indent=2))


def common(p):
    p.add_argument('--manifest', required=True); p.add_argument('--preflight', required=True)
    p.add_argument('--config', required=True); p.add_argument('--epsilon-map', required=True)
    p.add_argument('--dataset', required=True); p.add_argument('--shard-index', type=int, required=True)
    p.add_argument('--shard-count', type=int, required=True)
    p.add_argument('--cube2mseed', default=os.environ.get('CUBE2MSEED')); p.add_argument('--out', required=True)


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    common(sub.add_parser('run-shard'))
    a = sub.add_parser('aggregate'); a.add_argument('--results', required=True); a.add_argument('--out', required=True)
    args = ap.parse_args()
    if args.cmd == 'run-shard': run_shard(args)
    else: aggregate(args)


if __name__ == '__main__': main()
