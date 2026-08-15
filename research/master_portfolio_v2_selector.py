#!/usr/bin/env python3
"""Fail-closed dominance selector for Master Portfolio V2.

A byte count is comparable only when candidates reconstruct the same object,
under the same reconstruction contract, metadata/accounting policy, and public
hard-error epsilon.  V2 therefore refuses cross-contract comparisons rather
than allowing a numerically smaller stream to win by reconstructing less data
or receiving more free side information.

The selector contains no survey/dataset routing rules.  Once a homogeneous
comparison domain is established, exact charged valid stream bytes decide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any
import math


@dataclass(frozen=True)
class Candidate:
    engine: str
    object_id: str
    contract_id: str
    accounting_id: str
    stream_bytes: int
    max_abs_error: float
    epsilon: float
    decode_verified: bool
    eligible: bool = True
    scope_rank: int = 0
    payload: Any = None

    @property
    def comparison_domain(self):
        return (self.object_id, self.contract_id, self.accounting_id)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "Candidate":
        # Deliberately no defaults for object/contract/accounting.  A candidate
        # whose fairness domain was not stated is not safe to compare.
        return cls(
            engine=str(row["engine"]),
            object_id=str(row["object_id"]),
            contract_id=str(row["contract_id"]),
            accounting_id=str(row["accounting_id"]),
            stream_bytes=int(row["stream_bytes"]),
            max_abs_error=float(row["max_abs_error"]),
            epsilon=float(row["epsilon"]),
            decode_verified=bool(row["decode_verified"]),
            eligible=bool(row.get("eligible", True)),
            scope_rank=int(row.get("scope_rank", 0)),
            payload=row.get("payload"),
        )


def _valid(c: Candidate) -> bool:
    if not c.engine or not c.object_id or not c.contract_id or not c.accounting_id:
        return False
    if not c.eligible or not c.decode_verified:
        return False
    if c.stream_bytes <= 0:
        return False
    if not math.isfinite(c.epsilon) or c.epsilon <= 0:
        return False
    if not math.isfinite(c.max_abs_error) or c.max_abs_error < 0:
        return False
    # Tiny relative allowance only for floating-point verification noise; this
    # is not additional distortion budget.
    return c.max_abs_error <= c.epsilon * (1.0 + 3e-6)


def _normalize(candidates):
    return [c if isinstance(c, Candidate) else Candidate.from_mapping(c) for c in candidates]


def _same_epsilon(rows):
    if not rows:
        return True
    e0 = rows[0].epsilon
    return all(math.isclose(c.epsilon, e0, rel_tol=1e-12, abs_tol=0.0) for c in rows[1:])


def comparison_groups(candidates: Iterable[Candidate | Mapping[str, Any]]):
    """Return candidates grouped by explicit fairness/completeness domain."""
    normalized = _normalize(candidates)
    groups = {}
    for c in normalized:
        groups.setdefault(c.comparison_domain, []).append(c)
    return groups


def select_smallest_valid(
    candidates: Iterable[Candidate | Mapping[str, Any]],
    *,
    object_id: str | None = None,
    contract_id: str | None = None,
    accounting_id: str | None = None,
) -> Candidate:
    """Return the smallest independently valid stream in one fair domain.

    If no explicit domain is supplied, all candidates must already belong to
    one comparison domain.  This is intentionally fail-closed: PR169-style
    numeric-payload streams cannot be compared directly with PR171-style
    complete-file streams, and streams using different metadata freebies cannot
    compete merely because their integer byte counts are smaller.
    """
    normalized = _normalize(candidates)
    if not normalized:
        raise ValueError("empty candidate set")

    any_filter = object_id is not None or contract_id is not None or accounting_id is not None
    if any_filter:
        chosen = [
            c for c in normalized
            if (object_id is None or c.object_id == object_id)
            and (contract_id is None or c.contract_id == contract_id)
            and (accounting_id is None or c.accounting_id == accounting_id)
        ]
        if not chosen:
            raise ValueError("no candidates in requested comparison domain")
    else:
        domains = {c.comparison_domain for c in normalized}
        if len(domains) != 1:
            raise ValueError(
                "mixed comparison domains; normalize accounting or select an explicit domain: "
                + repr(sorted(domains))
            )
        chosen = normalized

    domains = {c.comparison_domain for c in chosen}
    if len(domains) != 1:
        raise ValueError("requested filter still spans multiple comparison domains: " + repr(sorted(domains)))
    if not _same_epsilon(chosen):
        raise ValueError("candidate epsilon mismatch inside one comparison domain")

    valid = [c for c in chosen if _valid(c)]
    if not valid:
        raise ValueError("no fully valid eligible candidate stream in comparison domain")

    # Bytes dominate. Native scope is only a deterministic tie-break at exactly
    # equal bytes; engine id is the final stable tie-break.
    return min(valid, key=lambda c: (c.stream_bytes, -c.scope_rank, c.engine))


def dominance_report(candidates: Iterable[Candidate | Mapping[str, Any]], **domain):
    normalized = _normalize(candidates)
    winner = select_smallest_valid(normalized, **domain)
    rows = []
    for c in normalized:
        comparable = c.comparison_domain == winner.comparison_domain and math.isclose(
            c.epsilon, winner.epsilon, rel_tol=1e-12, abs_tol=0.0
        )
        rows.append({
            "engine": c.engine,
            "object_id": c.object_id,
            "contract_id": c.contract_id,
            "accounting_id": c.accounting_id,
            "stream_bytes": c.stream_bytes,
            "valid": _valid(c),
            "comparable_to_winner": comparable,
            "eligible": c.eligible,
            "decode_verified": c.decode_verified,
            "max_abs_error": c.max_abs_error,
            "epsilon": c.epsilon,
            "scope_rank": c.scope_rank,
            "bytes_over_winner": c.stream_bytes - winner.stream_bytes if comparable else None,
            "factor_vs_winner": c.stream_bytes / winner.stream_bytes if comparable and c.stream_bytes > 0 else None,
        })
    return {
        "winner": winner.engine,
        "winner_bytes": winner.stream_bytes,
        "object_id": winner.object_id,
        "contract_id": winner.contract_id,
        "accounting_id": winner.accounting_id,
        "epsilon": winner.epsilon,
        "candidates": rows,
    }


def _c(engine, nbytes, err, eps, ok, *, eligible=True, rank=0, obj="sha256:test", contract="numeric_payload", accounting="shared_headers_excluded"):
    return Candidate(engine, obj, contract, accounting, nbytes, err, eps, ok, eligible=eligible, scope_rank=rank)


def _self_test():
    eps = 0.1
    rows = [
        _c("whole_record", 1000, 0.099999, eps, True, rank=2),
        _c("panel_fallback", 1400, 0.09, eps, True, rank=1),
        _c("invalid_too_small", 400, 0.1001, eps, True, rank=3),
        _c("undecodable", 300, 0.01, eps, False, rank=3),
        _c("ineligible", 200, 0.01, eps, True, eligible=False, rank=3),
    ]
    assert select_smallest_valid(rows).engine == "whole_record"

    # A genuinely smaller fully valid competitor must win, regardless of family.
    rows.append(_c("new_valid_breakthrough", 700, 0.08, eps, True))
    assert select_smallest_valid(rows).engine == "new_valid_breakthrough"

    # Equal-byte tie: scope rank matters only after byte equality.
    tie = [_c("panel", 500, 0.01, eps, True, rank=1), _c("whole", 500, 0.01, eps, True, rank=2)]
    assert select_smallest_valid(tie).engine == "whole"

    # A complete-file stream is NOT byte-comparable with a numeric-only stream.
    mixed = [
        _c("numeric", 100, 0.01, eps, True),
        _c("whole_file", 90, 0.01, eps, True, contract="complete_segy", accounting="self_contained"),
    ]
    try:
        select_smallest_valid(mixed)
    except ValueError as e:
        assert "mixed comparison domains" in str(e)
    else:
        raise AssertionError("cross-contract candidate comparison was accepted")
    assert select_smallest_valid(mixed, contract_id="complete_segy", accounting_id="self_contained").engine == "whole_file"

    # Same output but unequal metadata-accounting rules must also fail closed.
    mixed_accounting = [
        _c("fair", 100, 0.01, eps, True),
        _c("more_freebies", 80, 0.01, eps, True, accounting="geometry_and_headers_free"),
    ]
    try:
        select_smallest_valid(mixed_accounting)
    except ValueError:
        pass
    else:
        raise AssertionError("mixed accounting policies were compared")

    # Different objects and different epsilons can never race on bytes.
    try:
        select_smallest_valid([_c("a", 100, 0.01, eps, True), _c("b", 90, 0.01, eps, True, obj="sha256:other")])
    except ValueError:
        pass
    else:
        raise AssertionError("different source objects were compared")
    try:
        select_smallest_valid([_c("a", 100, 0.01, eps, True), _c("b", 90, 0.01, 0.2, True)])
    except ValueError as e:
        assert "epsilon mismatch" in str(e)
    else:
        raise AssertionError("different public epsilons were compared")

    try:
        select_smallest_valid([_c("bad", 1, 1.0, eps, True)])
    except ValueError:
        pass
    else:
        raise AssertionError("fail-closed selector accepted no-valid-candidate set")

    print("MASTER_PORTFOLIO_V2_SELECTOR_SELF_TEST_OK")


if __name__ == "__main__":
    _self_test()
