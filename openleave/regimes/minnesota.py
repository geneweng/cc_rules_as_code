"""Minnesota Paid Leave, Minn. Stat. ch. 268B (benefits began Jan 1, 2026)."""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Entitlement, Finding, LeaveReason, RegimeResult, resolve_eligibility
from ..facts import Facts

STAT_268B = "Minn. Stat. § 268B"

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(aww: float, saww: float) -> float:
    """Progressive replacement per Minn. Stat. § 268B.06: 90% of wages up to
    50% of SAWW, 66% between 50% and 100% of SAWW, 55% above; capped at SAWW."""
    half = 0.5 * saww
    benefit = 0.9 * min(aww, half)
    if aww > half:
        benefit += 0.66 * (min(aww, saww) - half)
    if aww > saww:
        benefit += 0.55 * (aww - saww)
    return round(min(benefit, saww), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(regime="mn_paid_leave", name="Minnesota Paid Leave", applies=facts.employee.work_state == "MN", eligible=None)
    if not result.applies:
        return result

    if not parameters.in_force("mn.saww", as_of):
        result.applies = False
        result.notes.append("Minnesota Paid Leave benefits are not in force on the evaluation date (program began 2026-01-01).")
        return result

    is_family = facts.event.type in FAMILY_REASONS
    is_medical = facts.event.type in MEDICAL_REASONS
    if not (is_family or is_medical):
        result.applies = False
        return result

    saww = parameters.get("mn.saww", as_of)
    threshold = parameters.get("mn.wage_threshold_fraction_of_saaw", as_of) * saww * 52
    wages = facts.base_period_wages

    result.findings = [
        Finding(
            key="wage_threshold",
            description=f"Base-period wages of at least 5.3% of the state average annual wage (~${threshold:,.0f})",
            met=None if wages is None else wages >= threshold,
            citation=Citation(f"{STAT_268B}.04"),
            detail="Wage data not provided" if wages is None else f"Base-period wages: ${wages:,.0f}",
        ),
        Finding(
            key="covered_employment",
            description="Employment in Minnesota is covered (nearly all employers, regardless of size)",
            met=True,
            citation=Citation(f"{STAT_268B}.01"),
            detail=f"Employer size {facts.employer.total_employees}; no minimum size applies.",
        ),
    ]
    if wages is None:
        result.human_judgment.append("Provide wage data to determine monetary eligibility.")

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(f"{STAT_268B}.01 subd. 41"),
                detail="Requires certification and case-by-case judgment.",
            )
        )
        result.human_judgment.append("MN 'serious health condition' determination requires certification.")

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is not False:
        weeks_key = "mn.family.weeks" if is_family else "mn.medical.weeks"
        combined = parameters.get("mn.combined.weeks", as_of)
        job_protected = facts.tenure_weeks * 7 >= 90
        aww = facts.employee.average_weekly_wage
        benefit = _weekly_benefit(aww, saww) if aww is not None else None
        notes = [f"Combined family + medical leave is capped at {combined:.0f} weeks per benefit year ({STAT_268B}.04)."]
        if not job_protected:
            notes.append(f"Job protection requires 90 days of employment ({STAT_268B}.09); tenure is below that.")
        if benefit is None:
            notes.append("Provide average_weekly_wage to estimate the weekly benefit.")
        result.entitlement = Entitlement(
            weeks=parameters.get(weeks_key, as_of),
            job_protected=job_protected,
            weekly_benefit=benefit,
            notes=notes,
        )
    return result
