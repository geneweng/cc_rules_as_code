"""California: CFRA (Gov. Code § 12945.2) job protection + Paid Family Leave
(Unemp. Ins. Code §§ 3300–3306) wage replacement.

CFRA provides job-protected leave; PFL provides wage replacement only (no
independent job protection). Own-health wage replacement in CA is SDI, which
this prototype notes but does not encode.
"""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Entitlement, Finding, LeaveReason, RegimeResult, resolve_eligibility
from ..facts import Facts

GOV_12945_2 = "Cal. Gov. Code § 12945.2"
UIC_3301 = "Cal. Unemp. Ins. Code § 3301"
UIC_2652 = "Cal. Unemp. Ins. Code § 2652"
SB_951 = "Cal. SB 951 (2022), amending Unemp. Ins. Code § 3301"

CFRA_REASONS = {
    LeaveReason.BONDING,
    LeaveReason.OWN_SERIOUS_HEALTH,
    LeaveReason.FAMILY_CARE,
    LeaveReason.MILITARY_EXIGENCY,
}
PFL_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
HEALTH_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.FAMILY_CARE}


def evaluate_cfra(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(regime="ca_cfra", name="California CFRA", applies=facts.employee.work_state == "CA", eligible=None)
    if not result.applies:
        return result

    if facts.event.type not in CFRA_REASONS:
        result.applies = False
        result.notes.append(
            f"Reason {facts.event.type.value!r} is outside CFRA; pregnancy disability is covered separately "
            f"by PDL (Cal. Gov. Code § 12945)."
        )
        return result

    result.findings = [
        Finding(
            key="employer_size",
            description="Employer has 5 or more employees",
            met=facts.employer.total_employees >= 5,
            citation=Citation(f"{GOV_12945_2}(b)"),
            detail=f"Total employees: {facts.employer.total_employees}",
        ),
        Finding(
            key="tenure",
            description="More than 12 months of service with the employer",
            met=facts.tenure_months >= 12,
            citation=Citation(f"{GOV_12945_2}(a)"),
            detail=f"Tenure at leave start: {facts.tenure_months:.1f} months",
        ),
        Finding(
            key="hours",
            description="At least 1,250 hours of service in the previous 12 months",
            met=facts.employee.hours_last_12mo >= 1250,
            citation=Citation(f"{GOV_12945_2}(a)"),
            detail=f"Hours in previous 12 months: {facts.employee.hours_last_12mo:.0f}",
        ),
    ]

    if facts.event.type in HEALTH_REASONS:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(f"{GOV_12945_2}(b)(12)"),
                detail="Requires certification and case-by-case judgment.",
            )
        )
        result.human_judgment.append("CFRA 'serious health condition' determination requires certification.")

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is not False:
        result.entitlement = Entitlement(
            weeks=12,
            job_protected=True,
            weekly_benefit=None,
            notes=["CFRA leave is unpaid; pair with CA PFL or SDI for wage replacement."],
        )
    return result


def evaluate_pfl(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(regime="ca_pfl", name="California Paid Family Leave", applies=facts.employee.work_state == "CA", eligible=None)
    if not result.applies:
        return result

    if facts.event.type not in PFL_REASONS:
        result.applies = False
        if facts.event.type in (LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY):
            result.notes.append(
                "Own disability (including pregnancy) is covered by CA SDI (Unemp. Ins. Code § 2652 et seq.), "
                "not PFL; SDI is not encoded in this prototype."
            )
        return result

    wages = facts.base_period_wages
    min_earnings = parameters.get("ca.pfl.min_base_period_earnings", as_of)
    result.findings = [
        Finding(
            key="base_period_earnings",
            description=f"At least ${min_earnings:.0f} in SDI-covered base-period wages",
            met=None if wages is None else wages >= min_earnings,
            citation=Citation(UIC_2652),
            detail="Wage data not provided" if wages is None else f"Base-period wages: ${wages:,.0f}",
        ),
    ]
    if wages is None:
        result.human_judgment.append("Provide wage data to determine PFL monetary eligibility.")

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is not False:
        benefit = None
        notes = []
        aww = facts.employee.average_weekly_wage
        if aww is not None:
            saww = parameters.get("ca.saww", as_of)
            low_rate = parameters.get("ca.pfl.low_earner_rate", as_of)
            std_rate = parameters.get("ca.pfl.standard_rate", as_of)
            rate = low_rate if aww < 0.7 * saww else std_rate
            cap = parameters.get("ca.pfl.max_weekly_benefit", as_of)
            benefit = round(min(rate * aww, cap), 2)
            notes.append(f"Wage replacement at {rate:.0%} of AWW under {SB_951}, capped at ${cap:,.0f}/week.")
        else:
            notes.append("Provide average_weekly_wage to estimate the weekly benefit.")
        notes.append("PFL provides wage replacement only; job protection comes from CFRA/FMLA where eligible.")
        result.entitlement = Entitlement(
            weeks=parameters.get("ca.pfl.weeks", as_of),
            job_protected=False,
            weekly_benefit=benefit,
            notes=notes,
        )
    return result
