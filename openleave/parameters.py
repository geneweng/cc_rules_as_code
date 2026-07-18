"""Effective-dated statutory parameters.

Data lives in parameters.json: each key maps to a list of
[effective_date, value] pairs. `get(key, as_of)` returns the value in force on
`as_of` — this is what lets a determination be evaluated "under the law as of"
any date.

If the OPENLEAVE_PARAM_OVERRIDES environment variable points to a JSON file of
the same shape, its entries are merged over the base data at import time. The
amendment watcher uses this to run the regression suite against a *proposed*
parameter change without touching the canonical data.

PROTOTYPE NOTE: values are approximations gathered for demonstration. Verify
against the responsible agency's current published figures before any real use.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

DATA_FILE = Path(__file__).parent / "parameters.json"


def _load() -> dict[str, list[tuple[date, float]]]:
    raw = json.loads(DATA_FILE.read_text())
    override_path = os.environ.get("OPENLEAVE_PARAM_OVERRIDES")
    if override_path:
        for key, entries in json.loads(Path(override_path).read_text()).items():
            merged = dict(raw.get(key, []))
            merged.update({d: v for d, v in entries})
            raw[key] = sorted(merged.items())
    return {
        key: [(date.fromisoformat(d), v) for d, v in entries]
        for key, entries in raw.items()
    }


_PARAMETERS = _load()


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


def known_keys() -> list[str]:
    return sorted(_PARAMETERS)


def current_entries() -> dict[str, list[tuple[str, float]]]:
    return {k: [(d.isoformat(), v) for d, v in entries] for k, entries in _PARAMETERS.items()}
