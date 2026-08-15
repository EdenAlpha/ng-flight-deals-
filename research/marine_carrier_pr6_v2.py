#!/usr/bin/env python3
"""Recover the buried PR #6 marine carrier/certificate lineage for V2.

Historical PR #6 counted zlib(anchor)+zlib(correction)+64 bytes but reconstructed
from encoder-side arrays. This module preserves that exact 64-byte accounting
while making those 64 bytes a real header and requiring reconstruction from the
serialized stream itself.

Active V2 loading is structural: trace/sample geometry is inferred from SEG-Y
headers + file length. No dataset filename or known shot count participates in
routing. The historical --shots option is retained only as an optional regression
assertion against the auto-detected geometry.
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
# This recovered family is the regular 48-receiver marine geometry from PR6.
# Forty-eight is a structural eligibility constraint, not a dataset identity.
DEFAULT_CHANNELS = 48
# 8s magic, H version, H flags, I shots, I channels, I samples, d epsilon,
# I M, I anchor-zlib bytes, I correction-zlib bytes, 20 reserved = exactly 64.
HEADER = struct.Struct("<8sHHIIIdIII20s")
assert HEADER.size == 64


def _u16_candidates(buf: bytes, offset: int):
    if offset < 0 or offset + 2 > len(buf):
        return []
    raw = buf[offset:offset + 2]
    return [int.from_bytes(raw, "big"), int.from_bytes(raw, "little")]


def detect_pr6_geometry(path: str, channels: int = DEFAULT_CHANNELS):
    """Infer fixed-length SEG-Y geometry without fixture identity or shot count.

    Eligibility requires:
      * standard 3600-byte SEG-Y preamble;
      * fixed 240-byte trace headers + float32 samples;
      * a sample count advertised by the binary or first-trace header that is
        consistent with the exact file length;
      * a trace count divisible by the structural receiver count.

    Both byte orders are considered for header sample-count fields because the
    historical PR6 public files used a nonstandard little-endian IEEE payload.
    """
    size = os.path.getsize(path)
    channels = int(channels)
    if channels <= 0 or size <= 3600:
        raise ValueError(("incompatible PR6 structural geometry", path, size, channels))

    with open(path, "rb") as f:
        prefix = f.read(min(size, 3840))
    if len(prefix) < 3600:
        raise ValueError("truncated SEG-Y preamble")

    # SEG-Y binary-header samples/trace: bytes 3221-3222 (zero offsets 3220:3222).
    # First trace header samples/trace: bytes 115-116 (file offsets 3714:3716).
    ns_candidates = []
    for off in (3220, 3714):
        for ns in _u16_candidates(prefix, off):
            if 0 < ns <= 1_000_000 and ns not in ns_candidates:
                ns_candidates.append(ns)

    matches = []
    for ns in ns_candidates:
        stride = 240 + 4 * int(ns)
        payload = size - 3600
        if stride <= 240 or payload % stride:
            continue
        ntr = payload // stride
        if ntr <= 0 or ntr % channels:
            continue
        shots = ntr // channels
        matches.append((int(shots), channels, int(ns), int(stride), int(ntr)))

    # Deduplicate candidates that came from both header fields / byte orders.
    matches = list(dict.fromkeys(matches))
    if len(matches) != 1:
        raise ValueError(("ambiguous/ineligible PR6 SEG-Y geometry", path, size, ns_candidates, matches))

    shots, channels, ns, stride, ntr = matches[0]
    return {
        "shots": shots,
        "channels": channels,
        "samples": ns,
        "trace_stride": stride,
        "traces": ntr,
        "geometry_source": "SEG-Y sample-count header(s) + exact file length + regular receiver grouping",
    }


def pr6_load_auto(path: str, channels: int = DEFAULT_CHANNELS, expected_shots: int | None = None):
    """Load the PR6 numeric cube using only decoder-visible structural geometry."""
    g = detect_pr6_geometry(path, channels)
    if expected_shots is not None and int(expected_shots) != g["shots"]:
        raise ValueError(("historical shot-count assertion failed", expected_shots, g["shots"]))

    mm = np.memmap(path, dtype=np.uint8, mode="r")
    X = np.ndarray(
        (g["traces"], g["samples"]),
        dtype="<f4",
        buffer=mm,
        offset=3600 + 240,
        strides=(g["trace_stride"], 4),
    ).copy().reshape(g["shots"], g["channels"], g["samples"])
    if not np.isfinite(X).all():
        raise ValueError("non-finite samples under PR6 little-endian IEEE payload interpretation")
    return X, g


def pr6_load_exact(path: str, shots: int):
    """Historical compatibility wrapper; shots is now assertion-only."""
    X, _ = pr6_load_auto(path, DEFAULT_CHANNELS, expected_shots=int(shots))
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
    A = np.rint(X[:, :, idx] / eps).astype("<i2")
    P = _carrier_from_anchors(A, ns, M, eps)
    C = np.rint((X - P) / (2 * eps)).astype("<i2")
    K = np.empty_like(C, dtype="<i2")
    K[:, :, 0] = C[:, :, 0]
    K[:, :, 1:] = C[:, :, 1:] - C[:, :, :-1]

    ab = zlib.compress(A.tobytes(order="C"), 6)
    kb = zlib.compress(K.tobytes(order="C"), 6)
    hdr = HEADER.pack(
        MAGIC, VERSION, 0, shots, channels, ns, float(eps), int(M),
        len(ab), len(kb), b"\0" * 20,
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
        rows.append({"M": int(M), "bytes": len(blob), "max_abs_error": maxerr, "valid": valid, **meta})
    valid = [r for r in rows if r["valid"]]
    if not valid:
        raise RuntimeError("no valid PR6 carrier candidate")
    best = min(valid, key=lambda r: (r["bytes"], r["M"]))
    return best, rows


def run_fixture(path: str, shots: int | None, epsilon: float | None, historical_eps: float | None, channels: int = DEFAULT_CHANNELS):
    X, geometry = pr6_load_auto(path, channels, expected_shots=shots)
    eps = float(historical_eps if historical_eps is not None else epsilon if epsilon is not None else 0.10 * X.astype(np.float64).std())
    best, candidates = compete(X, eps)
    sb, se = sz3_bytes(X, eps)
    if se > eps * (1.0 + 3e-6):
        raise RuntimeError(("SZ3 invalid", se, eps))
    return {
        "file": os.path.basename(path),
        "shape": list(map(int, X.shape)),
        "geometry": geometry,
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
        "dataset_label_used_for_routing": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--shots", type=int, help="optional historical regression assertion; never used for active routing")
    ap.add_argument("--channels", type=int, default=DEFAULT_CHANNELS, help="structural receiver-group eligibility constraint")
    ap.add_argument("--epsilon", type=float)
    ap.add_argument("--historical-epsilon", type=float)
    ap.add_argument("--m-values", type=int, nargs="+", default=[16, 24, 32, 40, 48, 56, 64, 80, 96, 128])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.epsilon is not None and args.historical_epsilon is not None:
        raise SystemExit("choose one epsilon mode")

    X, geometry = pr6_load_auto(args.file, args.channels, expected_shots=args.shots)
    eps = float(args.historical_epsilon if args.historical_epsilon is not None else args.epsilon if args.epsilon is not None else 0.10 * X.astype(np.float64).std())
    best, candidates = compete(X, eps, args.m_values)
    sb, se = sz3_bytes(X, eps)
    result = {
        "kind": "marine-carrier-pr6-v2",
        "file": os.path.basename(args.file),
        "shape": list(map(int, X.shape)),
        "geometry": geometry,
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
        "dataset_label_used_for_routing": False,
    }
    if best["max_abs_error"] > eps * (1.0 + 3e-6) or se > eps * (1.0 + 3e-6):
        raise RuntimeError(("hard error invalid", result))
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
