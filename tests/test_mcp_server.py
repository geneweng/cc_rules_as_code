"""Tests for the openleave_mcp server.

Most tests call the tool functions directly (fast). One end-to-end test drives
the server as a subprocess over stdio with a real MCP client, proving the
protocol wiring — schema generation, dispatch, and error propagation.
"""

import asyncio
import json
import sys

import pytest

from openleave.mcp_server import (
    JurisdictionsInput,
    LeaveEligibilityInput,
    ParameterLookupInput,
    openleave_check_leave_eligibility,
    openleave_list_jurisdictions,
    openleave_lookup_statutory_parameter,
)


def call(coro):
    return asyncio.run(coro)


def eligibility(**overrides):
    base = dict(
        work_state="MN",
        hire_date="2025-03-01",
        leave_start_date="2026-09-01",
        leave_reason="bonding",
        hours_last_12mo=1400,
        employer_total_employees=85,
        average_weekly_wage=1100,
    )
    base.update(overrides)
    return LeaveEligibilityInput(**base)


class TestCheckEligibility:
    def test_markdown_carries_verdicts_citations_and_benefit(self):
        out = call(openleave_check_leave_eligibility(eligibility()))
        assert "FMLA (federal) — ELIGIBLE" in out
        assert "Minnesota Paid Leave — ELIGIBLE" in out
        assert "29 U.S.C. § 2611(2)(A)(ii)" in out
        assert "$896.76/week" in out
        assert "Interaction rules" in out
        assert "not legal advice" in out

    def test_json_format_is_valid_and_structured(self):
        out = call(openleave_check_leave_eligibility(eligibility(response_format="json")))
        data = json.loads(out)
        assert data["as_of"] == "2026-09-01"
        mn = next(r for r in data["regimes"] if r["regime"] == "mn_paid_leave")
        assert mn["entitlement"]["weekly_benefit"] == 896.76
        assert all(f["citation"]["ref"] for r in data["regimes"] for f in r["findings"])

    def test_failed_condition_is_visible_with_its_citation(self):
        out = call(openleave_check_leave_eligibility(eligibility(hours_last_12mo=900)))
        assert "FMLA (federal) — NOT ELIGIBLE" in out
        assert "✗ At least 1250 hours" in out
        assert "Hours in previous 12 months: 900" in out

    def test_open_textured_reason_requires_human_judgment(self):
        out = call(openleave_check_leave_eligibility(eligibility(leave_reason="own_serious_health")))
        assert "REQUIRES HUMAN JUDGMENT" in out
        assert "Requires human judgment:" in out
        assert "29 C.F.R. § 825.113" in out

    def test_uncovered_program_state_leads_with_incomplete_coverage(self):
        out = call(openleave_check_leave_eligibility(eligibility(work_state="OR")))
        banner = out.split("## ")[0]
        assert "INCOMPLETE COVERAGE" in banner  # before any regime section
        assert "Oregon Paid Leave" in banner
        assert "INCOMPLETE COVERAGE" not in out.split(banner)[1]  # stated once, not repeated

    def test_state_without_a_program_is_not_flagged_incomplete(self):
        out = call(openleave_check_leave_eligibility(eligibility(work_state="TX")))
        assert "INCOMPLETE COVERAGE" not in out
        assert "No state paid-leave program" in out

    def test_as_of_evaluates_under_prior_law(self):
        now = call(openleave_check_leave_eligibility(
            eligibility(work_state="NY", average_weekly_wage=5000, hire_date="2024-01-01",
                        response_format="json")))
        then = call(openleave_check_leave_eligibility(
            eligibility(work_state="NY", average_weekly_wage=5000, hire_date="2024-01-01",
                        as_of="2025-06-01", response_format="json")))
        benefit = lambda d: next(r for r in json.loads(d)["regimes"]
                                 if r["regime"] == "ny_pfl")["entitlement"]["weekly_benefit"]
        assert benefit(now) == pytest.approx(1232.36)
        assert benefit(then) == pytest.approx(1177.32)

    def test_state_code_is_normalized(self):
        out = call(openleave_check_leave_eligibility(eligibility(work_state="mn")))
        assert "Minnesota Paid Leave" in out

    def test_invalid_state_rejected_by_schema(self):
        with pytest.raises(ValueError):
            eligibility(work_state="MINNESOTA")


