#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import math
import os
import sys
from typing import Any

import h5py
import numpy as np
import segyio
import zstandard as zstd

TILE_SPACE = 128
TILE_TIME = 1024
MAX_TILES = 8
LAGS = (1, 2, 4, 6, 8, 12, 16, 24, 32)
CARRIER_M = (16, 32, 64, 96, 128)
ZC = zstd.ZstdCompressor(level=9)


def stream_std_array(a: np.ndarray, block: int = 256) -> float:
    s = 0.0
    ss = 0.0
    n = 0
    for i in range(0, a.shape[0], block):
        x = np.asarray(a[i:i + block], dtype=np.float64)
        s += float(x.sum())
        ss += float((x * x).sum())
        n += int(x.size)
    mu = s / n
    return float(np.sqrt(max(0.0, ss / n - mu * mu)))


def stream_std_h5(d: h5py.Dataset, block: int = 2048) -> float:
    s = 0.0
    ss = 0.0
    n = 0
    for i in range(0, d.shape[0], block):
        x = np.asarray(d[i:min(i + block, d.shape[0])], dtype=np.float64)
        s += float(x.sum())
        ss += float((x * x).sum())
        n += int(x.size)
    mu = s / n
    return float(np.sqrt(max(0.0, ss / n - mu * mu)))


def load_segy(path: str) -> tuple[np.ndarray, dict[str, Any]]:
    errors = []
    for endian in ("big", "little"):
        try:
            with segyio.open(path, "r", ignore_geometry=True, endian=endian) as f:
                f.mmap()
                ntr = int(f.tracecount)
                ns = int(len(f.samples))
                if ntr <= 0 or ns <= 0:
                    raise RuntimeError((ntr, ns))
                a = np.asarray(segyio.tools.collect(f.trace.raw[:]), dtype=np.float32)
                if a.shape != (ntr, ns):
                    a = a.reshape(ntr, ns)
                if not np.isfinite(a).all():
                    raise RuntimeError("non-finite SEG-Y samples")
                return a, {"container": "SEG-Y", "endian": endian, "trace_count": ntr, "samples_per_trace": ns}
        except Exception as e:
            errors.append(f"{endian}:{type(e).__name__}:{e}")
    raise RuntimeError("SEG-Y parse failed: " + " | ".join(errors))


def starts(n: int, width: int) -> list[int]:
    if n <= width:
        return [0]
    last = n - width
    vals = [0, last // 3, (2 * last) // 3, last]
    return sorted(set(int(x) for x in vals))


def pick_pairs(nspace: int, ntime: int) -> list[tuple[int, int]]:
    ss = starts(nspace, min(TILE_SPACE, nspace))
    ts = starts(ntime, min(TILE_TIME, ntime))
    allp = list(itertools.product(ss, ts))
    if len(allp) <= MAX_TILES:
        return allp
    idx = np.linspace(0, len(allp) - 1, MAX_TILES).round().astype(int)
    return [allp[int(i)] for i in idx]


def empirical_entropy(a: np.ndarray) -> float:
    _, c = np.unique(np.asarray(a).ravel(), return_counts=True)
    p = c.astype(np.float64) / float(c.sum())
    return float(-(p * np.log2(p)).sum())


def narrow_int(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a)
    lo = int(a.min()) if a.size else 0
    hi = int(a.max()) if a.size else 0
    if lo >= -128 and hi <= 127:
        return np.ascontiguousarray(a.astype(np.int8, copy=False))
    if lo >= -32768 and hi <= 32767:
        return np.ascontiguousarray(a.astype(np.int16, copy=False))
    return np.ascontiguousarray(a.astype(np.int32, copy=False))


def zbytes(a: np.ndarray) -> int:
    return len(ZC.compress(narrow_int(a).tobytes(order="C")))


def corr_flat(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, dtype=np.float64).ravel()
    y = np.asarray(b, dtype=np.float64).ravel()
    if x.size == 0 or y.size == 0:
        return 0.0
    x = x - x.mean()
    y = y - y.mean()
    den = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / den) if den > 0 else 0.0


