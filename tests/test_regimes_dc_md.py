"""District of Columbia Paid Family Leave and Maryland FAMLI encodings.

DC exercises the inverse of Connecticut: a minimum-wage-pegged benefit with no
earnings test, but job protection from a *narrower* companion statute (DC FMLA,
20+ employees / 12 months / 1,000 hours), so many DC claimants are paid but not
protected. Maryland exercises a new machine state entirely — a program that is
enacted but not payable until 2028-01-03 — which must be reported as pending,
never as a denial and never as silent under-coverage.
"""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state,
    hire=date(2020, 3, 1),
    total=120,
    hours=1600,
    reason=LeaveReason.BONDING,
    start=date(2026, 9, 1),
    aww=1200.0,
):
    return Facts(
        employee=Employee(
            work_state=state, hire_date=hire, hours_last_12mo=hours, average_weekly_wage=aww
        ),
        employer=Employer(total_employees=total),
        event=LeaveEvent(type=reason, start=start),
    )


def regime(result, rid):
    matches = [r for r in result["regimes"] if r["regime"] == rid]
    return matches[0] if matches else None


class TestDC:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("DC")), "dc_pfl")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_no_earnings_minimum(self):
        # A trivial wage still qualifies: DC has no earnings, hours, or tenure test.
        r = regime(determine(make_facts("DC", aww=50.0)), "dc_pfl")
        assert r["eligible"] is True

    def test_tier1_at_threshold(self):
        # 150% of ($17.95 x 40) = $1,077/wk; at the threshold, 90% applies.
        r = regime(determine(make_facts("DC", aww=1077.0, start=date(2026, 3, 1))), "dc_pfl")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(969.30)

    def test_benefit_capped(self):
        r = regime(determine(make_facts("DC", aww=2000.0, start=date(2026, 3, 1))), "dc_pfl")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1190.00)

    def test_minimum_wage_increase_widens_the_ninety_percent_band(self):
        # The 90% band runs to 150% x min wage x 40: $1,077 at $17.95, $1,104 at
        # $18.40 (2026-07-01). A $1,100 earner crosses from tier 2 to tier 1.
        before = regime(determine(make_facts("DC", aww=1100.0, start=date(2026, 3, 1))), "dc_pfl")
        after = regime(determine(make_facts("DC", aww=1100.0, start=date(2026, 8, 1))), "dc_pfl")
        assert before["entitlement"]["weekly_benefit"] == pytest.approx(980.80)  # tier 2
        assert after["entitlement"]["weekly_benefit"] == pytest.approx(990.00)  # 90% of 1100

    def test_small_employer_is_paid_but_not_protected(self):
        # DC PFL pays, but DC FMLA needs 20+ employees — so no job protection.
        r = regime(determine(make_facts("DC", total=10)), "dc_pfl")
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False

    def test_insufficient_hours_defeats_protection(self):
        r = regime(determine(make_facts("DC", hours=500)), "dc_pfl")
        assert r["entitlement"]["job_protected"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("DC", start=date(2024, 6, 1)), date(2024, 6, 1)), "dc_pfl")
        assert r["eligible"] is None
        assert any("outside the encoded range" in n for n in r["notes"])


class TestMarylandNotYetInForce:
    def test_pending_program_is_reported_not_denied(self):
        r = regime(determine(make_facts("MD")), "md_famli")
        # Not eligible/ineligible — the program simply is not payable yet.
        assert r["applies"] is False
        assert r["eligible"] is None
        assert any("not yet in force" in n and "2028-01-03" in n for n in r["notes"])

    def test_pending_program_is_not_silent_under_coverage(self):
        # Coverage stays "complete": MD is encoded, and the regime note tells the
        # caller exactly why there is no benefit yet — not a missing program.
        result = determine(make_facts("MD"))
        assert result["coverage"]["complete"] is True
        md = regime(result, "md_famli")
        assert md is not None  # present via its note even though applies is False

    def test_in_force_after_2028_computes_eligibility(self):
        r = regime(determine(make_facts("MD", start=date(2028, 6, 1))), "md_famli")
        assert r["applies"] is True
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12

    def test_in_force_hours_test_can_fail(self):
        r = regime(determine(make_facts("MD", start=date(2028, 6, 1), hours=400)), "md_famli")
        assert r["eligible"] is False

    def test_in_force_benefit_is_a_documented_none_not_a_fabricated_figure(self):
        r = regime(determine(make_facts("MD", start=date(2028, 6, 1))), "md_famli")
        assert r["entitlement"]["weekly_benefit"] is None
        assert any("$1,000" in n and "SAWW" in n for n in r["entitlement"]["notes"])


class TestCoverageAndInteractions:
    def test_new_jurisdictions_are_no_longer_gaps(self):
        for state in ("DC", "MD"):
            assert determine(make_facts(state))["coverage"]["complete"] is True

    def test_dc_runs_concurrently_with_fmla(self):
        interactions = determine(make_facts("DC"))["interactions"]
        assert any("DC Paid Family Leave" in n and "concurrently" in n for n in interactions)

    def test_pending_maryland_does_not_generate_concurrency_noise(self):
        # A not-yet-in-force program must not appear as a live concurrent regime.
        interactions = determine(make_facts("MD"))["interactions"]
        assert not any("Maryland" in n for n in interactions)
