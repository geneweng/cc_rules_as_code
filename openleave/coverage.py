"""Which jurisdictions this encoding actually covers — and, critically, which
ones it does *not*.

Silent under-coverage is the most dangerous failure mode for a rules oracle.
An employee in Washington has a state paid-leave entitlement; if the engine
quietly returns "FMLA only" because Washington isn't encoded yet, a caller
(especially an LLM) will confidently tell that employee they have no state
benefit. That is worse than refusing to answer.

So every determination reports its own coverage: which regimes were evaluated,
and whether the work state has a known program outside this encoding.

PROTOTYPE NOTE: the program list below is a prototype approximation and needs
verification by counsel, like every other statutory value in this repo.
"""

from __future__ import annotations

ENCODED_STATES = {"CA", "MN", "NY"}

# States/territories understood to have a mandatory paid family and/or medical
# leave program that this encoding does NOT yet implement. Value is the short
# program name used in the warning text.
UNENCODED_PROGRAM_STATES = {
    "CO": "Colorado FAMLI",
    "CT": "Connecticut Paid Leave",
    "DC": "DC Paid Family Leave",
    "DE": "Delaware Paid Leave",
    "MA": "Massachusetts PFML",
    "ME": "Maine Paid Family and Medical Leave",
    "MD": "Maryland FAMLI",
    "NJ": "New Jersey FLI/TDI",
    "OR": "Oregon Paid Leave",
    "RI": "Rhode Island TCI/TDI",
    "WA": "Washington Paid Family and Medical Leave",
}

FEDERAL_ONLY_NOTE = (
    "No state paid-leave program is known for this state; the federal FMLA analysis "
    "above is the complete encoded picture. Local ordinances (city/county paid sick "
    "leave) are not encoded."
)


def assess(work_state: str) -> dict:
    """Report what this encoding does and does not cover for a work state.

    Returns a dict with:
        state (str), encoded (bool), complete (bool), warnings (list[str])

    `complete` is True only when the state is fully encoded, or is a state with
    no known state-level program (so FMLA alone is the right answer).
    """
    state = (work_state or "").upper()

    if state in ENCODED_STATES:
        return {"state": state, "encoded": True, "complete": True, "warnings": []}

    if state in UNENCODED_PROGRAM_STATES:
        program = UNENCODED_PROGRAM_STATES[state]
        return {
            "state": state,
            "encoded": False,
            "complete": False,
            "program": program,
            "warnings": [
                f"{state} operates {program}, which is not yet encoded in this prototype. "
                f"The employee is likely entitled to state benefits and/or job protection "
                f"beyond what is shown. Do not represent this determination as a complete "
                f"answer for {state} — consult {program} directly."
            ],
        }

    return {
        "state": state,
        "encoded": False,
        "complete": True,
        "warnings": [FEDERAL_ONLY_NOTE],
    }


def encoded_jurisdictions() -> list[dict]:
    """The regimes this encoding implements, for capability discovery."""
    return [
        {"jurisdiction": "Federal", "regime": "FMLA", "citation": "29 U.S.C. §§ 2601–2654",
         "provides": "12 weeks unpaid, job-protected"},
        {"jurisdiction": "California", "regime": "CFRA", "citation": "Cal. Gov. Code § 12945.2",
         "provides": "12 weeks unpaid, job-protected (5+ employees)"},
        {"jurisdiction": "California", "regime": "Paid Family Leave", "citation": "Cal. Unemp. Ins. Code §§ 3300–3306",
         "provides": "8 weeks wage replacement (no job protection of its own)"},
        {"jurisdiction": "Minnesota", "regime": "Minnesota Paid Leave", "citation": "Minn. Stat. ch. 268B",
         "provides": "12 weeks family / 12 medical (20 combined), paid + job-protected after 90 days"},
        {"jurisdiction": "New York", "regime": "NY Paid Family Leave", "citation": "N.Y. Workers' Comp. Law art. 9",
         "provides": "12 weeks at 67% of AWW, job-protected"},
    ]
