"""Wage-and-hour determinations — a sibling capability to the leave engine.

Covers minimum wage (state/local/federal, with tip-credit handling), overtime
(FLSA/WA weekly and CA daily/7th-day, with a blended regular rate), white-collar
exempt classification (salary test decided, duties test flagged for human
judgment), and final-pay-on-separation timing (with accrued-vacation payout), for
the federal floor plus California and Washington and twelve encoded localities.

Shares the leave engine's substrate: effective-dated `parameters`, the
`Finding`/`Citation` justification-tree types, and the coverage-reporting reflex.
"""

from __future__ import annotations

from datetime import date

from .. import DISCLAIMER, __version__
from . import coverage, exemptions, final_pay, minimum_wage, overtime
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
    for optional in (exemptions.assess(facts, as_of), overtime.assess(facts, as_of),
                     final_pay.assess(facts, as_of)):
        if optional is not None:
            topics.append(optional)

    return {
        "as_of": as_of.isoformat(),
        "jurisdiction": {"state": facts.work_state.upper(), "locality": facts.work_locality},
        "topics": [t.as_dict() for t in topics],
        "coverage": coverage.assess(facts.work_state, facts.work_locality, as_of),
        "disclaimer": DISCLAIMER,
        "engine_version": __version__,
    }
