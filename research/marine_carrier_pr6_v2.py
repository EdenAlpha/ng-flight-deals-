#!/usr/bin/env python3
"""Recover the buried PR #6 marine carrier/certificate lineage for V2.

Historical PR #6 counted zlib(anchor)+zlib(correction)+64 bytes but reconstructed
from encoder-side arrays. This module preserves that exact 64-byte accounting
while making those 64 bytes a real header and requiring reconstruction from the
serialized stream itself.

No dataset label participates in codec selection. M is decoder-visible and can
be competed over a fixed candidate menu; exact valid stream bytes decide.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import struct
import zlib

import numpy as np
from pysz import sz, szConfig, szErrorBoundMode

MAGIC = b"MCRPR6V2"
VERSION = 1
# 8s magic, H version, H flags, I shots, I channels, I samples, d epsilon,
# I M, I anchor-zlib bytes, I correction-zlib bytes, 20 reserved = exactly 64.
HEADER = struct.Struct("<8sHHIIIdIII20s")
assert HEADER.size == 64


def pr6_load_exact(path: str, shots: int):
    """Exact numeric loader used by historical PR #6, with ns inferred.

    PR #6's public marine files are simple 3600-byte SEG-Y global header +
    repeated 240-byte trace header + little-endian IEEE float32 samples. The
    number of shots is supplied by the benchmark fixture; the codec itself does
    not encode or route by this label.
    """
    size = os.path.getsize(path)
    ntr = int(shots) * 48
    if ntr <= 0 or (size - 3600) % ntr:
        raise ValueError(("incompatible PR6 fixture geometry", path, size, shots))
    stride = (size - 3600) // ntr
    if stride <= 240 or (stride - 240) % 4:
        raise ValueError(("incompatible trace stride", stride))
    ns = (stride - 240) // 4
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    X = np.ndarray(
        (ntr, ns),
        dtype="<f4",
        buffer=mm,
        offset=3600 + 240,
        strides=(stride, 4),
    ).copy().reshape(int(shots), 48, ns)
    if not np.isfinite(X).all():
        raise ValueError("non-finite samples")
    return X


def _indices(ns: int, M: int):
    if M <= 0:
        raise ValueError(M)
    idx = np.arange(0, ns, M, dtype=np.int32)
    if idx.size == 0 or idx[-1] != ns - 1:
        idx = np.r_[idx, ns - 1]
    return idx


def _carrier_from_anchors(A: np.ndarray, ns: int, M: int, eps: float):
    idx = _indices(ns, M)
    if A.shape[-1] != len(idx):
        raise ValueError((A.shape, len(idx)))
    Ad = A.astype(np.float32) * np.float32(eps)
    P = np.empty(A.shape[:2] + (ns,), dtype=np.float32)
    for j in range(len(idx) - 1):
        a, b = int(idx[j]), int(idx[j + 1])
        L = b - a
        u = np.arange(L, dtype=np.float32) / L
        P[:, :, a:b] = (
            Ad[:, :, j, None] * (1 - u)[None, None, :]
            + Ad[:, :, j + 1, None] * u[None, None, :]
        )
    P[:, :, -1] = Ad[:, :, -1]
    return P


def encode_array(X: np.ndarray, eps: float, M: int) -> bytes:
    X = np.ascontiguousarray(X, dtype=np.float32)
    if X.ndim != 3:
        raise ValueError(("expected shot,channel,time", X.shape))
    shots, channels, ns = map(int, X.shape)
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError(eps)

    idx = _indices(ns, M)
    # Preserve PR6's exact float32 / int16 arithmetic path.
    A = np.rint(X[:, :, idx] / eps).astype("<i2")
    P = _carrier_from_anchors(A, ns, M, eps)
    C = np.rint((X - P) / (2 * eps)).astype("<i2")
    K = np.empty_like(C, dtype="<i2")
    K[:, :, 0] = C[:, :, 0]
    K[:, :, 1:] = C[:, :, 1:] - C[:, :, :-1]

    ab = zlib.compress(A.tobytes(order="C"), 6)
    kb = zlib.compress(K.tobytes(order="C"), 6)
    hdr = HEADER.pack(
        MAGIC,
        VERSION,
        0,
        shots,
        channels,
        ns,
        float(eps),
        int(M),
        len(ab),
        len(kb),
        b"\0" * 20,
    )
    return hdr + ab + kb


def decode_stream(blob: bytes):
    if len(blob) < HEADER.size:
        raise ValueError("truncated marine carrier stream")
    magic, ver, flags, shots, channels, ns, eps, M, nab, nkb, _ = HEADER.unpack_from(blob, 0)
    if magic != MAGIC or ver != VERSION or flags != 0:
        raise ValueError((magic, ver, flags))
    end_a = HEADER.size + int(nab)
    end_k = end_a + int(nkb)
    if end_k != len(blob):
        raise ValueError(("length mismatch", end_k, len(blob)))

    idx = _indices(int(ns), int(M))
    ar = zlib.decompress(blob[HEADER.size:end_a])
    kr = zlib.decompress(blob[end_a:end_k])
    expected_a = int(shots) * int(channels) * len(idx) * 2
    expected_k = int(shots) * int(channels) * int(ns) * 2
    if len(ar) != expected_a or len(kr) != expected_k:
        raise ValueError(("decoded payload length", len(ar), expected_a, len(kr), expected_k))

    A = np.frombuffer(ar, dtype="<i2").reshape(int(shots), int(channels), len(idx))
    K = np.frombuffer(kr, dtype="<i2").reshape(int(shots), int(channels), int(ns))
    # Modular int16 temporal integration exactly inverts PR6's int16 first
    # difference, including two's-complement wrap if it ever occurs.
    C = np.cumsum(K.astype(np.int64), axis=2).astype("<i2")
    P = _carrier_from_anchors(A, int(ns), int(M), float(eps))
    R = P + C.astype(np.float32) * np.float32(2 * float(eps))
    return R, {
        "shots": int(shots),
        "channels": int(channels),
        "samples": int(ns),
        "epsilon": float(eps),
        "M": int(M),
        "anchor_stream_bytes": int(nab),
        "correction_stream_bytes": int(nkb),
        "header_bytes": HEADER.size,
    }


def sz3_bytes(X: np.ndarray, eps: float):
    cfg = szConfig()
    cfg.errorBoundMode = szErrorBoundMode.ABS
    cfg.absErrorBound = float(eps)
    b, _ = sz.compress(np.ascontiguousarray(X, dtype=np.float32), cfg)
    Y, _ = sz.decompress(b, np.float32, X.shape)
    return int(b.size), float(np.max(np.abs(X.astype(np.float64) - Y.astype(np.float64))))


def compete(X: np.ndarray, eps: float, m_values=(32, 48, 64)):
    rows = []
    for M in m_values:
        blob = encode_array(X, eps, int(M))
        R, meta = decode_stream(blob)
        maxerr = float(np.max(np.abs(X.astype(np.float64) - R.astype(np.float64))))
        valid = bool(maxerr <= eps * (1.0 + 3e-6))
        rows.append({
            "M": int(M),
            "bytes": len(blob),
            "max_abs_error": maxerr,
            "valid": valid,
            **meta,
        })
    valid = [r for r in rows if r["valid"]]
    if not valid:
        raise RuntimeError("no valid PR6 carrier candidate")
    best = min(valid, key=lambda r: (r["bytes"], r["M"]))
    return best, rows


def run_fixture(path: str, shots: int, epsilon: float | None, historical_eps: float | None):
    X = pr6_load_exact(path, shots)
    eps = float(historical_eps if historical_eps is not None else epsilon if epsilon is not None else 0.10 * X.astype(np.float64).std())
    best, candidates = compete(X, eps)
    sb, se = sz3_bytes(X, eps)
    if se > eps * (1.0 + 3e-6):
        raise RuntimeError(("SZ3 invalid", se, eps))
    return {
        "file": os.path.basename(path),
        "shape": list(map(int, X.shape)),
        "raw_numeric_bytes": int(X.nbytes),
        "std": float(X.astype(np.float64).std()),
        "epsilon": eps,
        "epsilon_mode": "historical-fixed" if historical_eps is not None else "external" if epsilon is not None else "survey-global-10pct-std",
        "best": best,
        "candidates": candidates,
        "sz3_bytes": sb,
        "sz3_max_abs_error": se,
        "gain_sz3_over_carrier": float(sb / best["bytes"]),
        "decode_verified_from_stream": True,
        "all_candidate_bytes_fully_charged": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--shots", type=int, required=True)
    ap.add_argument("--epsilon", type=float)
    ap.add_argument("--historical-epsilon", type=float)
    ap.add_argument("--m-values", type=int, nargs="+", default=[32, 48, 64])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.epsilon is not None and args.historical_epsilon is not None:
        raise SystemExit("choose one epsilon mode")
    X = pr6_load_exact(args.file, args.shots)
    eps = float(args.historical_epsilon if args.historical_epsilon is not None else args.epsilon if args.epsilon is not None else 0.10 * X.astype(np.float64).std())
    best, candidates = compete(X, eps, args.m_values)
    sb, se = sz3_bytes(X, eps)
    result = {
        "kind": "marine-carrier-pr6-v2",
        "file": os.path.basename(args.file),
        "shape": list(map(int, X.shape)),
        "raw_numeric_bytes": int(X.nbytes),
        "std": float(X.astype(np.float64).std()),
        "epsilon": eps,
        "epsilon_mode": "historical-fixed" if args.historical_epsilon is not None else "external" if args.epsilon is not None else "survey-global-10pct-std",
        "best": best,
        "candidates": candidates,
        "sz3_bytes": sb,
        "sz3_max_abs_error": se,
        "gain_sz3_over_carrier": float(sb / best["bytes"]),
        "decode_verified_from_stream": True,
    }
    if best["max_abs_error"] > eps * (1.0 + 3e-6) or se > eps * (1.0 + 3e-6):
        raise RuntimeError(("hard error invalid", result))
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
