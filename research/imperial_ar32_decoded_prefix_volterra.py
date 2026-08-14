import json, sys
import h5py
import numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as base

SPECS = (("hard", 512), ("easy", 2304))
C = 128
NT = 4096
TRAIN = 1024
P = 32
STEP = 267
L = 8
LAMBDAS = (0.1, 1.0)
STRENGTHS = (0.25, 0.5, 1.0)
CLIP_K = 4.0
SELECTOR_BYTES = 1

# Reuse the audited incumbent implementation at the shorter gate length.
base.NT = NT


def ar_pred(hist, co):
    a = float(co[0])
    b = np.asarray(co[1:], np.float32)
    return int(np.rint(a + float(np.dot(b, hist[-P:][::-1].astype(np.float32)))))


def feat_from_hist(hist, mu, sd):
    z = (hist[-L:].astype(np.float64) - mu) / sd
    # Compact second-order Volterra basis: linear lags, squares, adjacent products.
    return np.concatenate((np.ones(1, np.float64), z, z * z, z[:-1] * z[1:]))


def fit_volterra(prefix_R, prefix_K, co, lam):
    nfeat = 1 + L + L + (L - 1)
    W = np.empty((C, nfeat), np.float64)
    mus = np.empty(C, np.float64)
    sds = np.empty(C, np.float64)
    reg = np.eye(nfeat, dtype=np.float64) * float(lam)
    reg[0, 0] = 0.0
    for c in range(C):
        r = prefix_R[c].astype(np.float64)
        mu = float(np.mean(r))
        sd = max(float(np.std(r)), 1.0)
        mus[c] = mu
        sds[c] = sd
        rows = []
        y = []
        for t in range(max(P, L), TRAIN):
            rows.append(feat_from_hist(r[:t], mu, sd))
            y.append(float(prefix_K[c, t]))
        A = np.asarray(rows, np.float64)
        yy = np.asarray(y, np.float64)
        lhs = A.T @ A + reg
        rhs = A.T @ yy
        try:
            W[c] = np.linalg.solve(lhs, rhs)
        except np.linalg.LinAlgError:
            W[c] = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
    return W, mus, sds


def encode_candidate(X, co, Rbase, Kbase, lam, strength):
    R = np.zeros((C, NT), np.int32)
    K = np.zeros((C, NT), np.int32)
    R[:, :TRAIN] = Rbase[:, :TRAIN]
    K[:, :TRAIN] = Kbase[:, :TRAIN]
    W, mus, sds = fit_volterra(R[:, :TRAIN], K[:, :TRAIN], co, lam)
    for c in range(C):
        for t in range(TRAIN, NT):
            p_ar = ar_pred(R[c, :t], co)
            f = feat_from_hist(R[c, :t], mus[c], sds[c])
            pred_k = float(np.dot(W[c], f))
            corr = float(strength) * STEP * float(np.clip(pred_k, -CLIP_K, CLIP_K))
            p = int(np.rint(p_ar + corr))
            k = int(np.rint((float(X[c, t]) - p) / STEP))
            K[c, t] = k
            R[c, t] = p + STEP * k
    return R, K, W


def decode_candidate(K, co, lam, strength):
    R = np.zeros((C, NT), np.int32)
    # Prefix uses the unchanged incumbent AR32 decoder.
    for c in range(C):
        for t in range(TRAIN):
            p = 0 if t < P else ar_pred(R[c, :t], co)
            R[c, t] = p + STEP * int(K[c, t])
    W, mus, sds = fit_volterra(R[:, :TRAIN], K[:, :TRAIN], co, lam)
    for c in range(C):
        for t in range(TRAIN, NT):
            p_ar = ar_pred(R[c, :t], co)
            f = feat_from_hist(R[c, :t], mus[c], sds[c])
            pred_k = float(np.dot(W[c], f))
            corr = float(strength) * STEP * float(np.clip(pred_k, -CLIP_K, CLIP_K))
            p = int(np.rint(p_ar + corr))
            R[c, t] = p + STEP * int(K[c, t])
    return R, W