class TestListJurisdictions:
    def test_lists_encoded_regimes_and_known_gaps(self):
        out = call(openleave_list_jurisdictions(JurisdictionsInput()))
        assert "Minnesota Paid Leave" in out
        assert "Known gaps" in out
        assert "**OR** — Oregon Paid Leave" in out

    def test_json_shape(self):
        out = call(openleave_list_jurisdictions(JurisdictionsInput(response_format="json")))
        data = json.loads(out)
        assert set(data["encoded_states"]) == {"CA", "MA", "MN", "NJ", "NY", "WA"}
        assert "OR" in data["known_gaps"]
        assert "WA" not in data["known_gaps"]
        assert "bonding" in data["leave_reasons"]
        assert len(data["encoded_regimes"]) == 8


class TestLookupParameter:
    def test_value_in_force_with_history(self):
        out = call(openleave_lookup_statutory_parameter(
            ParameterLookupInput(key="ny.saww", as_of="2026-06-01")))
        assert "1839.34" in out
        assert "2025-01-01: 1757.19" in out

    def test_earlier_date_returns_earlier_value(self):
        out = call(openleave_lookup_statutory_parameter(
            ParameterLookupInput(key="ny.saww", as_of="2025-06-01", response_format="json")))
        assert json.loads(out)["value"] == pytest.approx(1757.19)

    def test_not_yet_in_force_is_an_informative_error(self):
        out = call(openleave_lookup_statutory_parameter(
            ParameterLookupInput(key="mn.saww", as_of="2025-01-01")))
        assert out.startswith("Error:")
        assert "not in force" in out

    def test_unknown_key_lists_valid_keys(self):
        out = call(openleave_lookup_statutory_parameter(ParameterLookupInput(key="nope.bad")))
        assert out.startswith("Error: Unknown parameter")
        assert "ny.saww" in out

    def test_omitting_key_lists_all_parameters(self):
        out = call(openleave_lookup_statutory_parameter(
            ParameterLookupInput(as_of="2026-06-01", response_format="json")))
        params = json.loads(out)["parameters"]
        assert params["fmla.min_hours"] == 1250
        assert len(params) >= 17


class TestProtocolEndToEnd:
    """Drives the server as a subprocess over stdio, as a real MCP client would."""

    def test_stdio_session_lists_and_calls_tools(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def session_run():
            server = StdioServerParameters(command=sys.executable, args=["-m", "openleave.mcp_server"])
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {t.name for t in tools.tools}

                    ok = await session.call_tool("openleave_check_leave_eligibility", {"params": {
                        "work_state": "MN", "hire_date": "2025-03-01",
                        "leave_start_date": "2026-09-01", "leave_reason": "bonding",
                        "hours_last_12mo": 1400, "employer_total_employees": 85,
                        "average_weekly_wage": 1100}})
                    bad = await session.call_tool("openleave_check_leave_eligibility", {"params": {
                        "work_state": "TOOLONG", "hire_date": "2025-03-01",
                        "leave_start_date": "2026-09-01", "leave_reason": "bonding",
                        "hours_last_12mo": 1400, "employer_total_employees": 85}})
                    return names, ok, bad

        names, ok, bad = asyncio.run(asyncio.wait_for(session_run(), timeout=60))

        assert names == {
            "openleave_check_leave_eligibility",
            "openleave_list_jurisdictions",
            "openleave_lookup_statutory_parameter",
        }
        assert ok.isError is False
        assert "$896.76/week" in ok.content[0].text
        assert bad.isError is True  # schema violation surfaces as a tool error
