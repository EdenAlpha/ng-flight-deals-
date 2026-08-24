#!/usr/bin/env python3
"""Bounded-memory adapter for the strict all-engine bake-off.

For direct SEG-Y objects too large for the historical whole-file native codecs,
this wrapper downloads the object once to disk, then presents deterministic
contiguous trace slabs to the *unchanged* recovered Soda/FORGE/carrier codecs.
Each slab is independently decoded and hard-bound checked by the historical
codec. Reported bytes are the sum of the historical serialized slab streams plus
an explicit tiny framing charge, so chunking cannot create free metadata.

The frozen survey-global epsilon, SZ3 comparison, panel families, and blind
classifier are untouched. Dataset names are never used to choose an engine.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections import defaultdict

import numpy as np

import master_portfolio_v2_all_engine_bakeoff as legacy


_STREAM_TARGET_BYTES = int(os.environ.get("ALL_ENGINE_NATIVE_STREAM_CHUNK_BYTES", str(256 * 1024 * 1024)))
# The legacy runner's guard is a materialization policy, not a format limit. The
# local file remains on disk; only trace slabs are materialized into NumPy.
os.environ.setdefault("ALL_ENGINE_NATIVE_MAX_OBJECT_BYTES", str(16 * 1024 * 1024 * 1024))


def _copy_trace_slab(src, start: int, stop: int, out_path: str) -> tuple[int, int]:
    import segyio

    count = int(stop - start)
    spec = segyio.spec()
    spec.format = src.format
    spec.sorting = src.sorting
    spec.samples = src.samples
    spec.tracecount = count
    with segyio.create(out_path, spec) as dst:
        dst.text[0] = src.text[0]
        dst.bin = src.bin
        for j, i in enumerate(range(start, stop)):
            dst.header[j] = src.header[i]
            dst.trace[j] = src.trace[i]
        dst.flush()
    return count, len(src.samples)


def _iter_trace_slabs(path: str, tmp: str):
    import segyio

    with segyio.open(path, "r", ignore_geometry=True) as src:
        ntr = int(src.tracecount)
        ns = int(len(src.samples))
        # SEG-Y trace = 240-byte header + samples. Conservatively assume 4-byte
        # samples for sizing even when the on-disk encoding is smaller.
        trace_bytes = max(244, 240 + 4 * ns)
        traces_per = max(1, int((_STREAM_TARGET_BYTES - 3600) // trace_bytes))
        for chunk_id, start in enumerate(range(0, ntr, traces_per)):
            stop = min(ntr, start + traces_per)
            out = os.path.join(tmp, f"native_stream_{chunk_id:05d}.sgy")
            shape = _copy_trace_slab(src, start, stop, out)
            yield chunk_id, start, stop, out, shape
            try:
                os.remove(out)
            except FileNotFoundError:
                pass


def _attempt_native_streaming(path: str, eps: float):
    """Run every recovered native family as a deterministic framed trace stream."""
    totals = defaultdict(lambda: {
        "bytes": 0, "max_abs_error": 0.0, "chunks": 0,
        "samples": 0, "traces": 0, "failures": [], "chunk_summaries": [],
    })
    engine_names = (
        "soda_record_run_lattice_pr169",
        "forge_wholefile_lattice_pr203",
        "marine_anchor_carrier_pr6",
    )

    with tempfile.TemporaryDirectory(prefix="native_stream_slabs_") as tmp:
        for cid, start, stop, slab, shape in _iter_trace_slabs(path, tmp):
            slab_trials = legacy._attempt_native(slab, eps)
            by_engine = {t["engine"]: t for t in slab_trials}
            for engine in engine_names:
                a = totals[engine]
                t = by_engine.get(engine)
                a["chunks"] += 1
                a["traces"] += int(shape[0])
                a["samples"] += int(shape[0] * shape[1])
                if not t or t.get("status") != "valid":
                    a["failures"].append({
                        "chunk": cid, "trace_start": start, "trace_stop": stop,
                        "reason": (t or {}).get("reason", "engine returned no trial"),
                    })
                    continue
                a["bytes"] += int(t["bytes"])
                a["max_abs_error"] = max(a["max_abs_error"], float(t["max_abs_error"]))
                if len(a["chunk_summaries"]) < 8:
                    a["chunk_summaries"].append({
                        "chunk": cid, "trace_start": start, "trace_stop": stop,
                        "bytes": int(t["bytes"]), "max_abs_error": float(t["max_abs_error"]),
                    })
            print("NATIVE_STREAM_PROGRESS", os.path.basename(path), cid, start, stop, flush=True)

    out = []
    # Explicit stream framing: 32-byte file header + 16 bytes per slab for
    # slab length/trace-count. Historical codec headers are already included in
    # each slab's byte count.
    for engine in engine_names:
        a = totals[engine]
        if a["chunks"] <= 0 or a["failures"]:
            out.append({
                "engine": engine,
                "status": "streaming_ineligible_or_failed",
                "reason": "one or more deterministic trace slabs failed the unchanged native codec",
                "chunks": int(a["chunks"]),
                "failures": a["failures"][:8],
            })
            continue
        framing = 32 + 16 * int(a["chunks"])
        charged = int(a["bytes"] + framing)
        out.append({
            "engine": engine,
            "status": "valid",
            "bytes": charged,
            "payload_bytes": int(a["bytes"]),
            "stream_framing_bytes": int(framing),
            "max_abs_error": float(a["max_abs_error"]),
            "shape": [int(a["traces"]), None],
            "samples": int(a["samples"]),
            "chunks": int(a["chunks"]),
            "streaming_adapter": "deterministic_contiguous_trace_slabs_v1",
            "chunk_target_bytes": int(_STREAM_TARGET_BYTES),
            "chunk_summaries": a["chunk_summaries"],
        })
    return out


# Monkey-patch only the native attempt. All scoring/aggregation logic remains
# the strict existing implementation. Small objects are also streamed here so
# the rerun has one uniform native-family semantics and no dataset-name routing.
legacy._attempt_native = _attempt_native_streaming


if __name__ == "__main__":
    legacy.main()
