"""Washington Paid Family and Medical Leave, RCW Title 50A.

Two things make Washington distinctive in this encoding:

1. Eligibility is hours-based across *any* Washington employer (820 hours in the
   qualifying period), not tenure with the current one — so a job-switcher can be
   benefit-eligible while failing FMLA's 12-month test.
2. Job protection is a separate test from benefit eligibility, and it changed on
   2026-01-01: the employer-size threshold dropped from 50 to 25 employees, the
   service requirement dropped from 12 months to 180 days, and the 1,250-hour
   requirement was removed.
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

PROGRAM = "Washington Paid Family and Medical Leave"
RCW_50A_15 = "RCW 50A.15"
RCW_50A_35 = "RCW 50A.35.010"
RCW_50A_05 = "RCW 50A.05.010"

# Benefit parameters are encoded from 2026 onward; the program itself began in 2020.
ENCODED_FROM = date(2026, 1, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(aww: float, saww: float, cap: float) -> float:
    """Two-tier replacement per RCW 50A.15.020: 90% of wages up to 50% of the
    state average weekly wage, then 50% of the excess, capped."""
    half = 0.5 * saww
    if aww <= half:
        benefit = 0.9 * aww
    else:
        benefit = 0.9 * half + 0.5 * (aww - half)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="wa_pfml", name=PROGRAM, applies=facts.employee.work_state == "WA", eligible=None
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

    min_hours = parameters.get("wa.min_hours", as_of)
    result.findings = [
        Finding(
            key="qualifying_hours",
            description=f"At least {min_hours:.0f} hours worked in the qualifying period "
            f"(across any Washington employer, not just the current one)",
            met=facts.employee.hours_last_12mo >= min_hours,
            citation=Citation(f"{RCW_50A_15}.020"),
            detail=f"Hours in previous 12 months: {facts.employee.hours_last_12mo:.0f}",
        ),
        Finding(
            key="covered_employment",
            description="Employment in Washington is covered (no minimum employer size for benefits)",
            met=True,
            citation=Citation(RCW_50A_05),
            detail=f"Employer size {facts.employer.total_employees}; benefits do not depend on it.",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(RCW_50A_05),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"WA 'serious health condition' determination requires certification ({RCW_50A_05})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("wa.family.weeks" if is_family else "wa.medical.weeks", as_of)
    combined = parameters.get("wa.combined.weeks", as_of)
    saww = parameters.get("wa.saww", as_of)
    cap = parameters.get("wa.max_weekly_benefit", as_of)
    min_employees = parameters.get("wa.job_protection.min_employees", as_of)
    min_days = parameters.get("wa.job_protection.min_service_days", as_of)

    tenure_days = (facts.event.start - facts.employee.hire_date).days
    job_protected = facts.employer.total_employees >= min_employees and tenure_days >= min_days

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, saww, cap) if aww is not None else None

    notes = [
        f"Combined family + medical leave is capped at {combined:.0f} weeks per claim year "
        f"({RCW_50A_15}.020); an additional 2 weeks may apply for incapacity from pregnancy "
        f"complications.",
    ]
    if job_protected:
        notes.append(
            f"Job protection requires an employer with {min_employees:.0f}+ employees and "
            f"{min_days:.0f} days of service ({RCW_50A_35})."
        )
    else:
        reason = (
            f"employer has {facts.employer.total_employees} employees (needs {min_employees:.0f}+)"
            if facts.employer.total_employees < min_employees
            else f"{tenure_days} days of service (needs {min_days:.0f})"
        )
        notes.append(
            f"Benefits are payable but WA job protection does not attach: {reason} ({RCW_50A_35}). "
            f"Check whether FMLA or another law protects the position."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
