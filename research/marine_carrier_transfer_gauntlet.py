#!/usr/bin/env python3
"""Targeted transfer test of the proven PR6 Marine Carrier on the marine failures.

Uses exactly the same deterministic reservoir panels and survey-global epsilon as
General Seismic All-Engines Gauntlet V1, but evaluates the recovered Marine
Carrier directly. The exact current-protocol M menu from pinned winning run
31877667477 is retained: {16,24,32,40,48,56,64,80,96,128}. Every stream is
self-contained, decoded independently, hard-bound checked, and compared with
matched SZ3 on the same panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

import general_seismic_benchmark_runner as br
import general_seismic_all_engines_gauntlet as gg
import marine_carrier_pr6_v2 as mc
from general_seismic_numeric_io import matched_sz3

# Exact fixed candidate menu used by the pinned current-protocol marine winner
# (run 31877667477): F1 selected M=64 and Tie selected M=96.
M_VALUES = (16, 24, 32, 40, 48, 56, 64, 80, 96, 128)


def hard_error(a, b):
    return float(np.max(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)))) if np.size(a) else 0.0


def run_survey(args):
    manifest = br.load_json(args.manifest)
    pre = br.load_json(args.preflight)
    cfg = br.load_json(args.config)
    ds = br.dataset_def(manifest, args.dataset)
    row = br.dataset_row(pre, args.dataset)

    seed = int.from_bytes(hashlib.sha256(("GAUNTLET-V1:" + ds["id"]).encode()).digest()[:8], "little")
    with tempfile.TemporaryDirectory(prefix="marine_carrier_transfer_") as tmp:
        st, panels = gg.reservoir_stats_and_panels(ds, row, cfg, tmp, None, int(args.sample_panels), seed)

    eps = 0.10 * float(st["std"])
    if not np.isfinite(eps) or eps <= 0 or eps > 1e12:
        raise RuntimeError(("implausible survey epsilon; input decoding must be audited", ds["id"], st["std"], eps))

    print("MARINE_CARRIER_EPSILON", ds["id"], st["std"], eps, "sampled", len(panels), "of", st["panels"], flush=True)

    total_carrier = 0
    total_sz3 = 0
    total_samples = 0
    maxerr = 0.0
    sz3_maxerr = 0.0
    winner_m = {str(m): 0 for m in M_VALUES}
    panel_rows = []

    for rank, (source_panel_index, P, meta) in enumerate(panels):
        X = np.ascontiguousarray(P, dtype=np.float32)[None, :, :]

        # Fail loudly rather than permit historical int16 conversion to wrap.
        anchor_ratio = np.max(np.abs(X.astype(np.float64) / eps)) if X.size else 0.0
        if anchor_ratio >= 32760:
            raise RuntimeError(("marine carrier int16 anchor range unsafe", ds["id"], source_panel_index, anchor_ratio))

        best, candidates = mc.compete(X, eps, M_VALUES)
        blob = mc.encode_array(X, eps, int(best["M"]))
        R3, decoded_meta = mc.decode_stream(blob)
        me = hard_error(X, R3)
        if me > eps * (1.0 + 3e-6):
            raise RuntimeError(("marine carrier hard-bound", ds["id"], source_panel_index, me, eps))

        sb, sme = matched_sz3(P, eps)
        if float(sme) > eps * (1.0 + 3e-6):
            raise RuntimeError(("SZ3 hard-bound", ds["id"], source_panel_index, sme, eps))

        cb = len(blob)
        total_carrier += cb
        total_sz3 += int(sb)
        total_samples += int(P.size)
        maxerr = max(maxerr, me)
        sz3_maxerr = max(sz3_maxerr, float(sme))
        winner_m[str(int(best["M"]))] += 1

        row_out = {
            "sample_rank": int(rank),
            "source_panel_index": int(source_panel_index),
            "shape": list(map(int, P.shape)),
            "samples": int(P.size),
            "carrier_bytes": int(cb),
            "sz3_bytes": int(sb),
            "gain_vs_sz3": float(sb / cb),
            "maxerr": float(me),
            "sz3_maxerr": float(sme),
            "best_M": int(best["M"]),
            "candidate_bytes": {str(int(c["M"])): int(c["bytes"]) for c in candidates},
            "decoded_meta": decoded_meta,
        }
        panel_rows.append(row_out)
        print("MARINE_CARRIER_PANEL", ds["id"], source_panel_index, "SZ3", int(sb), "CARRIER", cb, "M", int(best["M"]), "GAIN", float(sb / cb), flush=True)

    result = {
        "kind": "marine-carrier-transfer-gauntlet-v2-exact-menu",
        "dataset_id": ds["id"],
        "epsilon": float(eps),
        "std": float(st["std"]),
        "sampled_panels": len(panels),
        "total_source_panels": int(st["panels"]),
        "samples": int(total_samples),
        "carrier_bytes": int(total_carrier),
        "sz3_bytes": int(total_sz3),
        "carrier_bps": float(8.0 * total_carrier / total_samples),
        "sz3_bps": float(8.0 * total_sz3 / total_samples),
        "gain_vs_sz3": float(total_sz3 / total_carrier),
        "reduction_percent_vs_sz3": float(100.0 * (1.0 - total_carrier / total_sz3)),
        "maxerr": float(maxerr),
        "sz3_maxerr": float(sz3_maxerr),
        "winner_M_counts": winner_m,
        "exact_current_protocol_M_menu": list(M_VALUES),
        "reference_winning_run": 31877667477,
        "same_reservoir_seed_as_all_engines_gauntlet": True,
        "all_streams_materialized_and_decoded": True,
        "panels": panel_rows,
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "panels"}, indent=2), flush=True)


def aggregate(args):
    rows = []
    for p in sorted(Path(args.results).glob("*.json")):
        rows.append(json.loads(p.read_text()))
    out = {
        "kind": "marine-carrier-transfer-headline-v2-exact-menu",
        "surveys": [
            {
                "dataset_id": r["dataset_id"],
                "gain_vs_sz3": r["gain_vs_sz3"],
                "reduction_percent_vs_sz3": r["reduction_percent_vs_sz3"],
                "carrier_bps": r["carrier_bps"],
                "sz3_bps": r["sz3_bps"],
                "sampled_panels": r["sampled_panels"],
            }
            for r in rows
        ],
        "wins": sum(float(r["gain_vs_sz3"]) > 1.0 for r in rows),
        "complete_surveys": len(rows),
        "median_gain": float(np.median([r["gain_vs_sz3"] for r in rows])) if rows else None,
        "byte_weighted_gain": float(sum(r["sz3_bytes"] for r in rows) / sum(r["carrier_bytes"] for r in rows)) if rows else None,
        "exact_current_protocol_M_menu": list(M_VALUES),
        "reference_winning_run": 31877667477,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("survey")
    s.add_argument("--manifest", required=True)
    s.add_argument("--preflight", required=True)
    s.add_argument("--config", required=True)
    s.add_argument("--dataset", required=True)
    s.add_argument("--sample-panels", type=int, default=48)
    s.add_argument("--out", required=True)
    a = sp.add_parser("aggregate")
    a.add_argument("--results", required=True)
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "survey":
        run_survey(args)
    else:
        aggregate(args)


if __name__ == "__main__":
    main()
