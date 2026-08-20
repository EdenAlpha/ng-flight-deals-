#!/usr/bin/env python3
"""Test the marine-discovered residual-roughness mechanism on stubborn Imperial DAS.

This is deliberately a strict transfer gate.  The Imperial predictor, quantizer,
error tolerance, residual K field, model bytes, container and bitplane arithmetic
coder are frozen to the current PR #639 t1/train64 baseline.  We add only a few
public decoder-known context families that summarize *coarse residual roughness*
from already decoded higher K bitplanes and causal neighbors.  No neural model,
no Imperial-trained probability table, and no extra side model is transmitted.

If the exact materialized K stream gets smaller, the same residual-roughness
mechanism discovered by the marine/Kahu neural probe has transferred to land DAS
in a real decoder-reproducible byte stream.
"""
from __future__ import annotations
import json, sys
import h5py
import numpy as np

import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_wave_stencil_current_address as wave
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A = cm.a
ROUGH = (
    'rough_t4',
    'rough_cross',
    'prefix_rough_t4',
    'prefix_rough_cross',
    'tc_rough_t4',
    'tc_rough_cross',
    'cp2_rough_t4',
    'cp2_rough_cross',
)


def _pfx(known, bit, c, t, shift_extra=0):
    if c < 0 or t < 0 or c >= known.shape[0] or t >= known.shape[1]:
        return 0
    return int(known[c, t] >> (bit + 1 + shift_extra))


