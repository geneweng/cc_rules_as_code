#!/usr/bin/env python3
"""MCP server exposing OpenLeave as a tool for AI assistants.

This is the "LLM at the edges, verified rules engine at the core" pattern: the
assistant handles the conversation, and every substantive leave-law conclusion
comes from the deterministic, citation-backed engine instead of from model
recall. Open-textured questions come back flagged for human judgment, and
jurisdictions outside the encoding come back with an explicit incompleteness
warning rather than a confident partial answer.

Run locally over stdio:

    python -m openleave.mcp_server
"""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import DISCLAIMER, __version__, coverage, determine, parameters
from .engine import LeaveReason
from .facts import Employee, Employer, Facts, LeaveEvent

mcp = FastMCP("openleave_mcp")

MARK = {True: "✓", False: "✗", None: "⚖"}


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


# --------------------------------------------------------------------------
# Input models
# --------------------------------------------------------------------------

class LeaveEligibilityInput(BaseModel):
    """Facts describing one employee's leave situation."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    work_state: str = Field(
        ...,
        description="Two-letter state code where the employee physically works, e.g. 'MN'. "
        "This is the state whose law applies — not the employer's headquarters.",
        min_length=2,
        max_length=2,
    )
    hire_date: date = Field(..., description="Employee's hire date, ISO format (e.g. '2025-03-01')")
    leave_start_date: date = Field(..., description="Date the leave begins, ISO format (e.g. '2026-09-01')")
    leave_reason: LeaveReason = Field(
        ...,
        description="Qualifying reason: 'bonding' (new child), 'own_serious_health', "
        "'family_care' (care for a family member), 'pregnancy', or 'military_exigency'",
    )
    hours_last_12mo: float = Field(
        ..., description="Hours the employee worked in the 12 months before leave (e.g. 1400)", ge=0, le=10000
    )
    employer_total_employees: int = Field(
        ..., description="Total employees at the employer (e.g. 85)", ge=1, le=10_000_000
    )
    average_weekly_wage: Optional[float] = Field(
        default=None,
        description="Employee's average weekly wage in dollars (e.g. 1100). Required to compute "
        "state wage-replacement benefit amounts; omit only if unknown.",
        ge=0,
    )
    hours_per_week: Optional[float] = Field(
        default=None,
        description="Typical hours per week. Affects NY PFL's part-time eligibility test.",
        ge=0,
        le=168,
    )
    employees_within_75_miles: Optional[int] = Field(
        default=None,
        description="Employees within 75 miles of the worksite; drives the FMLA worksite test. "
        "Defaults to employer_total_employees if omitted.",
        ge=0,
    )
    as_of: Optional[date] = Field(
        default=None,
        description="Evaluate under the law in force on this date (e.g. '2025-06-01' to reconstruct "
        "a past determination for an audit). Defaults to the leave start date.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="'markdown' for readable output, 'json' for the raw structure"
    )

    @field_validator("work_state")
    @classmethod
    def _upper_state(cls, v: str) -> str:
        if not v.isalpha():
            raise ValueError("work_state must be two letters, e.g. 'CA'")
        return v.upper()


class JurisdictionsInput(BaseModel):
    """No parameters beyond output format."""

    model_config = ConfigDict(extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="'markdown' for readable output, 'json' for the raw structure"
    )


class ParameterLookupInput(BaseModel):
    """Look up an effective-dated statutory parameter."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    key: Optional[str] = Field(
        default=None,
        description="Parameter key, e.g. 'ny.saww', 'mn.saww', 'fmla.min_hours'. "
        "Omit to list every available key with its current value.",
    )
    as_of: Optional[date] = Field(
        default=None,
        description="Return the value in force on this date, ISO format. Defaults to today.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="'markdown' for readable output, 'json' for the raw structure"
    )


# --------------------------------------------------------------------------
# Shared formatting helpers
# --------------------------------------------------------------------------

def _format_coverage(cov: dict[str, Any]) -> list[str]:
    """Coverage banner — leads the output when the answer is incomplete."""
    if not cov["complete"]:
        return ["> **⚠️ INCOMPLETE COVERAGE** — " + " ".join(cov["warnings"]), ""]
    return []