def best_temporal_corr(w: np.ndarray) -> tuple[int, float]:
    best = (0, 0.0)
    nt = w.shape[1]
    for lag in LAGS:
        if lag >= nt:
            continue
        c = corr_flat(w[:, :-lag], w[:, lag:])
        if abs(c) > abs(best[1]):
            best = (lag, c)
    return best


def best_neighbor_shift_corr(w: np.ndarray, radius: int = 16) -> tuple[int, float]:
    if w.shape[0] < 2:
        return 0, 0.0
    nt = w.shape[1]
    best = (0, 0.0)
    for lag in range(-radius, radius + 1):
        if lag >= 0:
            if lag >= nt:
                continue
            a, b = w[:-1, :nt - lag], w[1:, lag:]
        else:
            q = -lag
            if q >= nt:
                continue
            a, b = w[:-1, q:], w[1:, :nt - q]
        c = corr_flat(a, b)
        if abs(c) > abs(best[1]):
            best = (lag, c)
    return best


def spectral_metrics(w: np.ndarray) -> dict[str, float]:
    f = np.fft.rfft2(np.asarray(w, dtype=np.float64))
    p = np.abs(f) ** 2
    flat = p.ravel()
    total = float(flat.sum())
    if total <= 0:
        return {"spectral_entropy_2d": 0.0, "top32_energy": 0.0, "top128_energy": 0.0, "top256_energy": 0.0, "top1024_energy": 0.0}
    prob = flat[flat > 0] / total
    h = float(-(prob * np.log2(prob)).sum() / math.log2(flat.size)) if flat.size > 1 else 0.0
    out = {"spectral_entropy_2d": h}
    for k in (32, 128, 256, 1024):
        kk = min(k, flat.size)
        if kk == flat.size:
            e = 1.0
        else:
            ii = np.argpartition(flat, -kk)[-kk:]
            e = float(flat[ii].sum() / total)
        out[f"top{k}_energy"] = e
    return out


def low_rank_metrics(w: np.ndarray) -> dict[str, float]:
    a = np.asarray(w, dtype=np.float64)
    g = a @ a.T
    ev = np.linalg.eigvalsh(g)
    ev = np.maximum(ev, 0.0)[::-1]
    total = float(ev.sum())
    out = {}
    for k in (1, 4, 8, 16, 32):
        out[f"svd{k}_energy"] = float(ev[:min(k, ev.size)].sum() / total) if total > 0 else 0.0
    ac = a - a.mean(axis=1, keepdims=True)
    gc = ac @ ac.T
    ec = np.maximum(np.linalg.eigvalsh(gc), 0.0)[::-1]
    tc = float(ec.sum())
    out["svd16_centered_energy"] = float(ec[:min(16, ec.size)].sum() / tc) if tc > 0 else 0.0
    return out


def state_metrics(w: np.ndarray, eps: float) -> dict[str, float]:
    q = np.rint(np.asarray(w, dtype=np.float64) / (2.0 * eps)).astype(np.int32)
    dt = np.empty_like(q)
    dt[:, 0] = q[:, 0]
    dt[:, 1:] = q[:, 1:] - q[:, :-1]
    ds = np.empty_like(q)
    ds[0] = q[0]
    ds[1:] = q[1:] - q[:-1]
    lo = q.copy()
    if q.shape[0] > 1 and q.shape[1] > 1:
        lo[1:, 1:] = q[1:, 1:] - q[:-1, 1:] - q[1:, :-1] + q[:-1, :-1]
    n = float(q.size)
    return {
        "q_entropy_bits": empirical_entropy(q),
        "q_zstd_bps": 8.0 * zbytes(q) / n,
        "time_delta_nonzero_fraction": float(np.mean(dt != 0)),
        "time_delta_entropy_bits": empirical_entropy(dt),
        "time_delta_zstd_bps": 8.0 * zbytes(dt) / n,
        "space_delta_nonzero_fraction": float(np.mean(ds != 0)),
        "space_delta_entropy_bits": empirical_entropy(ds),
        "space_delta_zstd_bps": 8.0 * zbytes(ds) / n,
        "lorenzo_nonzero_fraction": float(np.mean(lo != 0)),
        "lorenzo_entropy_bits": empirical_entropy(lo),
        "lorenzo_zstd_bps": 8.0 * zbytes(lo) / n,
    }


