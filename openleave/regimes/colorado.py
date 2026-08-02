"""Colorado Family and Medical Leave Insurance (FAMLI), C.R.S. Title 8, Article 13.3.

Colorado resembles Washington in benefit design — the same two-tier 90%/50%
replacement around half the state average weekly wage — but differs in two ways
that matter for the encoding:

1. Eligibility is a wage floor, not an hours or tenure test: $2,500 in Colorado
   wages during the base period (the last five completed calendar quarters),
   earned across any employer.
2. Job protection is a single 180-days-of-service test with *no* employer-size
   threshold. Unlike FMLA (50 employees) or Washington (25), a Colorado worker at
   a two-person shop who has been there 180 days is entitled to reinstatement.

Sources (2026 benefit year, pending counsel review like every value here):
- Max weekly benefit $1,381.45, rising to $1,448.02 on 2026-07-01 (90% of the
  SAWW: $1,534.94, then $1,608.91). famli.colorado.gov.
- 12 weeks, +4 weeks for pregnancy/childbirth complications (16 max);
  C.R.S. 8-13.3-505. 180-day job protection: C.R.S. 8-13.3-509.
"""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import (
    Citation,
    Entitlement,
    Finding,
    LeaveReason,
    RegimeResult,
    encoded_range_note,
    resolve_eligibility,
)
from ..facts import Facts

PROGRAM = "Colorado Family and Medical Leave Insurance"
CRS_505 = "C.R.S. 8-13.3-505"
CRS_506 = "C.R.S. 8-13.3-506"
CRS_509 = "C.R.S. 8-13.3-509"

# Benefit parameters are encoded from 2026 onward; the program began paying in 2024.
ENCODED_FROM = date(2026, 1, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(aww: float, saww: float, cap: float) -> float:
    """Two-tier replacement per C.R.S. 8-13.3-506: 90% of wages up to 50% of the
    state average weekly wage, then 50% of the excess, capped."""
    half = 0.5 * saww
    if aww <= half:
        benefit = 0.9 * aww
    else:
        benefit = 0.9 * half + 0.5 * (aww - half)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="co_famli", name=PROGRAM, applies=facts.employee.work_state == "CO", eligible=None
    )
    if not result.applies:
        return result

    if as_of < ENCODED_FROM:
        result.applies = False
        result.notes.append(encoded_range_note(PROGRAM, ENCODED_FROM))
        return result

    is_family = facts.event.type in FAMILY_REASONS
    is_medical = facts.event.type in MEDICAL_REASONS
    if not (is_family or is_medical):
        result.applies = False
        return result

    minimum = parameters.get("co.min_base_period_earnings", as_of)
    wages = facts.base_period_wages
    result.findings = [
        Finding(
            key="minimum_earnings",
            description=f"At least ${minimum:,.0f} in Colorado wages during the base period "
            f"(across any employer, not just the current one)",
            met=None if wages is None else wages >= minimum,
            citation=Citation(CRS_505),
            detail="Wage data not provided" if wages is None else f"Base-period wages: ${wages:,.0f}",
        ),
        Finding(
            key="covered_employment",
            description="Employment in Colorado is covered (no minimum employer size)",
            met=True,
            citation=Citation(CRS_505),
            detail=f"Employer size {facts.employer.total_employees}; eligibility does not depend on it.",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(CRS_505),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"CO 'serious health condition' determination requires certification ({CRS_505})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("co.weeks", as_of)
    pregnancy_bonus = parameters.get("co.pregnancy_complication_weeks", as_of)
    combined = parameters.get("co.combined.weeks", as_of)
    saww = parameters.get("co.saww", as_of)
    cap = parameters.get("co.max_weekly_benefit", as_of)
    min_days = parameters.get("co.job_protection.min_service_days", as_of)

    tenure_days = (facts.event.start - facts.employee.hire_date).days
    job_protected = tenure_days >= min_days

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, saww, cap) if aww is not None else None

    notes = [
        f"Up to {weeks:.0f} weeks per benefit year, with up to {pregnancy_bonus:.0f} additional "
        f"weeks for a serious health condition related to pregnancy or childbirth complications "
        f"({combined:.0f} weeks max) ({CRS_505}).",
    ]
    if job_protected:
        notes.append(
            f"Job protection attaches after {min_days:.0f} days of service, with no employer-size "
            f"threshold ({CRS_509})."
        )
    else:
        notes.append(
            f"Benefits are payable but CO job protection does not attach: {tenure_days} days of "
            f"service (needs {min_days:.0f}) ({CRS_509}). Anti-retaliation protection still applies "
            f"regardless of tenure. Check whether FMLA or another law protects the position."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
