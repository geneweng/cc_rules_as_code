"""New Jersey Family Leave Insurance, N.J.S.A. 43:21-25 et seq.

New Jersey separates money from job security more sharply than any other state
encoded here, and that separation changed mid-2026:

- FLI pays benefits and, historically, provided no job protection at all.
- Job protection came from the separate New Jersey Family Leave Act (NJFLA),
  which has its own employer-size and service tests.
- Effective 2026-07-17, A3451 requires reinstatement for employees taking FLI
  (and TDI) leave — so for leave starting on or after that date, FLI carries
  protection of its own.

Eligibility also has an alternative route this encoding can only partly test:
a claimant qualifies on 20 base weeks at the base-week wage *or* on total
base-year earnings. Only the earnings route is computable from the facts this
engine collects, so failing it is reported as "needs review", never as a denial.
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

PROGRAM = "New Jersey Family Leave Insurance"
NJSA_43_21_27 = "N.J.S.A. 43:21-27"
NJSA_43_21_38 = "N.J.S.A. 43:21-38"
NJSA_34_11B_4 = "N.J.S.A. 34:11B-4"
A3451 = "N.J. A3451 (2026), amending N.J.S.A. 43:21-25 et seq."

# Benefit parameters are encoded from 2026 onward; FLI has paid benefits since 2009.
ENCODED_FROM = date(2026, 1, 1)

# A3451 extends reinstatement rights to FLI/TDI leave from this date.
FLI_REINSTATEMENT_FROM = date(2026, 7, 17)

FLI_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE}


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="nj_fli", name=PROGRAM, applies=facts.employee.work_state == "NJ", eligible=None
    )
    if not result.applies:
        return result

    if as_of < ENCODED_FROM:
        result.applies = False
        result.notes.append(encoded_range_note(PROGRAM, ENCODED_FROM))
        return result

    if facts.event.type not in FLI_REASONS:
        result.applies = False
        result.notes.append(
            "An employee's own disability (including pregnancy) is covered by New Jersey "
            "Temporary Disability Insurance (N.J.S.A. 43:21-25 et seq.), not Family Leave "
            "Insurance; NJ TDI is not encoded in this prototype."
        )
        return result

    min_earnings = parameters.get("nj.fli.min_base_year_earnings", as_of)
    base_week_wage = parameters.get("nj.fli.base_week_earnings", as_of)
    wages = facts.base_period_wages

    if wages is None:
        met, detail = None, "Wage data not provided"
    elif wages >= min_earnings:
        met, detail = True, f"Base-year wages: ${wages:,.0f}"
    else:
        # The 20-base-week alternative needs week-by-week wage history, which
        # this engine does not collect — so this is unresolved, not a denial.
        met = None
        detail = (
            f"Base-year wages ${wages:,.0f} are below the ${min_earnings:,.0f} earnings route. "
            f"The claimant may still qualify on 20 base weeks of at least ${base_week_wage:,.0f}, "
            f"which requires week-by-week wage history not collected here."
        )

    result.findings = [
        Finding(
            key="monetary_eligibility",
            description=f"Either 20 base weeks of at least ${base_week_wage:,.0f}, or at least "
            f"${min_earnings:,.0f} in base-year wages",
            met=met,
            citation=Citation(f"{NJSA_43_21_27}(e)"),
            detail=detail,
        ),
    ]
    if met is None:
        result.human_judgment.append(
            "Confirm New Jersey FLI monetary eligibility against week-by-week wage history "
            f"(20 base weeks at ${base_week_wage:,.0f}) — the earnings route alone is not decisive."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    rate = parameters.get("nj.fli.wage_replacement_rate", as_of)
    cap = parameters.get("nj.fli.max_weekly_benefit", as_of)
    weeks = parameters.get("nj.fli.weeks", as_of)
    njfla_min_employees = parameters.get("nj.njfla.min_employees", as_of)
    njfla_min_hours = parameters.get("nj.njfla.min_hours", as_of)

    aww = facts.employee.average_weekly_wage
    benefit = round(min(rate * aww, cap), 2) if aww is not None else None

    njfla_protected = (
        facts.employer.total_employees >= njfla_min_employees
        and facts.tenure_months >= 12
        and facts.employee.hours_last_12mo >= njfla_min_hours
    )
    fli_protected = facts.event.start >= FLI_REINSTATEMENT_FROM
    job_protected = njfla_protected or fli_protected

    notes = [
        f"Benefit is {rate:.0%} of the average weekly wage, capped at ${cap:,.2f}/week "
        f"({NJSA_43_21_38}).",
        f"Up to {weeks:.0f} consecutive weeks, or 8 weeks of intermittent leave, in a "
        f"12-month period ({NJSA_43_21_38}).",
    ]

    sources = []
    if fli_protected:
        sources.append(f"FLI leave itself, effective {FLI_REINSTATEMENT_FROM.isoformat()} ({A3451})")
    if njfla_protected:
        sources.append(
            f"the New Jersey Family Leave Act — {njfla_min_employees:.0f}+ employees, 12 months "
            f"of service, {njfla_min_hours:.0f} hours ({NJSA_34_11B_4})"
        )
    if sources:
        notes.append("Job protection comes from " + "; and ".join(sources) + ".")
    else:
        notes.append(
            f"FLI pays benefits but provides no job protection for leave beginning before "
            f"{FLI_REINSTATEMENT_FROM.isoformat()} ({A3451}), and the NJFLA test is not met "
            f"({NJSA_34_11B_4}). The position is not protected by New Jersey law on these facts — "
            f"check FMLA."
        )
    if benefit is None:
        notes.append("Provide average_weekly_wage to estimate the weekly benefit.")

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=benefit, notes=notes
    )
    return result
