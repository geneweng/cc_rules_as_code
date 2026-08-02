"""Maine Paid Family and Medical Leave, 26 M.R.S. ch. 7, subch. 6-A (§ 850-A et seq.).

Maine's benefit formula has a distinctive second tier. Where Washington and
Colorado drop to 50% above the 50%-of-SAWW breakpoint, Maine drops only to 66%,
so middle earners are replaced more generously — 90% of wages up to half the
state average weekly wage, then 66% of the rest, with the whole benefit capped at
100% of the SAWW (not a fraction of it).

Eligibility is a wage floor expressed as a multiple of the SAWW: 6x the state
average weekly wage earned in the base period. Job protection vests quickly, at
120 days of service.

Sources (pending counsel review): benefits began 2026-05-01; max weekly benefit
$1,198 through 2026-06-30 then the SAWW $1,249.12 (2026-07-01 to 2027-06-30);
90%/66% formula around 50% of SAWW, capped at 100% of SAWW; 6x-SAWW earnings
test; 12 weeks (16 combined); 120-day job protection; maine.gov/paidleave.
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

PROGRAM = "Maine Paid Family and Medical Leave"
ME_850A = "26 M.R.S. § 850-A"
ME_850_BENEFITS = "26 M.R.S. ch. 7, subch. 6-A"
ME_850_PROTECTION = "26 M.R.S. § 850-F"

# Benefits became payable 2026-05-01.
ENCODED_FROM = date(2026, 5, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def _weekly_benefit(aww: float, saww: float, r1: float, r2: float, threshold_fraction: float) -> float:
    """90% of the average weekly wage up to 50% of the state average weekly wage,
    then 66% of the excess, capped at 100% of the SAWW (26 M.R.S. ch. 7, subch. 6-A)."""
    threshold = threshold_fraction * saww
    if aww <= threshold:
        benefit = r1 * aww
    else:
        benefit = r1 * threshold + r2 * (aww - threshold)
    return round(min(benefit, saww), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="me_pfml", name=PROGRAM, applies=facts.employee.work_state == "ME", eligible=None
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

    saww = parameters.get("me.saww", as_of)
    multiple = parameters.get("me.eligibility_saww_multiple", as_of)
    minimum = multiple * saww
    wages = facts.base_period_wages

    result.findings = [
        Finding(
            key="minimum_earnings",
            description=f"Base-period earnings of at least {multiple:.0f}x the state average weekly "
            f"wage (${minimum:,.0f})",
            met=None if wages is None else wages >= minimum,
            citation=Citation(ME_850A),
            detail="Wage data not provided" if wages is None else f"Base-period wages: ${wages:,.0f}",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(ME_850A),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"ME 'serious health condition' determination requires certification ({ME_850A})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("me.weeks", as_of)
    combined = parameters.get("me.combined.weeks", as_of)
    r1 = parameters.get("me.tier1_rate", as_of)
    r2 = parameters.get("me.tier2_rate", as_of)
    threshold_fraction = parameters.get("me.tier_threshold_fraction", as_of)
    min_days = parameters.get("me.job_protection.min_service_days", as_of)

    tenure_days = (facts.event.start - facts.employee.hire_date).days
    job_protected = tenure_days >= min_days

    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, saww, r1, r2, threshold_fraction) if aww is not None else None

    notes = [
        f"Up to {weeks:.0f} weeks of family or medical leave, capped at {combined:.0f} weeks "
        f"combined per benefit year ({ME_850_BENEFITS}).",
        f"Benefit is {r1 * 100:.0f}% of wages up to {threshold_fraction * 100:.0f}% of the "
        f"${saww:,.2f} SAWW, then {r2 * 100:.0f}%, capped at the full SAWW ({ME_850_BENEFITS}).",
    ]
    if job_protected:
        notes.append(
            f"Job protection attaches after {min_days:.0f} days of service ({ME_850_PROTECTION})."
        )
    else:
        notes.append(
            f"Benefits are payable but Maine job protection does not attach: {tenure_days} days of "
            f"service (needs {min_days:.0f}) ({ME_850_PROTECTION}). Check whether FMLA or another "
            f"law protects the position."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
