#!/usr/bin/env python3
"""Generic dominance selector for Master Portfolio V2.

The selector knows nothing about Soda, FORGE, DAS, land, marine, or any dataset
label. Candidate engines run at their own native scope and return independently
verified results. The only optimization criterion here is the number of charged
bytes in a fully valid decoder-usable stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any
import math


@dataclass(frozen=True)
class Candidate:
    engine: str
    stream_bytes: int
    max_abs_error: float
    epsilon: float
    decode_verified: bool
    eligible: bool = True
    scope_rank: int = 0
    payload: Any = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "Candidate":
        return cls(
            engine=str(row["engine"]),
            stream_bytes=int(row["stream_bytes"]),
            max_abs_error=float(row["max_abs_error"]),
            epsilon=float(row["epsilon"]),
            decode_verified=bool(row["decode_verified"]),
            eligible=bool(row.get("eligible", True)),
            scope_rank=int(row.get("scope_rank", 0)),
            payload=row.get("payload"),
        )


def _valid(c: Candidate) -> bool:
    if not c.engine:
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


def select_smallest_valid(candidates: Iterable[Candidate | Mapping[str, Any]]) -> Candidate:
    """Return the smallest independently valid stream.

    Selection is deliberately byte-driven, not prediction-driven. `scope_rank`
    is used only as a deterministic tie-break after exact charged bytes, so a
    panel engine can never displace a smaller valid whole-record stream merely
    because of routing heuristics. The final engine id tie-break makes repeated
    runs deterministic.
    """
    normalized = [c if isinstance(c, Candidate) else Candidate.from_mapping(c) for c in candidates]
    valid = [c for c in normalized if _valid(c)]
    if not valid:
        raise ValueError("no fully valid eligible candidate stream")
    return min(valid, key=lambda c: (c.stream_bytes, -c.scope_rank, c.engine))


def dominance_report(candidates: Iterable[Candidate | Mapping[str, Any]]):
    normalized = [c if isinstance(c, Candidate) else Candidate.from_mapping(c) for c in candidates]
    winner = select_smallest_valid(normalized)
    rows = []
    for c in normalized:
        rows.append({
            "engine": c.engine,
            "stream_bytes": c.stream_bytes,
            "valid": _valid(c),
            "eligible": c.eligible,
            "decode_verified": c.decode_verified,
            "max_abs_error": c.max_abs_error,
            "epsilon": c.epsilon,
            "scope_rank": c.scope_rank,
            "bytes_over_winner": c.stream_bytes - winner.stream_bytes,
            "factor_vs_winner": c.stream_bytes / winner.stream_bytes if c.stream_bytes > 0 else None,
        })
    return {
        "winner": winner.engine,
        "winner_bytes": winner.stream_bytes,
        "candidates": rows,
    }


def _self_test():
    eps = 0.1
    rows = [
        # A protected native-scope winner.
        Candidate("whole_record", 1000, 0.099999, eps, True, scope_rank=2),
        # A larger valid fallback must not replace it.
        Candidate("panel_fallback", 1400, 0.09, eps, True, scope_rank=1),
        # A smaller stream that fails the hard-error contract must never win.
        Candidate("invalid_too_small", 400, 0.1001, eps, True, scope_rank=3),
        # A smaller stream that cannot decode must never win.
        Candidate("undecodable", 300, 0.01, eps, False, scope_rank=3),
        # An ineligible engine cannot route itself in by label or wishful logic.
        Candidate("ineligible", 200, 0.01, eps, True, eligible=False, scope_rank=3),
    ]
    w = select_smallest_valid(rows)
    assert w.engine == "whole_record", w

    # A genuinely smaller fully valid competitor must win, regardless of family.
    rows.append(Candidate("new_valid_breakthrough", 700, 0.08, eps, True, scope_rank=0))
    w2 = select_smallest_valid(rows)
    assert w2.engine == "new_valid_breakthrough", w2

    # Equal-byte tie: preserve native scope preference only after bytes tie.
    tie = [
        Candidate("panel", 500, 0.01, eps, True, scope_rank=1),
        Candidate("whole", 500, 0.01, eps, True, scope_rank=2),
    ]
    assert select_smallest_valid(tie).engine == "whole"

    try:
        select_smallest_valid([Candidate("bad", 1, 1.0, eps, True)])
    except ValueError:
        pass
    else:
        raise AssertionError("fail-closed selector accepted no-valid-candidate set")

    print("MASTER_PORTFOLIO_V2_SELECTOR_SELF_TEST_OK")


if __name__ == "__main__":
    _self_test()
