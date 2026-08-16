#!/usr/bin/env python3
"""Object-scope adapter for the frozen General Seismic Portfolio V1.

V2 native record/file engines must never lose merely because the fallback was
forgotten, and the fallback must never win through heuristic prediction.  This
module executes the exact frozen V1 panel codec over *all* samples of one
numeric object, decodes every charged panel stream, reconstructs the complete
numeric payload, and exposes the aggregate as a contract-aware V2 Candidate.

No survey labels are inspected.  All leading dimensions are preserved in C
order and treated as logical trace/channel order; only the final dimension is
time.  The V1 frozen 128 x 8192 partition is deterministic and therefore needs
no additional aggregate manifest under the numeric-payload/shared-file-metadata
comparison contract.  Each V1 panel stream already includes its charged
one-byte codec selector.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

import numpy as np

import general_seismic_codec_portfolio as v1
from master_portfolio_v2_selector import Candidate, select_smallest_valid

CONFIG = Path("benchmarks/general_seismic_codec_portfolio_v1.json")
CONTRACT_ID = "numeric_payload"
ACCOUNTING_ID = "numeric_samples_only_shared_file_metadata_excluded"
CHANNELS_PER_PANEL = 128
TIME_PER_PANEL = 8192


def load_config():
    cfg = json.loads(CONFIG.read_text())
    pc = cfg.get("panel_contract", {})
    if int(pc.get("channels_per_panel", -1)) != CHANNELS_PER_PANEL:
        raise RuntimeError("V1 channel partition drift")
    if int(pc.get("time_samples_per_panel", -1)) != TIME_PER_PANEL:
        raise RuntimeError("V1 time partition drift")
    if int(pc.get("selector_bytes", -1)) != 1:
        raise RuntimeError("V1 selector accounting drift")
    return cfg


def numeric_object_id(X: np.ndarray) -> str:
    """Content identity for exactly the numeric object being compared.

    Shape and dtype are hashed before bytes, so a reshape/reinterpretation can
    never accidentally enter the same comparison domain.
    """
    A = np.ascontiguousarray(X)
    h = hashlib.sha256()
    h.update(b"MASTER_PORTFOLIO_V2_NUMERIC_OBJECT_V1\0")
    ds = A.dtype.str.encode("ascii")
    h.update(struct.pack("<I", len(ds)))
    h.update(ds)
    h.update(struct.pack("<I", A.ndim))
    for d in A.shape:
        h.update(struct.pack("<Q", int(d)))
    h.update(memoryview(A).cast("B"))
    return "sha256:" + h.hexdigest()


def _as_trace_time(X):
    A = np.asarray(X)
    if A.ndim == 0:
        raise ValueError("scalar is not a seismic numeric object")
    if A.ndim == 1:
        return A.reshape(1, A.shape[0])
    return A.reshape(int(np.prod(A.shape[:-1], dtype=np.int64)), int(A.shape[-1]))


def encode_decode_v1_fallback(X, epsilon: float, *, source_integer: bool | None = None):
    A = np.asarray(X)
    TT = _as_trace_time(A)
    eps = float(epsilon)
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError(("bad epsilon", eps))
    if source_integer is None:
        source_integer = bool(np.issubdtype(A.dtype, np.integer))

    cfg = load_config()
    R = np.empty(TT.shape, dtype=np.float64)
    rows = []
    total = 0

    for c0 in range(0, TT.shape[0], CHANNELS_PER_PANEL):
        c1 = min(c0 + CHANNELS_PER_PANEL, TT.shape[0])
        for t0 in range(0, TT.shape[1], TIME_PER_PANEL):
            t1 = min(t0 + TIME_PER_PANEL, TT.shape[1])
            P = np.ascontiguousarray(TT[c0:c1, t0:t1])
            blob, meta = v1.encode_portfolio(P, eps, cfg, bool(source_integer))
            decoded = np.asarray(v1.decode_portfolio(blob), dtype=np.float64)
            if decoded.shape != P.shape:
                raise RuntimeError(("V1 fallback decoded shape drift", decoded.shape, P.shape))
            me = float(np.max(np.abs(P.astype(np.float64) - decoded))) if P.size else 0.0
            if me > eps * (1.0 + 3e-6):
                raise RuntimeError(("V1 fallback panel hard error", c0, t0, me, eps))
            R[c0:c1, t0:t1] = decoded
            n = len(blob)
            total += n
            rows.append({
                "channel_range": [int(c0), int(c1)],
                "time_range": [int(t0), int(t1)],
                "shape": list(map(int, P.shape)),
                "stream_bytes": int(n),
                "max_abs_error": me,
                "selected_id": int(meta["selected_id"]),
                "selected_engine": str(meta["selected_engine"]),
            })

    whole_err = float(np.max(np.abs(TT.astype(np.float64) - R))) if TT.size else 0.0
    if whole_err > eps * (1.0 + 3e-6):
        raise RuntimeError(("V1 fallback object hard error", whole_err, eps))

    oid = numeric_object_id(A)
    candidate = Candidate(
        engine="general_seismic_portfolio_v1_panel_fallback",
        object_id=oid,
        contract_id=CONTRACT_ID,
        accounting_id=ACCOUNTING_ID,
        stream_bytes=int(total),
        max_abs_error=whole_err,
        epsilon=eps,
        decode_verified=True,
        eligible=True,
        scope_rank=1,
        payload={
            "original_shape": list(map(int, A.shape)),
            "trace_time_shape": list(map(int, TT.shape)),
            "panels": rows,
            "source_integer": bool(source_integer),
            "aggregate_manifest_bytes": 0,
            "reason_manifest_is_zero": "object shape and deterministic 128x8192 partition are shared decoder-visible metadata under this comparison contract; each panel stream charges its one-byte V1 selector",
        },
    )
    return candidate, R.reshape(A.shape)


def _self_test():
    # Fixed synthetic signal, not benchmark-answer hardcoding.  It exercises
    # panel encode, serialized decode, aggregate reconstruction and selector
    # contract compatibility.
    rng = np.random.default_rng(20260815)
    t = np.arange(96, dtype=np.float32)
    X = np.stack([
        np.sin(np.float32(0.03 + 0.001 * c) * t) + np.float32(0.02) * rng.standard_normal(t.size).astype(np.float32)
        for c in range(12)
    ]).astype(np.float32)
    eps = float(0.10 * X.astype(np.float64).std())
    fallback, R = encode_decode_v1_fallback(X, eps)
    assert fallback.decode_verified
    assert fallback.stream_bytes > 0
    assert fallback.max_abs_error <= eps * (1.0 + 3e-6)
    assert np.max(np.abs(X.astype(np.float64) - R.astype(np.float64))) <= eps * (1.0 + 3e-6)

    # A native engine represented in exactly the same fairness domain can race
    # the fallback solely on actual bytes.
    native = Candidate(
        engine="synthetic_native_scope_probe",
        object_id=fallback.object_id,
        contract_id=fallback.contract_id,
        accounting_id=fallback.accounting_id,
        stream_bytes=fallback.stream_bytes + 7,
        max_abs_error=eps,
        epsilon=eps,
        decode_verified=True,
        scope_rank=2,
    )
    assert select_smallest_valid([native, fallback]).engine == fallback.engine
    print(json.dumps({
        "ok": True,
        "fallback_bytes": fallback.stream_bytes,
        "panels": len(fallback.payload["panels"]),
        "max_abs_error": fallback.max_abs_error,
        "epsilon": eps,
        "object_id": fallback.object_id,
    }, indent=2))


if __name__ == "__main__":
    _self_test()
