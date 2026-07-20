"""Cross-regime interaction rules: concurrency, pairing, and stacking notes."""

from __future__ import annotations

from .engine import RegimeResult

DOL_2026_NOTE = (
    "Per 2026 U.S. DOL guidance on FMLA/PFML interplay, an employer may not automatically require "
    "the employee to substitute employer-provided paid leave while the employee is receiving state "
    "PFML benefits."
)

# State regimes that run concurrently with FMLA for the same qualifying reason.
STATE_LEAVE_REGIMES = ("ca_cfra", "mn_paid_leave", "ny_pfl", "wa_pfml", "ma_pfml", "nj_fli")

# State regimes that pay benefits (and so trigger the no-forced-stacking rule).
PAID_REGIMES = ("ca_pfl", "mn_paid_leave", "ny_pfl", "wa_pfml", "ma_pfml", "nj_fli")

# Regimes that replace wages without carrying job protection of their own.
PAY_ONLY_REGIMES = ("ca_pfl", "nj_fli")


def evaluate(results: list[RegimeResult]) -> list[str]:
    by_id = {r.regime: r for r in results}
    live = {rid for rid, r in by_id.items() if r.applies and r.eligible is not False}
    notes: list[str] = []

    def name(rid: str) -> str:
        return by_id[rid].name

    if "fmla" in live:
        for rid in STATE_LEAVE_REGIMES:
            if rid in live:
                notes.append(
                    f"FMLA and {name(rid)} cover the same qualifying reason: leave generally runs "
                    f"concurrently, drawing down both entitlements at once when properly designated."
                )

    for rid in PAY_ONLY_REGIMES:
        if rid not in live:
            continue
        entitlement = by_id[rid].entitlement
        # NJ FLI can now carry protection of its own; only pair it when it doesn't.
        if entitlement is not None and entitlement.job_protected:
            continue
        protection = next(
            (p for p in ("ca_cfra", "fmla") if p in live and _protects(by_id[p])), None
        )
        if protection:
            notes.append(
                f"{name(rid)} supplies wage replacement while {name(protection)} supplies the job "
                f"protection; they are designed to be taken together."
            )
        else:
            notes.append(
                f"{name(rid)} wage replacement applies, but no job-protection regime was found "
                f"eligible: the employee's position is not protected on these facts."
            )

    if any(rid in live for rid in PAID_REGIMES):
        notes.append(DOL_2026_NOTE)

    return notes


def _protects(result: RegimeResult) -> bool:
    return result.entitlement is not None and result.entitlement.job_protected
