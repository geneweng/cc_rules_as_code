"""Paid Leave Oregon, ORS Chapter 657B.

Oregon's benefit formula is the odd one out in this encoding. Where Washington,
Colorado, and Massachusetts all replace 90%/80% of low wages then 50% of the
rest, Oregon replaces *100%* of wages up to 65% of the state average weekly wage,
then 50% of the excess — with a benefit floor (5% of SAWW) as well as a cap
(120% of SAWW). A low earner in Oregon is made whole.

Two other distinctives:
1. The qualifying wage floor is low: $1,000 in Oregon wages during the base year,
   earned across any employer.
2. Job protection has no employer-size threshold at all — reinstatement after
   90 days of service applies to the smallest employers exactly as to the
   largest (the 25-employee line in the statute is about premium contributions,
   not job restoration).

Sources (benefit years beginning on/after 2026-06-28, pending counsel review):
- Max weekly benefit $1,692.16 (120% of SAWW $1,410.13); min $70.51 (5%).
  oregon.gov. Prior benefit-year figures ($1,636.56 / $68.19) encoded from
  2026-01-01. 12 weeks, +2 for pregnancy-related conditions (14 max); ORS
  657B.020, .050. 90-day job restoration: ORS 657B.060.
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

PROGRAM = "Paid Leave Oregon"
ORS_010 = "ORS 657B.010"
ORS_015 = "ORS 657B.015"
ORS_050 = "ORS 657B.050"
ORS_060 = "ORS 657B.060"

# Benefit parameters are encoded from 2026 onward; the program began paying in 2023.
ENCODED_FROM = date(2026, 1, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(aww: float, saww: float, cap: float, floor: float) -> float:
    """Per ORS 657B.050: 100% of the average weekly wage up to 65% of the state
    average weekly wage, then 50% of the excess. Floored at 5% and capped at
    120% of the SAWW."""
    threshold = 0.65 * saww
    if aww <= threshold:
        benefit = aww
    else:
        benefit = threshold + 0.5 * (aww - threshold)
    return round(min(max(benefit, floor), cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="or_pfml", name=PROGRAM, applies=facts.employee.work_state == "OR", eligible=None
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

    minimum = parameters.get("or.min_base_year_earnings", as_of)
    wages = facts.base_period_wages
    result.findings = [
        Finding(
            key="minimum_earnings",
            description=f"At least ${minimum:,.0f} in Oregon wages during the base year "
            f"(across any employer, not just the current one)",
            met=None if wages is None else wages >= minimum,
            citation=Citation(ORS_015),
            detail="Wage data not provided" if wages is None else f"Base-year wages: ${wages:,.0f}",
        ),
        Finding(
            key="covered_employment",
            description="Employment in Oregon is covered (no minimum employer size)",
            met=True,
            citation=Citation(ORS_010),
            detail=f"Employer size {facts.employer.total_employees}; eligibility does not depend on it.",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(ORS_010),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"OR 'serious health condition' determination requires certification ({ORS_010})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("or.weeks", as_of)
    pregnancy_extra = parameters.get("or.pregnancy_extra_weeks", as_of)
    combined = parameters.get("or.combined.weeks", as_of)
    saww = parameters.get("or.saww", as_of)
    cap = parameters.get("or.max_weekly_benefit", as_of)
    floor = parameters.get("or.min_weekly_benefit", as_of)
    min_days = parameters.get("or.job_protection.min_service_days", as_of)

    tenure_days = (facts.event.start - facts.employee.hire_date).days
    job_protected = tenure_days >= min_days

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, saww, cap, floor) if aww is not None else None

    notes = [
        f"Up to {weeks:.0f} weeks per benefit year, with up to {pregnancy_extra:.0f} additional "
        f"weeks for pregnancy, childbirth, or a related medical condition ({combined:.0f} weeks "
        f"max) ({ORS_050}).",
        f"Weekly benefit is floored at ${floor:,.2f} and capped at ${cap:,.2f} ({ORS_050}); a "
        f"worker earning at or below 65% of the state average weekly wage is paid 100% of wages.",
    ]
    if job_protected:
        notes.append(
            f"Job restoration attaches after {min_days:.0f} days of service, at every employer "
            f"size ({ORS_060})."
        )
    else:
        notes.append(
            f"Benefits are payable but OR job restoration does not attach: {tenure_days} days of "
            f"service (needs {min_days:.0f}) ({ORS_060}). Check whether FMLA or another law "
            f"protects the position."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
