"""Colorado FAMLI and Paid Leave Oregon encodings.

Each state is here because it exercises something the earlier eight did not:
Colorado has a mid-year (2026-07-01) parameter change to time-travel across, and
Oregon is the only regime that replaces 100% of a low earner's wages and floors
the weekly benefit — a distinct formula from every 90%/80%-then-50% program.
"""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state,
    hire=date(2024, 3, 1),
    total=120,
    reason=LeaveReason.BONDING,
    start=date(2026, 9, 1),
    aww=1200.0,
):
    return Facts(
        employee=Employee(
            work_state=state, hire_date=hire, hours_last_12mo=1600, average_weekly_wage=aww
        ),
        employer=Employer(total_employees=total),
        event=LeaveEvent(type=reason, start=start),
    )


def regime(result, rid):
    matches = [r for r in result["regimes"] if r["regime"] == rid]
    return matches[0] if matches else None


class TestColorado:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("CO")), "co_famli")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_two_tier_benefit_low_earner(self):
        # AWW below 50% of SAWW ($767.47) is replaced at a flat 90%.
        r = regime(determine(make_facts("CO", aww=600.0, start=date(2026, 3, 1))), "co_famli")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(540.0)

    def test_two_tier_benefit_high_earner(self):
        r = regime(determine(make_facts("CO", aww=2000.0, start=date(2026, 3, 1))), "co_famli")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1306.99)

    def test_benefit_capped_at_max(self):
        r = regime(determine(make_facts("CO", aww=5000.0, start=date(2026, 3, 1))), "co_famli")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1381.45)

    def test_mid_year_cap_increase_is_effective_dated(self):
        # The maximum benefit rises from $1,381.45 to $1,448.02 on 2026-07-01.
        before = regime(determine(make_facts("CO", aww=5000.0, start=date(2026, 6, 1))), "co_famli")
        after = regime(determine(make_facts("CO", aww=5000.0, start=date(2026, 8, 1))), "co_famli")
        assert before["entitlement"]["weekly_benefit"] == pytest.approx(1381.45)
        assert after["entitlement"]["weekly_benefit"] == pytest.approx(1448.02)

    def test_job_protection_has_no_employer_size_test(self):
        # A tiny employer still owes reinstatement after 180 days — unlike FMLA.
        r = regime(determine(make_facts("CO", total=2)), "co_famli")
        assert r["entitlement"]["job_protected"] is True

    def test_short_tenure_is_paid_but_unprotected(self):
        r = regime(
            determine(make_facts("CO", hire=date(2026, 8, 1), start=date(2026, 9, 1))), "co_famli"
        )
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False

    def test_below_earnings_floor_is_ineligible(self):
        # $2,500 base-period minimum; $40/wk * 52 = $2,080 falls short.
        r = regime(determine(make_facts("CO", aww=40.0)), "co_famli")
        assert r["eligible"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("CO", start=date(2025, 6, 1)), date(2025, 6, 1)), "co_famli")
        assert r["eligible"] is None
        assert any("outside the encoded range" in n for n in r["notes"])


class TestOregon:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("OR")), "or_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_low_earner_made_whole(self):
        # AWW at or below 65% of SAWW ($916.58) is replaced at 100%.
        r = regime(determine(make_facts("OR", aww=800.0, start=date(2026, 8, 1))), "or_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(800.0)

    def test_benefit_floor_applies(self):
        # 5% of SAWW ($70.51) is the floor even for a near-zero wage.
        r = regime(determine(make_facts("OR", aww=50.0, start=date(2026, 8, 1))), "or_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(70.51)

    def test_high_earner_uses_second_tier(self):
        r = regime(determine(make_facts("OR", aww=2000.0, start=date(2026, 8, 1))), "or_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1458.29)

    def test_benefit_capped_at_max(self):
        r = regime(determine(make_facts("OR", aww=5000.0, start=date(2026, 8, 1))), "or_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1692.16)

    def test_job_restoration_at_any_employer_size(self):
        r = regime(determine(make_facts("OR", total=3)), "or_pfml")
        assert r["entitlement"]["job_protected"] is True

    def test_short_tenure_is_paid_but_unprotected(self):
        r = regime(
            determine(make_facts("OR", hire=date(2026, 8, 15), start=date(2026, 9, 1))), "or_pfml"
        )
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("OR", start=date(2025, 6, 1)), date(2025, 6, 1)), "or_pfml")
        assert r["eligible"] is None
        assert any("outside the encoded range" in n for n in r["notes"])


class TestCoverageAndInteractions:
    def test_new_states_are_no_longer_reported_as_gaps(self):
        for state in ("CO", "OR"):
            assert determine(make_facts(state))["coverage"]["complete"] is True

    def test_fmla_runs_concurrently_with_each_new_regime(self):
        for state, label in (("CO", "Colorado"), ("OR", "Paid Leave Oregon")):
            interactions = determine(make_facts(state))["interactions"]
            assert any(label in n and "concurrently" in n for n in interactions), state
