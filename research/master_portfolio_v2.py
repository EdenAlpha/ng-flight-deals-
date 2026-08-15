"""Master Portfolio V2 recovery adapters.

This file deliberately does NOT modify the running Portfolio V1 benchmark.
It wraps exact historical winner source blobs and lets them run under an
externally supplied epsilon.  The Soda adapter uses SEG-Y headers/geometry as
shared side information, matching the historical sample-payload contract.
"""

import argparse
import json
import os
import struct
from pathlib import Path

import numpy as np


def _exec_without_cli(path, sentinel):
    src = Path(path).read_text()
    if sentinel not in src:
        raise RuntimeError(("legacy sentinel not found", path, sentinel))
    src = src.split(sentinel, 1)[0]
    ns = {"__name__": "legacy_v2_recovered"}
    exec(compile(src, path, "exec"), ns)
    return ns


_SODA = None
_FORGE = None


def soda_ns():
    global _SODA
    if _SODA is None:
        _SODA = _exec_without_cli(
            "research/soda_hard4_frozen_record.py", "\nmain(sys.argv[1])"
        )
    return _SODA


def forge_ns():
    global _FORGE
    if _FORGE is None:
        _FORGE = _exec_without_cli(
            "research/forge_standalone_segc.py", "\nif __name__=='__main__':"
        )
    return _FORGE


def soda_record_codec(path, epsilon=None):
    """Run exact PR169 frozen record/run codec with caller-controlled epsilon.

    The stream materializes the historically charged outer header. SEG-Y
    geometry is shared side information under the numeric-payload contract.
    """
    n = soda_ns()
    X, gx, gy, dt = n["load"](path)
    X = np.asarray(X, np.float32)
    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError(("bad epsilon", eps))
    step = 2.0 * eps

    G, tm, outids, geom = n["geometry_map"](X, gx, gy)
    for tid, c, l, s in tm:
        G[c, l, s] = np.rint(X[tid] / step).astype(np.int32)
    O = np.rint(X[outids] / step).astype(np.int32)
    K = n["delta"](G, 3)

    main_blob, main_parts = n["encode_main_fixed"](K)
    RK = n["decode_main"](main_blob)
    if not np.array_equal(RK, K):
        raise RuntimeError("recovered Soda main stream failed exact K decode")

    bo = n["best_out"](O)
    if len(bo) < 7:
        raise RuntimeError(("unexpected historical best_out tuple", bo))
    out_blob = bo[6]
    RO = n["decode_out_best"](bo, O.shape)
    if not np.array_equal(RO, O):
        raise RuntimeError("recovered Soda outlier stream failed exact decode")

    kind = 0 if bo[1] == "gap" else 1
    mode = kind | (2 if bool(bo[2]) else 0)
    header = struct.pack("<8sdQQB", b"V2SODA01", eps, len(main_blob), len(out_blob), mode)
    blob = header + main_blob + out_blob
    if len(header) != int(n["TOPS"]):
        raise RuntimeError(("Soda top-header accounting drift", len(header), n["TOPS"]))

    hs = struct.calcsize("<8sdQQB")
    magic, ee, lm, lo, m = struct.unpack("<8sdQQB", blob[:hs])
    if magic != b"V2SODA01" or hs + lm + lo != len(blob):
        raise RuntimeError("bad V2 Soda outer stream")
    p = hs
    main2 = blob[p:p+lm]
    p += lm
    out2 = blob[p:p+lo]
    RK2 = n["decode_main"](main2)
    tdiff = bool(m & 2)
    if (m & 1) == 0:
        RO2 = n["decode"](out2).reshape(O.shape)
        if tdiff:
            RO2 = n["undelta"](RO2, 1)
    else:
        RO2 = n["decode_out_sparse"](out2)
        if tdiff:
            RO2 = n["undelta"](RO2, 1)
    if not np.array_equal(RK2, K) or not np.array_equal(RO2, O):
        raise RuntimeError("V2 Soda outer stream did not reconstruct integer state")

    RG = n["undelta"](RK2, 3)
    Y = np.empty_like(X)
    for tid, c, l, s in tm:
        Y[tid] = RG[c, l, s].astype(np.float32) * np.float32(2.0 * ee)
    Y[outids] = RO2.astype(np.float32) * np.float32(2.0 * ee)
    maxerr = float(np.max(np.abs(X.astype(np.float64) - Y.astype(np.float64))))
    if maxerr > eps * (1.0 + 3e-6):
        raise RuntimeError(("Soda hard error failure", maxerr, eps))

    sz3_bytes, sz3_maxerr = n["sz3_bytes"](X, eps)
    if float(sz3_maxerr) > eps * (1.0 + 3e-6):
        raise RuntimeError(("Soda matched SZ3 hard error failure", sz3_maxerr, eps))

    return {
        "engine": "soda_record_run_lattice_pr169",
        "file": os.path.basename(path),
        "shape": list(map(int, X.shape)),
        "epsilon": eps,
        "raw_numeric_bytes": int(X.nbytes),
        "ours_bytes": int(len(blob)),
        "sz3_bytes": int(sz3_bytes),
        "gain_sz3_over_ours": float(sz3_bytes / len(blob)),
        "ours_ratio": float(X.nbytes / len(blob)),
        "sz3_ratio": float(X.nbytes / sz3_bytes),
        "ours_maxerr": maxerr,
        "sz3_maxerr": float(sz3_maxerr),
        "K_nonzero_fraction": float(np.mean(K != 0)),
        "geometry": geom,
        "main_parts": main_parts,
        "outlier": {
            "bytes": int(bo[0]),
            "kind": str(bo[1]),
            "tdiff": bool(bo[2]),
            "mode": int(bo[3]),
            "level": int(bo[4]),
        },
        "outer_stream_materialized": True,
        "metadata_contract": "SEG-Y geometry/header side information shared/excluded equally; numeric payload bytes compared",
    }


