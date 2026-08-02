"""Wage-and-hour determinations — a sibling capability to the leave engine.

Phase 1 vertical slice: state + federal minimum wage (with tip-credit handling)
and final-pay-on-separation timing (with accrued-vacation payout), for the
federal floor plus California and Washington. Localities are reported as coverage
gaps rather than silently ignored. Overtime, exempt classification, and meal/rest
breaks are deliberately deferred to a later phase.

Shares the leave engine's substrate: effective-dated `parameters`, the
`Finding`/`Citation` justification-tree types, and the coverage-reporting reflex.
"""

from __future__ import annotations

from datetime import date

from .. import DISCLAIMER, __version__
from . import coverage, final_pay, minimum_wage
from .facts import PayBasis, Separation, SeparationType, WageFacts

__all__ = [
    "WageFacts",
    "Separation",
    "SeparationType",
    "PayBasis",
    "assess_wage_hour",
]


def assess_wage_hour(facts: WageFacts, as_of: date | None = None) -> dict:
    """Evaluate every encoded wage-and-hour topic against the facts, as of the
    given date (defaults to today)."""
    as_of = as_of or date.today()

    topics = [minimum_wage.assess(facts, as_of)]
    fp = final_pay.assess(facts, as_of)
    if fp is not None:
        topics.append(fp)

    return {
        "as_of": as_of.isoformat(),
        "jurisdiction": {"state": facts.work_state.upper(), "locality": facts.work_locality},
        "topics": [t.as_dict() for t in topics],
        "coverage": coverage.assess(facts.work_state, facts.work_locality),
        "disclaimer": DISCLAIMER,
        "engine_version": __version__,
    }
