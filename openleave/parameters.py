"""Effective-dated statutory parameters.

Each key maps to a list of (effective_date, value) pairs sorted ascending.
`get(key, as_of)` returns the value in force on `as_of` — this is what lets a
determination be evaluated "under the law as of" any date.

PROTOTYPE NOTE: values are approximations gathered for demonstration. Verify
against the responsible agency's current published figures before any real use.
"""

from __future__ import annotations

from datetime import date

_PARAMETERS: dict[str, list[tuple[date, float]]] = {
    # New York — NYS DFL/PFL; SAWW set annually by NYSDOL
    "ny.saww": [(date(2025, 1, 1), 1757.19), (date(2026, 1, 1), 1839.34)],
    "ny.pfl.weeks": [(date(2021, 1, 1), 12)],
    "ny.pfl.wage_replacement_rate": [(date(2021, 1, 1), 0.67)],
    # Minnesota — Paid Leave (Minn. Stat. ch. 268B), benefits began 2026-01-01
    "mn.saww": [(date(2026, 1, 1), 1423.00)],
    "mn.wage_threshold_fraction_of_saaw": [(date(2026, 1, 1), 0.053)],  # of state average ANNUAL wage
    "mn.family.weeks": [(date(2026, 1, 1), 12)],
    "mn.medical.weeks": [(date(2026, 1, 1), 12)],
    "mn.combined.weeks": [(date(2026, 1, 1), 20)],
    # California — CFRA (Gov. Code § 12945.2) + PFL (Unemp. Ins. Code)
    "ca.saww": [(date(2025, 1, 1), 1642.00), (date(2026, 1, 1), 1704.00)],
    "ca.pfl.weeks": [(date(2025, 1, 1), 8)],
    "ca.pfl.max_weekly_benefit": [(date(2025, 1, 1), 1681.00)],
    "ca.pfl.low_earner_rate": [(date(2025, 1, 1), 0.90)],  # SB 951
    "ca.pfl.standard_rate": [(date(2025, 1, 1), 0.70)],
    "ca.pfl.min_base_period_earnings": [(date(2025, 1, 1), 300.00)],
    # Federal FMLA
    "fmla.weeks": [(date(1993, 8, 5), 12)],
    "fmla.min_hours": [(date(1993, 8, 5), 1250)],
    "fmla.min_worksite_headcount": [(date(1993, 8, 5), 50)],
}


def get(key: str, as_of: date) -> float:
    entries = _PARAMETERS[key]
    value = None
    for effective, v in entries:
        if effective <= as_of:
            value = v
    if value is None:
        raise KeyError(f"Parameter {key!r} has no value in force on {as_of.isoformat()}")
    return value


def in_force(key: str, as_of: date) -> bool:
    try:
        get(key, as_of)
        return True
    except KeyError:
        return False
