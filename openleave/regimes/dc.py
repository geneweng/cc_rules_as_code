"""District of Columbia Paid Family Leave, D.C. Code § 32-541.01 et seq.
(Universal Paid Leave Amendment Act), with job protection supplied by the
separate DC Family and Medical Leave Act, D.C. Code § 32-501 et seq.

DC is the mirror image of Connecticut on job protection. Connecticut's paid
program has no protection of its own but its companion statute (CT FMLA) is
*broader* than the pay program — one employee, three months. DC's companion
statute is *narrower*: DC FMLA reaches only employers with 20+ employees and
vests after 12 months and 1,000 hours, while DC PFL pays essentially every
covered DC worker with no earnings, hours, or tenure minimum at all. So a DC
worker at a 10-person shop is paid but not job-protected — the opposite gap.

Like Connecticut, the benefit is pegged to the minimum wage: 90% of wages up to
150% of (minimum wage x 40 hours), then 50% of the excess, capped at a maximum
set by DOES. The DC minimum wage rises from $17.95 to $18.40 on 2026-07-01, so
the 90% band widens automatically mid-2026.

Sources (pending counsel review): max weekly benefit $1,190 for leave dates on
or after 2025-09-28 (dcpaidfamilyleave.dc.gov); formula D.C. Code § 32-541.03;
12 weeks each parental/family/medical + 2 prenatal (14 max); DC FMLA
20-employee / 12-month / 1,000-hour protection, D.C. Code § 32-503.
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

PROGRAM = "DC Paid Family Leave"
DC_541_01 = "D.C. Code § 32-541.01"
DC_541_03 = "D.C. Code § 32-541.03"
DC_503 = "D.C. Code § 32-503"

# Full-time week used in the minimum-wage-pegged threshold (min wage x 40 hours).
WEEKLY_HOURS = 40

# Benefit parameters are encoded from the 2025-09-28 maximum-benefit update.
ENCODED_FROM = date(2025, 9, 28)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(
    aww: float, min_wage: float, multiple: float, r1: float, r2: float, cap: float
) -> float:
    """Per D.C. Code § 32-541.03: 90% of the average weekly wage up to 150% of
    (minimum wage x 40 hours), then 50% of the excess, capped."""
    threshold = multiple * min_wage * WEEKLY_HOURS
    if aww <= threshold:
        benefit = r1 * aww
    else:
        benefit = r1 * threshold + r2 * (aww - threshold)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="dc_pfl", name=PROGRAM, applies=facts.employee.work_state == "DC", eligible=None
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

    # DC has no earnings, hours, or tenure minimum: any covered DC worker qualifies.
    result.findings = [
        Finding(
            key="covered_employment",
            description="Worked for a covered employer, spending a majority of work time in DC "
            "(no minimum earnings, hours, or tenure)",
            met=True,
            citation=Citation(DC_541_01),
            detail=f"Employer size {facts.employer.total_employees}; eligibility does not depend on it.",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(DC_541_01),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"DC 'serious health condition' determination requires certification ({DC_541_01})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("dc.weeks", as_of)
    prenatal = parameters.get("dc.pfl.prenatal_weeks", as_of)
    combined = parameters.get("dc.combined.weeks", as_of)
    min_wage = parameters.get("dc.minimum_wage", as_of)
    multiple = parameters.get("dc.pfl.threshold_multiple", as_of)
    r1 = parameters.get("dc.pfl.tier1_rate", as_of)
    r2 = parameters.get("dc.pfl.tier2_rate", as_of)
    cap = parameters.get("dc.pfl.max_weekly_benefit", as_of)
    fmla_min_employees = parameters.get("dc.fmla.min_employees", as_of)
    fmla_min_months = parameters.get("dc.fmla.min_tenure_months", as_of)
    fmla_min_hours = parameters.get("dc.fmla.min_hours", as_of)

    # Job protection is the separate, NARROWER DC FMLA: 20+ employees, 12 months, 1,000 hours.
    job_protected = (
        facts.employer.total_employees >= fmla_min_employees
        and facts.tenure_months >= fmla_min_months
        and facts.employee.hours_last_12mo >= fmla_min_hours
    )

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, min_wage, multiple, r1, r2, cap) if aww is not None else None
    threshold = round(multiple * min_wage * WEEKLY_HOURS, 2)

    notes = [
        f"Up to {weeks:.0f} weeks each of parental, family, and medical leave (capped at "
        f"{weeks:.0f} combined per 52 weeks), plus up to {prenatal:.0f} weeks of prenatal leave "
        f"({combined:.0f} weeks max) ({DC_541_03}).",
        f"The benefit is pegged to the ${min_wage:,.2f} minimum wage: 90% of wages up to "
        f"${threshold:,.2f}/wk (150% of minimum wage x 40 hours), then 50%, capped at "
        f"${cap:,.2f}/wk ({DC_541_03}).",
    ]
    if job_protected:
        notes.append(
            f"Job protection comes from the separate DC FMLA, not the paid program: it requires a "
            f"{fmla_min_employees:.0f}+ employee employer, {fmla_min_months:.0f} months, and "
            f"{fmla_min_hours:.0f} hours ({DC_503})."
        )
    else:
        reason = (
            f"employer has {facts.employer.total_employees} employees (needs {fmla_min_employees:.0f}+)"
            if facts.employer.total_employees < fmla_min_employees
            else f"{facts.tenure_months:.1f} months / {facts.employee.hours_last_12mo:.0f} hours "
            f"(needs {fmla_min_months:.0f} months and {fmla_min_hours:.0f} hours)"
        )
        notes.append(
            f"Benefits are payable but DC FMLA job protection does not attach: {reason} ({DC_503}). "
            f"DC PFL covers far more workers than DC FMLA protects; federal FMLA is unlikely to help "
            f"a sub-20-employee worksite either."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