def carrier_one(w: np.ndarray, eps: float, m: int) -> dict[str, float]:
    nt = w.shape[1]
    idx = np.arange(0, nt, m, dtype=np.int32)
    if idx[-1] != nt - 1:
        idx = np.r_[idx, nt - 1]
    ai = np.rint(np.asarray(w[:, idx], dtype=np.float64) / eps).astype(np.int32)
    ad = ai.astype(np.float64) * eps
    p = np.empty_like(w, dtype=np.float64)
    for j in range(len(idx) - 1):
        a, b = int(idx[j]), int(idx[j + 1])
        l = b - a
        u = np.arange(l, dtype=np.float64) / float(l)
        p[:, a:b] = ad[:, j, None] * (1.0 - u)[None, :] + ad[:, j + 1, None] * u[None, :]
    p[:, -1] = ad[:, -1]
    c = np.rint((np.asarray(w, dtype=np.float64) - p) / (2.0 * eps)).astype(np.int32)
    k = np.empty_like(c)
    k[:, 0] = c[:, 0]
    k[:, 1:] = c[:, 1:] - c[:, :-1]
    da = ai.copy()
    if ai.shape[1] > 1:
        da[:, 1:] = ai[:, 1:] - ai[:, :-1]
    anchor_bytes = min(zbytes(ai), zbytes(da))
    correction_bytes = zbytes(k)
    total = 32 + anchor_bytes + correction_bytes
    r = p + c.astype(np.float64) * (2.0 * eps)
    me = float(np.max(np.abs(np.asarray(w, dtype=np.float64) - r)))
    if me > eps * (1.0 + 2e-6) + 1e-12:
        raise RuntimeError(("carrier hard error", m, me, eps))
    return {
        "m": int(m),
        "bytes": int(total),
        "bps": float(8.0 * total / w.size),
        "anchor_bytes": int(anchor_bytes),
        "correction_bytes": int(correction_bytes),
        "correction_nonzero_fraction": float(np.mean(c != 0)),
        "transition_nonzero_fraction": float(np.mean(k != 0)),
        "maxerr": me,
    }


