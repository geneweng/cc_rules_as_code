"""Delaware Paid Leave (Healthy Delaware Families Act), 19 Del. C. ch. 37.

Delaware's distinctive feature is that coverage depends on employer size *and the
reason for leave together*, not size alone:

- Fewer than 10 Delaware employees: the program does not apply at all.
- 10 to 24 employees: only parental (bonding) leave is available.
- 25+ employees: parental, medical, family, and military-exigency leave.

So a worker at a 15-person employer is covered for bonding but not for their own
serious health condition — a gap no other encoded regime has. Everything else is
straightforward: 80% of the average weekly wage, capped at $900 and floored at
$100 (for 2026-2027), with FMLA-style eligibility (12 months, 1,250 hours, 60%
of work time in Delaware).

Sources (pending counsel review): benefits began 2026-01-01; 80% replacement,
$900 max / $100 min for 2026-2027; 12 weeks parental, 6 weeks medical/family per
24 months (12 weeks max per application year); labor.delaware.gov.
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

PROGRAM = "Delaware Paid Leave"
DE_3702 = "19 Del. C. § 3702"
DE_3707 = "19 Del. C. § 3707"
DE_3711 = "19 Del. C. § 3711"

# Benefits became payable 2026-01-01.
ENCODED_FROM = date(2026, 1, 1)

PARENTAL_REASONS = {LeaveReason.BONDING}
MEDICAL_FAMILY_REASONS = {
    LeaveReason.OWN_SERIOUS_HEALTH,
    LeaveReason.PREGNANCY,
    LeaveReason.FAMILY_CARE,
    LeaveReason.MILITARY_EXIGENCY,
}


def _weekly_benefit(aww: float, rate: float, cap: float, floor: float) -> float:
    """80% of the average weekly wage, capped at $900 and floored at $100 (or the
    full wage if lower) per 19 Del. C. § 3707."""
    benefit = max(rate * aww, min(floor, aww))
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="de_pfml", name=PROGRAM, applies=facts.employee.work_state == "DE", eligible=None
    )
    if not result.applies:
        return result

    if as_of < ENCODED_FROM:
        result.applies = False
        result.notes.append(encoded_range_note(PROGRAM, ENCODED_FROM))
        return result

    is_parental = facts.event.type in PARENTAL_REASONS
    is_medical_family = facts.event.type in MEDICAL_FAMILY_REASONS
    if not (is_parental or is_medical_family):
        result.applies = False
        return result

    parental_min = parameters.get("de.parental.min_employees", as_of)
    medfam_min = parameters.get("de.medical_family.min_employees", as_of)

    # Below the parental threshold, the program does not cover the employer at all.
    if facts.employer.total_employees < parental_min:
        result.applies = False
        result.notes.append(
            f"Delaware Paid Leave covers employers with {parental_min:.0f}+ Delaware employees; "
            f"this employer has {facts.employer.total_employees} ({DE_3702})."
        )
        return result

    required_size = parental_min if is_parental else medfam_min
    leave_kind = "parental (bonding)" if is_parental else "medical/family"
    min_months = parameters.get("de.eligibility.min_months", as_of)
    min_hours = parameters.get("de.eligibility.min_hours", as_of)

    result.findings = [
        Finding(
            key="employer_size_for_leave_type",
            description=f"Employer is large enough for {leave_kind} leave "
            f"(parental at {parental_min:.0f}+ employees, medical/family at {medfam_min:.0f}+)",
            met=facts.employer.total_employees >= required_size,
            citation=Citation(DE_3702),
            detail=f"Employer has {facts.employer.total_employees} employees; "
            f"{leave_kind} leave requires {required_size:.0f}+.",
        ),
        Finding(
            key="minimum_service_months",
            description=f"Employed at least {min_months:.0f} months",
            met=facts.tenure_months >= min_months,
            citation=Citation(DE_3702),
            detail=f"Tenure: {facts.tenure_months:.1f} months",
        ),
        Finding(
            key="minimum_hours",
            description=f"Worked at least {min_hours:.0f} hours in the last 12 months "
            f"(and 60% of work time in Delaware)",
            met=facts.employee.hours_last_12mo >= min_hours,
            citation=Citation(DE_3702),
            detail=f"Hours in previous 12 months: {facts.employee.hours_last_12mo:.0f}",
        ),
    ]

    if facts.event.type in {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(DE_3702),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"DE 'serious health condition' determination requires certification ({DE_3702})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        # A 10-24 employee worker denied medical/family leave is the signature case.
        if is_medical_family and facts.employer.total_employees < medfam_min:
            result.notes.append(
                f"Bonding leave would be available here, but medical/family leave requires "
                f"{medfam_min:.0f}+ employees ({DE_3702})."
            )
        return result

    weeks = parameters.get("de.parental.weeks" if is_parental else "de.medical_family.weeks", as_of)
    combined = parameters.get("de.combined.weeks", as_of)
    rate = parameters.get("de.wage_replacement_rate", as_of)
    cap = parameters.get("de.max_weekly_benefit", as_of)
    floor = parameters.get("de.min_weekly_benefit", as_of)

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, rate, cap, floor) if aww is not None else None

    notes = [
        f"Parental leave runs to 12 weeks; medical/family/military leave to 6 weeks per 24 months; "
        f"total paid leave is capped at {combined:.0f} weeks per application year ({DE_3707}).",
        f"Benefit is {rate * 100:.0f}% of the average weekly wage, capped at ${cap:,.0f} and "
        f"floored at ${floor:,.0f} for 2026-2027 ({DE_3707}).",
        f"Delaware provides job restoration to eligible employees ({DE_3711}).",
    ]
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=True, weekly_benefit=benefit, notes=notes
    )
    return result
