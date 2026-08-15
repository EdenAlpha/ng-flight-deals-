#!/usr/bin/env python3
"""Static monotonicity invariants for Master Portfolio V2.

The protected V1 floor is meaningful only if it is the *exact frozen V1 code*,
not a later implementation reusing the same engine name.  Git blob identities
are recomputed from repository bytes so silent source/config drift fails closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks" / "seismic_master_engine_ledger_v2.json"
PROTECTED = ROOT / "benchmarks" / "seismic_protected_winners_v2.json"
V1_SOURCE = ROOT / "research" / "general_seismic_codec_portfolio.py"
V1_CONFIG = ROOT / "benchmarks" / "general_seismic_codec_portfolio_v1.json"

EXPECTED_V1_SOURCE_GIT_BLOB = "70b6d9e9975b7c7acc805fa0b8aca661bc5e9782"
EXPECTED_V1_CONFIG_GIT_BLOB = "c86bd111d8f2817adf5d2b30c792a737d327a23e"
FLOOR_ID = "general_seismic_portfolio_v1_panel_fallback"
EXPECTED_DOMAIN_KEYS = [
    "source_object_identity",
    "reconstructed_information_contract",
    "metadata_accounting_policy",
    "public_epsilon",
]


def git_blob_sha1(path: Path) -> str:
    b = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(b)}\0".encode("ascii"))
    h.update(b)
    return h.hexdigest()


def require(ok, msg):
    if not ok:
        raise SystemExit("V2 MONOTONICITY GATE FAILED: " + msg)


def main():
    ledger = json.loads(LEDGER.read_text())
    protected = json.loads(PROTECTED.read_text())
    cfg = json.loads(V1_CONFIG.read_text())

    require(git_blob_sha1(V1_SOURCE) == EXPECTED_V1_SOURCE_GIT_BLOB, "frozen V1 codec source drifted")
    require(git_blob_sha1(V1_CONFIG) == EXPECTED_V1_CONFIG_GIT_BLOB, "frozen V1 portfolio config drifted")

    by_id = {e["id"]: e for e in ledger.get("engines", [])}
    require(FLOOR_ID in by_id, "V1 floor missing from master ledger")
    floor = by_id[FLOOR_ID]
    require(floor.get("status") == "PRESENT_IN_V1", "V1 floor status changed")
    src = floor.get("source", {})
    require(src.get("branch") == "general-seismic-codec-portfolio-v1", "V1 floor source branch drifted")
    require(src.get("codec") == "research/general_seismic_codec_portfolio.py", "V1 floor codec pointer drifted")
    require(src.get("frozen_config") == "benchmarks/general_seismic_codec_portfolio_v1.json", "V1 floor config pointer drifted")
    require(src.get("v2_adapter") == "research/master_portfolio_v2_panel_fallback.py", "V1 floor adapter pointer drifted")

    protected_ids = {x["id"] for x in protected.get("protected", [])}
    require(FLOOR_ID in protected_ids, "V1 floor removed from protected set")

    g = ledger.get("governance", {})
    require(g.get("v1_benchmark_is_immutable") is True, "V1 immutability invariant removed")
    require(g.get("v1_panel_portfolio_is_protected_floor") is True, "V1 protected-floor invariant removed")
    require(g.get("active_engine_must_materialize_decodable_stream") is True, "decodable-stream invariant removed")
    require(g.get("comparison_domain_must_match") == EXPECTED_DOMAIN_KEYS, "comparison-domain fairness invariant changed")

    pc = cfg.get("panel_contract", {})
    require(pc.get("channels_per_panel") == 128, "frozen V1 channel partition changed")
    require(pc.get("time_samples_per_panel") == 8192, "frozen V1 time partition changed")
    require(pc.get("selector_bytes") == 1, "frozen V1 selector-byte accounting changed")
    require(cfg.get("selector", {}).get("no_category_rules") is True, "frozen V1 category-free selection changed")
    candidates = cfg.get("candidates", [])
    require([c.get("id") for c in candidates] == list(range(8)), "frozen V1 candidate ids changed")
    require([c.get("engine") for c in candidates[:3]] == ["ar32_zsm"] * 3, "frozen V1 AR family changed")
    require([c.get("engine") for c in candidates[3:]] == ["spectral_topn"] * 5, "frozen V1 spectral family changed")

    print(json.dumps({
        "ok": True,
        "protected_floor": FLOOR_ID,
        "v1_source_blob": EXPECTED_V1_SOURCE_GIT_BLOB,
        "v1_config_blob": EXPECTED_V1_CONFIG_GIT_BLOB,
        "comparison_domain_keys": EXPECTED_DOMAIN_KEYS,
        "frozen_candidate_ids": list(range(8)),
    }, indent=2))


if __name__ == "__main__":
    main()
