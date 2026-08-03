"""Minimum-wage assessment: the applicable floor on a given date, tip-credit
handling, and (if a pay rate is supplied) a compliance check.

The whole thing is an effective-dated lookup with one wrinkle — the tip credit.
Under the FLSA an employer may pay a tipped worker a $2.13 cash wage as long as
tips make up the difference to $7.25. Some states (California and Washington
among them) prohibit the tip credit entirely: tipped workers get the full state
minimum in cash, with tips on top. That contrast is the substance here.
"""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Finding
from . import localities
from .facts import PayBasis, WageFacts
from .result import WageTopic

# States that prohibit the tip credit (tipped workers get full minimum in cash).
# Cited to state law; only the Phase-1 encoded states are listed.
TIP_CREDIT_PROHIBITED = {
    "CA": Citation("Cal. Lab. Code § 351"),
    "WA": Citation("RCW 49.46.020(3)"),
}

FLSA = Citation("29 U.S.C. § 206(a)")
FLSA_TIP = Citation("29 U.S.C. § 203(m)")
STATE_MINWAGE_CITATION = {
    "CA": Citation("Cal. Lab. Code § 1182.12"),
    "WA": Citation("RCW 49.46.020"),
}


def assess(facts: WageFacts, as_of: date) -> WageTopic:
    state = facts.work_state.upper()
    topic = WageTopic(topic="minimum_wage", name="Minimum wage")

    # Build the stack of minimum-wage floors that apply — federal, state, and
    # (if the worksite is in an encoded locality) local. The highest governs; on a
    # tie the most local level wins.
    federal = parameters.get("minwage.federal", as_of)
    levels: list[tuple[str, float, Citation, str]] = [
        ("federal", federal, FLSA, f"federal ${federal:.2f}")
    ]

    state_key = f"minwage.{state}"
    state_min = parameters.get(state_key, as_of) if parameters.in_force(state_key, as_of) else None
    if state_min is not None:
        levels.append(
            ("state", state_min, STATE_MINWAGE_CITATION.get(state, FLSA), f"{state} state ${state_min:.2f}")
        )

    loc = localities.lookup(state, facts.work_locality)
    local_min = None
    if loc is not None and parameters.in_force(loc["param_key"], as_of):
        local_min = parameters.get(loc["param_key"], as_of)
        levels.append(
            ("local", local_min, Citation(loc["citation"]), f"{loc['display']} local ${local_min:.2f}")
        )

    governing = levels[0]
    for level in levels[1:]:
        if level[1] >= governing[1]:
            governing = level
    gov_level, applicable, source, _ = governing

    topic.findings.append(
        Finding(
            key="applicable_minimum_wage",
            description=f"The applicable minimum wage is ${applicable:.2f}/hour",
            met=True,
            citation=source,
            detail="; ".join(label for _, _, _, label in levels)
            + f"; the highest governs ({gov_level}).",
        )
    )
    topic.data["federal_minimum"] = federal
    topic.data["state_minimum"] = state_min
    topic.data["local_minimum"] = local_min
    topic.data["local_name"] = loc["display"] if local_min is not None else None
    topic.data["governing_level"] = gov_level
    topic.data["applicable_minimum"] = applicable

    # Tipped-wage handling.
    cash_floor = applicable
    if facts.is_tipped:
        if state in TIP_CREDIT_PROHIBITED:
            topic.findings.append(
                Finding(
                    key="tip_credit",
                    description=f"{state} prohibits the tip credit — the full ${applicable:.2f} "
                    f"minimum must be paid in cash, with tips on top",
                    met=True,
                    citation=TIP_CREDIT_PROHIBITED[state],
                    detail="Tips do not offset the employer's cash-wage obligation.",
                )
            )
            topic.data["tip_credit_allowed"] = False
        else:
            tipped_cash = parameters.get("minwage.federal.tipped_cash", as_of)
            credit_max = parameters.get("minwage.federal.tip_credit_max", as_of)
            cash_floor = tipped_cash
            topic.findings.append(
                Finding(
                    key="tip_credit",
                    description=f"Federal tip credit permitted: cash wage may be as low as "
                    f"${tipped_cash:.2f} if tips bring total pay to ${applicable:.2f}",
                    met=True,
                    citation=FLSA_TIP,
                    detail=f"Maximum tip credit ${credit_max:.2f}. State law may restrict this; "
                    f"only CA and WA tip rules are encoded in this slice.",
                )
            )
            topic.data["tip_credit_allowed"] = True
            topic.data["tipped_cash_floor"] = tipped_cash
            topic.human_judgment.append(
                f"Confirm whether {state} permits the federal tip credit — only CA/WA tip rules "
                f"are encoded here."
            )

    topic.data["cash_floor"] = cash_floor

    # Compliance check, only if a rate was supplied.
    if facts.pay_basis is PayBasis.SALARY:
        topic.notes.append(
            "Pay basis is salary; convert to an effective hourly rate (salary ÷ hours worked) to "
            "check minimum-wage compliance."
        )
    elif facts.hourly_rate is not None:
        compliant = facts.hourly_rate >= cash_floor
        topic.findings.append(
            Finding(
                key="rate_meets_minimum",
                description=f"The ${facts.hourly_rate:.2f}/hour cash rate meets the ${cash_floor:.2f} "
                f"cash floor",
                met=compliant,
                citation=source,
                detail=(
                    "At or above the floor."
                    if compliant
                    else f"Below the floor by ${cash_floor - facts.hourly_rate:.2f}/hour — likely a "
                    f"minimum-wage violation."
                ),
            )
        )
        topic.data["rate_compliant"] = compliant
        if facts.is_tipped and topic.data.get("tip_credit_allowed"):
            topic.notes.append(
                f"Tipped worker: the ${facts.hourly_rate:.2f} cash rate is only lawful if cash + tips "
                f"reach ${applicable:.2f}/hour each week; provide tip data to confirm."
            )
    else:
        topic.notes.append("Provide hourly_rate to check whether the wage paid meets the minimum.")

    return topic
