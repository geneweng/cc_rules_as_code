"""Locality coverage for wage-and-hour — the guard against silently understating
the minimum wage.

Phase 1 encodes state and federal minimum wages only. Dozens of cities and
counties set their own *higher* minimums (Seattle's $21.30 vs Washington's
$17.13, San Francisco's local rate vs California's $16.90). Telling a Seattle
worker the minimum wage is the state figure hands them a wrong, lower number —
the wage-and-hour analogue of returning "FMLA only". So every minimum-wage
answer reports its own locality coverage, loudly, exactly as the leave engine
does for unencoded state programs.

This mirrors `openleave.coverage`, one domain over.
"""

from __future__ import annotations

# States this slice encodes a state minimum wage for.
ENCODED_WAGE_STATES = {"CA", "WA"}

# States known to contain localities that set their own higher minimum wage.
# Value is a representative (not exhaustive) list, used only to warn — Phase 1
# does not encode any local rate. Phase 1.5 populates the local figures.
STATES_WITH_LOCAL_MINIMUMS = {
    "CA": [
        "many California cities and counties (e.g. San Francisco, Los Angeles city and county, "
        "San Jose, Oakland, Berkeley, Emeryville, Mountain View, Sunnyvale)"
    ],
    "WA": ["Seattle", "SeaTac", "Tukwila", "Bellingham", "Burien", "Everett", "Renton", "unincorporated King County"],
}

# Industry-specific state minimums above the general floor, also not encoded here.
INDUSTRY_CARVEOUTS = {
    "CA": [
        "fast-food restaurant employees (AB 1228, $20+/hr) and covered health-care workers "
        "have higher industry-specific minimums that are not encoded"
    ],
}


def assess(work_state: str, work_locality: str | None) -> dict:
    """Report whether the encoded state/federal minimum could understate the
    wage that actually applies at this worksite."""
    state = (work_state or "").upper()
    locality = (work_locality or "").strip()
    warnings: list[str] = []
    notes: list[str] = []
    complete = True

    if state not in ENCODED_WAGE_STATES:
        complete = False
        warnings.append(
            f"No state minimum wage is encoded for {state}; only the federal $7.25 floor is shown. "
            f"Most states set a higher minimum — do not treat this as {state}'s applicable rate."
        )

    if state in STATES_WITH_LOCAL_MINIMUMS:
        examples = STATES_WITH_LOCAL_MINIMUMS[state][0]
        if locality:
            complete = False
            warnings.append(
                f"'{locality}' may set its own higher local minimum wage, which is NOT encoded here. "
                f"The figure shown is the {state} state floor and may understate the applicable "
                f"minimum. Confirm the local ordinance before relying on this."
            )
        else:
            notes.append(
                f"{state} contains localities with higher minimum wages ({examples}). No worksite "
                f"locality was given; if the worksite is in one of them, the state figure is a floor, "
                f"not the applicable rate."
            )

    for note in INDUSTRY_CARVEOUTS.get(state, []):
        notes.append(f"{state}: {note}.")

    return {"state": state, "locality": locality or None, "complete": complete,
            "warnings": warnings, "notes": notes}
