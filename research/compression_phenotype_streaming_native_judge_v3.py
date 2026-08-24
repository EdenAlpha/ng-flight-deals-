#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os


def load(p):
    with open(p) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--predictions', required=True)
    ap.add_argument('--bakeoff', required=True)
    ap.add_argument('--streaming', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    pred = load(a.predictions)
    bake = load(a.bakeoff)
    pmap = {x['target']: x for x in pred['predictions']}
    bmap = {(x['dataset_id'], x['logical_file']): x for x in bake['files']}

    stream_rows = []
    for fn in glob.glob(os.path.join(a.streaming, '**', '*.json'), recursive=True):
        try:
            r = load(fn)
        except Exception:
            continue
        if isinstance(r, dict) and r.get('kind') == 'native-streaming-large-file-validation-v1':
            stream_rows.append(r)

    results = []
    for ds in sorted(stream_rows, key=lambda x: x['dataset_id']):
        did = ds['dataset_id']
        pp = pmap.get(did, {})
        engine_family = pp.get('predicted_engine_family')
        if engine_family == 'soda_or_forge_lattice':
            predicted_engines = {'soda_record_run_lattice_pr169', 'forge_wholefile_lattice_pr203'}
        elif engine_family:
            predicted_engines = {engine_family}
        else:
            predicted_engines = set()

        files = []
        total_sz3 = 0
        predicted_bytes = 0
        predicted_eligible = 0
        for f in ds.get('files', []):
            prior = bmap.get((did, f['logical_file']))
            sz3 = int(prior['sz3_bytes']) if prior else 0
            total_sz3 += sz3
            trials = []
            valid_pred = []
            for t in f.get('native_trials', []):
                q = dict(t)
                if t.get('status') == 'valid' and sz3 > 0:
                    q['gain_vs_sz3'] = float(sz3 / int(t['bytes']))
                else:
                    q['gain_vs_sz3'] = None
                q['is_predicted_family'] = t.get('engine') in predicted_engines
                if q['is_predicted_family'] and t.get('status') == 'valid':
                    valid_pred.append(q)
                trials.append(q)
            chosen = min(valid_pred, key=lambda x: (x['bytes'], x['engine'])) if valid_pred else None
            if chosen:
                predicted_eligible += 1
                predicted_bytes += int(chosen['bytes'])
            files.append({
                'logical_file': f['logical_file'],
                'source_bytes': f.get('source_bytes'),
                'sz3_bytes': sz3,
                'predicted_candidate': chosen,
                'native_trials': trials,
            })

        agg_gain = (float(total_sz3 / predicted_bytes)
                    if predicted_bytes > 0 and predicted_eligible == len(files) else None)
        results.append({
            'target': did,
            'predicted_family': pp.get('predicted_family'),
            'predicted_engine_family': engine_family,
            'predicted_native_engines': sorted(predicted_engines),
            'files': files,
            'predicted_engine_eligible_files': predicted_eligible,
            'file_count': len(files),
            'aggregate_predicted_gain_vs_sz3': agg_gain,
            'aggregate_crosses_2x': bool(agg_gain is not None and agg_gain >= 2.0),
        })

    out = {
        'kind': 'seismic-compression-phenotype-streaming-native-validation-v3',
        'predictions_frozen_before_streaming_test': True,
        'same_prior_matched_sz3_bytes': True,
        'results': results,
    }
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
