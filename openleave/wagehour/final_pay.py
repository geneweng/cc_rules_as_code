"""Final-pay-on-separation timing and accrued-vacation payout.

Two states, two very different regimes — the reason this is a good Phase-1 pair
with minimum wage:

- California (Lab. Code §§ 201-203, 227.3): the sharpest deadlines in the country.
  Fired or laid off -> wages due immediately, that day. Quit with 72+ hours'
  notice -> due the last day. Quit without notice -> due within 72 hours. A
  willful late payment triggers a waiting-time penalty of up to 30 days' wages.
  Accrued vacation is earned wages and MUST be paid out.
- Washington (RCW 49.48.010): final wages are due by the end of the next
  established pay period, whatever the manner of separation. Accrued vacation is
  NOT owed by statute — payout depends on the employer's own policy or contract.

Federal law sets no separation-specific deadline; state law governs. For a state
this slice doesn't encode, that is exactly what the result says.
"""

from __future__ import annotations

from datetime import date, timedelta

from .. import parameters
from ..engine import Citation, Finding
from .facts import SeparationType, WageFacts
from .result import WageTopic

CA_201 = Citation("Cal. Lab. Code § 201")  # discharge — immediate
CA_202 = Citation("Cal. Lab. Code § 202")  # quit — 72 hours / last day
CA_203 = Citation("Cal. Lab. Code § 203")  # waiting-time penalty
CA_227_3 = Citation("Cal. Lab. Code § 227.3")  # accrued vacation = wages
WA_49_48 = Citation("RCW 49.48.010")

INVOLUNTARY = {SeparationType.FIRED, SeparationType.LAID_OFF}


def _california(facts: WageFacts, as_of: date, topic: WageTopic) -> None:
    sep = facts.separation
    if sep.type in INVOLUNTARY:
        deadline = sep.last_day
        rule = "Involuntary separation: final wages are due immediately, on the day of termination."
        citation = CA_201
    elif sep.type is SeparationType.QUIT_WITH_NOTICE:
        deadline = sep.last_day
        rule = "Quit with at least 72 hours' notice: final wages are due on the last day worked."
        citation = CA_202
    else:  # QUIT_WITHOUT_NOTICE
        hours = parameters.get("finalpay.CA.quit_no_notice_hours", as_of)
        deadline = sep.last_day + timedelta(hours=hours)
        rule = f"Quit without notice: final wages are due within {hours:.0f} hours of the last day."
        citation = CA_202

    topic.findings.append(
        Finding(
            key="final_pay_deadline",
            description=rule,
            met=True,
            citation=citation,
            detail=f"Deadline: {deadline.isoformat()}.",
        )
    )
    topic.data["deadline"] = deadline.isoformat()

    if sep.final_pay_date is not None:
        on_time = sep.final_pay_date <= deadline
        penalty_days = parameters.get("finalpay.CA.waiting_time_penalty_max_days", as_of)
        topic.findings.append(
            Finding(
                key="final_pay_timely",
                description=f"Final wages were paid on time (by {deadline.isoformat()})",
                met=on_time,
                citation=CA_203,
                detail=(
                    "Paid on or before the deadline."
                    if on_time
                    else f"Paid {sep.final_pay_date.isoformat()}, after the deadline. A willful "
                    f"late payment exposes the employer to a waiting-time penalty of up to "
                    f"{penalty_days:.0f} days' wages."
                ),
            )
        )
        topic.data["paid_on_time"] = on_time
        if not on_time:
            topic.human_judgment.append(
                "Whether the late payment was 'willful' (and so triggers the § 203 penalty) is a "
                "fact question for a human."
            )

    _vacation(facts, topic, required=True, citation=CA_227_3,
              rule="California treats accrued, unused vacation as earned wages that must be paid out.")


def _washington(facts: WageFacts, as_of: date, topic: WageTopic) -> None:
    topic.findings.append(
        Finding(
            key="final_pay_deadline",
            description="Final wages are due by the end of the next established pay period, "
            "regardless of how the employment ended.",
            met=True,
            citation=WA_49_48,
            detail="Washington sets no immediate-payment rule; the exact date depends on the "
            "employer's pay schedule.",
        )
    )
    topic.data["deadline"] = "end of next established pay period"
    topic.notes.append(
        "Provide the employer's pay schedule to compute an exact final-pay deadline date."
    )
    _vacation(facts, topic, required=False, citation=WA_49_48,
              rule="Washington does not require accrued-vacation payout by statute; it depends on "
              "the employer's policy or contract.")


def _vacation(facts: WageFacts, topic: WageTopic, required: bool, citation: Citation, rule: str) -> None:
    sep = facts.separation
    topic.data["vacation_payout_required"] = required
    if required:
        finding_met: bool | None = True
        detail = rule
        if sep.accrued_vacation_hours and facts.hourly_rate is not None:
            owed = round(sep.accrued_vacation_hours * facts.hourly_rate, 2)
            topic.data["vacation_payout_owed"] = owed
            detail = f"{rule} {sep.accrued_vacation_hours:.1f} hrs × ${facts.hourly_rate:.2f} = ${owed:,.2f} owed."
    else:
        finding_met = None  # turns on employer policy, not statute
        detail = rule
    topic.findings.append(
        Finding(
            key="accrued_vacation_payout",
            description="Accrued unused vacation must be paid out" if required
            else "Accrued-vacation payout is not required by statute (depends on policy)",
            met=finding_met,
            citation=citation,
            detail=detail,
        )
    )
    if not required:
        topic.human_judgment.append(
            "Whether accrued vacation is owed depends on the employer's written policy or contract — "
            "check it."
        )


_HANDLERS = {"CA": _california, "WA": _washington}


def assess(facts: WageFacts, as_of: date) -> WageTopic | None:
    """Assess final-pay timing and vacation payout. Returns None when the facts
    carry no separation to reason about."""
    if facts.separation is None:
        return None

    state = facts.work_state.upper()
    topic = WageTopic(topic="final_pay", name="Final pay on separation")
    topic.data["separation_type"] = facts.separation.type.value

    handler = _HANDLERS.get(state)
    if handler is None:
        topic.notes.append(
            f"Final-pay timing is governed by state law, and {state} is not encoded in this slice. "
            f"Federal law sets no separation-specific deadline. Do not treat the absence of a rule "
            f"here as 'no deadline applies'."
        )
        topic.data["deadline"] = None
        return topic

    handler(facts, as_of, topic)
    return topic
