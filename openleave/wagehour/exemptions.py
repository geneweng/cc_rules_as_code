"""White-collar overtime-exemption analysis.

This is the module the scope doc warned about most: the place where a rules
engine is most tempting to over-reach. An executive/administrative/professional
exemption has TWO independent requirements — a salary paid on a salary basis at
or above a threshold, AND a duties test. The salary threshold is a clean,
effective-dated number. The DUTIES TEST is a multi-factor legal judgment that
decides most misclassification cases, and it is exactly the kind of open-textured
question this engine refuses to auto-answer.

So the honest design, implemented here:
- The salary test is decided by rule. If salary is below the threshold, the
  worker is non-exempt, full stop — no duties analysis can rescue a
  sub-threshold salary.
- The duties test is ALWAYS returned as `met: null` with a human_judgment entry.
  The engine never classifies duties.
- The overall conclusion is therefore, at best, "may be exempt IF the duties
  test is met" — never a bare "exempt".

Thresholds: federal $684/week (29 C.F.R. § 541.600 — the 2019 level, restored
after the 2024 rule was vacated). California is 2x the state minimum wage for a
full-time week; Washington is 2.25x in 2026 (phasing to 2.5x by 2028). Both are
computed from the encoded minimum wage, so they rise with it. The threshold most
favorable to the employee (the highest) governs.
"""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Finding
from .facts import PayBasis, WageFacts
from .result import WageTopic

CFR_541_600 = Citation("29 C.F.R. § 541.600")
CFR_541_100 = Citation("29 C.F.R. § 541.100")  # duties tests (executive et al.)
CA_515 = Citation("Cal. Lab. Code § 515(a)")
WA_296_128 = Citation("WAC 296-128-545")

_STATE_THRESHOLD_CITATION = {"CA": CA_515, "WA": WA_296_128}


def applies(facts: WageFacts) -> bool:
    """Exemption analysis is only meaningful for a salaried or claimed-exempt worker."""
    return facts.claimed_exempt or facts.pay_basis is PayBasis.SALARY or facts.annual_salary is not None


def salary_test(facts: WageFacts, as_of: date) -> dict:
    """The salary-basis half of the exemption: the governing weekly threshold, the
    worker's weekly salary, and whether it clears the bar (None if unknown)."""
    state = facts.work_state.upper()
    federal = parameters.get("exempt.federal.salary_weekly", as_of)
    levels = [("federal", federal, CFR_541_600)]

    mult_key = f"exempt.{state}.multiplier"
    if parameters.in_force(mult_key, as_of):
        weekly = parameters.get(mult_key, as_of) * parameters.get(f"minwage.{state}", as_of) * 40
        levels.append((state, weekly, _STATE_THRESHOLD_CITATION[state]))

    # Most favorable to the employee: the highest threshold governs.
    governing = max(levels, key=lambda lvl: lvl[1])
    weekly_salary = facts.annual_salary / 52 if facts.annual_salary is not None else None
    meets = None if weekly_salary is None else weekly_salary >= governing[1]
    return {
        "threshold_weekly": round(governing[1], 2),
        "threshold_annual": round(governing[1] * 52, 2),
        "governing_level": governing[0],
        "citation": governing[2],
        "weekly_salary": round(weekly_salary, 2) if weekly_salary is not None else None,
        "meets": meets,
    }


def assess(facts: WageFacts, as_of: date) -> WageTopic | None:
    if not applies(facts):
        return None

    topic = WageTopic(topic="exemption", name="Overtime exemption (white-collar)")
    st = salary_test(facts, as_of)
    topic.data.update(
        applicable_salary_threshold_weekly=st["threshold_weekly"],
        applicable_salary_threshold_annual=st["threshold_annual"],
        threshold_governing_level=st["governing_level"],
        weekly_salary=st["weekly_salary"],
        salary_meets_threshold=st["meets"],
    )

    if st["weekly_salary"] is None:
        topic.findings.append(
            Finding(
                key="salary_basis",
                description=f"Paid a salary of at least ${st['threshold_weekly']:,.2f}/week "
                f"(${st['threshold_annual']:,.0f}/year)",
                met=None,
                citation=st["citation"],
                detail="Provide annual_salary to evaluate the salary-basis test.",
            )
        )
    else:
        topic.findings.append(
            Finding(
                key="salary_basis",
                description=f"Salary of ${st['weekly_salary']:,.2f}/week meets the "
                f"${st['threshold_weekly']:,.2f}/week threshold ({st['governing_level']})",
                met=st["meets"],
                citation=st["citation"],
                detail=f"Annual threshold ${st['threshold_annual']:,.0f}; the higher of federal and "
                f"state governs (most favorable to the employee).",
            )
        )

    # The duties test is never decided by the engine.
    topic.findings.append(
        Finding(
            key="duties_test",
            description="The exemption's duties test is met (executive / administrative / professional)",
            met=None,
            citation=CFR_541_100,
            detail="A multi-factor legal analysis of the employee's actual job duties. This engine "
            "never classifies duties — it must be determined by a human.",
        )
    )
    topic.human_judgment.append(
        "The white-collar duties test is open-textured and decides most misclassification cases; "
        "a qualified human must analyze the employee's actual duties. A title or a salary alone "
        "does not establish exemption."
    )

    # Conclusion.
    if st["meets"] is False:
        status = "non_exempt_salary_below_threshold"
        topic.notes.append(
            "The worker is NON-EXEMPT: the salary is below the threshold, so the exemption fails on "
            "the salary basis alone, regardless of duties. Overtime rules apply."
        )
    elif st["meets"] is True:
        status = "possibly_exempt_pending_duties"
        topic.notes.append(
            "The salary test is met, so the worker MAY be exempt — but only if the duties test is "
            "also satisfied. Until a human confirms the duties, treat the worker as non-exempt for "
            "overtime purposes."
        )
    else:
        status = "salary_unknown"
    topic.data["status"] = status
    return topic
