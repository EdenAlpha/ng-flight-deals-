import argparse, copy, glob, json, math, os, tempfile
from collections import Counter, defaultdict

import numpy as np

import general_seismic_benchmark_runner as base


def load(p):
    return base.load_json(p)


def dump(x, p):
    base.dump_json(x, p)


def shard_row(row, ds, shard_index, shard_count):
    """Partition the already-frozen selected records exactly once by source bytes.

    This changes execution parallelism only. Selection, ordering, numeric decoding,
    epsilon, candidate menu and byte accounting are unchanged.
    """
    shard_index = int(shard_index)
    shard_count = int(shard_count)
    if shard_count <= 0 or not (0 <= shard_index < shard_count):
        raise ValueError((shard_index, shard_count))
    rr = base.records(row)
    if ds.get('assembly'):
        chosen = rr if shard_index == 0 else []
    else:
        total = sum(max(0, int(o.get('size', 0))) for o in rr)
        if total <= 0:
            chosen = rr if shard_index == 0 else []
        else:
            # Contiguous weighted assignment. Each complete frozen record is sent
            # to exactly one shard; no signal values or compression results enter.
            target = total / float(shard_count)
            buckets = [[] for _ in range(shard_count)]
            bi = 0
            acc = 0
            for o in rr:
                n = max(0, int(o.get('size', 0)))
                if bi < shard_count - 1 and buckets[bi] and acc + n > target:
                    bi += 1
                    acc = 0
                buckets[bi].append(o)
                acc += n
            chosen = buckets[shard_index]
    q = copy.deepcopy(row)
    q['selected'] = [{'span_id': f'execution-shard-{shard_index:02d}-of-{shard_count:02d}', 'objects': chosen}]
    q['selected_bytes'] = int(sum(int(o.get('size', 0)) for o in chosen))
    q['selected_gb'] = q['selected_bytes'] / 1e9
    q['execution_shard'] = {'index': shard_index, 'count': shard_count, 'record_count': len(chosen)}
    return q


def empty_stats(dataset_id, shard_index, shard_count, selected_bytes):
    return {
        'kind': 'stats-shard', 'dataset_id': dataset_id,
        'shard_index': int(shard_index), 'shard_count': int(shard_count),
        'selected_source_bytes': int(selected_bytes), 'empty': True,
        'samples': 0, 'mean': 0.0, 'M2': 0.0, 'std': None,
        'numeric_bytes': 0, 'panels': 0, 'seconds': 0.0,
    }


def run_stats_shard(args):
    manifest = load(args.manifest); pre = load(args.preflight); cfg = load(args.config)
    ds = base.dataset_def(manifest, args.dataset)
    row = shard_row(base.dataset_row(pre, args.dataset), ds, args.shard_index, args.shard_count)
    if not base.records(row):
        out = empty_stats(ds['id'], args.shard_index, args.shard_count, row['selected_bytes'])
    else:
        with tempfile.TemporaryDirectory(prefix='general_seismic_stats_') as tmp:
            st = base.stats_pass(ds, row, cfg, tmp, args.cube2mseed)
        out = {'kind': 'stats-shard', 'dataset_id': ds['id'],
               'shard_index': int(args.shard_index), 'shard_count': int(args.shard_count),
               'selected_source_bytes': int(row['selected_bytes']), 'empty': False}
        out.update(st)
    dump(out, args.out); print(json.dumps(out, indent=2)); return out


def merge_moments(rows):
    n = 0; mean = 0.0; M2 = 0.0; numeric_bytes = 0; panels = 0; seconds = 0.0
    for r in sorted(rows, key=lambda x: int(x['shard_index'])):
        ni = int(r.get('samples', 0)); numeric_bytes += int(r.get('numeric_bytes', 0)); panels += int(r.get('panels', 0)); seconds += float(r.get('seconds', 0.0))
        if ni <= 0: continue
        mui = float(r['mean']); m2i = float(r['M2'])
        if n == 0:
            n = ni; mean = mui; M2 = m2i
        else:
            delta = mui - mean; tot = n + ni
            M2 += m2i + delta * delta * n * ni / tot
            mean += delta * ni / tot; n = tot
    if n <= 0: raise RuntimeError('merged stats contain no samples')
    var = M2 / n
    if var < 0 and abs(var) < 1e-12 * max(1.0, mean * mean): var = 0.0
    if var <= 0: raise RuntimeError(('merged nonpositive variance', var, n, mean))
    return {'samples': int(n), 'mean': float(mean), 'M2': float(M2), 'std': float(math.sqrt(var)),
            'numeric_bytes': int(numeric_bytes), 'panels': int(panels), 'sum_shard_seconds': float(seconds)}