def forge_whole_gather_codec(path, epsilon=None):
    """Run recovered PR203 sample engine with caller-controlled epsilon."""
    n = forge_ns()
    X, gx, gy, sx, sy, offs, layout = n["load_segy"](path)
    X = np.asarray(X, np.float32)
    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError(("bad epsilon", eps))

    blob, meta = n["encode_samples"](X, gx, gy, sx, sy, offs, eps)
    Y, public_eps, internal_eps, dmeta = n["decode_samples"](
        blob, X.shape[0], X.shape[1], gx, gy, sx, sy, offs
    )
    maxerr = float(np.max(np.abs(X.astype(np.float64) - np.asarray(Y, np.float64))))
    if maxerr > eps * (1.0 + 3e-6):
        raise RuntimeError(("FORGE lattice hard error failure", maxerr, eps))

    best, _ = n["best_sz3_blob"](X, gx, gy, sx, sy, offs, eps)
    szb = int(best[0])
    szme = float(best[4])
    if szme > eps * (1.0 + 3e-6):
        raise RuntimeError(("FORGE matched SZ3 hard error failure", szme, eps))

    return {
        "engine": "forge_wholefile_lattice_pr203",
        "file": os.path.basename(path),
        "shape": list(map(int, X.shape)),
        "epsilon": eps,
        "raw_numeric_bytes": int(X.nbytes),
        "ours_bytes": int(len(blob)),
        "sz3_bytes": szb,
        "gain_sz3_over_ours": float(szb / len(blob)),
        "ours_ratio": float(X.nbytes / len(blob)),
        "sz3_ratio": float(X.nbytes / szb),
        "ours_maxerr": maxerr,
        "sz3_maxerr": szme,
        "sample_meta": meta,
        "decode_meta": dmeta,
        "layout": layout,
        "metadata_contract": "SEG-Y geometry/header side information shared/excluded equally; baseline receives same geometry order dictionary",
    }


def run_soda_files(files, epsilon, historical, out):
    rows = []
    for path in files:
        r = soda_record_codec(path, None if historical else epsilon)
        rows.append(r)
        print("SODA_V2", json.dumps({
            "file": r["file"],
            "epsilon": r["epsilon"],
            "ours_bytes": r["ours_bytes"],
            "sz3_bytes": r["sz3_bytes"],
            "gain": r["gain_sz3_over_ours"],
            "maxerr": r["ours_maxerr"],
        }), flush=True)
    result = {
        "kind": "master-portfolio-v2-soda-recovery-regression",
        "epsilon_mode": "per-file-historical" if historical else "survey-global-external",
        "external_epsilon": None if historical else float(epsilon),
        "rows": rows,
        "minimum_gain": float(min(r["gain_sz3_over_ours"] for r in rows)),
        "median_gain": float(np.median([r["gain_sz3_over_ours"] for r in rows])),
        "byte_weighted_gain": float(sum(r["sz3_bytes"] for r in rows) / sum(r["ours_bytes"] for r in rows)),
        "all_valid": True,
    }
    Path(out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("soda-files")
    s.add_argument("--files", nargs="+", required=True)
    s.add_argument("--epsilon", type=float)
    s.add_argument("--historical-per-file-epsilon", action="store_true")
    s.add_argument("--out", required=True)

    f = sub.add_parser("forge-one")
    f.add_argument("--file", required=True)
    f.add_argument("--epsilon", type=float)
    f.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "soda-files":
        if not args.historical_per_file_epsilon and args.epsilon is None:
            raise SystemExit("--epsilon required unless --historical-per-file-epsilon")
        run_soda_files(args.files, args.epsilon, args.historical_per_file_epsilon, args.out)
    else:
        r = forge_whole_gather_codec(args.file, args.epsilon)
        Path(args.out).write_text(json.dumps(r, indent=2))
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
