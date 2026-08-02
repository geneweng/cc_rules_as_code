"""Rhode Island Temporary Disability Insurance (TDI) and Temporary Caregiver
Insurance (TCI), R.I. Gen. Laws ch. 28-41.

Rhode Island is the oldest program in this encoding (TDI dates to 1942, TCI to
2014) and the only one that pays a UI-style benefit computed from a single
quarter: 4.62% of the wages in the highest quarter of the base period, not a
percentage of the average weekly wage. It is really two programs sharing one
fund, and they differ on the two things a caller most needs to know:

- TCI (bonding / family care) pays up to 8 weeks AND carries job protection.
- TDI (the worker's own disability) pays up to 30 weeks but has NO job
  protection of its own — reinstatement, if any, comes from the RI Parental and
  Family Medical Leave Act (employers with 50+ employees) or the FMLA.

Military-exigency leave is not a covered reason under either.

Sources (pending counsel review): 4.62% of high-quarter wages, not to exceed 85%
of the average weekly wage; max $1,150/wk (plus a dependency allowance up to
$1,552 with five dependents), min $148/wk, effective 2026-07-01; $19,200
base-period earnings (with an alternate test); TCI 8 weeks, TDI 30 weeks;
dlt.ri.gov.
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

PROGRAM = "Rhode Island Temporary Disability & Caregiver Insurance"
RIGL_28_41_5 = "R.I. Gen. Laws § 28-41-5"
RIGL_28_41_35 = "R.I. Gen. Laws § 28-41-35"
RIGL_TCI_PROTECTION = "R.I. Gen. Laws § 28-41-36"

# Benefit parameters are encoded from the 2026-07-01 maximum-benefit update.
ENCODED_FROM = date(2026, 7, 1)

# A quarter of the base period, approximated as 13 weeks of the average weekly wage.
WEEKS_PER_QUARTER = 13

CAREGIVER_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE}  # TCI
DISABILITY_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}  # TDI


def _weekly_benefit(
    high_quarter: float, aww: float, rate: float, aww_cap_fraction: float, cap: float, floor: float
) -> float:
    """4.62% of the highest-quarter wages, not to exceed 85% of the average weekly
    wage, then floored and capped (R.I. Gen. Laws § 28-41-5). The dependency
    allowance (up to $1,552 with five dependents) is not modeled here."""
    benefit = min(rate * high_quarter, aww_cap_fraction * aww)
    benefit = max(benefit, floor)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="ri_tci_tdi", name=PROGRAM, applies=facts.employee.work_state == "RI", eligible=None
    )
    if not result.applies:
        return result

    if as_of < ENCODED_FROM:
        result.applies = False
        result.notes.append(encoded_range_note(PROGRAM, ENCODED_FROM))
        return result

    is_tci = facts.event.type in CAREGIVER_REASONS
    is_tdi = facts.event.type in DISABILITY_REASONS
    if not (is_tci or is_tdi):
        # Military-exigency leave is not covered by TDI or TCI.
        result.applies = False
        return result

    minimum = parameters.get("ri.min_base_period_earnings", as_of)
    wages = facts.base_period_wages
    result.findings = [
        Finding(
            key="base_period_earnings",
            description=f"At least ${minimum:,.0f} in base-period earnings (or the alternate "
            f"earnings test)",
            met=None if wages is None else wages >= minimum,
            citation=Citation(RIGL_28_41_5),
            detail="Wage data not provided"
            if wages is None
            else f"Base-period wages: ${wages:,.0f}. An alternate test may qualify lower earners.",
        ),
    ]

    if is_tdi:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a disability under TDI",
                met=None,
                citation=Citation(RIGL_28_41_5),
                detail="Requires medical certification and case-by-case judgment.",
            )
        )
        result.human_judgment.append(
            f"RI TDI disability determination requires medical certification ({RIGL_28_41_5})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    program = "TCI (caregiver)" if is_tci else "TDI (own disability)"
    weeks = parameters.get("ri.tci.weeks" if is_tci else "ri.tdi.weeks", as_of)
    rate = parameters.get("ri.benefit_rate_of_high_quarter", as_of)
    aww_cap_fraction = parameters.get("ri.aww_cap_fraction", as_of)
    cap = parameters.get("ri.max_weekly_benefit", as_of)
    floor = parameters.get("ri.min_weekly_benefit", as_of)

    aww = facts.employee.average_weekly_wage
    benefit = (
        _weekly_benefit(aww * WEEKS_PER_QUARTER, aww, rate, aww_cap_fraction, cap, floor)
        if aww is not None
        else None
    )

    notes = [
        f"This is a {program} claim: up to {weeks:.0f} weeks ({RIGL_28_41_35}).",
        f"Weekly benefit is {rate * 100:.2f}% of the highest base-period quarter, capped at "
        f"${cap:,.0f} (plus a dependency allowance up to $1,552 with five dependents) and floored "
        f"at ${floor:,.0f} ({RIGL_28_41_5}).",
    ]
    if is_tci:
        job_protected = True
        notes.append(
            f"TCI carries its own job protection — restoration to the prior or a comparable "
            f"position ({RIGL_TCI_PROTECTION})."
        )
    else:
        job_protected = False
        notes.append(
            "TDI pays wage replacement but carries no job protection of its own. Reinstatement, if "
            "any, comes from the RI Parental and Family Medical Leave Act (employers with 50+ "
            "employees) or the federal FMLA."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