def main(path):
    with h5py.File(path, "r") as f:
        d = f["Acoustic"]
        _, gstd = base.m.stats(d)
        eps = 0.1 * gstd
        rows = []
        for region, c0 in SPECS:
            X = np.asarray(d[:NT, c0:c0 + C], np.float64).T
            _, co = base.fits(X)
            Rbase, Kbase = base.run_ar(X, co)
            base_bytes, _, _, Kcheck = base.arithmetic(Kbase)
            Rcheck = base.decode_source(Kcheck, co)
            base_me = float(np.max(np.abs(X - Rcheck.astype(np.float64))))
            if base_me > eps * (1 + 1e-12):
                raise RuntimeError((region, "baseline hard error", base_me, eps))

            sz3 = 0
            for t0 in range(0, NT, base.TB):
                b, _ = base.m.szrun(X[:, t0:t0 + base.TB], eps)
                sz3 += b

            candidates = []
            for lam in LAMBDAS:
                for strength in STRENGTHS:
                    R, K, Wenc = encode_candidate(X, co, Rbase, Kbase, lam, strength)
                    me = float(np.max(np.abs(X - R.astype(np.float64))))
                    if me > eps * (1 + 1e-12):
                        raise RuntimeError((region, lam, strength, "encoder hard error", me, eps))
                    nbytes, nbit, nbsym, Kd = base.arithmetic(K)
                    nbytes += SELECTOR_BYTES
                    Rd, Wdec = decode_candidate(Kd, co, lam, strength)
                    if not np.array_equal(Rd, R):
                        raise RuntimeError((region, lam, strength, "decoder replay mismatch"))
                    if not np.allclose(Wenc, Wdec, rtol=0, atol=1e-12):
                        raise RuntimeError((region, lam, strength, "derived model mismatch"))
                    dme = float(np.max(np.abs(X - Rd.astype(np.float64))))
                    if dme > eps * (1 + 1e-12):
                        raise RuntimeError((region, lam, strength, "decoder hard error", dme, eps))
                    cand = {
                        "lambda": float(lam),
                        "strength": float(strength),
                        "bytes": int(nbytes),
                        "bps": 8.0 * nbytes / X.size,
                        "gain_vs_baseline": float(base_bytes / nbytes),
                        "gain_vs_sz3": float(sz3 / nbytes),
                        "zero_fraction": float(np.mean(K == 0)),
                        "k_std": float(np.std(K.astype(np.float64))),
                        "maxerr": dme,
                        "arithmetic_bits": int(nbit),
                        "symbol_bits": int(nbsym),
                        "selector_bytes": SELECTOR_BYTES,
                    }
                    candidates.append(cand)
                    print(json.dumps({"region": region, "candidate": cand}, indent=2), flush=True)

            best = min(candidates, key=lambda q: q["bytes"])
            row = {
                "region": region,
                "c0": c0,
                "samples": int(X.size),
                "eps": float(eps),
                "baseline_bytes": int(base_bytes),
                "baseline_bps": 8.0 * base_bytes / X.size,
                "baseline_zero_fraction": float(np.mean(Kbase == 0)),
                "sz3_bytes": int(sz3),
                "sz3_bps": 8.0 * sz3 / X.size,
                "best": best,
                "candidates": candidates,
            }
            rows.append(row)
            print(json.dumps({"summary": row}, indent=2), flush=True)

    out = {
        "rows": rows,
        "scope": "Decoder-real nonlinear temporal gate. The first 1024 samples use the unchanged Huber AR32 step267 reconstruction. From that already-decoded prefix alone, encoder and decoder independently fit one per-channel ridge second-order Volterra model to the exact incumbent K residuals using 8 normalized reconstructed lags, their squares and adjacent products. No nonlinear coefficients are transmitted. After the prefix the derived nonlinear model supplies only a bounded +/-4K correction to the ordinary AR32 prediction; strengths and two fixed ridge values are screened and one selector byte is charged. Exact K arithmetic decoding, independent nonlinear model regeneration, complete recursive source replay and the unchanged max-error contract are mandatory. No AI. Draft/do not merge."
    }
    json.dump(out, open("imperial_ar32_decoded_prefix_volterra.json", "w"), indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
