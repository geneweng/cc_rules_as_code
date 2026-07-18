"""Federal Family and Medical Leave Act, 29 U.S.C. §§ 2601–2654."""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Entitlement, Finding, LeaveReason, RegimeResult, resolve_eligibility
from ..facts import Facts

USC_2611 = "29 U.S.C. § 2611"
USC_2612 = "29 U.S.C. § 2612(a)(1)"
CFR_825_113 = "29 C.F.R. § 825.113"

COVERED_REASONS = {
    LeaveReason.BONDING,
    LeaveReason.OWN_SERIOUS_HEALTH,
    LeaveReason.FAMILY_CARE,
    LeaveReason.PREGNANCY,
    LeaveReason.MILITARY_EXIGENCY,
}

HEALTH_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.FAMILY_CARE, LeaveReason.PREGNANCY}


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(regime="fmla", name="FMLA (federal)", applies=True, eligible=None)

    if facts.event.type not in COVERED_REASONS:
        result.applies = False
        result.notes.append(f"Leave reason {facts.event.type.value!r} is not an FMLA qualifying reason ({USC_2612}).")
        return result

    min_hours = parameters.get("fmla.min_hours", as_of)
    min_headcount = parameters.get("fmla.min_worksite_headcount", as_of)

    result.findings = [
        Finding(
            key="tenure",
            description="Employed by this employer for at least 12 months",
            met=facts.tenure_months >= 12,
            citation=Citation(f"{USC_2611}(2)(A)(i)"),
            detail=f"Tenure at leave start: {facts.tenure_months:.1f} months",
        ),
        Finding(
            key="hours",
            description=f"At least {min_hours:.0f} hours of service in the previous 12 months",
            met=facts.employee.hours_last_12mo >= min_hours,
            citation=Citation(f"{USC_2611}(2)(A)(ii)"),
            detail=f"Hours in previous 12 months: {facts.employee.hours_last_12mo:.0f}",
        ),
        Finding(
            key="worksite",
            description=f"Employer has {min_headcount:.0f}+ employees within 75 miles of the worksite",
            met=facts.worksite_headcount >= min_headcount,
            citation=Citation(f"{USC_2611}(2)(B)(ii)"),
            detail=f"Employees within 75 miles: {facts.worksite_headcount}",
        ),
    ]

    if facts.event.type in HEALTH_REASONS:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(CFR_825_113),
                detail="Requires medical certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"Whether the condition is a 'serious health condition' ({CFR_825_113}) must be resolved via medical certification."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is not False:
        result.entitlement = Entitlement(
            weeks=parameters.get("fmla.weeks", as_of),
            job_protected=True,
            weekly_benefit=None,
            notes=["FMLA leave is unpaid; job protection and benefits continuation per 29 U.S.C. § 2614."],
        )
    return result
