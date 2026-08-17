#!/usr/bin/env python3
"""Geometry-aware migrated-volume compression experiment.

One codec family, no dataset-name routing.  Quantize once under the public
absolute-error contract, then compete reversible 2-D predictors designed for
migrated seismic images: temporal/spatial differences, Lorenzo, second
differences, and blockwise slope-aligned neighboring-trace predictors.

Every candidate is serialized into a self-contained stream, decoded from that
stream, hard-bound checked, and compared with matched SZ3 on the same panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np
import zstandard as zstd

import general_seismic_benchmark_runner as br
import general_seismic_all_engines_gauntlet as gg
from general_seismic_numeric_io import matched_sz3

MAGIC = b"MVGEO1\0\0"
HDR = "<8sddIIHHII"
HSZ = struct.calcsize(HDR)
INTERNAL_MARGIN = 1.0 - 1e-4

T_RAW = 0
T_TIME1 = 1
T_TRACE1 = 2
T_LORENZO = 3
T_TIME2 = 4
T_TRACE2 = 5
T_ROWLAG8 = 6
T_BLOCK256 = 7
T_BLOCK128 = 8
T_BLOCK64 = 9
T_ADAPT128 = 10

TRANSFORM_NAMES = {
    T_RAW: "raw_q",
    T_TIME1: "time_delta1",
    T_TRACE1: "trace_delta1",
    T_LORENZO: "lorenzo_2d",
    T_TIME2: "time_delta2",
    T_TRACE2: "trace_delta2",
    T_ROWLAG8: "row_lag_r8",
    T_BLOCK256: "block_lag_b256_r8",
    T_BLOCK128: "block_lag_b128_r12",
    T_BLOCK64: "block_lag_b64_r12",
    T_ADAPT128: "adaptive_plane_b128_r12",
}

STATIC_IDS = {T_RAW, T_TIME1, T_TRACE1, T_LORENZO, T_TIME2, T_TRACE2}
BLOCK_PARAMS = {
    T_BLOCK256: (256, 8),
    T_BLOCK128: (128, 12),
    T_BLOCK64: (64, 12),
    T_ADAPT128: (128, 12),
}

CCTX = zstd.ZstdCompressor(level=12)
DCTX = zstd.ZstdDecompressor()


def hard_error(a, b):
    return float(np.max(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)))) if np.size(a) else 0.0


def _shift_block(row, start, end, lag):
    n = int(end - start)
    out = np.zeros(n, dtype=np.int32)
    s0 = max(start, -lag)
    s1 = min(end, row.size - lag)
    if s1 > s0:
        out[s0-start:s1-start] = row[s0+lag:s1+lag]
    return out


def _static_forward(Q, tid):
    Q = np.asarray(Q, np.int32)
    R = np.empty_like(Q)
    if tid == T_RAW:
        return Q.copy()
    if tid == T_TIME1:
        R[:, 0] = Q[:, 0]
        if Q.shape[1] > 1:
            R[:, 1:] = Q[:, 1:] - Q[:, :-1]
        return R
    if tid == T_TRACE1:
        R[0] = Q[0]
        if Q.shape[0] > 1:
            R[1:] = Q[1:] - Q[:-1]
        return R
    if tid == T_LORENZO:
        R[0, 0] = Q[0, 0]
        if Q.shape[1] > 1:
            R[0, 1:] = Q[0, 1:] - Q[0, :-1]
        if Q.shape[0] > 1:
            R[1:, 0] = Q[1:, 0] - Q[:-1, 0]
        if Q.shape[0] > 1 and Q.shape[1] > 1:
            R[1:, 1:] = Q[1:, 1:] - Q[:-1, 1:] - Q[1:, :-1] + Q[:-1, :-1]
        return R
    if tid == T_TIME2:
        R[:, 0] = Q[:, 0]
        if Q.shape[1] > 1:
            R[:, 1] = Q[:, 1] - Q[:, 0]
        if Q.shape[1] > 2:
            R[:, 2:] = Q[:, 2:] - 2 * Q[:, 1:-1] + Q[:, :-2]
        return R
    if tid == T_TRACE2:
        R[0] = Q[0]
        if Q.shape[0] > 1:
            R[1] = Q[1] - Q[0]
        if Q.shape[0] > 2:
            R[2:] = Q[2:] - 2 * Q[1:-1] + Q[:-2]
        return R
    raise ValueError(tid)


def _static_inverse(R, tid):
    R = np.asarray(R, np.int32)
    if tid == T_RAW:
        return R.copy()
    if tid == T_TIME1:
        return np.cumsum(R, axis=1, dtype=np.int32)
    if tid == T_TRACE1:
        return np.cumsum(R, axis=0, dtype=np.int32)
    if tid == T_LORENZO:
        return np.cumsum(np.cumsum(R, axis=0, dtype=np.int32), axis=1, dtype=np.int32)
    if tid == T_TIME2:
        Q = np.empty_like(R)
        Q[:, 0] = R[:, 0]
        if R.shape[1] > 1:
            Q[:, 1] = R[:, 1] + Q[:, 0]
        for t in range(2, R.shape[1]):
            Q[:, t] = R[:, t] + 2 * Q[:, t-1] - Q[:, t-2]
        return Q
    if tid == T_TRACE2:
        Q = np.empty_like(R)
        Q[0] = R[0]
        if R.shape[0] > 1:
            Q[1] = R[1] + Q[0]
        for i in range(2, R.shape[0]):
            Q[i] = R[i] + 2 * Q[i-1] - Q[i-2]
        return Q
    raise ValueError(tid)


def _row_lag_forward(Q, radius=8):
    nr, nt = Q.shape
    R = np.empty_like(Q)
    R[0] = Q[0]
    codes = np.zeros(max(0, nr-1), dtype=np.int8)
    for i in range(1, nr):
        cur = Q[i]
        prev = Q[i-1]
        best = None
        for lag in range(-radius, radius+1):
            pred = _shift_block(prev, 0, nt, lag)
            score = int(np.abs(cur.astype(np.int64) - pred.astype(np.int64)).sum())
            key = (score, abs(lag), lag)
            if best is None or key < best[0]:
                best = (key, lag, pred)
        lag, pred = best[1], best[2]
        codes[i-1] = np.int8(lag)
        R[i] = cur - pred
    return R, codes.tobytes()


def _row_lag_inverse(R, side, radius=8):
    nr, nt = R.shape
    lags = np.frombuffer(side, dtype=np.int8, count=max(0, nr-1))
    Q = np.empty_like(R)
    Q[0] = R[0]
    for i in range(1, nr):
        lag = int(lags[i-1])
        if abs(lag) > radius:
            raise RuntimeError(("bad lag", lag, radius))
        Q[i] = R[i] + _shift_block(Q[i-1], 0, nt, lag)
    return Q


def _block_lag_forward(Q, block, radius, adaptive=False):
    nr, nt = Q.shape
    nb = (nt + block - 1) // block
    R = np.empty_like(Q)
    R[0] = Q[0]
    codes = np.zeros((max(0, nr-1), nb), dtype=np.uint8)
    for i in range(1, nr):
        for b in range(nb):
            s = b * block
            e = min(nt, s + block)
            cur = Q[i, s:e]
            best = None
            for lag in range(-radius, radius+1):
                p1 = _shift_block(Q[i-1], s, e, lag)
                d1 = cur.astype(np.int64) - p1.astype(np.int64)
                score1 = int(np.abs(d1).sum())
                code1 = int(lag + radius)
                key1 = (score1, 0, abs(lag), lag)
                if best is None or key1 < best[0]:
                    best = (key1, code1, p1)
                if adaptive and i >= 2:
                    p2a = p1.astype(np.int64)
                    p2b = _shift_block(Q[i-2], s, e, 2*lag).astype(np.int64)
                    pp = 2 * p2a - p2b
                    if np.all(pp >= np.iinfo(np.int32).min) and np.all(pp <= np.iinfo(np.int32).max):
                        pp32 = pp.astype(np.int32)
                        score2 = int(np.abs(cur.astype(np.int64) - pp).sum())
                        code2 = 32 + int(lag + radius)
                        key2 = (score2, 1, abs(lag), lag)
                        if key2 < best[0]:
                            best = (key2, code2, pp32)
            if adaptive:
                pt = np.zeros(e-s, dtype=np.int32)
                if s == 0:
                    if e-s > 1:
                        pt[1:] = Q[i, s:e-1]
                else:
                    pt[:] = Q[i, s-1:e-1]
                scoret = int(np.abs(cur.astype(np.int64) - pt.astype(np.int64)).sum())
                keyt = (scoret, 2, 0, 0)
                if keyt < best[0]:
                    best = (keyt, 64, pt)
                scorez = int(np.abs(cur.astype(np.int64)).sum())
                keyz = (scorez, 3, 0, 0)
                if keyz < best[0]:
                    best = (keyz, 96, np.zeros(e-s, dtype=np.int32))
            code, pred = best[1], best[2]
            codes[i-1, b] = np.uint8(code)
            R[i, s:e] = cur - pred
    return R, codes.tobytes()


def _block_lag_inverse(R, side, block, radius, adaptive=False):
    nr, nt = R.shape
    nb = (nt + block - 1) // block
    codes = np.frombuffer(side, dtype=np.uint8)
    if codes.size != max(0, nr-1) * nb:
        raise RuntimeError(("side size", codes.size, nr, nb))
    codes = codes.reshape(max(0, nr-1), nb)
    Q = np.empty_like(R)
    Q[0] = R[0]
    for i in range(1, nr):
        for b in range(nb):
            s = b * block
            e = min(nt, s + block)
            code = int(codes[i-1, b])
            mode = code // 32 if adaptive else 0
            if not adaptive:
                lag = code - radius
                if abs(lag) > radius:
                    raise RuntimeError(("bad block lag", lag, radius))
                pred = _shift_block(Q[i-1], s, e, lag)
            elif mode == 0:
                lag = (code % 32) - radius
                if abs(lag) > radius:
                    raise RuntimeError(("bad adaptive lag", lag, radius))
                pred = _shift_block(Q[i-1], s, e, lag)
            elif mode == 1:
                lag = (code % 32) - radius
                if i < 2 or abs(lag) > radius:
                    raise RuntimeError(("bad plane code", code, i))
                pred64 = 2 * _shift_block(Q[i-1], s, e, lag).astype(np.int64) - _shift_block(Q[i-2], s, e, 2*lag).astype(np.int64)
                pred = pred64.astype(np.int32)
            elif mode == 2:
                if s == 0:
                    for j in range(e-s):
                        predj = 0 if j == 0 else Q[i, s+j-1]
                        Q[i, s+j] = R[i, s+j] + predj
                    continue
                for j in range(e-s):
                    predj = Q[i, s+j-1]
                    Q[i, s+j] = R[i, s+j] + predj
                continue
            elif mode == 3:
                pred = np.zeros(e-s, dtype=np.int32)
            else:
                raise RuntimeError(("bad adaptive mode", code, mode))
            Q[i, s:e] = R[i, s:e] + pred
    return Q


def forward_transform(Q, tid):
    if tid in STATIC_IDS:
        return _static_forward(Q, tid), b""
    if tid == T_ROWLAG8:
        return _row_lag_forward(Q, 8)
    if tid in BLOCK_PARAMS:
        block, radius = BLOCK_PARAMS[tid]
        return _block_lag_forward(Q, block, radius, adaptive=(tid == T_ADAPT128))
    raise ValueError(tid)


def inverse_transform(R, tid, side):
    if tid in STATIC_IDS:
        if side:
            raise RuntimeError("static transform with side data")
        return _static_inverse(R, tid)
    if tid == T_ROWLAG8:
        return _row_lag_inverse(R, side, 8)
    if tid in BLOCK_PARAMS:
        block, radius = BLOCK_PARAMS[tid]
        return _block_lag_inverse(R, side, block, radius, adaptive=(tid == T_ADAPT128))
    raise ValueError(tid)


def _shuffle_bytes(a):
    a = np.ascontiguousarray(a)
    w = a.dtype.itemsize
    return a.view(np.uint8).reshape(-1, w).T.copy().tobytes()


def _unshuffle_bytes(data, dtype, n):
    dt = np.dtype(dtype)
    w = dt.itemsize
    u = np.frombuffer(data, dtype=np.uint8)
    if u.size != n * w:
        raise RuntimeError(("unshuffle size", u.size, n, w))
    raw = u.reshape(w, n).T.copy().reshape(n*w)
    return raw.view(dt)


def _zigzag32(x):
    a = np.asarray(x, np.int64).reshape(-1)
    z = (a << 1) ^ (a >> 63)
    if np.any(z < 0) or np.any(z > np.iinfo(np.uint32).max):
        raise OverflowError("zigzag32 overflow")
    return z.astype(np.uint32)


def _unzigzag32(z):
    z = np.asarray(z, np.uint32).astype(np.uint64)
    a = (z >> 1).astype(np.int64) ^ -((z & 1).astype(np.int64))
    if np.any(a < np.iinfo(np.int32).min) or np.any(a > np.iinfo(np.int32).max):
        raise OverflowError("unzigzag overflow")
    return a.astype(np.int32)


def encode_residual(R):
    flat = np.asarray(R, np.int32).reshape(-1)
    trials = []
    mn = int(flat.min()) if flat.size else 0
    mx = int(flat.max()) if flat.size else 0
    if -128 <= mn and mx <= 127:
        raw = flat.astype(np.int8).tobytes(); c = CCTX.compress(raw)
        trials.append((len(c), 0, c))
    if -32768 <= mn and mx <= 32767:
        a = flat.astype("<i2")
        for pid, raw in [(1, a.tobytes()), (2, _shuffle_bytes(a))]:
            c = CCTX.compress(raw); trials.append((len(c), pid, c))
    a4 = flat.astype("<i4")
    for pid, raw in [(3, a4.tobytes()), (4, _shuffle_bytes(a4))]:
        c = CCTX.compress(raw); trials.append((len(c), pid, c))
    zz = _zigzag32(flat)
    if zz.size == 0 or int(zz.max()) <= 65535:
        z2 = zz.astype("<u2")
        c = CCTX.compress(_shuffle_bytes(z2)); trials.append((len(c), 5, c))
    z4 = zz.astype("<u4")
    c = CCTX.compress(_shuffle_bytes(z4)); trials.append((len(c), 6, c))
    _, pid, body = min(trials, key=lambda x: (x[0], x[1]))
    return pid, body


def decode_residual(pid, body, shape):
    n = int(np.prod(shape))
    raw = DCTX.decompress(body)
    if pid == 0:
        a = np.frombuffer(raw, dtype=np.int8, count=n).astype(np.int32)
    elif pid == 1:
        a = np.frombuffer(raw, dtype="<i2", count=n).astype(np.int32)
    elif pid == 2:
        a = _unshuffle_bytes(raw, "<i2", n).astype(np.int32)
    elif pid == 3:
        a = np.frombuffer(raw, dtype="<i4", count=n).astype(np.int32)
    elif pid == 4:
        a = _unshuffle_bytes(raw, "<i4", n).astype(np.int32)
    elif pid == 5:
        z = _unshuffle_bytes(raw, "<u2", n).astype(np.uint32); a = _unzigzag32(z)
    elif pid == 6:
        z = _unshuffle_bytes(raw, "<u4", n).astype(np.uint32); a = _unzigzag32(z)
    else:
        raise RuntimeError(("bad pack id", pid))
    if a.size != n:
        raise RuntimeError(("residual size", a.size, n))
    return a.reshape(shape)


def encode_candidate(P, eps, tid):
    internal = float(eps) * INTERNAL_MARGIN
    step = 2.0 * internal
    q64 = np.rint(np.asarray(P, np.float64) / step)
    if np.any(q64 < np.iinfo(np.int32).min) or np.any(q64 > np.iinfo(np.int32).max):
        raise OverflowError("quantized migrated volume exceeds int32")
    Q = q64.astype(np.int32)
    R, side_raw = forward_transform(Q, tid)
    side_blob = CCTX.compress(side_raw) if side_raw else b""
    pid, payload = encode_residual(R)
    hdr = struct.pack(HDR, MAGIC, float(eps), internal, int(P.shape[0]), int(P.shape[1]), int(tid), int(pid), len(side_blob), len(payload))
    blob = hdr + side_blob + payload
    diag = {"transform": TRANSFORM_NAMES[tid], "pack_id": int(pid), "residual_nonzero_fraction": float(np.mean(R != 0)), "residual_mean_abs": float(np.mean(np.abs(R.astype(np.int64)))), "side_bytes": int(len(side_blob)), "payload_bytes": int(len(payload)), "stream_bytes": int(len(blob))}
    return blob, diag


def decode_stream(blob):
    if len(blob) < HSZ:
        raise RuntimeError("short migrated-volume stream")
    magic, public_eps, internal, nr, nt, tid, pid, side_n, payload_n = struct.unpack(HDR, blob[:HSZ])
    if magic != MAGIC:
        raise RuntimeError("bad migrated-volume magic")
    if len(blob) != HSZ + int(side_n) + int(payload_n):
        raise RuntimeError(("stream length", len(blob), side_n, payload_n))
    p = HSZ
    side_blob = blob[p:p+side_n]; p += side_n
    payload = blob[p:p+payload_n]
    side_raw = DCTX.decompress(side_blob) if side_blob else b""
    R = decode_residual(int(pid), payload, (int(nr), int(nt)))
    Q = inverse_transform(R, int(tid), side_raw)
    X = Q.astype(np.float64) * (2.0 * float(internal))
    return X, {"public_eps": float(public_eps), "internal_eps": float(internal), "shape": [int(nr), int(nt)], "transform_id": int(tid), "transform": TRANSFORM_NAMES[int(tid)], "pack_id": int(pid)}


def compete(P, eps):
    rows = []
    for tid in sorted(TRANSFORM_NAMES):
        blob, diag = encode_candidate(P, eps, tid)
        X, meta = decode_stream(blob)
        me = hard_error(P, X)
        if me > float(eps) * (1.0 + 3e-6):
            raise RuntimeError(("hard bound", TRANSFORM_NAMES[tid], me, eps))
        rows.append({"bytes": len(blob), "tid": tid, "blob": blob, "maxerr": me, "diag": diag})
    return min(rows, key=lambda r: (r["bytes"], r["tid"])), rows


def sanity():
    rng = np.random.default_rng(20260817)
    nr, nt = 19, 311
    t = np.arange(nt)
    X = np.empty((nr, nt), np.float32)
    for i in range(nr):
        X[i] = (40*np.sin((t + 2*i)/19.0) + 12*np.sin((t-i)/7.0) + rng.normal(0, 1.5, nt)).astype(np.float32)
    eps = 2.5
    best, rows = compete(X, eps)
    for r in rows:
        Y, _ = decode_stream(r["blob"])
        if hard_error(X, Y) > eps * (1+3e-6):
            raise RuntimeError(("sanity hard bound", r["tid"]))
    print("MIGRATED_VOLUME_SANITY_OK", TRANSFORM_NAMES[best["tid"]], best["bytes"])


def reservoir(ds, row, cfg, sample_panels, seed):
    with tempfile.TemporaryDirectory(prefix="migrated_volume_") as tmp:
        return gg.reservoir_stats_and_panels(ds, row, cfg, tmp, None, int(sample_panels), int(seed))


def run_survey(args):
    manifest = br.load_json(args.manifest); pre = br.load_json(args.preflight); cfg = br.load_json(args.config)
    ds = br.dataset_def(manifest, args.dataset); row = br.dataset_row(pre, args.dataset)
    seed = int.from_bytes(hashlib.sha256(("GAUNTLET-V1:" + ds["id"]).encode()).digest()[:8], "little")
    st, panels = reservoir(ds, row, cfg, args.sample_panels, seed)
    eps = 0.10 * float(st["std"])
    if not np.isfinite(eps) or eps <= 0 or eps > 1e12:
        raise RuntimeError(("implausible epsilon", ds["id"], st["std"], eps))
    print("MV_EPSILON", ds["id"], st["std"], eps, "sampled", len(panels), "of", st["panels"], flush=True)
    total_mv = total_sz3 = total_samples = 0
    maxerr = sz3_maxerr = 0.0
    winners = Counter()
    transform_totals = {TRANSFORM_NAMES[k]: {"bytes": 0, "wins": 0} for k in TRANSFORM_NAMES}
    rows_out = []
    for rank, (source_panel_index, P, meta) in enumerate(panels):
        sb, sme = matched_sz3(P, eps)
        best, candidates = compete(P, eps)
        for c in candidates:
            transform_totals[TRANSFORM_NAMES[c["tid"]]]["bytes"] += int(c["bytes"])
        winner = TRANSFORM_NAMES[best["tid"]]
        transform_totals[winner]["wins"] += 1; winners[winner] += 1
        Y, decoded = decode_stream(best["blob"]); me = hard_error(P, Y); nb = int(best["bytes"])
        total_mv += nb; total_sz3 += int(sb); total_samples += int(P.size)
        maxerr = max(maxerr, me); sz3_maxerr = max(sz3_maxerr, float(sme))
        cand_out = [{"transform": TRANSFORM_NAMES[c["tid"]], "bytes": int(c["bytes"]), "gain_vs_sz3": float(sb / c["bytes"]), "maxerr": float(c["maxerr"]), **c["diag"]} for c in candidates]
        po = {"sample_rank": int(rank), "source_panel_index": int(source_panel_index), "shape": list(map(int, P.shape)), "samples": int(P.size), "sz3_bytes": int(sb), "mv_bytes": nb, "gain_vs_sz3": float(sb / nb), "winner": winner, "maxerr": float(me), "sz3_maxerr": float(sme), "meta": meta, "decoded": decoded, "candidates": cand_out}
        rows_out.append(po)
        print("MV_PANEL", ds["id"], source_panel_index, "SZ3", sb, "MV", nb, "GAIN", float(sb/nb), "WINNER", winner, flush=True)
    result = {"kind": "migrated-volume-geometry-engine-v1", "dataset_id": ds["id"], "std": float(st["std"]), "epsilon": float(eps), "sampled_panels": len(panels), "total_source_panels": int(st["panels"]), "samples": int(total_samples), "mv_bytes": int(total_mv), "sz3_bytes": int(total_sz3), "gain_vs_sz3": float(total_sz3 / total_mv), "reduction_percent_vs_sz3": float(100.0 * (1.0 - total_mv / total_sz3)), "mv_bps": float(8.0 * total_mv / total_samples), "sz3_bps": float(8.0 * total_sz3 / total_samples), "maxerr": float(maxerr), "sz3_maxerr": float(sz3_maxerr), "winner_counts": dict(winners), "transform_totals": transform_totals, "same_reservoir_seed_as_all_engines_gauntlet": True, "no_dataset_label_routing": True, "all_selected_streams_materialized_and_decoded": True, "panels": rows_out}
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != "panels"}, indent=2), flush=True)


def aggregate(args):
    rows = [json.loads(p.read_text()) for p in sorted(Path(args.results).glob("*.json"))]
    out = {"kind": "migrated-volume-geometry-headline-v1", "surveys": [{"dataset_id": r["dataset_id"], "gain_vs_sz3": r["gain_vs_sz3"], "reduction_percent_vs_sz3": r["reduction_percent_vs_sz3"], "mv_bps": r["mv_bps"], "sz3_bps": r["sz3_bps"], "winner_counts": r["winner_counts"]} for r in rows], "wins": sum(r["gain_vs_sz3"] > 1.0 for r in rows), "complete_surveys": len(rows), "median_gain": float(np.median([r["gain_vs_sz3"] for r in rows])) if rows else None, "byte_weighted_gain": float(sum(r["sz3_bytes"] for r in rows) / sum(r["mv_bytes"] for r in rows)) if rows else None}
    Path(args.out).write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True); sp.add_parser("sanity")
    s = sp.add_parser("survey"); s.add_argument("--manifest", required=True); s.add_argument("--preflight", required=True); s.add_argument("--config", required=True); s.add_argument("--dataset", required=True); s.add_argument("--sample-panels", type=int, default=16); s.add_argument("--out", required=True)
    a = sp.add_parser("aggregate"); a.add_argument("--results", required=True); a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "sanity": sanity()
    elif args.cmd == "survey": run_survey(args)
    else: aggregate(args)


if __name__ == "__main__":
    main()
