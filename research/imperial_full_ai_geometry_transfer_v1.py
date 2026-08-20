#!/usr/bin/env python3
"""Mechanism-preserving transfer of the migrated-volume learned probability engine to Imperial DAS.

This is deliberately NOT an Imperial-tuned model search. The learned base model,
normalization and boundary model are fitted only on Waka/Kahu/Opunake/Tui using
the same 320/240/160, 19-class, causal-scale feature stack that produced the
migrated-volume hard-case gains. Imperial is never used to choose weights,
normalization, feature thresholds, network size, learning rate or adaptation
cadence.

Two predeclared geometry interfaces are scored on the canonical stubborn
32x1024 Imperial tile:

  literal_single_row
      Treat DAS as a one-row native seismic volume. This preserves the exact
      migrated-volume predictor, quantizer, feature semantics and source-trained
      boundary MLP. It is the strictest "same implementation" transfer control.

  imperial_ar1_carrier
      Keep the established Imperial shared AR1/prefix64 deterministic carrier
      and step267 correction field, but expose that field to the SAME semantic
      learned probability mechanism. DAS has one spatial axis, so the source
      feature slots for the absent second spatial axis are explicitly zero/missing
      rather than filled with invented target-specific neighbors. The AR1 model
      is the ordinary charged per-file carrier; it does not train the AI.

For each interface we report pristine zero-shot probability rate and the same
1024-symbol charge-before-update full-model causal adaptation used by the
successful migrated-volume engine. Every target chunk is scored before its
symbols update the network. No result here is a serialized-rANS claim: this is
an ideal probability-rate transfer gate. A positive gate must later be
materialized with independent decoder-side probability regeneration.
"""
from __future__ import annotations

import argparse, copy, json, math
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn.functional as F

import boundary_waveform_probability_v1 as bw
import kahu_unseen_causal_scale_features_v1 as scale
import migrated_volume_multisource15_replay_loso_v1 as multi
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # noqa: F401; installs object-aware extractor
from general_seismic_numeric_io import matched_sz3

# Frozen Imperial benchmark identity / gate.
T0 = 14488
C0 = 512
C = 32
T = 1024
EPS = 133.69778037805762
IMPERIAL_CURRENT_BASELINE_BYTES = 22527  # exact PR #639 t1/train64 current-address stream
IMPERIAL_CURRENT_SZ3_BYTES = 26751       # exact canonical comparator with best CT/T orientation
AR_STEP = 267.0
AR_TRAIN = 64
AR_MODEL_BYTES = 10
HEADER_BYTES = 128

# Frozen learned-mechanism settings from the successful migrated-volume line.
SOURCE_FRACS = multi.SOURCE_FRACS
CHUNK = 1024
FULL_LR = 3e-4
WEIGHT_DECAY = 1e-5
FIRST_CHUNK_STEPS = 2
LATER_CHUNK_STEPS = 1
SEED = 20262020


def _cls(t):
    return q.b.cls(np.asarray(t, np.int32))


def _tail_bits(t):
    t = np.asarray(t, np.int32)
    return float(q.b.gamma_bits(np.maximum(np.abs(t) - q.b.LIM, 0)).sum())


def _static_boundary_bits(static, R, I):
    mask = np.zeros(R.shape, bool)
    for y, x, t in np.asarray(I):
        mask[int(y), int(x), int(t)] = True
    rb = np.asarray(R)[~mask]
    return float(static[_cls(rb)].sum() + q.b.gamma_bits(np.maximum(np.abs(rb) - q.b.LIM, 0)).sum())


def _fit_imperial_ar1(X):
    """Exact shared AR1+intercept fit rule used by the prefix64 Imperial carrier."""
    Z = np.asarray(X[:, :AR_TRAIN], np.float64)
    yy = Z[:, 1:].reshape(-1)
    A = np.empty((yy.size, 2), np.float64)
    A[:, 0] = Z[:, :-1].reshape(-1)
    A[:, 1] = 1.0
    return np.linalg.lstsq(A, yy, rcond=1e-8)[0].astype(np.float32)