def aggregate_stats(args):
    rows = []
    for f in sorted(glob.glob(os.path.join(args.results, '**', '*.json'), recursive=True)):
        try: r = load(f)
        except Exception: continue
        if isinstance(r, dict) and r.get('kind') == 'stats-shard': rows.append(r)
    groups = defaultdict(list)
    for r in rows: groups[r['dataset_id']].append(r)
    expected = set(args.datasets.split(',')) if args.datasets else set(groups)
    missing = expected - set(groups)
    if missing: raise RuntimeError(('missing stats datasets', sorted(missing)))
    out = {'benchmark': 'general-seismic-benchmark-v1', 'kind': 'survey-global-epsilon-map', 'shard_count': int(args.shard_count), 'datasets': {}}
    for did in sorted(expected):
        rr = groups[did]
        seen = {int(r['shard_index']) for r in rr}
        if seen != set(range(int(args.shard_count))): raise RuntimeError(('stats shard coverage', did, sorted(seen)))
        st = merge_moments(rr); eps = 0.10 * st['std']
        out['datasets'][did] = {'global_stats': st, 'epsilon': eps,
                                'selected_source_bytes': int(sum(int(r.get('selected_source_bytes', 0)) for r in rr))}
        print('GLOBAL_EPSILON', did, st['samples'], st['std'], eps, flush=True)
    dump(out, args.out); return out


def empty_compression(dataset_id, shard_index, shard_count, selected_bytes, eps):
    return {'kind': 'compression-shard', 'dataset_id': dataset_id,
            'shard_index': int(shard_index), 'shard_count': int(shard_count),
            'selected_source_bytes': int(selected_bytes), 'epsilon': float(eps), 'empty': True,
            'samples': 0, 'panels': 0, 'ours_bytes': 0, 'sz3_bytes': 0,
            'ours_maxerr': 0.0, 'sz3_maxerr': 0.0,
            'engine_panel_counts': {}, 'candidate_panel_counts': {},
            'ours_encode_seconds': 0.0, 'sz3_roundtrip_seconds': 0.0, 'compression_pass_seconds': 0.0}


def run_compress_shard(args):
    manifest = load(args.manifest); pre = load(args.preflight); cfg = load(args.config); em = load(args.epsilon_map)
    ds = base.dataset_def(manifest, args.dataset)
    row = shard_row(base.dataset_row(pre, args.dataset), ds, args.shard_index, args.shard_count)
    eps = float(em['datasets'][ds['id']]['epsilon'])
    if not base.records(row):
        out = empty_compression(ds['id'], args.shard_index, args.shard_count, row['selected_bytes'], eps)
    else:
        with tempfile.TemporaryDirectory(prefix='general_seismic_compress_') as tmp:
            co = base.compression_pass(ds, row, cfg, eps, tmp, args.cube2mseed)
        out = {'kind': 'compression-shard', 'dataset_id': ds['id'],
               'shard_index': int(args.shard_index), 'shard_count': int(args.shard_count),
               'selected_source_bytes': int(row['selected_bytes']), 'epsilon': eps, 'empty': False}
        out.update(co)
    dump(out, args.out); print(json.dumps(out, indent=2)); return out


def sum_counts(rows, key):
    c = Counter()
    for r in rows: c.update({str(k): int(v) for k, v in r.get(key, {}).items()})
    return dict(c)


