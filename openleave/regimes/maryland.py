"""Maryland Family and Medical Leave Insurance (FAMLI), the Time to Care Act,
Md. Code, Labor & Employment § 8.3-101 et seq.

Maryland is the first regime in this encoding that is *enacted but not yet in
force*. The Time to Care Act passed in 2022, but implementation has been delayed
three years running: as of the 2025 amendment (HB 102), payroll contributions
begin 2027-01-01 and benefits become payable 2028-01-03. So for every date this
prototype is realistically asked about today, the correct answer is not an
eligibility result but a pending-program notice — which is exactly what a rules
oracle must say instead of silently returning "FMLA only" (which would read as
"no state benefit") or inventing a benefit that cannot be claimed yet.

This is the mirror image of the WA/CO/OR/CT "outside the encoded range" case:
there the program was paying and we lacked historic rates; here the program pays
nothing yet. The engine distinguishes the two.

Once in force (2028-01-03), FAMLI provides 12 weeks (up to 24 if a worker both
welcomes a child and has their own serious health condition in the same year),
paid at 90% of wages up to 65% of the state average weekly wage then 50%, floored
at $50 and capped at $1,000 — but the launch-year SAWW is set annually by the
Maryland Secretary of Labor and is not published yet, so this encoding reports
the statutory structure and bounds rather than a fabricated benefit figure.

Sources (pending counsel review): 680-hour eligibility, $50-$1,000 benefit,
12/24 weeks (paidleave.maryland.gov); 2028-01-03 benefit start (HB 102, 2025);
15-employee job-protection threshold.
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
    not_yet_in_force_note,
    resolve_eligibility,
)
from ..facts import Facts

PROGRAM = "Maryland Family and Medical Leave Insurance"
MD_8_3_701 = "Md. Code, Lab. & Empl. § 8.3-701"
MD_8_3_707 = "Md. Code, Lab. & Empl. § 8.3-707"
MD_8_3_301 = "Md. Code, Lab. & Empl. § 8.3-301"

# Benefits become payable on this date (Time to Care Act, as amended by HB 102, 2025).
IN_FORCE = date(2028, 1, 3)

FAMILY_REASONS = {LeaveReason.BONDING, LeaveReason.FAMILY_CARE, LeaveReason.MILITARY_EXIGENCY}
MEDICAL_REASONS = {LeaveReason.OWN_SERIOUS_HEALTH, LeaveReason.PREGNANCY}


def evaluate(facts: Facts, as_of: date) -> RegimeResult:
    result = RegimeResult(
        regime="md_famli", name=PROGRAM, applies=facts.employee.work_state == "MD", eligible=None
    )
    if not result.applies:
        return result

    if as_of < IN_FORCE:
        result.applies = False
        result.notes.append(not_yet_in_force_note(PROGRAM, IN_FORCE))
        return result

    is_family = facts.event.type in FAMILY_REASONS
    is_medical = facts.event.type in MEDICAL_REASONS
    if not (is_family or is_medical):
        result.applies = False
        return result

    min_hours = parameters.get("md.eligibility.min_hours", as_of)
    result.findings = [
        Finding(
            key="qualifying_hours",
            description=f"At least {min_hours:.0f} hours worked in Maryland in the four quarters "
            f"before leave",
            met=facts.employee.hours_last_12mo >= min_hours,
            citation=Citation(MD_8_3_301),
            detail=f"Hours in previous 12 months: {facts.employee.hours_last_12mo:.0f}",
        ),
    ]

    if is_medical:
        result.findings.append(
            Finding(
                key="serious_health_condition",
                description="The condition qualifies as a 'serious health condition'",
                met=None,
                citation=Citation(MD_8_3_701),
                detail="Requires certification and case-by-case judgment; not determinable by rule.",
            )
        )
        result.human_judgment.append(
            f"MD 'serious health condition' determination requires certification ({MD_8_3_701})."
        )

    result.eligible = resolve_eligibility(result.findings)
    if result.eligible is False:
        return result

    weeks = parameters.get("md.weeks", as_of)
    extended = parameters.get("md.extended.weeks", as_of)
    max_benefit = parameters.get("md.pfl.max_weekly_benefit", as_of)
    min_benefit = parameters.get("md.pfl.min_weekly_benefit", as_of)
    min_employees = parameters.get("md.job_protection.min_employees", as_of)

    job_protected = facts.employer.total_employees >= min_employees

    notes = [
        f"Up to {weeks:.0f} weeks per application year; up to {extended:.0f} weeks if the worker "
        f"both welcomes a child and has their own serious health condition in the same year "
        f"({MD_8_3_707}).",
        f"Weekly benefit is 90% of wages up to 65% of the Maryland state average weekly wage, then "
        f"50%, floored at ${min_benefit:,.0f} and capped at ${max_benefit:,.0f} ({MD_8_3_707}). The "
        f"launch-year SAWW is set annually by the Secretary of Labor and is not encoded here, so no "
        f"point estimate is given.",
    ]
    if job_protected:
        notes.append(
            f"Job restoration is provided for employers with {min_employees:.0f}+ employees "
            f"({MD_8_3_707})."
        )
    else:
        notes.append(
            f"Benefits are payable but Maryland job restoration may not attach: employer has "
            f"{facts.employer.total_employees} employees (threshold {min_employees:.0f}) "
            f"({MD_8_3_707}). Check whether federal FMLA or another law protects the position."
        )

    result.entitlement = Entitlement(
        weeks=weeks, job_protected=job_protected, weekly_benefit=None, notes=notes
    )
    return result