def _build_imperial_ar1(X):
    X = np.asarray(X, np.float64)
    co = _fit_imperial_ar1(X)
    R = np.zeros(X.shape, np.int32)
    K = np.zeros(X.shape, np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            if t == 0:
                pred = 0
            else:
                pred = int(np.rint(float(co[0]) * float(R[c, t-1]) + float(co[1])))
            k = int(np.rint((float(X[c, t]) - pred) / AR_STEP))
            R[c, t] = pred + int(AR_STEP) * k
            K[c, t] = k
    me = float(np.max(np.abs(X - R.astype(np.float64))))
    if me > EPS * (1 + 5e-6):
        raise RuntimeError(('Imperial AR1 hard error', me, EPS))
    return R, K, co, me


def _lg(z):
    return np.log1p(np.asarray(z, np.float64)).astype(np.float32)


def _meanabs(z):
    return np.mean(np.abs(z), axis=1)


def _rms(z):
    return np.sqrt(np.mean(np.asarray(z, np.float64) ** 2, axis=1))


def _carrier_features(R, K):
    """Map a 1-D DAS carrier into the exact semantic feature layout of the source AI.

    The existing migrated model has two spatial axes. DAS has only one. We
    therefore preserve l/l2 (nearest and second-nearest already-decoded channel)
    and set u/ul to the explicit missing-axis zero state. This is equivalent to
    evaluating the source feature grammar on y=0 everywhere, not inventing a
    target-specific pseudo-axis.
    """
    S = np.asarray(R, np.float64) / AR_STEP
    K = np.asarray(K, np.int32)
    nc, nt = K.shape
    rad = q.b.RAD
    hist = q.b.HIST
    w = 2 * rad + 1
    Z = np.zeros(nt, np.float64)
    Zi = np.zeros(nt, np.int32)
    F, TT, IDX = [], [], []

    for c in range(1, nc):
        cur = S[c]
        cr = K[c]
        l = S[c-1]
        l2 = S[c-2] if c > 1 else l
        u = Z
        ul = Z
        lr = K[c-1]
        l2r = K[c-2] if c > 1 else lr
        ur = Zi
        ulr = Zi
        for t in range(14, nt-rad-1):
            f = []
            f.extend((cur[t-10:t] - cur[t-1]).tolist())
            for z in (l, l2, u, ul):
                f.extend((z[t-rad:t+rad+1] - z[t]).tolist())
            for z in (lr, l2r, ur, ulr):
                f.extend(np.asarray(z[t-rad:t+rad+1]).tolist())
            f.extend(cr[t-hist:t].tolist())
            f += [l[t], l2[t], u[t], ul[t], l[t]-l2[t], l[t]-u[t], cur[t-1]-l[t-1], cur[t-1]-u[t-1]]
            F.append(f)
            TT.append(int(cr[t]))
            IDX.append((0, c, t))

    A = np.asarray(F, np.float32)
    TT = np.asarray(TT, np.int32)
    I = np.asarray(IDX, np.int32)
    expected = 10 + 8*w + hist + 8
    if A.shape[1] != expected:
        raise RuntimeError(('carrier base feature drift', A.shape, expected))

    p = 0
    cur = A[:, p:p+10]; p += 10
    waves = [A[:, p+i*w:p+(i+1)*w] for i in range(4)]; p += 4*w
    res = [A[:, p+i*w:p+(i+1)*w] for i in range(4)]; p += 4*w
    crh = A[:, p:p+hist]; p += hist
    extra = [_lg(_meanabs(cur)), _lg(_rms(cur))]
    extra += [_lg(_rms(z)) for z in waves]
    extra += [_lg(_meanabs(z)) for z in res]
    extra += [_lg(_meanabs(crh)), _lg(_rms(crh))]
    E = np.stack(extra, axis=1).astype(np.float32)
    Cc = np.stack([
        np.zeros(len(I), np.float32),
        I[:, 1].astype(np.float32) / float(max(1, nc-1)),
        I[:, 2].astype(np.float32) / float(max(1, nt-1)),
    ], axis=1)
    return np.concatenate([A, E, Cc], axis=1), TT, I, K[None, :, :]


def _ood_stats(A, mu, sd):
    Z = (np.asarray(A, np.float32) - mu) / sd
    az = np.abs(Z.astype(np.float64))
    return {
        'mean_abs_source_z': float(az.mean()),
        'p99_abs_source_z': float(np.quantile(az, .99)),
        'fraction_abs_z_gt_5': float(np.mean(az > 5)),
        'fraction_abs_z_gt_10': float(np.mean(az > 10)),
        'max_abs_source_z': float(az.max()),
    }


def _score_pristine(net, mu, sd, static, A, TT, I, R, boundary_mode, extra_bytes=0):
    Xn = torch.from_numpy(((A-mu)/sd).astype(np.float32))
    Y = torch.from_numpy(_cls(TT))
    bits = 0.0
    net.eval()
    with torch.no_grad():
        for s in range(0, len(Xn), 16384):
            xx = Xn[s:s+16384]; yy = Y[s:s+16384]
            lp = F.log_softmax(net(xx), 1) / math.log(2)
            bits += float((-lp[torch.arange(len(yy)), yy]).sum())
    bits += _tail_bits(TT)
    if boundary_mode == 'source_boundary_mlp':
        bits += float(q.boundary_bits(static, R, I))
    elif boundary_mode == 'source_static':
        bits += _static_boundary_bits(static, R, I)
    else:
        raise ValueError(boundary_mode)
    total = int(math.ceil(bits / 8.0)) + HEADER_BYTES + int(extra_bytes)
    return bits, total


def _score_causal_adapt(net0, mu, sd, static, A, TT, I, R, boundary_mode, extra_bytes=0):
    net = copy.deepcopy(net0)
    for p in net.parameters():
        p.requires_grad_(True)
    opt = torch.optim.AdamW(net.parameters(), lr=FULL_LR, weight_decay=WEIGHT_DECAY)
    Xn = torch.from_numpy(((A-mu)/sd).astype(np.float32))
    Y = torch.from_numpy(_cls(TT))
    bits = 0.0
    chunk_bps = []
    for ci, s in enumerate(range(0, len(Xn), CHUNK)):
        e = min(len(Xn), s+CHUNK); xx = Xn[s:e]; yy = Y[s:e]
        net.eval()
        with torch.no_grad():
            lp = F.log_softmax(net(xx), 1) / math.log(2)
            cb = float((-lp[torch.arange(len(yy)), yy]).sum())
        bits += cb
        chunk_bps.append(cb / max(1, len(yy)))
        steps = FIRST_CHUNK_STEPS if ci == 0 else LATER_CHUNK_STEPS
        net.train()
        for _ in range(steps):
            opt.zero_grad(set_to_none=True)
            loss = F.cross_entropy(net(xx), yy)
            loss.backward(); opt.step()
    bits += _tail_bits(TT)
    if boundary_mode == 'source_boundary_mlp':
        bits += float(q.boundary_bits(static, R, I))
    else:
        bits += _static_boundary_bits(static, R, I)
    total = int(math.ceil(bits / 8.0)) + HEADER_BYTES + int(extra_bytes)
    return bits, total, chunk_bps


def _row(name, A, TT, I, R, net, mu, sd, static, sz3_bytes, boundary_mode, extra_bytes=0, carrier_meta=None):
    pb, pbytes = _score_pristine(net, mu, sd, static, A, TT, I, R, boundary_mode, extra_bytes)
    ab, abytes, chunks = _score_causal_adapt(net, mu, sd, static, A, TT, I, R, boundary_mode, extra_bytes)
    samples = C*T
    row = {
        'interface': name,
        'feature_dim': int(A.shape[1]),
        'modeled_symbols': int(len(TT)),
        'modeled_fraction': float(len(TT)/samples),
        'residual_zero_fraction': float(np.mean(np.asarray(R) == 0)),
        'residual_std': float(np.asarray(R).std()),
        'residual_tail_fraction_abs_gt_8': float(np.mean(np.abs(np.asarray(R)) > q.b.LIM)),
        'boundary_mode': boundary_mode,
        'extra_carrier_bytes': int(extra_bytes),
        'zero_shot_ideal_bits': float(pb),
        'zero_shot_ideal_bytes_plus_overhead': int(pbytes),
        'zero_shot_ideal_bps': float(8*pbytes/samples),
        'zero_shot_gain_vs_sz3': float(sz3_bytes/pbytes),
        'causal_adapt_ideal_bits': float(ab),
        'causal_adapt_ideal_bytes_plus_overhead': int(abytes),
        'causal_adapt_ideal_bps': float(8*abytes/samples),
        'causal_adapt_gain_vs_sz3': float(sz3_bytes/abytes),
        'causal_adapt_gain_vs_current_imperial_baseline': float(IMPERIAL_CURRENT_BASELINE_BYTES/abytes),
        'modeled_chunk_bps_first': float(chunks[0]) if chunks else None,
        'modeled_chunk_bps_last': float(chunks[-1]) if chunks else None,
        'adaptation_improves_total': bool(abytes < pbytes),
        'ood_vs_source_normalization': _ood_stats(A, mu, sd),
    }
    if carrier_meta:
        row.update(carrier_meta)
    return row


def _canonical_sz3(X):
    """Reproduce the Imperial comparator: float32 and best of CT/T orientation."""
    best = None
    for name, A in (('CT', np.ascontiguousarray(X.astype(np.float32))), ('T', np.ascontiguousarray(X.T.astype(np.float32)))):
        b, me = matched_sz3(A, EPS)
        row = (int(b), name, float(me))
        if best is None or row[0] < best[0]:
            best = row
    return best


def main(a):
    # Install the winning causal-scale+y/x/t source feature grammar, then train
    # the source-only boundary MLP around the same source residuals.
    q.b.build = scale.build_with_scale_yxt
    bw.install(multi)

    manifest = json.load(open(a.manifest))
    epsj = json.load(open(a.eps))
    source = []
    source_meta = []
    for ds in q.SURVEYS:
        for frac in SOURCE_FRACS:
            X, ep, md = q.b.extract(ds, manifest, epsj, frac)
            X = q.crop(X)
            source.append((X, ep))
            source_meta.append({'dataset': ds, 'fraction': float(frac), 'shape': list(map(int, X.shape)), 'trace_first': md.get('trace_first')})
            print('IMPERIAL_AI_SOURCE', ds, frac, X.shape, flush=True)

    # Same AI architecture/training mechanism; broader source-only pretraining is
    # legitimate here because Imperial is outside all four source surveys.
    net, mu, sd, static = multi.wide_fit(source, SEED)
    print('IMPERIAL_AI_SOURCE_READY', {'feature_dim': len(mu), 'source_tiles': len(source)}, flush=True)

    with h5py.File(a.imperial, 'r') as f:
        Ximp = np.asarray(f['Acoustic'][T0:T0+T, C0:C0+C], np.float64).T
    if Ximp.shape != (C, T):
        raise RuntimeError(('Imperial shape', Ximp.shape))
    sz3_bytes, sz3_orientation, sz3_me = _canonical_sz3(Ximp)
    if int(sz3_bytes) != IMPERIAL_CURRENT_SZ3_BYTES:
        raise RuntimeError(('SZ3 benchmark drift', sz3_bytes, IMPERIAL_CURRENT_SZ3_BYTES, sz3_orientation))

    rows = []

    # A: exact migrated implementation on a one-row geometry.
    Al, Tl, Il, Rl = scale.build_with_scale_yxt(Ximp[None, :, :], EPS)
    rows.append(_row(
        'literal_single_row', Al, Tl, Il, Rl, net, mu, sd, static, sz3_bytes,
        boundary_mode='source_boundary_mlp', extra_bytes=0,
        carrier_meta={
            'predictor': 'exact migrated-volume causal predictor on ny=1',
            'predictor_fit_on_imperial': False,
            'second_spatial_axis': 'absent (native ny=1 boundary semantics)',
        }
    ))
    print('IMPERIAL_AI_LITERAL', json.dumps(rows[-1]), flush=True)

    # B: target-appropriate deterministic carrier, same learned probability law.
    Rar, Kar, co, me = _build_imperial_ar1(Ximp)
    Ac, Tc, Ic, Rc = _carrier_features(Rar, Kar)
    if Ac.shape[1] != len(mu):
        raise RuntimeError(('feature dimension mismatch', Ac.shape[1], len(mu)))
    rows.append(_row(
        'imperial_ar1_carrier', Ac, Tc, Ic, Rc, net, mu, sd, static, sz3_bytes,
        boundary_mode='source_static', extra_bytes=AR_MODEL_BYTES,
        carrier_meta={
            'predictor': 'Imperial shared AR1 + intercept, prefix64, step267',
            'predictor_fit_on_imperial': True,
            'predictor_fit_scope': 'first 64 samples only; coefficients charged as carrier bytes; AI remains source-only',
            'predictor_coefficients_float32': [float(x) for x in co],
            'predictor_max_error': float(me),
            'second_spatial_axis': 'explicit missing-axis zeros; no invented pseudo-neighbors',
        }
    ))
    print('IMPERIAL_AI_CARRIER', json.dumps(rows[-1]), flush=True)

    out = {
        'kind': 'imperial-full-ai-geometry-transfer-v1',
        'status': 'ideal_probability_rate_transfer_gate_not_serialized_codec',
        'imperial_used_in_base_ai_training_or_normalization': False,
        'source_ai_weights_charged_per_file_bytes': 0,
        'installed_universal_model_assumption': True,
        'source_surveys': list(q.SURVEYS),
        'source_training_fractions': list(map(float, SOURCE_FRACS)),
        'source_training_tiles': len(source),
        'source_feature_model': 'causal scale/roughness + y/x/t, 320/240/160, 19 classes',
        'source_training_epochs': multi.EPOCHS,
        'adaptation_chunk': CHUNK,
        'target_chunks_charged_before_update': True,
        'target_adaptation_rule_changed_for_imperial': False,
        'geometry_adapter_selected_using_imperial_scores': False,
        'imperial': {
            'dataset': 'Imperial Valley continuous DAS',
            'region': 'canonical stubborn hard mini-tile',
            'shape': [C, T],
            't0': T0,
            'c0': C0,
            'epsilon': EPS,
            'matched_sz3_bytes': int(sz3_bytes),
            'matched_sz3_orientation': sz3_orientation,
            'matched_sz3_maxerr': float(sz3_me),
            'current_exact_baseline_bytes': IMPERIAL_CURRENT_BASELINE_BYTES,
        },
        'rows': rows,
        'source_meta': source_meta,
        'interpretation_rule': (
            'literal_single_row asks whether the exact migrated implementation transfers. '
            'imperial_ar1_carrier asks the user-specified stronger question: keep the same learned residual-probability mechanism but express it through the native DAS carrier/geometry without target-tuning the AI. '
            'Do not choose between adapters post hoc as a generalization claim. A positive ideal-rate result requires a later finite-CDF independent-decoder byte-stream gate.'
        ),
    }
    Path(a.out).write_text(json.dumps(out, indent=2))
    print('IMPERIAL_FULL_AI_TRANSFER_FINAL', json.dumps({k:v for k,v in out.items() if k != 'source_meta'}, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--eps', required=True)
    p.add_argument('--imperial', required=True)
    p.add_argument('--out', required=True)
    main(p.parse_args())
