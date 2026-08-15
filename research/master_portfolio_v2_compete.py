#!/usr/bin/env python3
"""Direct native-scope vs frozen-V1 competitions for Master Portfolio V2.

This is the executable monotonicity bridge.  A recovered native engine does not
replace V1 because a router predicts it will be better.  Both codecs encode the
same complete numeric object at the identical public epsilon, both decode and
verify, and the contract-aware selector chooses the smaller charged stream.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import master_portfolio_v2 as native
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


def compete_soda(path: str, epsilon: float):
    n = native.soda_ns()
    X, _, _, _ = n["load"](path)
    X = np.asarray(X, np.float32)
    r_native = native.soda_record_codec(path, float(epsilon))
    c_native = _native_candidate(r_native, X)
    c_v1, _ = encode_decode_v1_fallback(X, float(epsilon), source_integer=False)

    if c_native.comparison_domain != c_v1.comparison_domain:
        raise RuntimeError(("Soda native/V1 comparison-domain mismatch", c_native.comparison_domain, c_v1.comparison_domain))
    winner = select_smallest_valid([c_native, c_v1])
    return {
        "kind": "master-portfolio-v2-native-vs-v1",
        "object_kind": "segy_numeric_payload",
        "source_file": Path(path).name,
        "shape": list(map(int, X.shape)),
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
    }


def compete_forge(path: str, epsilon: float | None):
    n = native.forge_ns()
    X, _, _, _, _, _, _ = n["load_segy"](path)
    X = np.asarray(X, np.float32)
    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    r_native = native.forge_whole_gather_codec(path, eps)
    c_native = _native_candidate(r_native, X)
    c_v1, _ = encode_decode_v1_fallback(X, eps, source_integer=False)

    if c_native.comparison_domain != c_v1.comparison_domain:
        raise RuntimeError(("FORGE native/V1 comparison-domain mismatch", c_native.comparison_domain, c_v1.comparison_domain))
    winner = select_smallest_valid([c_native, c_v1])
    return {
        "kind": "master-portfolio-v2-native-vs-v1",
        "object_kind": "segy_numeric_payload",
        "source_file": Path(path).name,
        "shape": list(map(int, X.shape)),
        "object_id": c_native.object_id,
        "contract_id": CONTRACT_ID,
        "accounting_id": ACCOUNTING_ID,
        "epsilon": eps,
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
    }


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
    args = ap.parse_args()

    result = compete_soda(args.file, args.epsilon) if args.cmd == "soda" else compete_forge(args.file, args.epsilon)
    if not result["selected_is_no_worse_than_v1"]:
        raise RuntimeError(("V2 monotonicity violation", result))
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
