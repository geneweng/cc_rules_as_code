"""Scenario-based regression suite. Each scenario states the expected legal
outcome; the suite is the contract an amendment must not silently break."""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state="CA",
    hire=date(2024, 3, 1),
    hours=1600,
    total=120,
    within_75=None,
    reason=LeaveReason.BONDING,
    start=date(2026, 9, 1),
    aww=1200.0,
    hours_per_week=40.0,
):
    return Facts(
        employee=Employee(
            work_state=state,
            hire_date=hire,
            hours_last_12mo=hours,
            hours_per_week=hours_per_week,
            average_weekly_wage=aww,
        ),
        employer=Employer(total_employees=total, employees_within_75_miles=within_75),
        event=LeaveEvent(type=reason, start=start),
    )


def regime(result, rid):
    matches = [r for r in result["regimes"] if r["regime"] == rid]
    return matches[0] if matches else None


class TestFMLA:
    def test_bonding_eligible(self):
        r = regime(determine(make_facts()), "fmla")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True
        assert r["entitlement"]["weekly_benefit"] is None  # FMLA is unpaid

    def test_short_tenure_fails(self):
        r = regime(determine(make_facts(hire=date(2026, 1, 5))), "fmla")
        assert r["eligible"] is False
        assert any(f["key"] == "tenure" and f["met"] is False for f in r["findings"])

    def test_under_1250_hours_fails(self):
        r = regime(determine(make_facts(hours=1100)), "fmla")
        assert r["eligible"] is False

    def test_small_worksite_fails(self):
        r = regime(determine(make_facts(total=120, within_75=30)), "fmla")
        assert r["eligible"] is False
        assert any(f["key"] == "worksite" and f["met"] is False for f in r["findings"])

    def test_health_reason_flags_human_judgment(self):
        r = regime(determine(make_facts(reason=LeaveReason.OWN_SERIOUS_HEALTH)), "fmla")
        assert r["eligible"] is None  # objective conditions met, SHC needs certification
        assert r["human_judgment"]

    def test_citations_present_on_every_finding(self):
        r = regime(determine(make_facts()), "fmla")
        assert all(f["citation"]["ref"] for f in r["findings"])


class TestCalifornia:
    def test_cfra_small_employer_covered_unlike_fmla(self):
        # 10-employee CA shop: CFRA applies (5+ threshold), FMLA does not (50+)
        result = determine(make_facts(total=10))
        assert regime(result, "ca_cfra")["eligible"] is True
        assert regime(result, "fmla")["eligible"] is False

    def test_cfra_under_5_employees_fails(self):
        r = regime(determine(make_facts(total=4)), "ca_cfra")
        assert r["eligible"] is False

    def test_pfl_pays_but_does_not_protect(self):
        r = regime(determine(make_facts()), "ca_pfl")
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False
        assert r["entitlement"]["weeks"] == 8

    def test_pfl_low_earner_gets_90_percent(self):
        # AWW $500 is under 70% of CA SAWW -> 90% replacement under SB 951
        r = regime(determine(make_facts(aww=500.0)), "ca_pfl")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(450.0)

    def test_pfl_benefit_capped(self):
        r = regime(determine(make_facts(aww=5000.0)), "ca_pfl")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1681.0)

    def test_own_health_routes_to_sdi_note(self):
        r = regime(determine(make_facts(reason=LeaveReason.OWN_SERIOUS_HEALTH)), "ca_pfl")
        assert r["applies"] is False
        assert any("SDI" in n for n in r["notes"])


class TestMinnesota:
    def test_bonding_eligible_any_employer_size(self):
        r = regime(determine(make_facts(state="MN", total=3)), "mn_paid_leave")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12

    def test_progressive_benefit_formula(self):
        # AWW $1000, SAWW $1423: 90% of 711.50 + 66% of (1000 - 711.50)
        r = regime(determine(make_facts(state="MN", aww=1000.0)), "mn_paid_leave")
        expected = 0.9 * 711.50 + 0.66 * (1000 - 711.50)
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(round(expected, 2))

    def test_benefit_capped_at_saww(self):
        r = regime(determine(make_facts(state="MN", aww=6000.0)), "mn_paid_leave")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1423.0)

    def test_before_2026_program_not_in_force(self):
        r = regime(
            determine(make_facts(state="MN", start=date(2025, 6, 1), hire=date(2023, 1, 1))),
            "mn_paid_leave",
        )
        assert r["applies"] is False  # time travel: program had not launched

    def test_short_tenure_eligible_but_not_job_protected(self):
        r = regime(determine(make_facts(state="MN", hire=date(2026, 8, 1))), "mn_paid_leave")
        assert r["eligible"] is True  # monetary eligibility is wage-based, not tenure-based
        assert r["entitlement"]["job_protected"] is False  # under 90 days


class TestNewYork:
    def test_bonding_eligible(self):
        r = regime(determine(make_facts(state="NY")), "ny_pfl")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_benefit_is_67_percent_capped(self):
        r = regime(determine(make_facts(state="NY", aww=1200.0)), "ny_pfl")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(0.67 * 1200, abs=0.01)
        cap = round(0.67 * 1839.34, 2)
        r2 = regime(determine(make_facts(state="NY", aww=5000.0)), "ny_pfl")
        assert r2["entitlement"]["weekly_benefit"] == pytest.approx(cap)

    def test_under_26_weeks_service_fails(self):
        r = regime(determine(make_facts(state="NY", hire=date(2026, 5, 1))), "ny_pfl")
        assert r["eligible"] is False

    def test_own_health_routes_to_dbl_note(self):
        r = regime(determine(make_facts(state="NY", reason=LeaveReason.OWN_SERIOUS_HEALTH)), "ny_pfl")
        assert r["applies"] is False
        assert any("DBL" in n for n in r["notes"])

    def test_saww_time_travel(self):
        # Same facts, evaluated under 2025 vs 2026 SAWW, produce different caps
        facts = make_facts(state="NY", aww=5000.0, start=date(2026, 9, 1), hire=date(2024, 1, 1))
        cap_2026 = regime(determine(facts), "ny_pfl")["entitlement"]["weekly_benefit"]
        cap_2025 = regime(determine(facts, as_of=date(2025, 6, 1)), "ny_pfl")["entitlement"]["weekly_benefit"]
        assert cap_2026 == pytest.approx(round(0.67 * 1839.34, 2))
        assert cap_2025 == pytest.approx(round(0.67 * 1757.19, 2))


class TestInteractions:
    def test_fmla_and_cfra_run_concurrently(self):
        result = determine(make_facts())
        assert any("runs concurrently" in n or "run concurrently" in n for n in result["interactions"])

    def test_ca_pfl_pairs_with_protection(self):
        result = determine(make_facts())
        assert any("wage replacement" in n and "job protection" in n for n in result["interactions"])

    def test_stacking_note_when_state_pfml_applies(self):
        result = determine(make_facts(state="MN"))
        assert any("DOL" in n for n in result["interactions"])

    def test_texas_gets_fmla_only(self):
        result = determine(make_facts(state="TX"))
        live = [r["regime"] for r in result["regimes"] if r["applies"]]
        assert live == ["fmla"]
