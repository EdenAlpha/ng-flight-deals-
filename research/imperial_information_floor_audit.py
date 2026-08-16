import json, math, sys, zlib
import h5py
import numpy as np
import zstandard as zstd

C = 128
NT = 30000
C0 = 512
TRAIN = 8192
STEP = 267
CURRENT_BYTES = 2468803
MATCHED_SZ3 = 2767977
TARGET_2X_BYTES = MATCHED_SZ3 / 2.0


def h0_bits(a):
    a = np.asarray(a).reshape(-1)
    _, cnt = np.unique(a, return_counts=True)
    p = cnt.astype(np.float64) / cnt.sum()
    return float(-(p * np.log2(p)).sum())


def zbytes(a, level=19):
    a = np.ascontiguousarray(a)
    return len(zstd.ZstdCompressor(level=level).compress(a.tobytes()))


def transform_set(a):
    a = np.asarray(a, dtype=np.int32)
    out = {"raw": a}
    dt = a.copy()
    dt[:, 1:] = a[:, 1:] - a[:, :-1]
    out["dt1"] = dt
    ds = a.copy()
    ds[1:, :] = a[1:, :] - a[:-1, :]
    out["ds1"] = ds
    mix = dt.copy()
    mix[1:, :] = dt[1:, :] - dt[:-1, :]
    out["dt_ds"] = mix
    d2 = a.copy()
    d2[:, 1:] = a[:, 1:] - a[:, :-1]
    d2[:, 2:] = a[:, 2:] - 2 * a[:, 1:-1] + a[:, :-2]
    out["dt2"] = d2
    return out


def summarize_transforms(a, n):
    rows = []
    for name, v in transform_set(a).items():
        hb = h0_bits(v)
        zb = zbytes(v)
        rows.append({
            "name": name,
            "h0_bps": hb,
            "zstd_bytes": int(zb),
            "zstd_bps": float(8.0 * zb / n),
        })
        print(json.dumps({"transform": rows[-1]}), flush=True)
    return rows


def fit_ar_per_channel(x, p, train):
    C_, T = x.shape
    co = np.zeros((C_, p + 1), np.float64)
    for c in range(C_):
        y = x[c, p:train]
        A = np.empty((len(y), p + 1), np.float64)
        A[:, 0] = 1.0
        for j in range(p):
            A[:, j + 1] = x[c, p - 1 - j:train - 1 - j]
        scale = max(float(np.std(y)), 1.0)
        mu = float(np.mean(y))
        As = A.copy()
        As[:, 1:] = (As[:, 1:] - mu) / scale
        ys = (y - mu) / scale
        b, *_ = np.linalg.lstsq(As, ys, rcond=None)
        # Convert normalized predictor back to raw-coordinate coefficients.
        co[c, 1:] = b[1:]
        co[c, 0] = mu + scale * b[0] - mu * float(np.sum(b[1:]))
    return co


def ar_residual(x, co, p, start):
    C_, T = x.shape
    chunks = []
    for c in range(C_):
        y = x[c, start:T]
        pred = np.full(len(y), co[c, 0], np.float64)
        for j in range(p):
            pred += co[c, j + 1] * x[c, start - 1 - j:T - 1 - j]
        r = np.rint(y - np.rint(pred)).astype(np.int32)
        chunks.append(r)
    return np.concatenate(chunks)


def fit_global(x, feature_fn, train_start, train_end):
    F, y = feature_fn(x, train_start, train_end)
    # Deterministic thinning caps memory while retaining the whole training region.
    if len(y) > 600000:
        idx = np.linspace(0, len(y) - 1, 600000, dtype=np.int64)
        F = F[idx]
        y = y[idx]
    mu = np.mean(F, axis=0)
    sc = np.std(F, axis=0)
    sc[sc < 1e-9] = 1.0
    ym = float(np.mean(y))
    ys = max(float(np.std(y)), 1.0)
    A = np.column_stack([np.ones(len(y)), (F - mu) / sc])
    b, *_ = np.linalg.lstsq(A, (y - ym) / ys, rcond=None)
    return {"b": b, "mu": mu, "sc": sc, "ym": ym, "ys": ys}


def apply_global(model, F, y):
    predn = model["b"][0] + ((F - model["mu"]) / model["sc"]) @ model["b"][1:]
    pred = model["ym"] + model["ys"] * predn
    return np.rint(y - np.rint(pred)).astype(np.int32)


def causal_wave_features(x, t0, t1):
    # Interior channels only. All features are decoder-causal in time-major,
    # ascending-channel reconstruction order.
    t = slice(t0, t1)
    t1s = slice(t0 - 1, t1 - 1)
    t2s = slice(t0 - 2, t1 - 2)
    y = x[1:-1, t].reshape(-1)
    a = x[1:-1, t1s]
    b = x[1:-1, t2s]
    lp = x[:-2, t1s]
    rp = x[2:, t1s]
    lc = x[:-2, t]
    lap = lp + rp - 2.0 * a
    F = np.stack([a, b, lp, rp, lc, lap], axis=-1).reshape(-1, 6)
    return F, y


def oracle_features(x, t0, t1):
    # Deliberately noncausal diagnostic: current right neighbor + future sample.
    t = slice(t0, t1)
    t1s = slice(t0 - 1, t1 - 1)
    t2s = slice(t0 - 2, t1 - 2)
    fut = slice(t0 + 1, t1 + 1)
    y = x[1:-1, t].reshape(-1)
    a = x[1:-1, t1s]
    b = x[1:-1, t2s]
    lp = x[:-2, t1s]
    rp = x[2:, t1s]
    lc = x[:-2, t]
    rc = x[2:, t]
    ff = x[1:-1, fut]
    lap = lp + rp - 2.0 * a
    F = np.stack([a, b, lp, rp, lc, rc, ff, lap], axis=-1).reshape(-1, 8)
    return F, y


