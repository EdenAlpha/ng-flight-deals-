#!/usr/bin/env python3
"""Protect exact negative lineage evidence from historical amnesia."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmarks" / "seismic_negative_lineage_audit_v2.json"


def req(ok, msg):
    if not ok:
        raise SystemExit("V2 NEGATIVE AUDIT GATE FAILED: " + msg)


def main():
    data = json.loads(AUDIT.read_text())
    rows = {r["id"]: r for r in data.get("lineages", [])}

    w = rows.get("forge_wavelet_surface_annihilator_pr59")
    req(w is not None, "PR59 wavelet-annihilator audit missing")
    req(w.get("status") == "AUDITED_RESEARCH_ONLY", "PR59 must remain research-only without explicit re-audit")
    req(w["matched_sz3"].get("bytes") == 266939, "PR59 SZ3 control drift")
    req(w["best_valid"].get("bytes") == 478813, "PR59 best exact bytes drift")
    req(w["best_valid"]["bytes"] > w["matched_sz3"]["bytes"], "PR59 classification changed; re-audit before promotion")

    a = rows.get("forge_reflector_atlas_pr65")
    req(a is not None, "PR65 reflector-atlas audit missing")
    req(a.get("status") == "AUDITED_RESEARCH_ONLY", "PR65 must remain research-only without explicit re-audit")
    req(a["matched_sz3"].get("bytes") == 266939, "PR65 SZ3 control drift")
    req(a["best_valid"].get("bytes") == 519145, "PR65 best exact bytes drift")
    req(a["best_valid"]["bytes"] > a["matched_sz3"]["bytes"], "PR65 classification changed; re-audit before promotion")

    m = rows.get("forge_multiscale_wavelet_certificate_pr68")
    req(m is not None and m.get("status") == "NO_COMPLETED_EXACT_RESULT", "PR68 cancelled lineage must not become a remembered winner")
    req(m["source"].get("conclusion") == "cancelled", "PR68 historical workflow conclusion drift")

    h = rows.get("forge_tracked_reflector_surface_atlas_pr85")
    req(h is not None and h.get("status") == "NO_COMPLETED_EXACT_RESULT", "PR85 failed lineage must not become a remembered winner")
    req(h["source"].get("conclusion") == "failure", "PR85 historical workflow conclusion drift")

    print(json.dumps({"ok": True, "negative_lineages": sorted(rows)}, indent=2))


if __name__ == "__main__":
    main()