def _format_regime(regime: dict[str, Any]) -> list[str]:
    verdict = {True: "ELIGIBLE", False: "NOT ELIGIBLE", None: "REQUIRES HUMAN JUDGMENT"}[regime["eligible"]]
    lines = [f"## {regime['name']} — {verdict}"]

    ent = regime.get("entitlement")
    if ent:
        bits = []
        if ent["weeks"] is not None:
            bits.append(f"{ent['weeks']:g} weeks")
        bits.append("job-protected" if ent["job_protected"] else "no job protection")
        bits.append(
            f"${ent['weekly_benefit']:,.2f}/week" if ent["weekly_benefit"] is not None else "unpaid / not computed"
        )
        lines.append("**Entitlement:** " + " · ".join(bits))

    for f in regime["findings"]:
        lines.append(f"- {MARK[f['met']]} {f['description']} `[{f['citation']['ref']}]`")
        if f["detail"]:
            lines.append(f"    {f['detail']}")

    if ent and ent["notes"]:
        lines += [f"- _{n}_" for n in ent["notes"]]
    if regime["human_judgment"]:
        lines.append("")
        lines.append("**Requires human judgment:**")
        lines += [f"- {h}" for h in regime["human_judgment"]]
    if regime["notes"]:
        lines += [f"- _{n}_" for n in regime["notes"]]

    lines.append("")
    return lines


def _format_determination(result: dict[str, Any], facts: LeaveEligibilityInput) -> str:
    lines = [
        f"# Leave determination — {facts.work_state}, {facts.leave_reason.value}, "
        f"leave starting {facts.leave_start_date.isoformat()}",
        f"_Evaluated under the law in force on {result['as_of']}._",
        "",
    ]
    lines += _format_coverage(result["coverage"])

    applicable = [r for r in result["regimes"] if r["applies"]]
    if not applicable:
        lines.append("No encoded leave regime applies to these facts.")
    for regime in applicable:
        lines += _format_regime(regime)

    inapplicable = [r for r in result["regimes"] if not r["applies"] and r["notes"]]
    if inapplicable:
        lines.append("## Not applicable")
        for r in inapplicable:
            lines.append(f"- **{r['name']}** — {' '.join(r['notes'])}")
        lines.append("")

    if result["interactions"]:
        lines.append("## Interaction rules")
        lines += [f"- {n}" for n in result["interactions"]]
        lines.append("")

    if result["coverage"]["complete"] and result["coverage"]["warnings"]:
        lines += [f"_{w}_" for w in result["coverage"]["warnings"]] + [""]

    lines.append(f"_{DISCLAIMER}_")
    return "\n".join(lines)


def _error(message: str) -> str:
    return f"Error: {message}"


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