def residual_report(name, r, sample_count):
    hb = h0_bits(r)
    zb = zbytes(r)
    row = {
        "name": name,
        "samples": int(sample_count),
        "residual_h0_bps": float(hb),
        "residual_zstd_bps": float(8.0 * zb / sample_count),
        "residual_zstd_bytes": int(zb),
        "shannon_style_floor_from_h0_bps": float(max(0.0, hb - math.log2(2 * 133 + 1))),
    }
    print(json.dumps({"predictor": row}), flush=True)
    return row


def main(path):
    with h5py.File(path, "r") as hf:
        d = hf["Acoustic"]
        # Recompute the same survey-global epsilon used by the compression gates.
        total_n = d.shape[0] * d.shape[1]
        s = 0.0
        s2 = 0.0
        chunk = 4096
        for i in range(0, d.shape[0], chunk):
            a = np.asarray(d[i:i + chunk, :], np.float64)
            s += float(a.sum())
            s2 += float(np.square(a).sum())
        mean = s / total_n
        var = max(0.0, s2 / total_n - mean * mean)
        std = math.sqrt(var)
        eps = 0.1 * std
        Xf = np.asarray(d[:, C0:C0 + C], np.float64).T
        source_dtype = str(d.dtype)

    Xi = np.rint(Xf).astype(np.int64)
    integer_error = float(np.max(np.abs(Xf - Xi)))
    n = Xi.size
    if integer_error > 1e-6:
        raise RuntimeError(("source not integer-valued", integer_error))

    # A fixed legal scalar reconstruction. This is an actual achievable upper
    # bound when paired with any reversible encoding of Q; it is not a lower bound.
    Q = np.rint(Xi / STEP).astype(np.int32)
    Rq = Q.astype(np.int64) * STEP
    qerr = float(np.max(np.abs(Xi - Rq)))
    if qerr > eps * (1 + 5e-6):
        raise RuntimeError(("scalar hard error", qerr, eps))

    ball_cardinality = 2 * int(math.floor(eps)) + 1
    ball_bits = math.log2(ball_cardinality)
    target_bps = 8.0 * TARGET_2X_BYTES / n
    current_bps = 8.0 * CURRENT_BYTES / n

    meta = {
        "shape": [C, NT], "samples": n, "source_dtype": source_dtype,
        "global_std": std, "eps": eps, "integer_error": integer_error,
        "hard_error_ball_cardinality": ball_cardinality,
        "log2_ball": ball_bits,
        "current_bytes": CURRENT_BYTES, "current_bps": current_bps,
        "matched_sz3_bytes": MATCHED_SZ3,
        "two_x_target_bytes": TARGET_2X_BYTES, "two_x_target_bps": target_bps,
        "scalar_step": STEP, "scalar_maxerr": qerr,
    }
    print(json.dumps({"meta": meta}, indent=2), flush=True)

    q_transforms = summarize_transforms(Q, n)

    # Exact-source structural diagnostics (lossless transforms; zstd is only a
    # practical universal-code proxy, never called a mathematical floor).
    source32 = Xi.astype(np.int32)
    source_transforms = summarize_transforms(source32, n)

    predictors = []
    for p in (1, 4, 16, 32):
        co = fit_ar_per_channel(Xf, p, TRAIN)
        r = ar_residual(Xf, co, p, TRAIN)
        predictors.append(residual_report(f"heldout_per_channel_ar{p}", r, len(r)))

    cm = fit_global(Xf, causal_wave_features, 2, TRAIN)
    Fc, yc = causal_wave_features(Xf, TRAIN, NT)
    rc = apply_global(cm, Fc, yc)
    predictors.append(residual_report("heldout_causal_wave6", rc, len(rc)))

    om = fit_global(Xf, oracle_features, 2, TRAIN)
    Fo, yo = oracle_features(Xf, TRAIN, NT - 1)
    ro = apply_global(om, Fo, yo)
    predictors.append(residual_report("heldout_noncausal_oracle8", ro, len(ro)))

    best_q_actual = min(q_transforms, key=lambda r: r["zstd_bytes"])
    best_source_code = min(source_transforms, key=lambda r: r["zstd_bytes"])
    best_causal_h0 = min([r for r in predictors if "noncausal" not in r["name"]], key=lambda r: r["residual_h0_bps"])
    oracle = [r for r in predictors if "noncausal" in r["name"]][0]

    report = {
        "meta": meta,
        "quantized_legal_reconstruction_transforms": q_transforms,
        "exact_source_transforms": source_transforms,
        "heldout_predictive_diagnostics": predictors,
        "summary": {
            "best_actual_scalar_quantized_zstd": best_q_actual,
            "best_exact_source_zstd_proxy": best_source_code,
            "best_causal_residual_h0": best_causal_h0,
            "noncausal_oracle_residual_h0": oracle,
            "target_2x_bps": target_bps,
            "current_bps": current_bps,
            "interpretation": "Actual scalar-quantized zstd sizes are achievable upper bounds for that fixed legal reconstruction. Residual H0 and zstd rates are held-out entropy-rate diagnostics, not rigorous lower bounds. The H0-minus-log2(error-ball) quantity is a Shannon-style diagnostic only; it must not be used to claim impossibility for this finite file. A large causal-to-oracle drop indicates hidden spatiotemporal structure not captured causally; flat AR order and oracle curves indicate a harder innovation floor."
        }
    }
    with open("imperial_information_floor_audit.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"summary": report["summary"]}, indent=2), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
