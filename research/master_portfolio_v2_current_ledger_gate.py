#!/usr/bin/env python3
"""Current-evidence-aware fail-closed governance gate for Master Portfolio V2.

The original PR491 ledger captured the audit state at an earlier point in time.
This gate applies the explicit correction overlay, preserves all historical
negative/near-miss facts, and additionally requires the completed pinned current
protocol evidence. Dataset labels are never used for active routing.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "benchmarks"

ALLOWED_STATUSES = {
    "RECOVERED", "PRESENT_BUT_REDUCED_IN_V1", "PRESENT_IN_V1",
    "QUARANTINED_COMPARATOR_PROOF_MISSING", "AUDITED_RESEARCH_ONLY",
}
NON_ACTIVE = {"QUARANTINED_COMPARATOR_PROOF_MISSING", "AUDITED_RESEARCH_ONLY"}


def load(name):
    return json.loads((B / name).read_text(encoding="utf-8"))


def require(ok, msg):
    if not ok:
        raise SystemExit("V2 CURRENT LEDGER GATE FAILED: " + msg)


def corrected_engines():
    ledger = load("seismic_master_engine_ledger_v2.json")
    corr = load("seismic_ledger_corrections_v2.json")
    engines = copy.deepcopy(ledger.get("engines", []))
    by_id = {e["id"]: e for e in engines}
    for ov in corr.get("overrides", []):
        require(ov.get("id") in by_id, f"overlay targets unknown engine {ov.get('id')}")
        for k, v in ov.items():
            if k != "id":
                by_id[ov["id"]][k] = copy.deepcopy(v)
    for e in corr.get("append_engines", []):
        require(e.get("id") not in by_id, f"append duplicates engine {e.get('id')}")
        engines.append(copy.deepcopy(e))
        by_id[e["id"]] = engines[-1]
    return ledger, engines, by_id


def main():
    ledger, engines, by_id = corrected_engines()
    protected = load("seismic_protected_winners_v2.json")
    audit = load("seismic_historical_lineage_audit_v2.json")
    supplement = load("seismic_lineage_recovery_supplement_v2.json")
    current = load("seismic_current_protocol_evidence_v2.json")

    ids = [e.get("id") for e in engines]
    require(len(ids) == len(set(ids)), "duplicate corrected engine id")
    for e in engines:
        require(e.get("status") in ALLOWED_STATUSES, f"bad status for {e.get('id')}")
        require(e.get("family"), f"missing family for {e.get('id')}")
        require(e.get("native_scope"), f"missing native_scope for {e.get('id')}")
        require(e.get("source"), f"missing source provenance for {e.get('id')}")

    protected_ids = [p["id"] for p in protected.get("protected", [])]
    require(len(protected_ids) == len(set(protected_ids)), "duplicate protected id")
    for eid in protected_ids:
        require(eid in by_id, f"protected winner missing from corrected ledger: {eid}")
        require(by_id[eid]["status"] not in NON_ACTIVE, f"protected winner demoted: {eid}")

    audits = {a["lineage"]: a for a in audit.get("audits", [])}
    require(audits["pulse_v1_stage_ab_pr29"]["source"].get("pr") == 29, "PULSE provenance drift")
    require(audits["pulse_v1_stage_ab_pr29"]["exact_result"].get("output_bytes") == 11376848, "PULSE bytes drift")
    require(by_id["pulse_v1_stage_ab_pr29"]["status"] == "QUARANTINED_COMPARATOR_PROOF_MISSING", "PULSE premature promotion")

    sub = audits["forge_analytic_subband_hpez_pr93"]
    require(sub["best_exact_result"].get("output_bytes") == 263192, "analytic subband bytes drift")
    require(sub["matched_controls"]["official_hpez_best_orientation"].get("bytes") == 234700, "analytic HPEZ control drift")
    require(by_id["forge_analytic_subband_hpez_pr93"]["status"] == "AUDITED_RESEARCH_ONLY", "analytic subband premature promotion")

    topn = audits["spectral_topn_pr56_pr100_pr101"]
    require(topn["brady_pr56"]["best"].get("output_bytes") == 12025, "Top-N Brady bytes drift")
    require(topn["brady_pr56"]["matched_sz3"].get("bytes") == 28664, "Top-N Brady SZ3 drift")
    require(topn["brady_pr56"].get("gain_vs_sz3", 0) > 2.0, "Top-N Brady win lost")
    require(topn["forge_pr100"]["best"].get("output_bytes") > topn["forge_pr100"]["matched_sz3"].get("bytes"), "Top-N FORGE negative lost")
    require(any(r["topn_bytes"] > r["sz3_bytes"] for r in topn["soda_pr101"].get("rows", [])), "Top-N Soda transfer loss lost")

    whole = audits["soda_whole_segy_container_pr171"]
    wr = whole["exact_result"]
    hostile = whole["matched_controls"]["hostile_whole_file_accounting"]
    require(wr.get("container_bytes") == 69787 and wr.get("headers_bit_exact") is True, "PR171 historical proof drift")
    require(hostile.get("clears_strict_2x") is False, "PR171 historical p75 near-miss rewritten")
    require(1.99 < float(hostile.get("gain_vs_ours", 0)) < 2.0, "PR171 historical p75 ratio drift")

    supplemental = {x["id"]: x for x in supplement.get("lineages", [])}
    mh = supplemental["marine_anchor_carrier_pr6"]
    require(mh["source"].get("pr") == 6, "marine historical provenance drift")
    rows = {(r["dataset"], float(r["epsilon"])): r for r in mh.get("historical_exact_results", [])}
    require(len(rows) == 6, "marine six historical rows missing")
    require(rows[("F1", 1.0)]["carrier_bytes"] == 1368582, "marine F1 historical bytes drift")
    require(rows[("Tie", 1.0)]["carrier_bytes"] == 1209511, "marine Tie historical bytes drift")
    require(rows[("F1", 2.0)]["gain_vs_sz3"] > 4.0 and rows[("Tie", 2.0)]["gain_vs_sz3"] > 4.0, "marine historical >4x evidence lost")

    cur = {x["id"]: x for x in current.get("completed_evidence", [])}
    marine = cur["marine_anchor_carrier_pr6_current_protocol"]
    require(marine.get("status") == "CURRENT_PROTOCOL_PROVEN_WINNER", "marine current proof missing")
    require(marine["aggregate"].get("minimum_gain_vs_sz3", 0) > 3.8, "marine current SZ3 gain drift")
    require(marine["aggregate"].get("minimum_gain_vs_hpez", 0) > 2.0, "marine current strongest-baseline >2x proof lost")
    require(marine["aggregate"].get("all_hard_error_valid") is True, "marine hard-error proof lost")
    require(marine["aggregate"].get("all_decodes_verified") is True, "marine decode proof lost")
    require(by_id["marine_anchor_carrier_pr6"]["status"] == "RECOVERED", "marine not active in corrected ledger")

    soda171 = cur["soda_whole_segy_container_pr171_current_protocol"]
    require(soda171.get("status") == "CURRENT_PROTOCOL_PROVEN_WINNER", "PR171 current proof missing")
    require(soda171["aggregate"].get("wins_over_2x") == 3, "PR171 3/3 current wins lost")
    require(soda171["aggregate"].get("minimum_gain", 0) > 2.0, "PR171 current >2x proof lost")
    require(soda171["aggregate"].get("all_headers_bit_exact") is True, "PR171 current header proof lost")
    require(soda171["aggregate"].get("all_hard_error_valid") is True, "PR171 current error proof lost")

    p45 = cur["soda_record_run_lattice_pr169_vs_frozen_v1_p45"]
    require(p45.get("native_bytes") == 87275 and p45.get("frozen_v1_fallback_bytes") == 169993, "p45 native-vs-V1 bytes drift")
    require(p45.get("selected_is_no_worse_than_v1") is True, "V2 monotonicity proof lost")

    band = supplemental["forge_critically_sampled_bandcore_pr91"]
    require(band.get("status") == "AUDITED_RESEARCH_ONLY", "FORGE band-core promotion without re-audit")
    require(band["best_exact_result"].get("bytes") == 272522, "FORGE band-core bytes drift")

    causal = supplemental["imperial_sparse_causal_law_pr310_pr313"]
    require(causal.get("status") == "AUDITED_RESEARCH_ONLY", "Imperial causal-law promotion without re-audit")
    require(causal["pr313_hard_region_exact"].get("codelength_shaped_bytes") == 2638815, "Imperial PR313 bytes drift")

    g = ledger.get("governance", {})
    require(g.get("dataset_label_routing_forbidden") is True, "dataset-label routing ban removed")
    require(g.get("selection_must_be_decoder_visible_and_byte_charged") is True, "byte charging invariant removed")
    require(g.get("promotion_requires_matched_strongest_baseline") is True, "strongest-baseline rule removed")

    print(json.dumps({
        "ok": True,
        "corrected_ledger_engines": len(engines),
        "protected_winners": protected_ids,
        "current_protocol_proven": [
            "marine_anchor_carrier_pr6",
            "soda_whole_segy_container_pr171",
            "soda_record_run_lattice_pr169_vs_frozen_v1_p45"
        ]
    }, indent=2))


if __name__ == "__main__":
    main()
