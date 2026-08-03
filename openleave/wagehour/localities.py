"""Encoded local minimum wages — the cities and counties whose own higher
minimum this slice now knows, so a worksite there gets a real answer instead of
only a coverage warning.

A locality name is normalized to a slug (`"San Francisco"` -> `"san_francisco"`,
`"unincorporated King County"` -> `"king_county"`) and looked up against the set
below. A hit means the engine applies that city's rate; a miss still warns, so
the long tail of small-city ordinances stays honestly flagged rather than
silently ignored.

PROTOTYPE NOTE: rates are 2026 figures and, like everything here, unverified by
counsel. Several localities also have employer-size tiers (small employers may
pay a lower rate); this slice encodes the standard/large-employer rate and notes
the caveat rather than modeling every tier.
"""

from __future__ import annotations

import re

# state -> { slug: (display name, citation ref) }. The parameter key for each is
# minwage.<STATE>.<slug>.
ENCODED: dict[str, dict[str, tuple[str, str]]] = {
    "WA": {
        "seattle": ("Seattle", "Seattle Municipal Code 14.19"),
        "tukwila": ("Tukwila", "Tukwila Minimum Wage Ordinance (Initiative 1)"),
        "burien": ("Burien", "Burien Minimum Wage Ordinance"),
        "renton": ("Renton", "Renton Minimum Wage Ordinance (Initiative 23-02)"),
        "everett": ("Everett", "Everett Minimum Wage Ordinance (Initiative 24-01)"),
        "bellingham": ("Bellingham", "Bellingham Minimum Wage Ordinance"),
        "king_county": ("unincorporated King County", "King County Code ch. 3.15"),
    },
    "CA": {
        "san_francisco": ("San Francisco", "S.F. Admin. Code ch. 12R"),
        "los_angeles": ("Los Angeles (city)", "L.A. Municipal Code § 187.02"),
        "los_angeles_county": ("unincorporated Los Angeles County", "L.A. County Code ch. 8.101"),
        "oakland": ("Oakland", "Oakland Municipal Code ch. 5.92"),
        "san_jose": ("San Jose", "San José Municipal Code ch. 4.100"),
    },
}


def slug(locality: str | None) -> str:
    """Normalize a locality name to a lookup slug. Drops a leading
    'unincorporated' so 'unincorporated King County' matches 'king_county'."""
    s = (locality or "").lower().replace("unincorporated", " ")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def lookup(state: str, locality: str | None) -> dict | None:
    """Return {slug, display, citation, param_key} if this locality has an encoded
    minimum wage, else None."""
    if not locality:
        return None
    s = slug(locality)
    entry = ENCODED.get(state.upper(), {}).get(s)
    if entry is None:
        return None
    return {
        "slug": s,
        "display": entry[0],
        "citation": entry[1],
        "param_key": f"minwage.{state.upper()}.{s}",
    }


def encoded_display_names(state: str) -> list[str]:
    return [display for display, _ in ENCODED.get(state.upper(), {}).values()]
