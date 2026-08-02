"""Connecticut Paid Leave, Conn. Gen. Stat. § 31-49e et seq., with job
protection supplied by the Connecticut FMLA, Conn. Gen. Stat. § 31-51kk et seq.

Connecticut is distinctive in this encoding in two ways:

1. Every other program pegs its benefit to a *state average weekly wage*.
   Connecticut pegs to the *minimum wage*: the second-tier threshold is 40x the
   hourly minimum wage and the cap is 60x it. So the whole benefit schedule
   moves when the minimum wage moves — no separate SAWW announcement. The
   2026-01-01 minimum-wage bump ($16.35 -> $16.94) raised the cap from $981.00
   to $1,016.40 automatically, and this encoding reproduces that by effective-
   dating the minimum wage alone.

2. The paid-leave program pays wage replacement but carries no job protection of
   its own; reinstatement comes from the separate Connecticut FMLA. CT FMLA is
   unusually broad — it reaches employers with a *single* employee and vests
   after just three months — so in practice almost every Connecticut claimant
   who has been on the job three months is protected. We compute that companion
   test inline and cite it to its own statute.

Sources (2026, pending counsel review like every value here): minimum wage
$16.94 (ctpaidleave.org); benefit 95% up to 40x min wage then 60%, capped at
60x = $1,016.40; $2,325 highest-quarter earnings to qualify; 12 weeks + 2 for
pregnancy incapacity (14 max); CT FMLA 3-month / 1-employee reinstatement.
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

PROGRAM = "Connecticut Paid Leave"
CGS_31_49E = "Conn. Gen. Stat. § 31-49e"
CGS_31_49G = "Conn. Gen. Stat. § 31-49g"
CGS_31_51KK = "Conn. Gen. Stat. § 31-51kk"
CGS_31_51LL = "Conn. Gen. Stat. § 31-51ll"
CGS_31_51NN = "Conn. Gen. Stat. § 31-51nn"

# Benefit parameters are encoded from 2025 onward; the program began paying in 2022.
ENCODED_FROM = date(2025, 1, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(
    aww: float, min_wage: float, cap_hours: float, break_hours: float, r1: float, r2: float
) -> float:
    """Per Conn. Gen. Stat. § 31-49g: 95% of the average weekly wage up to 40x
    the hourly minimum wage, then 60% of the excess, capped at 60x the minimum
    wage."""
    breakpoint = break_hours * min_wage
    cap = cap_hours * min_wage
    if aww <= breakpoint:
        benefit = r1 * aww
    else:
        benefit = r1 * breakpoint + r2 * (aww - breakpoint)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="ct_pfml", name=PROGRAM, applies=facts.employee.work_state == "CT", eligible=None
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

    min_high_quarter = parameters.get("ct.pfml.min_high_quarter_earnings", as_of)
    aww = facts.employee.average_weekly_wage
    # The statutory test is on highest-quarter earnings; approximate a quarter as
    # 13 weeks of the average weekly wage when only a weekly figure is provided.
    high_quarter = aww * 13 if aww is not None else (
        facts.base_period_wages / 4 if facts.base_period_wages is not None else None
    )

    result.findings = [
        Finding(
            key="highest_quarter_earnings",
            description=f"At least ${min_high_quarter:,.0f} earned in the highest quarter of the "
            f"base period",
            met=None if high_quarter is None else high_quarter >= min_high_quarter,
            citation=Citation(CGS_31_49E),
            detail="Wage data not provided"
            if high_quarter is None
            else f"Estimated highest-quarter earnings: ${high_quarter:,.0f} (approximated from the "
            f"average weekly wage)",
        ),
        Finding(
            key="covered_employment",
            description="Employment in Connecticut is covered (no minimum employer size)",
            met=True,
            citation=Citation(CGS_31_49E),
            detail=f"Employer size {facts.employer.total_employees}; eligibility does not depend on it.",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(CGS_31_49E),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"CT 'serious health condition' determination requires certification ({CGS_31_49E})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("ct.weeks", as_of)
    pregnancy_extra = parameters.get("ct.pregnancy_extra_weeks", as_of)
    combined = parameters.get("ct.combined.weeks", as_of)
    min_wage = parameters.get("ct.minimum_wage", as_of)
    cap_hours = parameters.get("ct.pfml.cap_hours", as_of)
    break_hours = parameters.get("ct.pfml.tier_break_hours", as_of)
    r1 = parameters.get("ct.pfml.tier1_rate", as_of)
    r2 = parameters.get("ct.pfml.tier2_rate", as_of)
    min_tenure_months = parameters.get("ct.fmla.min_tenure_months", as_of)

    # Job protection is a separate statute (CT FMLA): 1+ employee, 3 months of service.
    job_protected = facts.tenure_months >= min_tenure_months
    cap = round(cap_hours * min_wage, 2)

    benefit = (
        _weekly_benefit(aww, min_wage, cap_hours, break_hours, r1, r2) if aww is not None else None
    )

    notes = [
        f"Up to {weeks:.0f} weeks per 12-month period, with up to {pregnancy_extra:.0f} additional "
        f"weeks for incapacity from a pregnancy-related serious health condition ({combined:.0f} "
        f"weeks max) ({CGS_31_49G}).",
        f"The benefit schedule is pegged to the ${min_wage:,.2f} minimum wage: 95% of wages up to "
        f"40x ($ {break_hours * min_wage:,.2f}/wk), then 60%, capped at 60x (${cap:,.2f}/wk) "
        f"({CGS_31_49G}).",
    ]
    if job_protected:
        notes.append(
            f"Job protection comes from the Connecticut FMLA, not the paid-leave program: it "
            f"reaches employers with a single employee and vests after {min_tenure_months:.0f} "
            f"months of service ({CGS_31_51LL}, reinstatement {CGS_31_51NN})."
        )
    else:
        notes.append(
            f"Benefits are payable but CT FMLA job protection has not vested: {facts.tenure_months:.1f} "
            f"months of service (needs {min_tenure_months:.0f}) ({CGS_31_51LL}). Check whether "
            f"federal FMLA or another law protects the position."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
