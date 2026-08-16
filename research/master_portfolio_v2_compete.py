#!/usr/bin/env python3
"""Direct native-scope vs frozen-V1 competitions for Master Portfolio V2.

Recovered native engines do not replace V1 because a router predicts they will
be better. Both codecs encode the same complete numeric object at the identical
public epsilon, both decode and verify, and the contract-aware selector chooses
the smaller charged stream. Eligibility is structural; dataset labels never
participate in selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import master_portfolio_v2 as native
import marine_carrier_pr6_v2 as marine
from master_portfolio_v2_panel_fallback import (
    ACCOUNTING_ID,
    CONTRACT_ID,
    encode_decode_v1_fallback,
    numeric_object_id,
)
from master_portfolio_v2_selector import Candidate, dominance_report, select_smallest_valid


def _native_candidate(result, X, *, scope_rank=2):
    oid = numeric_object_id(np.asarray(X))
    return Candidate(
        engine=str(result["engine"]),
        object_id=oid,
        contract_id=CONTRACT_ID,
        accounting_id=ACCOUNTING_ID,
        stream_bytes=int(result["ours_bytes"]),
        max_abs_error=float(result["ours_maxerr"]),
        epsilon=float(result["epsilon"]),
        decode_verified=True,
        eligible=True,
        scope_rank=int(scope_rank),
        payload=result,
    )


def _result(c_native, c_v1, X, epsilon, object_kind, source_file, extra=None):
    if c_native.comparison_domain != c_v1.comparison_domain:
        raise RuntimeError(("native/V1 comparison-domain mismatch", c_native.comparison_domain, c_v1.comparison_domain))
    winner = select_smallest_valid([c_native, c_v1])
    result = {
        "kind": "master-portfolio-v2-native-vs-v1",
        "object_kind": object_kind,
        "source_file": Path(source_file).name,
        "shape": list(map(int, np.asarray(X).shape)),
        "object_id": c_native.object_id,
        "contract_id": CONTRACT_ID,
        "accounting_id": ACCOUNTING_ID,
        "epsilon": float(epsilon),
        "native_engine": c_native.engine,
        "native_bytes": c_native.stream_bytes,
        "v1_fallback_bytes": c_v1.stream_bytes,
        "native_gain_over_v1": float(c_v1.stream_bytes / c_native.stream_bytes),
        "winner": winner.engine,
        "winner_bytes": winner.stream_bytes,
        "native_is_no_regression": bool(c_native.stream_bytes <= c_v1.stream_bytes),
        "selected_is_no_worse_than_v1": bool(winner.stream_bytes <= c_v1.stream_bytes),
        "dominance": dominance_report([c_native, c_v1]),
        "v1_panels": c_v1.payload["panels"],
        "dataset_label_used_for_routing": False,
    }
    if extra:
        result.update(extra)
    return result


def compete_soda(path: str, epsilon: float):
    n = native.soda_ns()
    X, _, _, _ = n["load"](path)
    X = np.asarray(X, np.float32)
    r_native = native.soda_record_codec(path, float(epsilon))
    c_native = _native_candidate(r_native, X)
    c_v1, _ = encode_decode_v1_fallback(X, float(epsilon), source_integer=False)
    return _result(c_native, c_v1, X, epsilon, "segy_numeric_payload", path)


def compete_forge(path: str, epsilon: float | None):
    n = native.forge_ns()
    X, _, _, _, _, _, _ = n["load_segy"](path)
    X = np.asarray(X, np.float32)
    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    r_native = native.forge_whole_gather_codec(path, eps)
    c_native = _native_candidate(r_native, X)
    c_v1, _ = encode_decode_v1_fallback(X, eps, source_integer=False)
    return _result(c_native, c_v1, X, eps, "segy_numeric_payload", path)


def compete_marine(path: str, epsilon: float | None, channels: int = marine.DEFAULT_CHANNELS,
                   m_values=(16, 24, 32, 40, 48, 56, 64, 80, 96, 128)):
    """Race structurally eligible recovered PR6 carrier against frozen V1.

    Geometry is inferred from the SEG-Y itself; no known shot count or filename
    is supplied. The carrier's 64-byte stream contains the decoder-visible shape,
    epsilon and M, so its actual serialized size is fully charged.
    """
    X, geometry = marine.pr6_load_auto(path, channels=channels)
    X = np.asarray(X, np.float32)
    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    best, candidates = marine.compete(X, eps, m_values=m_values)
    if not best["valid"]:
        raise RuntimeError(("marine native invalid", best))

    oid = numeric_object_id(X)
    c_native = Candidate(
        engine="marine_anchor_carrier_pr6",
        object_id=oid,
        contract_id=CONTRACT_ID,
        accounting_id=ACCOUNTING_ID,
        stream_bytes=int(best["bytes"]),
        max_abs_error=float(best["max_abs_error"]),
        epsilon=eps,
        decode_verified=True,
        eligible=True,
        scope_rank=2,
        payload={
            "engine": "marine_anchor_carrier_pr6",
            "epsilon": eps,
            "ours_bytes": int(best["bytes"]),
            "ours_maxerr": float(best["max_abs_error"]),
            "best": best,
            "candidates": candidates,
            "geometry": geometry,
            "structural_eligibility": "fixed-length SEG-Y float32 traces, sample count consistent with file length, regular receiver grouping",
        },
    )
    c_v1, _ = encode_decode_v1_fallback(X, eps, source_integer=False)
    return _result(
        c_native, c_v1, X, eps, "segy_numeric_payload", path,
        extra={
            "marine_geometry": geometry,
            "marine_best_M": int(best["M"]),
            "marine_candidates": candidates,
            "eligibility_source": "SEG-Y structure only",
        },
    )


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("soda")
    s.add_argument("--file", required=True)
    s.add_argument("--epsilon", type=float, required=True)
    s.add_argument("--out", required=True)

    f = sub.add_parser("forge")
    f.add_argument("--file", required=True)
    f.add_argument("--epsilon", type=float)
    f.add_argument("--out", required=True)

    m = sub.add_parser("marine")
    m.add_argument("--file", required=True)
    m.add_argument("--epsilon", type=float)
    m.add_argument("--channels", type=int, default=marine.DEFAULT_CHANNELS)
    m.add_argument("--m-values", type=int, nargs="+", default=[16, 24, 32, 40, 48, 56, 64, 80, 96, 128])
    m.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "soda":
        result = compete_soda(args.file, args.epsilon)
    elif args.cmd == "forge":
        result = compete_forge(args.file, args.epsilon)
    else:
        result = compete_marine(args.file, args.epsilon, channels=args.channels, m_values=tuple(args.m_values))

    if not result["selected_is_no_worse_than_v1"]:
        raise RuntimeError(("V2 monotonicity violation", result))
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
