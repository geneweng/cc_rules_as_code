"""OpenLeave — an executable, citation-backed encoding of U.S. employee leave law.

PROTOTYPE: covers federal FMLA plus California, Minnesota, and New York.
Parameter values are approximations for demonstration; this is not legal advice.
"""

from __future__ import annotations

from datetime import date

from . import interactions
from .engine import Citation, Entitlement, Finding, LeaveReason, RegimeResult
from .facts import Employee, Employer, Facts, LeaveEvent
from .regimes import california, fmla, minnesota, new_york

__version__ = "0.1.0"

DISCLAIMER = (
    "OpenLeave prototype: decision support, not legal advice. Statutory parameter values are approximations; "
    "verify against agency publications. Open-textured questions are flagged for human judgment, never auto-resolved."
)


def determine(facts: Facts, as_of: date | None = None) -> dict:
    """Evaluate all encoded regimes against the facts, as of the given date
    (defaults to the leave start date)."""
    as_of = as_of or facts.event.start
    results = [
        fmla.evaluate(facts, as_of),
        california.evaluate_cfra(facts, as_of),
        california.evaluate_pfl(facts, as_of),
        minnesota.evaluate(facts, as_of),
        new_york.evaluate(facts, as_of),
    ]
    return {
        "as_of": as_of.isoformat(),
        "regimes": [r.as_dict() for r in results if r.applies or r.notes],
        "interactions": interactions.evaluate(results),
        "disclaimer": DISCLAIMER,
        "engine_version": __version__,
    }


__all__ = [
    "Citation",
    "DISCLAIMER",
    "Employee",
    "Employer",
    "Entitlement",
    "Facts",
    "Finding",
    "LeaveEvent",
    "LeaveReason",
    "RegimeResult",
    "determine",
]
