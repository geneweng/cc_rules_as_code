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

from datetime import date

from .. import parameters
from . import localities

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


def assess(work_state: str, work_locality: str | None, as_of: date) -> dict:
    """Report whether the encoded state/federal minimum could understate the
    wage that actually applies at this worksite, as of the given date."""
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
        encoded_here = localities.lookup(state, locality)
        # Only "applied" if the local rate is actually in force on this date.
        if encoded_here is not None and parameters.in_force(encoded_here["param_key"], as_of):
            notes.append(
                f"The {encoded_here['display']} local minimum wage is encoded and applied above; "
                f"it governs where higher than the {state} state rate."
            )
        elif encoded_here is not None:
            # Encoded, but its rate had not taken effect on this date.
            complete = False
            warnings.append(
                f"The {encoded_here['display']} local minimum wage is encoded but had not taken "
                f"effect on {as_of.isoformat()}; the {state} state floor is shown for that date."
            )
        elif locality:
            complete = False
            warn = (
                f"'{locality}' is not an encoded locality. If it sets its own higher local minimum "
                f"wage, the figure shown is the {state} state floor and may understate the applicable "
                f"minimum. Confirm the local ordinance before relying on this."
            )
            if localities.slug(locality) == "seatac":
                warn += (
                    " (SeaTac has a ~$20.74 minimum for hospitality and transportation workers only, "
                    "not a general city-wide rate — deliberately not encoded here.)"
                )
            warnings.append(warn)
        else:
            covered = ", ".join(localities.encoded_display_names(state))
            notes.append(
                f"{state} contains localities with higher minimum wages ({examples}). Encoded here: "
                f"{covered}. No worksite locality was given; if the worksite is in an unencoded one, "
                f"the state figure is a floor, not the applicable rate."
            )

    for note in INDUSTRY_CARVEOUTS.get(state, []):
        notes.append(f"{state}: {note}.")

    return {"state": state, "locality": locality or None, "complete": complete,
            "warnings": warnings, "notes": notes}