def carrier_metrics(w: np.ndarray, eps: float) -> dict[str, float]:
    rows = [carrier_one(w, eps, m) for m in CARRIER_M if m < w.shape[1]]
    if not rows:
        rows = [carrier_one(w, eps, max(2, w.shape[1] // 2))]
    b = min(rows, key=lambda r: r["bytes"])
    return {
        "carrier_best_m": float(b["m"]),
        "carrier_bps": float(b["bps"]),
        "carrier_correction_nonzero_fraction": float(b["correction_nonzero_fraction"]),
        "carrier_transition_nonzero_fraction": float(b["transition_nonzero_fraction"]),
        "carrier_maxerr": float(b["maxerr"]),
    }


def tile_metrics(w: np.ndarray, eps: float) -> dict[str, float]:
    w = np.asarray(w, dtype=np.float32)
    if w.shape[0] < 2 or w.shape[1] < 4:
        raise RuntimeError(("tile too small", w.shape))
    lag, tc = best_temporal_corr(w)
    shift, sc = best_neighbor_shift_corr(w)
    out: dict[str, float] = {
        "local_std": float(w.astype(np.float64).std()),
        "eps_over_local_std": float(eps / max(float(w.astype(np.float64).std()), 1e-30)),
        "adjacent_space_corr": corr_flat(w[:-1], w[1:]),
        "temporal_lag1_corr": corr_flat(w[:, :-1], w[:, 1:]),
        "best_temporal_lag": float(lag),
        "best_temporal_corr": float(tc),
        "best_neighbor_time_shift": float(shift),
        "best_neighbor_shift_corr": float(sc),
    }
    out.update(state_metrics(w, eps))
    out.update(spectral_metrics(w))
    out.update(low_rank_metrics(w))
    out.update(carrier_metrics(w, eps))
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted(k for k, v in rows[0]["metrics"].items() if isinstance(v, (int, float)))
    out: dict[str, Any] = {"tiles": len(rows), "metrics": {}}
    for k in keys:
        a = np.asarray([float(r["metrics"][k]) for r in rows], dtype=np.float64)
        out["metrics"][k] = {
            "mean": float(a.mean()),
            "median": float(np.median(a)),
            "min": float(a.min()),
            "max": float(a.max()),
            "std": float(a.std()),
        }
    td = np.asarray([r["metrics"]["time_delta_nonzero_fraction"] for r in rows], dtype=np.float64)
    out["stationarity"] = {
        "time_delta_nonzero_range": float(td.max() - td.min()),
        "time_delta_nonzero_cv": float(td.std() / max(td.mean(), 1e-30)),
    }
    return out


def probe_segy(path: str, name: str) -> dict[str, Any]:
    a, meta = load_segy(path)
    std = stream_std_array(a)
    eps = 0.1 * std
    pairs = pick_pairs(a.shape[0], a.shape[1])
    rows = []
    sw, tw = min(TILE_SPACE, a.shape[0]), min(TILE_TIME, a.shape[1])
    for s0, t0 in pairs:
        w = np.asarray(a[s0:s0 + sw, t0:t0 + tw], dtype=np.float32)
        m = tile_metrics(w, eps)
        row = {"s0": int(s0), "t0": int(t0), "shape": list(w.shape), "metrics": m}
        rows.append(row)
        print("TILE", name, s0, t0, json.dumps(m, sort_keys=True), flush=True)
    return {"dataset": name, "source": meta, "shape": list(a.shape), "global_std": std, "eps": eps, "epsilon_rule": "0.10 * full-object std", "tiles": rows, "summary": summarize(rows)}


def probe_imperial(path: str, name: str) -> dict[str, Any]:
    with h5py.File(path, "r") as f:
        d = f["Acoustic"]
        std = stream_std_h5(d)
        eps = 0.1 * std
        ntime, nspace = int(d.shape[0]), int(d.shape[1])
        pairs = pick_pairs(nspace, ntime)
        rows = []
        sw, tw = min(TILE_SPACE, nspace), min(TILE_TIME, ntime)
        for s0, t0 in pairs:
            w = np.asarray(d[t0:t0 + tw, s0:s0 + sw], dtype=np.float32).T
            m = tile_metrics(w, eps)
            row = {"s0": int(s0), "t0": int(t0), "shape": list(w.shape), "metrics": m}
            rows.append(row)
            print("TILE", name, s0, t0, json.dumps(m, sort_keys=True), flush=True)
        return {"dataset": name, "source": {"container": "HDF5", "dataset": "Acoustic", "stored_shape": [ntime, nspace], "logical_shape": [nspace, ntime]}, "shape": [nspace, ntime], "global_std": std, "eps": eps, "epsilon_rule": "0.10 * full-object std", "tiles": rows, "summary": summarize(rows)}


def main(path: str, name: str) -> None:
    if path.lower().endswith((".h5", ".hdf5")):
        out = probe_imperial(path, name)
    else:
        out = probe_segy(path, name)
    fn = f"compression_phenotype_{name.lower().replace('-', '_')}.json"
    with open(fn, "w") as f:
        json.dump(out, f, indent=2)
    print("FINAL", json.dumps({"dataset": out["dataset"], "shape": out["shape"], "global_std": out["global_std"], "eps": out["eps"], "summary": out["summary"]}, indent=2), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: compression_phenotype_probe_v1.py INPUT DATASET_NAME")
    main(sys.argv[1], sys.argv[2])
