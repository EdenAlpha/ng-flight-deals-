#!/usr/bin/env python3
"""Cross-survey strongest-engine gauntlet.

Every engine family is run on the SAME deterministic reservoir of canonical
128x8192 benchmark panels for each survey, under the frozen survey-global
absolute-error tolerance. Dataset/category labels NEVER route compression.
Every reported stream is materialized, decoded, hard-bound checked and byte
counted.

Families:
  * Huber AR32 + ZSM (best actual stream over frozen W={4,8,64})
  * expanded exact spectral Top-N (frozen V1 menu + strongest PR56 neighborhood)
  * portable PR169 Soda run-lattice structural stream
  * portable PR203 FORGE state-lattice stream

The two portable adapters deliberately remove survey-name routing and native
SEG-Y geometry assumptions so the structural principles can be tested on every
land/marine/DAS panel. Native geometry-aware engines remain separately
protected in Master Portfolio V2; this file tests cross-survey transfer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np

import general_seismic_benchmark_runner as br
import general_seismic_codec_portfolio as g
import general_seismic_portfolio_optimized as opt
import master_portfolio_v2 as native
from general_seismic_numeric_io import matched_sz3

SODA_MAGIC = b"GSRUN169"
SODA_HDR = "<8sddII"
SODA_HSZ = struct.calcsize(SODA_HDR)
FORGE_MAGIC = b"GSSTA203"
FORGE_HDR = "<8sddII"
FORGE_HSZ = struct.calcsize(FORGE_HDR)


def hard_error(X, R):
    return float(np.max(np.abs(np.asarray(X, np.float64) - np.asarray(R, np.float64)))) if np.size(X) else 0.0


def require_bound(X, R, eps, tag):
    me = hard_error(X, R)
    if me > float(eps) * (1.0 + 3e-6):
        raise RuntimeError((tag, "hard-bound", me, float(eps)))
    return me


def ar_family(P, eps, cfg, source_integer):
    cands = [c for c in cfg["candidates"] if c["engine"] == "ar32_zsm"]
    if P.shape[1] <= 32:
        raise ValueError("AR32 requires >32 time samples")
    prep = opt._prepare_ar(g, P, eps, cands[0], bool(source_integer))
    rows = []
    for c in cands:
        blob, meta = opt._ar_blob(g, prep, int(c["zsm_window"]))
        # V1 selector byte is supplied only to exercise the exact existing decoder;
        # it is not part of this family blob because AR_MAGIC self-identifies it.
        R = g.decode_portfolio(bytes([int(c["id"])]) + blob)
        me = require_bound(P, R, eps, "ar32_zsm")
        rows.append({"bytes": len(blob), "blob": blob, "id": int(c["id"]), "W": int(c["zsm_window"]), "maxerr": me, "meta": meta})
    best = min(rows, key=lambda r: (r["bytes"], r["id"]))
    return {"family": "ar32_zsm", "bytes": int(best["bytes"]), "maxerr": float(best["maxerr"]), "variant": {"W": best["W"], "candidate_id": best["id"]}, "blob": best["blob"]}


def spectral_menu(P, cfg):
    menu = []
    seen = set()
    for c in cfg["candidates"]:
        if c["engine"] != "spectral_topn":
            continue
        key = (int(c["time_block"]), round(float(c["fraction"]), 15))
        if key not in seen:
            seen.add(key); menu.append((key[0], float(c["fraction"]), "v1", None))
    # PR56's audited Brady winner was B=1024,N=256. Add its immediate strong
    # neighborhood while retaining the exact self-contained V1 spectral stream.
    for B, N in [(512,128), (1024,128), (1024,256), (2048,256)]:
        denom = int(P.shape[0]) * (B // 2 + 1)
        frac = min(1.0, float(N) / max(1, denom))
        key = (B, round(frac, 15))
        if key not in seen:
            seen.add(key); menu.append((B, frac, "pr56_neighborhood", N))
    return menu


def spectral_family(P, eps, cfg, source_integer):
    rows = []
    for j, (B, frac, origin, requested_N) in enumerate(spectral_menu(P, cfg)):
        blob, meta = g.encode_spectral_topn(P, eps, int(B), float(frac))
        # Candidate 3 dispatches the exact spectral decoder; B/N live in body.
        R = g.decode_portfolio(bytes([3]) + blob)
        me = require_bound(P, R, eps, "spectral_topn")
        nfull = max(1, int(round(frac * P.shape[0] * (B // 2 + 1))))
        rows.append({"bytes": len(blob), "blob": blob, "B": int(B), "fraction": float(frac), "N": int(nfull), "origin": origin, "requested_N": requested_N, "maxerr": me, "meta": meta, "rank": j})
    best = min(rows, key=lambda r: (r["bytes"], r["rank"]))
    return {"family": "spectral_topn_wide", "bytes": int(best["bytes"]), "maxerr": float(best["maxerr"]), "variant": {k: best[k] for k in ("B","N","fraction","origin","requested_N")}, "blob": best["blob"]}


def soda_portable_decode(blob):
    magic, public_eps, internal_eps, nr, nt = struct.unpack(SODA_HDR, blob[:SODA_HSZ])
    if magic != SODA_MAGIC:
        raise RuntimeError("bad portable Soda magic")
    n = native.soda_ns()
    K = n["decode_main"](blob[SODA_HSZ:])
    if tuple(K.shape) != (1, 1, int(nr), int(nt)):
        raise RuntimeError(("portable Soda shape", K.shape, nr, nt))
    Q = n["undelta"](K, 3).reshape(int(nr), int(nt))
    return Q.astype(np.float64) * (2.0 * float(internal_eps))


def soda_run_lattice_family(P, eps, cfg, source_integer):
    n = native.soda_ns()
    internal = float(eps) * (1.0 - 1e-4)
    step = 2.0 * internal
    Q64 = np.rint(np.asarray(P, np.float64) / step)
    if np.any(Q64 < np.iinfo(np.int32).min) or np.any(Q64 > np.iinfo(np.int32).max):
        raise OverflowError("portable Soda lattice exceeds int32")
    G = Q64.astype(np.int32).reshape(1, 1, int(P.shape[0]), int(P.shape[1]))
    K = n["delta"](G, 3)
    body, parts = n["encode_main_fixed"](K)
    RK = n["decode_main"](body)
    if not np.array_equal(RK, K):
        raise RuntimeError("portable Soda integer decode mismatch")
    blob = struct.pack(SODA_HDR, SODA_MAGIC, float(eps), internal, int(P.shape[0]), int(P.shape[1])) + body
    R = soda_portable_decode(blob)
    me = require_bound(P, R, eps, "run_lattice_pr169_portable")
    return {"family": "run_lattice_pr169_portable", "bytes": int(len(blob)), "maxerr": me, "variant": {"backend": "PR169 frozen", "K_nonzero_fraction": float(np.mean(K != 0)), "main_parts": parts}, "blob": blob}


def forge_portable_decode(blob):
    magic, public_eps, internal_eps, nr, nt = struct.unpack(FORGE_HDR, blob[:FORGE_HSZ])
    if magic != FORGE_MAGIC:
        raise RuntimeError("bad portable FORGE magic")
    n = native.forge_ns()
    oc, orient, K = n["decode_rep"](blob[FORGE_HSZ:])
    if int(oc) != 0 or tuple(K.shape) != (int(nr), int(nt)):
        raise RuntimeError(("portable FORGE shape/order", oc, K.shape, nr, nt))
    Q = np.cumsum(np.asarray(K, np.int32), axis=1, dtype=np.int32)
    return Q.astype(np.float64) * (2.0 * float(internal_eps))


def forge_state_lattice_family(P, eps, cfg, source_integer):
    n = native.forge_ns()
    internal = float(eps) * (1.0 - 1e-4)
    step = 2.0 * internal
    Q64 = np.rint(np.asarray(P, np.float64) / step)
    if np.any(Q64 < np.iinfo(np.int32).min) or np.any(Q64 > np.iinfo(np.int32).max):
        raise OverflowError("portable FORGE lattice exceeds int32")
    Q = Q64.astype(np.int32)
    K = np.empty_like(Q)
    K[:, 0] = Q[:, 0]
    if Q.shape[1] > 1:
        K[:, 1:] = Q[:, 1:] - Q[:, :-1]
    rows = []
    for orient in (0, 1):
        for rep in (0, 1, 2):
            body = n["encode_rep"](K, 0, orient, rep, 19)
            oc, ro, RK = n["decode_rep"](body)
            if int(oc) != 0 or int(ro) != orient or not np.array_equal(RK, K):
                raise RuntimeError(("portable FORGE integer candidate mismatch", orient, rep))
            rows.append((len(body), orient, rep, body))
    nb, orient, rep, body = min(rows, key=lambda x: (x[0], x[1], x[2]))
    blob = struct.pack(FORGE_HDR, FORGE_MAGIC, float(eps), internal, int(P.shape[0]), int(P.shape[1])) + body
    R = forge_portable_decode(blob)
    me = require_bound(P, R, eps, "state_lattice_pr203_portable")
    return {"family": "state_lattice_pr203_portable", "bytes": int(len(blob)), "maxerr": me, "variant": {"orient": int(orient), "rep": int(rep), "inner_bytes": int(nb), "K_nonzero_fraction": float(np.mean(K != 0))}, "blob": blob}


FAMILY_FUNCS = [ar_family, spectral_family, soda_run_lattice_family, forge_state_lattice_family]


def reservoir_stats_and_panels(ds, row, cfg, tmp, cube2mseed, sample_panels, seed):
    q = br.Moments()
    rng = np.random.default_rng(int(seed))
    reservoir = []
    seen = 0
    t0 = time.perf_counter()
    for P, meta in br.iter_panels(ds, row, cfg, tmp, cube2mseed):
        q.add(P); seen += 1
        item = (seen - 1, np.ascontiguousarray(P).copy(), dict(meta))
        if len(reservoir) < sample_panels:
            reservoir.append(item)
        else:
            j = int(rng.integers(0, seen))
            if j < sample_panels:
                reservoir[j] = item
        if seen % 100 == 0:
            print("GAUNTLET_STATS", ds["id"], seen, q.n, flush=True)
    st = q.result(); st["seconds"] = time.perf_counter() - t0
    reservoir.sort(key=lambda x: x[0])
    return st, reservoir


def run_survey(args):
    manifest = br.load_json(args.manifest); pre = br.load_json(args.preflight); cfg = br.load_json(args.config)
    ds = br.dataset_def(manifest, args.dataset); row = br.dataset_row(pre, args.dataset)
    seed = int.from_bytes(hashlib.sha256(("GAUNTLET-V1:" + ds["id"]).encode()).digest()[:8], "little")
    with tempfile.TemporaryDirectory(prefix="all_engines_") as tmp:
        st, panels = reservoir_stats_and_panels(ds, row, cfg, tmp, args.cube2mseed, int(args.sample_panels), seed)
    eps = 0.10 * float(st["std"])
    print("GAUNTLET_EPSILON", ds["id"], st["std"], eps, "sampled", len(panels), "of", st["panels"], flush=True)

    fam_names = ["ar32_zsm", "spectral_topn_wide", "run_lattice_pr169_portable", "state_lattice_pr203_portable"]
    agg = {k: {"bytes": 0, "samples": 0, "valid_panels": 0, "maxerr": 0.0, "failures": []} for k in fam_names}
    sz3_bytes = 0; sz3_samples = 0; sz3_maxerr = 0.0
    master_bytes = 0; master_samples = 0; master_maxerr = 0.0; master_counts = Counter()
    panel_rows = []

    for rank, (source_panel_index, P, meta) in enumerate(panels):
        sb, sme = matched_sz3(P, eps)
        if float(sme) > eps * (1.0 + 3e-6):
            raise RuntimeError(("SZ3 hard-bound", ds["id"], source_panel_index, sme, eps))
        sz3_bytes += int(sb); sz3_samples += int(P.size); sz3_maxerr = max(sz3_maxerr, float(sme))
        pr = {"sample_rank": int(rank), "source_panel_index": int(source_panel_index), "shape": list(map(int, P.shape)), "samples": int(P.size), "source_integer": bool(meta.get("source_integer", False)), "sz3_bytes": int(sb), "sz3_maxerr": float(sme), "families": {}}
        valid = []
        for fn in FAMILY_FUNCS:
            expected_name = {ar_family:"ar32_zsm", spectral_family:"spectral_topn_wide", soda_run_lattice_family:"run_lattice_pr169_portable", forge_state_lattice_family:"state_lattice_pr203_portable"}[fn]
            try:
                r = fn(P, eps, cfg, bool(meta.get("source_integer", False)))
                if r["family"] != expected_name:
                    raise RuntimeError(("family name drift", r["family"], expected_name))
                nbytes = int(r["bytes"]); me = float(r["maxerr"])
                if nbytes <= 0: raise RuntimeError("nonpositive stream")
                agg[expected_name]["bytes"] += nbytes; agg[expected_name]["samples"] += int(P.size); agg[expected_name]["valid_panels"] += 1; agg[expected_name]["maxerr"] = max(agg[expected_name]["maxerr"], me)
                pr["families"][expected_name] = {"valid": True, "bytes": nbytes, "gain_vs_sz3": float(sb / nbytes), "maxerr": me, "variant": r["variant"]}
                valid.append((nbytes, expected_name, r))
            except Exception as e:
                msg = repr(e)
                agg[expected_name]["failures"].append({"source_panel_index": int(source_panel_index), "error": msg})
                pr["families"][expected_name] = {"valid": False, "error": msg}
        if not valid:
            raise RuntimeError(("no valid family", ds["id"], source_panel_index, pr))
        nb, winner, rr = min(valid, key=lambda x: (x[0], x[1]))
        # Re-decode the selected materialized body through its family decoder.
        if winner == "ar32_zsm": R = g.decode_portfolio(bytes([0]) + rr["blob"])
        elif winner == "spectral_topn_wide": R = g.decode_portfolio(bytes([3]) + rr["blob"])
        elif winner == "run_lattice_pr169_portable": R = soda_portable_decode(rr["blob"])
        else: R = forge_portable_decode(rr["blob"])
        mme = require_bound(P, R, eps, "master-selected")
        master_bytes += int(nb); master_samples += int(P.size); master_maxerr = max(master_maxerr, mme); master_counts[winner] += 1
        pr["master"] = {"winner": winner, "bytes": int(nb), "gain_vs_sz3": float(sb / nb), "maxerr": mme}
        panel_rows.append(pr)
        print("GAUNTLET_PANEL", ds["id"], source_panel_index, "SZ3", int(sb), "WIN", winner, int(nb), "GAIN", float(sb/nb), flush=True)

    family_summary = {}
    for name, a in agg.items():
        complete = a["valid_panels"] == len(panels)
        family_summary[name] = {
            "complete": bool(complete), "valid_panels": int(a["valid_panels"]), "sampled_panels": len(panels),
            "bytes": int(a["bytes"]), "samples": int(a["samples"]),
            "bps": (8.0 * a["bytes"] / a["samples"]) if a["samples"] else None,
            "gain_vs_sz3_same_sample": (float(sz3_bytes / a["bytes"]) if complete and a["bytes"] else None),
            "reduction_percent_vs_sz3": (100.0 * (1.0 - a["bytes"] / sz3_bytes) if complete and sz3_bytes else None),
            "maxerr": float(a["maxerr"]), "failures": a["failures"][:20], "failure_count": len(a["failures"])
        }
    out = {
        "benchmark": "general-seismic-all-engines-gauntlet-v1",
        "dataset_id": ds["id"], "name": ds["name"], "category": ds["category"], "format": ds["format"],
        "selected_source_gb": float(row.get("selected_gb", 0.0)),
        "global_stats": st, "epsilon": float(eps), "reservoir_seed": int(seed), "sampled_panels": len(panels),
        "sampling": "deterministic uniform reservoir over every canonical panel encountered during the exact full survey-global statistics pass",
        "sz3": {"bytes": int(sz3_bytes), "samples": int(sz3_samples), "bps": 8.0*sz3_bytes/sz3_samples, "maxerr": float(sz3_maxerr)},
        "families": family_summary,
        "master_selector": {"bytes": int(master_bytes), "samples": int(master_samples), "bps": 8.0*master_bytes/master_samples, "gain_vs_sz3": float(sz3_bytes/master_bytes), "reduction_percent_vs_sz3": 100.0*(1.0-master_bytes/sz3_bytes), "maxerr": float(master_maxerr), "winner_panel_counts": dict(master_counts)},
        "panels": panel_rows,
    }
    br.dump_json(out, args.out); print(json.dumps({"dataset_id": ds["id"], "epsilon": eps, "sampled_panels": len(panels), "families": family_summary, "master_selector": out["master_selector"]}, indent=2), flush=True)
    return out


def aggregate(args):
    rows = []
    for f in sorted(Path(args.results).glob("*.json")):
        try: x = json.loads(f.read_text())
        except Exception: continue
        if isinstance(x, dict) and x.get("benchmark") == "general-seismic-all-engines-gauntlet-v1": rows.append(x)
    ids = {r["dataset_id"] for r in rows}
    if len(rows) != 13 or len(ids) != 13:
        raise RuntimeError(("need 13 unique gauntlet survey results", len(rows), sorted(ids)))
    names = ["ar32_zsm", "spectral_topn_wide", "run_lattice_pr169_portable", "state_lattice_pr203_portable"]
    fs = {}
    for name in names:
        complete = [r for r in rows if r["families"][name]["complete"]]
        gains = [r["families"][name]["gain_vs_sz3_same_sample"] for r in complete]
        fs[name] = {
            "complete_surveys": len(complete), "wins_vs_sz3": int(sum(float(x)>1.0 for x in gains)),
            "median_gain_vs_sz3": float(np.median(gains)) if gains else None,
            "min_gain_vs_sz3": float(min(gains)) if gains else None,
            "max_gain_vs_sz3": float(max(gains)) if gains else None,
            "byte_weighted_gain_vs_sz3": (float(sum(r["sz3"]["bytes"] for r in complete) / sum(r["families"][name]["bytes"] for r in complete)) if complete and sum(r["families"][name]["bytes"] for r in complete) else None)
        }
    mg = [float(r["master_selector"]["gain_vs_sz3"]) for r in rows]
    out = {
        "benchmark": "general-seismic-all-engines-gauntlet-v1", "survey_count": 13,
        "families": fs,
        "master_selector": {"wins_vs_sz3": int(sum(x>1.0 for x in mg)), "win_rate": float(np.mean(np.asarray(mg)>1.0)), "median_gain_vs_sz3": float(np.median(mg)), "min_gain_vs_sz3": float(min(mg)), "max_gain_vs_sz3": float(max(mg)), "byte_weighted_gain_vs_sz3": float(sum(r["sz3"]["bytes"] for r in rows)/sum(r["master_selector"]["bytes"] for r in rows)), "winner_panel_counts": dict(sum((Counter(r["master_selector"]["winner_panel_counts"]) for r in rows), Counter()))},
        "surveys": [{"dataset_id": r["dataset_id"], "selected_source_gb": r["selected_source_gb"], "sampled_panels": r["sampled_panels"], "master_gain": r["master_selector"]["gain_vs_sz3"], "master_winners": r["master_selector"]["winner_panel_counts"], "family_gains": {k:r["families"][k]["gain_vs_sz3_same_sample"] for k in names}} for r in sorted(rows, key=lambda z:z["dataset_id"])]
    }
    Path(args.out).write_text(json.dumps(out, indent=2)); print(json.dumps(out, indent=2)); return out


def self_test():
    try:
        from general_seismic_fast_backend import install
        install(g)
    except Exception as e:
        print("FAST_BACKEND_NOT_INSTALLED", repr(e), flush=True)
    rng = np.random.default_rng(20260817)
    t = np.arange(384, dtype=np.float32)
    P = np.stack([np.sin((0.02+0.0007*c)*t) + 0.03*rng.standard_normal(t.size) for c in range(12)]).astype(np.float32)
    eps = 0.10 * float(P.astype(np.float64).std())
    cfg = json.loads(Path("benchmarks/general_seismic_codec_portfolio_v1.json").read_text())
    rows = []
    for fn in FAMILY_FUNCS:
        r = fn(P, eps, cfg, False); rows.append({"family":r["family"], "bytes":r["bytes"], "maxerr":r["maxerr"]})
    print(json.dumps({"ok": True, "epsilon": eps, "rows": rows}, indent=2))


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("survey"); s.add_argument("--manifest", required=True); s.add_argument("--preflight", required=True); s.add_argument("--config", required=True); s.add_argument("--dataset", required=True); s.add_argument("--sample-panels", type=int, default=48); s.add_argument("--cube2mseed"); s.add_argument("--out", required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--results", required=True); a.add_argument("--out", required=True)
    sub.add_parser("self-test")
    args = ap.parse_args()
    if args.cmd == "survey": run_survey(args)
    elif args.cmd == "aggregate": aggregate(args)
    else: self_test()

if __name__ == "__main__": main()