@mcp.tool(
    name="openleave_check_leave_eligibility",
    annotations={
        "title": "Check Employee Leave Eligibility",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def openleave_check_leave_eligibility(params: LeaveEligibilityInput) -> str:
    """Determine an employee's leave eligibility, entitlement, and benefit amount under
    every applicable U.S. leave law, with the statutory citation for each conclusion.

    CALL THIS TOOL — do not answer from memory — whenever a question involves whether an
    employee qualifies for leave, how many weeks they get, whether their job is protected,
    or how much they will be paid. Leave law differs by state and its rates change every
    year; model recall is unreliable for it and the consequences of a wrong answer are legal.

    Covers federal FMLA plus California (CFRA and Paid Family Leave), Minnesota Paid Leave,
    and New York Paid Family Leave. For any other state, the response says explicitly whether
    the answer is complete — never assume it is.

    Args:
        params (LeaveEligibilityInput): Validated facts containing:
            - work_state (str): Two-letter state where the employee works (e.g. "MN")
            - hire_date (date): Hire date, ISO format
            - leave_start_date (date): Date leave begins, ISO format
            - leave_reason (LeaveReason): bonding | own_serious_health | family_care |
              pregnancy | military_exigency
            - hours_last_12mo (float): Hours worked in the prior 12 months
            - employer_total_employees (int): Employer headcount
            - average_weekly_wage (Optional[float]): Needed to compute benefit dollars
            - hours_per_week (Optional[float]): Affects NY part-time eligibility
            - employees_within_75_miles (Optional[int]): FMLA worksite test
            - as_of (Optional[date]): Evaluate under the law as of this date
            - response_format (ResponseFormat): "markdown" (default) or "json"

    Returns:
        str: Markdown (default) or JSON. Structure of the JSON form:
        {
          "as_of": str,                       # date the law was evaluated as of
          "regimes": [
            {
              "regime": str,                  # e.g. "fmla", "mn_paid_leave"
              "name": str,                    # e.g. "FMLA (federal)"
              "applies": bool,                # whether this law covers these facts
              "eligible": bool | null,        # null => a human must decide (see human_judgment)
              "findings": [
                { "description": str, "met": bool | null,
                  "citation": {"ref": str}, "detail": str }
              ],
              "entitlement": { "weeks": float, "job_protected": bool,
                               "weekly_benefit": float | null, "notes": [str] } | null,
              "human_judgment": [str],        # open-textured questions routed to a person
              "notes": [str]
            }
          ],
          "interactions": [str],              # concurrency / stacking rules across regimes
          "coverage": { "state": str, "encoded": bool, "complete": bool, "warnings": [str] },
          "disclaimer": str
        }

    Interpreting the result — three cases matter:
        - eligible == true/false: a determined answer; cite the findings when you explain it.
        - eligible == null: the law requires human judgment (e.g. whether a condition is a
          "serious health condition"). Say so and surface `human_judgment`. Never guess.
        - coverage.complete == false: the state has a paid-leave program this encoding does
          not implement. Lead with that warning; the answer is partial, not final.

    Examples:
        - Use when: "Does my employee in Minnesota qualify for parental leave, and what will
          she be paid?" -> work_state="MN", leave_reason="bonding", with wage and hours.
        - Use when: "Under 2025 rules, what would this New York claim have paid?" -> set
          as_of="2025-06-01" to evaluate under the law then in force.
        - Don't use when: The question is about which states are covered (use
          openleave_list_jurisdictions) or about a single statutory rate
          (use openleave_lookup_statutory_parameter).

    Error Handling:
        - Pydantic rejects malformed dates, bad state codes, and out-of-range numbers.
        - Returns "Error: ..." with guidance if the facts cannot be evaluated.
    """
    try:
        facts = Facts(
            employee=Employee(
                work_state=params.work_state,
                hire_date=params.hire_date,
                hours_last_12mo=params.hours_last_12mo,
                hours_per_week=params.hours_per_week,
                average_weekly_wage=params.average_weekly_wage,
            ),
            employer=Employer(
                total_employees=params.employer_total_employees,
                employees_within_75_miles=params.employees_within_75_miles,
            ),
            event=LeaveEvent(type=params.leave_reason, start=params.leave_start_date),
        )
        result = determine(facts, as_of=params.as_of)
    except ValueError as e:
        return _error(f"Could not evaluate these facts: {e}")

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(result, indent=2)
    return _format_determination(result, params)


@mcp.tool(
    name="openleave_list_jurisdictions",
    annotations={
        "title": "List Covered Leave-Law Jurisdictions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def openleave_list_jurisdictions(params: JurisdictionsInput) -> str:
    """List the leave-law regimes this encoding covers, and the states it knowingly does not.

    Call this before relying on a determination for an unfamiliar state, or when asked what
    the system supports. The uncovered list matters as much as the covered one: those states
    run real paid-leave programs that this encoding does not implement, so a determination
    for them is partial by construction.

    Args:
        params (JurisdictionsInput): Contains:
            - response_format (ResponseFormat): "markdown" (default) or "json"

    Returns:
        str: Markdown (default) or JSON of the form:
        {
          "engine_version": str,
          "encoded_regimes": [
            { "jurisdiction": str, "regime": str, "citation": str, "provides": str }
          ],
          "encoded_states": [str],            # state codes with full state-law coverage
          "known_gaps": { "<STATE>": str },   # state code -> program name NOT encoded
          "leave_reasons": [str]              # accepted leave_reason values
        }

    Examples:
        - Use when: "Which states does this cover?"
        - Use when: "Can I trust this for a Washington employee?" -> WA appears in known_gaps.
        - Don't use when: You have specific employee facts (use
          openleave_check_leave_eligibility, which reports coverage for that state anyway).

    Error Handling:
        - Takes no external input beyond format; does not fail under normal operation.
    """
    payload = {
        "engine_version": __version__,
        "encoded_regimes": coverage.encoded_jurisdictions(),
        "encoded_states": sorted(coverage.ENCODED_STATES),
        "known_gaps": dict(sorted(coverage.UNENCODED_PROGRAM_STATES.items())),
        "leave_reasons": [r.value for r in LeaveReason],
    }

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(payload, indent=2)

    lines = [f"# OpenLeave coverage (engine {__version__})", "", "## Encoded regimes"]
    for r in payload["encoded_regimes"]:
        lines.append(f"- **{r['jurisdiction']} — {r['regime']}** `[{r['citation']}]`: {r['provides']}")
    lines += [
        "",
        "## Known gaps — states with paid-leave programs NOT encoded",
        "A determination for these states covers federal FMLA only and is **incomplete**:",
    ]
    for code, program in payload["known_gaps"].items():
        lines.append(f"- **{code}** — {program}")
    lines += [
        "",
        f"Accepted leave reasons: {', '.join(payload['leave_reasons'])}.",
        "",
        f"_{DISCLAIMER}_",
    ]
    return "\n".join(lines)


@mcp.tool(
    name="openleave_lookup_statutory_parameter",
    annotations={
        "title": "Look Up a Statutory Rate or Threshold",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def openleave_lookup_statutory_parameter(params: ParameterLookupInput) -> str:
    """Look up a single statutory rate, cap, or threshold as it stood on a given date.

    Call this instead of recalling a figure when asked for a specific number — a state
    average weekly wage, a benefit cap, a weeks entitlement, the FMLA hours threshold.
    Every value is effective-dated, so a date gives the value actually in force then.

    Args:
        params (ParameterLookupInput): Contains:
            - key (Optional[str]): Parameter key such as "ny.saww", "mn.saww",
              "ca.pfl.max_weekly_benefit", "fmla.min_hours". Omit to list all keys.
            - as_of (Optional[date]): Date to evaluate; defaults to today.
            - response_format (ResponseFormat): "markdown" (default) or "json"

    Returns:
        str: Markdown (default) or JSON. Single-key form:
        { "key": str, "as_of": str, "value": float, "history": [[str, float]] }
        List form (key omitted):
        { "as_of": str, "parameters": { "<key>": float | null } }

    Examples:
        - Use when: "What's the New York state average weekly wage for 2026?" ->
          key="ny.saww", as_of="2026-06-01".
        - Use when: "What parameters does the engine track?" -> omit key.
        - Don't use when: You need an employee's benefit amount — that is a computation,
          not a lookup; use openleave_check_leave_eligibility.

    Error Handling:
        - Unknown key returns "Error: Unknown parameter ..." listing valid keys.
        - A date before a parameter took effect returns "Error: ... not in force on ...",
          which is itself the correct answer for "did this exist yet?".
    """
    as_of = params.as_of or date.today()

    if params.key is None:
        values = {}
        for key in parameters.known_keys():
            try:
                values[key] = parameters.get(key, as_of)
            except KeyError:
                values[key] = None
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"as_of": as_of.isoformat(), "parameters": values}, indent=2)
        lines = [f"# Statutory parameters in force on {as_of.isoformat()}", ""]
        for key, value in values.items():
            lines.append(f"- `{key}` = {value if value is not None else '_not yet in force_'}")
        lines += ["", f"_{DISCLAIMER}_"]
        return "\n".join(lines)

    key = params.key
    if key not in parameters.known_keys():
        return _error(
            f"Unknown parameter {key!r}. Valid keys: {', '.join(parameters.known_keys())}"
        )
    try:
        value = parameters.get(key, as_of)
    except KeyError:
        return _error(
            f"Parameter {key!r} was not in force on {as_of.isoformat()} — the program or "
            f"provision had not taken effect by that date."
        )

    history = parameters.current_entries()[key]
    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {"key": key, "as_of": as_of.isoformat(), "value": value, "history": history}, indent=2
        )
    lines = [
        f"# `{key}` = **{value}**",
        f"_In force on {as_of.isoformat()}._",
        "",
        "Effective-dated history:",
    ]
    lines += [f"- {eff}: {val}" for eff, val in history]
    lines += ["", f"_{DISCLAIMER}_"]
    return "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
