"""Massachusetts Paid Family and Medical Leave, M.G.L. c. 175M.

Massachusetts is the one program here whose eligibility test depends on the
benefit amount: a claimant needs base-period wages of at least 30 times their
own weekly benefit rate, so the benefit must be computed before eligibility can
be resolved. It also carries its own job protection — unlike California PFL or
New Jersey FLI, no companion statute is needed for reinstatement.
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

PROGRAM = "Massachusetts Paid Family and Medical Leave"
MGL_175M_1 = "M.G.L. c. 175M, § 1"
MGL_175M_2 = "M.G.L. c. 175M, § 2"
MGL_175M_3 = "M.G.L. c. 175M, § 3"
MGL_151A_24 = "M.G.L. c. 151A, § 24(a)"

# Benefit parameters are encoded from 2026 onward; the program began paying in 2021.
ENCODED_FROM = date(2026, 1, 1)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}

WAITING_PERIOD_DAYS = 7


def _weekly_benefit(iaww: float, saww: float, cap: float) -> float:
    """Two-tier replacement per M.G.L. c. 175M, § 3(b): 80% of the individual
    average weekly wage up to 50% of the state average weekly wage, then 50% of
    the excess, capped at 64% of the SAWW."""
    half = 0.5 * saww
    benefit = 0.8 * min(iaww, half)
    if iaww > half:
        benefit += 0.5 * (iaww - half)
    return round(min(benefit, cap), 2)


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="ma_pfml", name=PROGRAM, applies=facts.employee.work_state == "MA", eligible=None
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

    saww = parameters.get("ma.saww", as_of)
    cap = parameters.get("ma.max_weekly_benefit", as_of)
    minimum = parameters.get("ma.min_base_period_earnings", as_of)

    wages = facts.base_period_wages
    aww = facts.employee.average_weekly_wage
    benefit = _weekly_benefit(aww, saww, cap) if aww is not None else None

    result.findings = [
        Finding(
            key="minimum_earnings",
            description=f"At least ${minimum:,.0f} in base-period wages",
            met=None if wages is None else wages >= minimum,
            citation=Citation(f"{MGL_175M_2}(b)", None),
            detail="Wage data not provided" if wages is None else f"Base-period wages: ${wages:,.0f}",
        ),
    ]

    # The 30x test is self-referential: it compares base-period wages against the
    # claimant's own weekly benefit rate, so it can only be evaluated once the
    # benefit is known.
    if wages is None or benefit is None:
        result.findings.append(
            Finding(
                key="thirty_times_benefit",
                description="Base-period wages of at least 30 times the weekly benefit rate",
                met=None,
                citation=Citation(MGL_151A_24),
                detail="Provide average_weekly_wage and wage history to evaluate this test.",
            )
        )
        result.human_judgment.append(
            "Provide wage data to evaluate the 30x-weekly-benefit financial eligibility test."
        )
    else:
        threshold = 30 * benefit
        result.findings.append(
            Finding(
                key="thirty_times_benefit",
                description=f"Base-period wages of at least 30 times the weekly benefit rate "
                f"(30 × ${benefit:,.2f} = ${threshold:,.0f})",
                met=wages >= threshold,
                citation=Citation(MGL_151A_24),
                detail=f"Base-period wages: ${wages:,.0f}",
            )
        )

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(MGL_175M_1),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"MA 'serious health condition' determination requires certification ({MGL_175M_1})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("ma.family.weeks" if is_family else "ma.medical.weeks", as_of)
    combined = parameters.get("ma.combined.weeks", as_of)

    notes = [
        f"Combined family + medical leave is capped at {combined:.0f} weeks per benefit year "
        f"({MGL_175M_3}(a)); leave to care for a covered service member also runs to "
        f"{combined:.0f} weeks.",
        f"No benefits are payable for the first {WAITING_PERIOD_DAYS} calendar days of leave "
        f"({MGL_175M_3}(c)); accrued employer paid time off may cover that week.",
        f"Job restoration to the same or an equivalent position is provided by the statute "
        f"itself ({MGL_175M_2}(e)) — no companion job-protection law is required.",
    ]
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=True, weekly_benefit=benefit, notes=notes
    )
    return result
