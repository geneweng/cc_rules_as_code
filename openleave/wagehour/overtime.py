"""Overtime computation.

Two regimes:
- FLSA / Washington (29 U.S.C. § 207; RCW 49.46.130): time-and-a-half for hours
  over 40 in a workweek. No daily overtime.
- California (Cal. Lab. Code § 510): the intricate one. 1.5x over 8 hours in a
  day, 2x over 12 in a day, the seventh consecutive day of work paid at 1.5x for
  the first 8 hours and 2x beyond — plus the weekly 40-hour rule, applied so
  that hours already counted as daily overtime are not counted again (no
  pyramiding).

The regular rate folds in a nondiscretionary bonus (a blended rate) when one is
supplied, per 29 C.F.R. § 778.109.

Overtime is only owed to NON-EXEMPT workers, so the result is gated on the
exemption analysis: if the salary test leaves the worker possibly-exempt pending
the (human-only) duties test, the computed overtime is stated as conditional.
"""

from __future__ import annotations

from datetime import date

from .. import parameters
from ..engine import Citation, Finding
from . import exemptions
from .facts import WageFacts
from .result import WageTopic

FLSA_207 = Citation("29 U.S.C. § 207(a)")
CA_510 = Citation("Cal. Lab. Code § 510")
WA_49_46_130 = Citation("RCW 49.46.130")
CFR_778 = Citation("29 C.F.R. § 778.109")

DAILY_OT_STATES = {"CA"}


def _weekly_buckets(total: float, threshold: float) -> tuple[float, float, float]:
    """FLSA / WA: straight up to the weekly threshold, 1.5x beyond, no 2x."""
    straight = min(total, threshold)
    return straight, max(0.0, total - threshold), 0.0


def _california_buckets(
    daily_hours: list[float], daily_ot: float, double_ot: float, weekly_threshold: float
) -> tuple[float, float, float]:
    """CA daily + 7th-day rules, then the weekly rule without pyramiding."""
    seventh_consecutive = len(daily_hours) == 7 and all(h > 0 for h in daily_hours)
    straight = ot15 = ot2 = 0.0
    for i, h in enumerate(daily_hours):
        if seventh_consecutive and i == len(daily_hours) - 1:
            # Seventh consecutive day: first 8 hours at 1.5x, beyond 8 at 2x.
            ot15 += min(h, daily_ot)
            ot2 += max(0.0, h - daily_ot)
        else:
            straight += min(h, daily_ot)
            ot15 += max(0.0, min(h, double_ot) - daily_ot)
            ot2 += max(0.0, h - double_ot)
    # Weekly rule: straight-time hours beyond 40 convert to 1.5x (no pyramiding).
    if straight > weekly_threshold:
        convert = straight - weekly_threshold
        straight -= convert
        ot15 += convert
    return straight, ot15, ot2


def assess(facts: WageFacts, as_of: date) -> WageTopic | None:
    if facts.weekly_hours is None and facts.daily_hours is None:
        return None

    state = facts.work_state.upper()
    topic = WageTopic(topic="overtime", name="Overtime")

    weekly_threshold = parameters.get("overtime.federal.weekly_threshold_hours", as_of)
    total_hours = sum(facts.daily_hours) if facts.daily_hours is not None else facts.weekly_hours

    # Compute the hour buckets.
    if state in DAILY_OT_STATES and facts.daily_hours is not None:
        daily_ot = parameters.get("overtime.CA.daily_threshold_hours", as_of)
        double_ot = parameters.get("overtime.CA.double_time_daily_hours", as_of)
        straight, ot15, ot2 = _california_buckets(facts.daily_hours, daily_ot, double_ot, weekly_threshold)
        citation = CA_510
        basis = "California daily (>8 at 1.5x, >12 at 2x), 7th-day, and weekly (>40) rules"
    else:
        straight, ot15, ot2 = _weekly_buckets(total_hours, weekly_threshold)
        citation = WA_49_46_130 if state == "WA" else FLSA_207
        basis = f"{'Washington' if state == 'WA' else 'FLSA'} weekly rule (>{weekly_threshold:.0f} hours at 1.5x)"
        if state in DAILY_OT_STATES:
            topic.notes.append(
                "California also has daily and 7th-day overtime; provide daily_hours to compute them "
                "(only the weekly rule is applied here)."
            )

    topic.data.update(
        total_hours=total_hours, straight_hours=round(straight, 2),
        overtime_hours_1_5x=round(ot15, 2), overtime_hours_2x=round(ot2, 2),
    )
    topic.findings.append(
        Finding(
            key="overtime_hours",
            description=f"{ot15:g} hour(s) at 1.5x and {ot2:g} hour(s) at 2x, of {total_hours:g} worked",
            met=(ot15 + ot2) > 0,
            citation=citation,
            detail=basis + ".",
        )
    )

    # Regular rate (blended if a nondiscretionary bonus is present).
    rate = facts.hourly_rate
    if rate is not None:
        regular_rate = rate
        if facts.nondiscretionary_bonus and total_hours:
            regular_rate = (rate * total_hours + facts.nondiscretionary_bonus) / total_hours
            topic.findings.append(
                Finding(
                    key="regular_rate",
                    description=f"Blended regular rate ${regular_rate:.2f}/hour (includes the "
                    f"${facts.nondiscretionary_bonus:,.2f} nondiscretionary bonus)",
                    met=True,
                    citation=CFR_778,
                    detail=f"(${rate:.2f} × {total_hours:g} hrs + ${facts.nondiscretionary_bonus:,.2f}) "
                    f"÷ {total_hours:g} hrs.",
                )
            )
        premium = ot15 * 0.5 * regular_rate + ot2 * 1.0 * regular_rate
        gross = straight * regular_rate + ot15 * 1.5 * regular_rate + ot2 * 2.0 * regular_rate
        topic.data["regular_rate"] = round(regular_rate, 2)
        topic.data["overtime_premium_owed"] = round(premium, 2)
        topic.data["gross_pay"] = round(gross, 2)
    else:
        topic.notes.append("Provide hourly_rate to compute the overtime pay owed.")

    # Gate on exemption.
    if exemptions.applies(facts):
        st = exemptions.salary_test(facts, as_of)
        if st["meets"] is True:
            topic.notes.append(
                "This worker may be EXEMPT (the salary test is met): overtime is owed only if the "
                "duties test fails. See the exemption analysis — the duties test is unresolved, so "
                "the overtime above is conditional."
            )
            topic.human_judgment.append(
                "Confirm the worker is non-exempt (duties test) before treating overtime as owed."
            )
        elif st["meets"] is False:
            topic.notes.append(
                "The worker is non-exempt (salary below the exemption threshold), so this overtime "
                "is owed regardless of job duties."
            )

    return topic