def collapse_dataset(ds, rows, epsrow, shard_count):
    seen = {int(r['shard_index']) for r in rows}
    if seen != set(range(int(shard_count))): raise RuntimeError(('compression shard coverage', ds['id'], sorted(seen)))
    samples = sum(int(r.get('samples', 0)) for r in rows); ours = sum(int(r.get('ours_bytes', 0)) for r in rows); sz3 = sum(int(r.get('sz3_bytes', 0)) for r in rows)
    if samples <= 0 or ours <= 0 or sz3 <= 0: raise RuntimeError(('empty collapsed survey', ds['id'], samples, ours, sz3))
    if samples != int(epsrow['global_stats']['samples']): raise RuntimeError(('stats/compress sample mismatch', ds['id'], epsrow['global_stats']['samples'], samples))
    eps = float(epsrow['epsilon'])
    out = {'benchmark': 'general-seismic-benchmark-v1', 'dataset_id': ds['id'], 'name': ds['name'], 'category': ds['category'], 'format': ds['format'],
           'selected_source_bytes': int(sum(int(r.get('selected_source_bytes', 0)) for r in rows)),
           'selected_source_gb': sum(int(r.get('selected_source_bytes', 0)) for r in rows) / 1e9,
           'global_stats': epsrow['global_stats'], 'epsilon': eps,
           'samples': int(samples), 'panels': int(sum(int(r.get('panels', 0)) for r in rows)),
           'ours_bytes': int(ours), 'sz3_bytes': int(sz3), 'ours_bps': 8.0 * ours / samples, 'sz3_bps': 8.0 * sz3 / samples,
           'gain_sz3_over_ours': sz3 / ours, 'reduction_percent_vs_sz3': 100.0 * (1.0 - ours / sz3),
           'ours_maxerr': max(float(r.get('ours_maxerr', 0.0)) for r in rows), 'sz3_maxerr': max(float(r.get('sz3_maxerr', 0.0)) for r in rows),
           'engine_panel_counts': sum_counts(rows, 'engine_panel_counts'), 'candidate_panel_counts': sum_counts(rows, 'candidate_panel_counts'),
           'ours_encode_seconds_sum': sum(float(r.get('ours_encode_seconds', 0.0)) for r in rows),
           'sz3_roundtrip_seconds_sum': sum(float(r.get('sz3_roundtrip_seconds', 0.0)) for r in rows),
           'compression_pass_seconds_sum': sum(float(r.get('compression_pass_seconds', 0.0)) for r in rows),
           'execution_shards': int(shard_count)}
    if out['ours_maxerr'] > eps or out['sz3_maxerr'] > eps * (1 + 3e-6): raise RuntimeError(('collapsed hard bound failure', ds['id'], out['ours_maxerr'], out['sz3_maxerr'], eps))
    return out


