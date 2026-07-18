"""Core result types for OpenLeave determinations.

Every conclusion the engine produces is a Finding tied to a statutory or
regulatory Citation. Open-textured questions (e.g. whether a condition is a
"serious health condition") are never resolved by the engine: they surface as
findings with met=None and are listed in RegimeResult.human_judgment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LeaveReason(str, Enum):
    BONDING = "bonding"
    OWN_SERIOUS_HEALTH = "own_serious_health"
    FAMILY_CARE = "family_care"
    PREGNANCY = "pregnancy"
    MILITARY_EXIGENCY = "military_exigency"


@dataclass(frozen=True)
class Citation:
    ref: str
    url: str | None = None


@dataclass
class Finding:
    key: str
    description: str
    met: bool | None  # None => requires human judgment
    citation: Citation
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "description": self.description,
            "met": self.met,
            "citation": {"ref": self.citation.ref, "url": self.citation.url},
            "detail": self.detail,
        }


@dataclass
class Entitlement:
    weeks: float | None
    job_protected: bool
    weekly_benefit: float | None  # None => unpaid leave or not computable
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "weeks": self.weeks,
            "job_protected": self.job_protected,
            "weekly_benefit": self.weekly_benefit,
            "notes": self.notes,
        }


@dataclass
class RegimeResult:
    regime: str  # short id, e.g. "fmla"
    name: str
    applies: bool  # does this regime cover this employee/reason at all?
    eligible: bool | None  # None when eligibility turns on a human-judgment finding
    findings: list[Finding] = field(default_factory=list)
    entitlement: Entitlement | None = None
    human_judgment: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "regime": self.regime,
            "name": self.name,
            "applies": self.applies,
            "eligible": self.eligible,
            "findings": [f.as_dict() for f in self.findings],
            "entitlement": self.entitlement.as_dict() if self.entitlement else None,
            "human_judgment": self.human_judgment,
            "notes": self.notes,
        }


def resolve_eligibility(findings: list[Finding]) -> bool | None:
    """Combine findings: False if any hard condition fails, None if the only
    unresolved conditions require human judgment, True otherwise."""
    if any(f.met is False for f in findings):
        return False
    if any(f.met is None for f in findings):
        return None
    return True
