#!/usr/bin/env python3
"""Master Portfolio V2 adapter for the exact PR #171 whole-SEG-Y Soda codec.

This adapter deliberately reuses the historical standalone implementation that
already exists in the repository. It does not recreate the codec. The only
protocol change is that epsilon may be supplied externally so the exact same
whole-file engine can be judged under the V2 survey-global error contract.

The resulting candidate stream is a real self-contained file container:
  * global + trace headers are losslessly carried,
  * original trace order is restored,
  * IBM format-1 or IEEE format-5 samples are materialized,
  * the reconstructed SEG-Y is independently reopened and checked,
  * exact charged container bytes decide portfolio competition.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import tempfile

import numpy as np
import segyio

import master_portfolio_v2 as portfolio


_IMPL = None


def standalone_impl():
    """Load PR171's safe standalone wrapper exactly from repository source."""
    global _IMPL
    if _IMPL is None:
        path = Path("research/soda_record_standalone_safe.py")
        spec = importlib.util.spec_from_file_location("soda_pr171_v2_recovered", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load PR171 standalone implementation")
        wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        _IMPL = wrapper.m
    return _IMPL


def _read_samples(path):
    with segyio.open(path, "r", ignore_geometry=True) as f:
        X = np.asarray(f.trace.raw[:], np.float32).copy()
        gx = np.asarray(f.attributes(segyio.TraceField.GroupX)[:], np.int64)
        gy = np.asarray(f.attributes(segyio.TraceField.GroupY)[:], np.int64)
        ntr = int(f.tracecount)
        ns = int(len(f.samples))
    return X, gx, gy, ntr, ns


def _headers_exact(original: bytes, reconstructed: bytes, ntr: int, ns: int) -> bool:
    if len(original) != len(reconstructed):
        return False
    if original[:3600] != reconstructed[:3600]:
        return False
    stride = 240 + 4 * ns
    expected = 3600 + ntr * stride
    if len(original) != expected:
        return False
    for i in range(ntr):
        p = 3600 + i * stride
        if original[p:p + 240] != reconstructed[p:p + 240]:
            return False
    return True


def soda_whole_segy_codec(path: str, epsilon: float | None = None):
    """Run exact PR171 whole-file engine with caller-controlled public epsilon."""
    m = standalone_impl()
    raw = Path(path).read_bytes()
    X, gx, gy, ntr, ns = _read_samples(path)

    eps = float(0.10 * X.astype(np.float64).std() if epsilon is None else epsilon)
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError(("bad epsilon", eps))

    fmt = int.from_bytes(raw[3224:3226], "big")
    ns_bin = int.from_bytes(raw[3220:3222], "big")
    if fmt not in (1, 5):
        raise RuntimeError(("unsupported SEG-Y sample format", fmt))
    if ns_bin not in (0, ns):
        raise RuntimeError(("binary ns mismatch", ns_bin, ns))

    # PR171 used a 0.01% internal safety margin for final SEG-Y sample-format
    # rounding. Keep that exact rule while replacing only the public epsilon.
    internal_eps = eps * float(m.SAFETY)
    gh, H = m.split_headers(raw, ntr, ns)
    header_blob, header_diag = m.encode_headers(gh, H)
    sample_blob, sample_diag = m.encode_samples(X, gx, gy, internal_eps)

    file_header = struct.pack(
        m.FILE_HDR,
        m.FILE_MAGIC,
        1,
        ntr,
        ns,
        fmt,
        len(raw),
        len(header_blob),
        len(sample_blob),
    )
    if len(file_header) != int(m.FHS):
        raise RuntimeError(("PR171 file-header accounting drift", len(file_header), m.FHS))
    container = file_header + header_blob + sample_blob

    # Decode from the actual bytes to an actual reconstructed SEG-Y and reopen
    # it. No encoder-side arrays are accepted as proof of fidelity.
    with tempfile.TemporaryDirectory(prefix="soda-pr171-v2-") as td:
        cpath = Path(td) / "shot.srseg"
        rpath = Path(td) / "reconstructed.sgy"
        cpath.write_bytes(container)
        dmeta = m.decode_segc(str(cpath), str(rpath))
        reconstructed = rpath.read_bytes()
        Y, _, _, ntr2, ns2 = _read_samples(str(rpath))

    if ntr2 != ntr or ns2 != ns:
        raise RuntimeError(("reconstructed SEG-Y shape drift", (ntr2, ns2), (ntr, ns)))
    headers_exact = _headers_exact(raw, reconstructed, ntr, ns)
    if not headers_exact:
        raise RuntimeError("PR171 reconstructed non-sample SEG-Y bytes are not bit-exact")

    maxerr = float(np.max(np.abs(X.astype(np.float64) - Y.astype(np.float64))))
    if maxerr > eps * (1.0 + 3e-6):
        raise RuntimeError(("PR171 V2 hard error failure", maxerr, eps))

    # Matched current SZ3 baseline on the identical numeric payload/epsilon.
    # For whole-file accounting, advantage the baseline: give it the exact same
    # losslessly compressed PR171 header blob and file framing, while charging
    # zero bytes for any SZ3-specific sample-container metadata.
    sn = portfolio.soda_ns()
    sz3_bytes, sz3_maxerr = sn["sz3_bytes"](X, eps)
    sz3_bytes = int(sz3_bytes)
    sz3_maxerr = float(sz3_maxerr)
    if sz3_maxerr > eps * (1.0 + 3e-6):
        raise RuntimeError(("matched SZ3 hard error failure", sz3_maxerr, eps))
    optimistic_sz3_whole = int(m.FHS) + len(header_blob) + sz3_bytes

    return {
        "engine": "soda_whole_segy_container_pr171",
        "source_pr": 171,
        "file": os.path.basename(path),
        "shape": [ntr, ns],
        "sample_format": fmt,
        "epsilon": eps,
        "internal_epsilon": internal_eps,
        "original_file_bytes": len(raw),
        "raw_numeric_bytes": int(X.nbytes),
        "ours_whole_file_bytes": len(container),
        "ours_whole_file_ratio": float(len(raw) / len(container)),
        "file_header_bytes": int(m.FHS),
        "header_blob_bytes": len(header_blob),
        "sample_blob_bytes": len(sample_blob),
        "headers_bit_exact": True,
        "ours_maxerr": maxerr,
        "decode_verified": True,
        "matched_sz3_numeric_bytes": sz3_bytes,
        "matched_sz3_maxerr": sz3_maxerr,
        "optimistic_sz3_whole_file_bytes": optimistic_sz3_whole,
        "gain_sz3_over_ours_numeric": float(sz3_bytes / len(sample_blob)),
        "gain_optimistic_sz3_whole_over_ours": float(optimistic_sz3_whole / len(container)),
        "header_diag": header_diag,
        "sample_diag": sample_diag,
        "decode_meta": dmeta,
        "metadata_contract": "real self-contained ours; matched SZ3 receives identical compressed SEG-Y header blob/file framing and is charged zero SZ3 sample metadata",
    }


def run_files(files, epsilon, historical, out):
    rows = []
    for path in files:
        r = soda_whole_segy_codec(path, None if historical else epsilon)
        rows.append(r)
        print("SODA_WHOLE_V2", json.dumps({
            "file": r["file"],
            "epsilon": r["epsilon"],
            "ours_whole_file_bytes": r["ours_whole_file_bytes"],
            "optimistic_sz3_whole_file_bytes": r["optimistic_sz3_whole_file_bytes"],
            "gain": r["gain_optimistic_sz3_whole_over_ours"],
            "maxerr": r["ours_maxerr"],
            "headers_bit_exact": r["headers_bit_exact"],
        }), flush=True)

    gains = [r["gain_optimistic_sz3_whole_over_ours"] for r in rows]
    result = {
        "kind": "master-portfolio-v2-soda-pr171-whole-segy",
        "epsilon_mode": "per-file-historical" if historical else "survey-global-external",
        "external_epsilon": None if historical else float(epsilon),
        "rows": rows,
        "minimum_gain": float(min(gains)),
        "median_gain": float(np.median(gains)),
        "byte_weighted_gain": float(
            sum(r["optimistic_sz3_whole_file_bytes"] for r in rows)
            / sum(r["ours_whole_file_bytes"] for r in rows)
        ),
        "wins_over_2x": int(sum(g > 2.0 for g in gains)),
        "all_valid": bool(all(
            r["headers_bit_exact"]
            and r["decode_verified"]
            and r["ours_maxerr"] <= r["epsilon"] * (1.0 + 3e-6)
            and r["matched_sz3_maxerr"] <= r["epsilon"] * (1.0 + 3e-6)
            for r in rows
        )),
    }
    Path(out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--epsilon", type=float)
    ap.add_argument("--historical-per-file-epsilon", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not args.historical_per_file_epsilon and args.epsilon is None:
        raise SystemExit("--epsilon required unless --historical-per-file-epsilon")
    run_files(args.files, args.epsilon, args.historical_per_file_epsilon, args.out)


if __name__ == "__main__":
    main()