def headline_from_surveys(rows):
    gains = np.asarray([r['gain_sz3_over_ours'] for r in rows], float)
    rng = np.random.default_rng(20260814); boots = np.empty(20000, float)
    for i in range(boots.size): boots[i] = np.median(rng.choice(gains, size=len(gains), replace=True))
    h = {'survey_count': len(rows), 'win_rate': float(np.mean(gains > 1.0)), 'wins': int(np.sum(gains > 1.0)),
         'median_gain': float(np.median(gains)),
         'bootstrap95_median_gain': [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
         'p10_gain': float(np.percentile(gains, 10)),
         'byte_weighted_gain': sum(r['sz3_bytes'] for r in rows) / sum(r['ours_bytes'] for r in rows),
         'total_ours_bytes': int(sum(r['ours_bytes'] for r in rows)), 'total_sz3_bytes': int(sum(r['sz3_bytes'] for r in rows))}
    h['passes_preregistered_general_win'] = bool(h['win_rate'] >= 0.80 and h['median_gain'] >= 1.20 and h['bootstrap95_median_gain'][0] > 1.0)
    groups = {}
    for label, prefix in [('land', 'land-'), ('marine', 'marine-'), ('DAS', 'DAS-')]:
        rr = [r for r in rows if r['category'].startswith(prefix)]
        if rr:
            gg = np.asarray([r['gain_sz3_over_ours'] for r in rr], float)
            groups[label] = {'n': len(rr), 'wins': int(np.sum(gg > 1)), 'win_rate': float(np.mean(gg > 1)), 'median_gain': float(np.median(gg)),
                             'byte_weighted_gain': sum(r['sz3_bytes'] for r in rr) / sum(r['ours_bytes'] for r in rr)}
        else: groups[label] = {'n': 0}
    return h, groups


def aggregate_compression(args):
    manifest = load(args.manifest); em = load(args.epsilon_map)
    rows = []
    for f in sorted(glob.glob(os.path.join(args.results, '**', '*.json'), recursive=True)):
        try: r = load(f)
        except Exception: continue
        if isinstance(r, dict) and r.get('kind') == 'compression-shard': rows.append(r)
    groups = defaultdict(list)
    for r in rows: groups[r['dataset_id']].append(r)
    surveys = []
    for ds in manifest['datasets']:
        did = ds['id']
        if did not in em['datasets']: raise RuntimeError(('missing epsilon', did))
        surveys.append(collapse_dataset(ds, groups.get(did, []), em['datasets'][did], args.shard_count))
    if len(surveys) != 13: raise RuntimeError(('need 13 surveys', len(surveys)))
    h, gg = headline_from_surveys(surveys)
    out = {'benchmark': 'general-seismic-benchmark-v1', 'portfolio': 'general-seismic-codec-portfolio-v1',
           'execution': {'mode': 'deterministic-record-shards', 'shard_count_per_survey': int(args.shard_count)},
           'headline': h, 'groups': gg, 'surveys': sorted(surveys, key=lambda r: r['dataset_id'])}
    dump(out, args.out); print(json.dumps(out, indent=2)); return out


def selftest():
    row = {'selected': [{'objects': [{'bucket':'b','key':f'k{i}','size':n} for i,n in enumerate([1,2,3,4,5,6,7,8,9,10])]}]}
    ds = {'id':'x'}; seen=[]; total=0
    for i in range(4):
        q=shard_row(row,ds,i,4); rr=base.records(q); seen += [o['key'] for o in rr]; total += sum(o['size'] for o in rr)
    assert sorted(seen)==sorted(o['key'] for o in base.records(row)) and len(seen)==len(set(seen)) and total==55,(seen,total)
    a={'shard_index':0,'samples':2,'mean':1.5,'M2':0.5,'numeric_bytes':8,'panels':1,'seconds':1}
    b={'shard_index':1,'samples':2,'mean':3.5,'M2':0.5,'numeric_bytes':8,'panels':1,'seconds':1}
    m=merge_moments([a,b]); x=np.array([1.,2.,3.,4.]); assert m['samples']==4 and abs(m['mean']-x.mean())<1e-12 and abs(m['std']-x.std())<1e-12,m
    print(json.dumps({'shard_partition':'exact-once','moment_merge':'exact','merged':m},indent=2))


def common_survey_args(p):
    p.add_argument('--manifest',required=True);p.add_argument('--preflight',required=True);p.add_argument('--config',required=True);p.add_argument('--dataset',required=True)
    p.add_argument('--shard-index',type=int,required=True);p.add_argument('--shard-count',type=int,required=True);p.add_argument('--cube2mseed',default=os.environ.get('CUBE2MSEED'));p.add_argument('--out',required=True)


def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    common_survey_args(sub.add_parser('stats-shard'))
    s=sub.add_parser('aggregate-stats');s.add_argument('--results',required=True);s.add_argument('--datasets',default='');s.add_argument('--shard-count',type=int,required=True);s.add_argument('--out',required=True)
    common_survey_args(sub.add_parser('compress-shard'));sub.choices['compress-shard'].add_argument('--epsilon-map',required=True)
    a=sub.add_parser('aggregate-compression');a.add_argument('--manifest',required=True);a.add_argument('--epsilon-map',required=True);a.add_argument('--results',required=True);a.add_argument('--shard-count',type=int,required=True);a.add_argument('--out',required=True)
    sub.add_parser('selftest')
    args=ap.parse_args()
    if args.cmd=='stats-shard':run_stats_shard(args)
    elif args.cmd=='aggregate-stats':aggregate_stats(args)
    elif args.cmd=='compress-shard':run_compress_shard(args)
    elif args.cmd=='aggregate-compression':aggregate_compression(args)
    else:selftest()


if __name__=='__main__':main()
