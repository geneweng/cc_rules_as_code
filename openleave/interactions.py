"""Cross-regime interaction rules: concurrency, pairing, and stacking notes."""

from __future__ import annotations

from .engine import RegimeResult

DOL_2026_NOTE = (
    "Per 2026 U.S. DOL guidance on FMLA/PFML interplay, an employer may not automatically require the employee "
    "to substitute employer-provided paid leave while the employee is receiving state PFML benefits."
)


def evaluate(results: list[RegimeResult]) -> list[str]:
    by_id = {r.regime: r for r in results}
    live = {rid for rid, r in by_id.items() if r.applies and r.eligible is not False}
    notes: list[str] = []

    def name(rid: str) -> str:
        return by_id[rid].name

    if "fmla" in live:
        for rid in ("ca_cfra", "mn_paid_leave", "ny_pfl"):
            if rid in live:
                notes.append(
                    f"FMLA and {name(rid)} cover the same qualifying reason: leave generally runs concurrently, "
                    f"drawing down both entitlements at once when properly designated."
                )

    if "ca_pfl" in live:
        protection = next((rid for rid in ("ca_cfra", "fmla") if rid in live), None)
        if protection:
            notes.append(
                f"California PFL supplies wage replacement while {name(protection)} supplies the job protection; "
                f"they are designed to be taken together."
            )
        else:
            notes.append(
                "California PFL wage replacement applies, but no job-protection regime was found eligible: "
                "the employee's position is not protected by PFL itself."
            )

    if any(rid in live for rid in ("ca_pfl", "mn_paid_leave", "ny_pfl")):
        notes.append(DOL_2026_NOTE)

    return notes