def _bucket(vals):
    # Zig-zag residual prefixes are approximately proportional to |K|.  A
    # log2 bucket makes the context scale-free in integer residual units.
    if not vals:
        return 0
    v = (sum(int(x) for x in vals) + len(vals)//2) // len(vals)
    return min(7, int(v).bit_length())


def _rough_t4(known, bit, c, t, shift_extra=0):
    return _bucket([_pfx(known, bit, c, t-j, shift_extra) for j in range(1, 5)])


def _rough_cross(known, bit, c, t, shift_extra=0):
    # Current-time left neighbor plus the previous-time local spatial stencil.
    # All values are already decoder-known at the current bitplane.
    return _bucket([
        _pfx(known, bit, c-1, t, shift_extra),
        _pfx(known, bit, c,   t-1, shift_extra),
        _pfx(known, bit, c-1, t-1, shift_extra),
        _pfx(known, bit, c+1, t-1, shift_extra),
    ])


def install_roughness_contexts():
    old_adapt = tuple(A.ADAPT)
    old_key = A.akey
    A.ADAPT = old_adapt + ROUGH

    def key(known, B, bit, c, t, fam):
        if fam not in ROUGH:
            return old_key(known, B, bit, c, t, fam)
        prefix = int(known[c, t] >> (bit + 1))
        pt = int(B[c, t-1]) if t > 0 else 2
        pc = int(B[c-1, t]) if c > 0 else 2
        if fam.endswith('rough_t4'):
            r = _rough_t4(known, bit, c, t, 2 if fam.startswith('cp2_') else 0)
        else:
            r = _rough_cross(known, bit, c, t, 2 if fam.startswith('cp2_') else 0)
        if fam.startswith('prefix_'):
            return (prefix, r)
        if fam.startswith('tc_'):
            return (pt, pc, r)
        if fam.startswith('cp2_'):
            cp2 = int(known[c, t] >> (bit + 3))
            return (cp2, r)
        return r

    A.akey = key
    return old_adapt


def summarize(detail):
    selected = []
    for row in detail:
        fam = str(row.get('family', ''))
        if any(x in fam for x in ROUGH):
            selected.append({k: row.get(k) for k in ('bit','kind','family','groups','arith_bytes','arith_bits','stored','ones') if k in row})
    return selected


def main(path):
    with h5py.File(path, 'r') as f:
        ds = f['Acoustic']
        _, std = m.stats(ds)
        eps = .1 * std
        X = np.asarray(ds[g.T0:g.T0+g.T, g.C0:g.C0+g.C], np.float64).T

    szb, ori = m.szrun(X, eps)

    # Freeze the exact PR #639 incumbent predictor and K field.
    co = np.asarray(fair.fit(X, 1, 'prefix64'), np.float32)
    model_buf, model_rep, cod = wave.model_rt(co)
    R, K = wave.build(X, cod, wave.CONFIGS['t1'])
    me0 = float(np.max(np.abs(X - R.astype(np.float64))))
    if me0 > eps * (1 + 5e-6):
        raise RuntimeError(('baseline hard error', me0, eps))

    # Exact current address, before any new roughness family exists.
    base_field, _, K0, base_detail = A.hybrid_frame(K)
    if not np.array_equal(K0, K):
        raise RuntimeError('baseline K replay')
    base_total = fair.COMMON_HEADER + 1 + len(model_buf) + int(base_field)

    prior_families = install_roughness_contexts()

    # Same K field; only the address grammar has gained roughness contexts.
    rough_field, _, K1, rough_detail = A.hybrid_frame(K)
    if not np.array_equal(K1, K):
        raise RuntimeError('rough K replay')
    R1, me1 = wave.replay(X, cod, wave.CONFIGS['t1'], K1, eps)
    if not np.array_equal(R1, R):
        raise RuntimeError('rough reconstruction drift')
    rough_total = fair.COMMON_HEADER + 1 + len(model_buf) + int(rough_field)
    selected = summarize(rough_detail)

    out = {
        'kind': 'imperial-roughness-context-transfer-v1',
        'dataset': 'Imperial Valley continuous DAS',
        'region': 'canonical stubborn hard mini-tile',
        'shape': list(map(int, X.shape)),
        'samples': int(X.size),
        'global_std': float(std),
        'epsilon': float(eps),
        'step': int(wave.STEP),
        'predictor': 'frozen PR639 t1/train64',
        'predictor_changed': False,
        'residual_k_field_changed': False,
        'neural_network_used': False,
        'imperial_probability_training_used': False,
        'roughness_side_model_bytes': 0,
        'roughness_contexts': list(ROUGH),
        'prior_context_family_count': len(prior_families),
        'new_context_family_count': len(A.ADAPT),
        'model_bytes': len(model_buf),
        'model_rep': model_rep,
        'baseline': {
            'field_bytes': int(base_field),
            'total_bytes': int(base_total),
            'bps': float(8 * base_total / X.size),
            'max_error': me0,
        },
        'roughness': {
            'field_bytes': int(rough_field),
            'total_bytes': int(rough_total),
            'bps': float(8 * rough_total / X.size),
            'max_error': float(me1),
            'delta_bytes_vs_baseline': int(rough_total - base_total),
            'gain_vs_baseline': float(base_total / rough_total),
            'roughness_family_selected_on_any_plane': bool(selected),
            'selected_roughness_planes': selected,
        },
        'sz3': {
            'bytes': int(szb),
            'bps': float(8 * szb / X.size),
            'orientation': ori,
            'baseline_gain_vs_sz3': float(szb / base_total),
            'roughness_gain_vs_sz3': float(szb / rough_total),
        },
        'interpretation': (
            'Strict mechanism-transfer gate. The exact Imperial predictor, quantizer, K residual field, '
            'hard-error contract and container are unchanged. The only new option is a public logarithmic '
            'bucket of decoder-known coarse residual magnitude/roughness from causal temporal/spatial neighbors. '
            'A physical byte reduction with a selected roughness family is direct evidence that the residual-roughness '
            'mechanism discovered by the marine neural probe transfers to land DAS. A null result rejects this '
            'particular bitplane realization, not the broader roughness hypothesis.'
        ),
    }
    with open('imperial_roughness_context_transfer_v1.json', 'w') as f:
        json.dump(out, f, indent=2)
    print('IMPERIAL_ROUGHNESS_TRANSFER_FINAL', json.dumps(out, indent=2), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
