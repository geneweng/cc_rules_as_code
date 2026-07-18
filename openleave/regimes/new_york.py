"""New York Paid Family Leave, N.Y. Workers' Comp. Law art. 9 (§§ 200–242)."""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Entitlement, Finding, LeaveReason, RegimeResult, resolve_eligibility
from ..facts import Facts

WCL_201 = "N.Y. Workers' Comp. Law § 201"
WCL_203 = "N.Y. Workers' Comp. Law § 203"
WCL_203_B = "N.Y. Workers' Comp. Law § 203-b"
WCL_204 = "N.Y. Workers' Comp. Law § 204"

PFL_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(regime="ny_pfl", name="New York Paid Family Leave", applies=facts.employee.work_state == "NY", eligible=None)
    if not result.applies:
        return result

    if facts.event.type not in PFL_REASONS:
        result.applies = False
        if facts.event.type in (LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY):
            result.notes.append(
                "An employee's own disability is covered by NY DBL (WCL § 204), not PFL; DBL is not encoded in this prototype."
            )
        return result

    hours_per_week = facts.employee.hours_per_week
    if hours_per_week is None or hours_per_week >= 20:
        met = facts.tenure_weeks >= 26
        finding = Finding(
            key="service",
            description="26 consecutive weeks of employment (employees regularly working 20+ hours/week)",
            met=met,
            citation=Citation(f"{WCL_203}"),
            detail=f"Tenure at leave start: {facts.tenure_weeks:.0f} weeks",
        )
    else:
        days_worked = facts.tenure_weeks * min(hours_per_week / 8, 5)
        finding = Finding(
            key="service",
            description="175 days worked (employees regularly working under 20 hours/week)",
            met=days_worked >= 175,
            citation=Citation(f"{WCL_203}"),
            detail=f"Estimated days worked: {days_worked:.0f}",
        )
    result.findings = [finding]

    if facts.event.type == LeaveReason.FAMILY_CARE:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The family member has a 'serious health condition'",
                met=None,
                citation=Citation(f"{WCL_201}(18)"),
                detail="Requires certification and case-by-case judgment.",
            )
        )
        result.human_judgment.append("NY PFL 'serious health condition' determination requires certification.")

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is not False:
        rate = parameters.get("ny.pfl.wage_replacement_rate", as_of)
        saww = parameters.get("ny.saww", as_of)
        cap = round(rate * saww, 2)
        aww = facts.employee.average_weekly_wage
        benefit = round(min(rate * aww, cap), 2) if aww is not None else None
        notes = [f"Benefit is {rate:.0%} of the employee's AWW, capped at {rate:.0%} of the NY SAWW (${cap:,.2f}/week)."]
        if benefit is None:
            notes.append("Provide average_weekly_wage to estimate the weekly benefit.")
        result.entitlement = Entitlement(
            weeks=parameters.get("ny.pfl.weeks", as_of),
            job_protected=True,
            weekly_benefit=benefit,
            notes=notes + [f"Job restoration guaranteed by {WCL_203_B}."],
        )
    return result
