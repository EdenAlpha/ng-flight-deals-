#!/usr/bin/env python3
"""Fail-closed governance checks for Master Portfolio V2.

This is deliberately signal-independent. It protects provenance and portfolio
membership rules; it does not route by survey/dataset label and it does not
encode benchmark answers.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks" / "seismic_master_engine_ledger_v2.json"
PROTECTED = ROOT / "benchmarks" / "seismic_protected_winners_v2.json"
AUDIT = ROOT / "benchmarks" / "seismic_historical_lineage_audit_v2.json"

ALLOWED_STATUSES = {
    "RECOVERED",
    "PRESENT_BUT_REDUCED_IN_V1",
    "PRESENT_IN_V1",
    "QUARANTINED_COMPARATOR_PROOF_MISSING",
    "AUDITED_RESEARCH_ONLY",
}
NON_ACTIVE_STATUSES = {
    "QUARANTINED_COMPARATOR_PROOF_MISSING",
    "AUDITED_RESEARCH_ONLY",
}


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit("V2 LEDGER GATE FAILED: " + message)


def main():
    ledger = load(LEDGER)
    protected = load(PROTECTED)
    audit = load(AUDIT)

    engines = ledger.get("engines", [])
    ids = [e.get("id") for e in engines]
    require(all(isinstance(x, str) and x for x in ids), "every engine needs a non-empty id")
    require(len(ids) == len(set(ids)), "duplicate engine id detected")

    by_id = {e["id"]: e for e in engines}
    for engine in engines:
        status = engine.get("status")
        require(status in ALLOWED_STATUSES, f"unknown status {status!r} for {engine['id']}")
        require(engine.get("family"), f"missing family for {engine['id']}")
        require(engine.get("native_scope"), f"missing native_scope for {engine['id']}")
        require(engine.get("source"), f"missing source provenance for {engine['id']}")

    protected_ids = [p["id"] for p in protected.get("protected", [])]
    require(len(protected_ids) == len(set(protected_ids)), "duplicate protected winner id")
    for engine_id in protected_ids:
        require(engine_id in by_id, f"protected historical winner silently removed: {engine_id}")
        require(
            by_id[engine_id]["status"] not in NON_ACTIVE_STATUSES,
            f"protected historical winner silently quarantined/demoted: {engine_id}",
        )

    audits = {a["lineage"]: a for a in audit.get("audits", [])}
    require("pulse_v1_stage_ab_pr29" in audits, "missing recovered PULSE PR29 audit")
    pulse = audits["pulse_v1_stage_ab_pr29"]
    require(pulse["source"].get("pr") == 29, "PULSE provenance regression: must be PR #29")
    require(pulse["exact_result"].get("output_bytes") == 11376848, "PULSE exact-byte evidence drift")
    require(
        by_id.get("pulse_v1_stage_ab_pr29", {}).get("status") == "QUARANTINED_COMPARATOR_PROOF_MISSING",
        "PULSE must remain quarantined until matched comparator proof exists",
    )

    require("forge_analytic_subband_hpez_pr93" in audits, "missing analytic-subband audit")
    sub = audits["forge_analytic_subband_hpez_pr93"]
    require(sub["best_exact_result"].get("output_bytes") == 263192, "analytic-subband exact bytes drift")
    require(sub["matched_controls"]["sz3"].get("bytes") == 266939, "analytic-subband SZ3 control drift")
    require(
        sub["matched_controls"]["official_hpez_best_orientation"].get("bytes") == 234700,
        "analytic-subband strongest HPEZ control drift",
    )
    require(
        sub["best_exact_result"]["output_bytes"] > sub["matched_controls"]["official_hpez_best_orientation"]["bytes"],
        "analytic-subband classification changed; re-audit before promotion",
    )
    require(
        by_id.get("forge_analytic_subband_hpez_pr93", {}).get("status") == "AUDITED_RESEARCH_ONLY",
        "analytic subbands cannot become active without an explicit re-audit",
    )

    governance = ledger.get("governance", {})
    require(governance.get("dataset_label_routing_forbidden") is True, "dataset-label routing ban removed")
    require(governance.get("selection_must_be_decoder_visible_and_byte_charged") is True, "byte-charged selection invariant removed")
    require(governance.get("never_remove_historical_winner_without_explicit_supersession_evidence") is True, "winner retention invariant removed")
    require(governance.get("promotion_requires_matched_strongest_baseline") is True, "strongest-baseline promotion rule removed")

    print(json.dumps({
        "ok": True,
        "ledger_engines": len(engines),
        "protected_winners": protected_ids,
        "quarantined": [e["id"] for e in engines if e["status"] in NON_ACTIVE_STATUSES],
        "audit_entries": sorted(audits),
    }, indent=2))


if __name__ == "__main__":
    main()
