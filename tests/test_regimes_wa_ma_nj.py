"""Washington, Massachusetts, and New Jersey encodings.

Each state is here because it exercises something the first four did not:
WA separates benefit eligibility from job protection on different tests,
MA's eligibility depends on the benefit it is computing, and NJ's job
protection changes mid-2026 and can come from either of two statutes.
"""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state,
    hire=date(2024, 3, 1),
    hours=1600,
    total=120,
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


class TestWashington:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("WA")), "wa_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_two_tier_benefit_formula(self):
        # AWW 1200 > half of SAWW 1830 (915): 90% of 915 + 50% of (1200 - 915)
        r = regime(determine(make_facts("WA", aww=1200.0)), "wa_pfml")
        expected = 0.9 * 915 + 0.5 * (1200 - 915)
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(round(expected, 2))

    def test_low_earner_gets_flat_90_percent(self):
        r = regime(determine(make_facts("WA", aww=800.0)), "wa_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(720.0)

    def test_benefit_capped(self):
        r = regime(determine(make_facts("WA", aww=6000.0)), "wa_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1647.0)

    def test_under_820_hours_not_eligible(self):
        r = regime(determine(make_facts("WA", hours=700)), "wa_pfml")
        assert r["eligible"] is False

    def test_hours_test_ignores_tenure_unlike_fmla(self):
        # Hired 3 months ago with 900 hours: WA pays, FMLA does not
        result = determine(make_facts("WA", hire=date(2026, 6, 1), hours=900))
        assert regime(result, "wa_pfml")["eligible"] is True
        assert regime(result, "fmla")["eligible"] is False

    def test_small_employer_pays_but_does_not_protect(self):
        r = regime(determine(make_facts("WA", total=10)), "wa_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False
        assert any("job protection does not attach" in n for n in r["entitlement"]["notes"])

    def test_short_service_does_not_protect(self):
        r = regime(determine(make_facts("WA", hire=date(2026, 7, 1))), "wa_pfml")
        assert r["entitlement"]["job_protected"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(
            determine(make_facts("WA", start=date(2025, 6, 1), hire=date(2023, 1, 1))), "wa_pfml"
        )
        assert r["applies"] is False
        assert any("outside the encoded range" in n for n in r["notes"])
        assert any("not as an absence of entitlement" in n for n in r["notes"])


class TestMassachusetts:
    def test_bonding_eligible_with_own_job_protection(self):
        r = regime(determine(make_facts("MA")), "ma_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True
        assert any("statute itself" in n for n in r["entitlement"]["notes"])

    def test_medical_leave_runs_longer_than_family_leave(self):
        family = regime(determine(make_facts("MA")), "ma_pfml")
        medical = regime(
            determine(make_facts("MA", reason=LeaveReason.OWN_SERIOUS_HEALTH)), "ma_pfml"
        )
        assert family["entitlement"]["weeks"] == 12
        assert medical["entitlement"]["weeks"] == 20

    def test_two_tier_benefit_formula(self):
        # AWW 1200 > half of SAWW 1922.48 (961.24): 80% of 961.24 + 50% of the excess
        r = regime(determine(make_facts("MA", aww=1200.0)), "ma_pfml")
        expected = 0.8 * 961.24 + 0.5 * (1200 - 961.24)
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(round(expected, 2))

    def test_benefit_capped_at_64_percent_of_saww(self):
        r = regime(determine(make_facts("MA", aww=9000.0)), "ma_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1230.39)

    def test_thirty_times_benefit_test_is_evaluated_against_the_benefit(self):
        r = regime(determine(make_facts("MA", aww=1200.0)), "ma_pfml")
        finding = next(f for f in r["findings"] if f["key"] == "thirty_times_benefit")
        assert finding["met"] is True
        assert "30 ×" in finding["description"]

    def test_low_earner_fails_the_minimum_earnings_test(self):
        # $100/wk -> $5,200 base-period wages, under the $6,300 floor
        r = regime(determine(make_facts("MA", aww=100.0)), "ma_pfml")
        assert r["eligible"] is False
        assert any(f["key"] == "minimum_earnings" and f["met"] is False for f in r["findings"])

    def test_waiting_period_is_surfaced(self):
        r = regime(determine(make_facts("MA")), "ma_pfml")
        assert any("first 7 calendar days" in n for n in r["entitlement"]["notes"])

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("MA", start=date(2025, 6, 1))), "ma_pfml")
        assert r["applies"] is False
        assert any("outside the encoded range" in n for n in r["notes"])


class TestNewJersey:
    def test_bonding_eligible_at_85_percent(self):
        r = regime(determine(make_facts("NJ", aww=1000.0)), "nj_fli")
        assert r["eligible"] is True
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(850.0)
        assert r["entitlement"]["weeks"] == 12

    def test_benefit_capped(self):
        r = regime(determine(make_facts("NJ", aww=5000.0)), "nj_fli")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1119.0)

    def test_own_health_routes_to_tdi(self):
        r = regime(determine(make_facts("NJ", reason=LeaveReason.OWN_SERIOUS_HEALTH)), "nj_fli")
        assert r["applies"] is False
        assert any("Temporary Disability Insurance" in n for n in r["notes"])

    def test_fli_carries_protection_after_the_2026_amendment(self):
        r = regime(determine(make_facts("NJ", start=date(2026, 9, 1), total=5)), "nj_fli")
        assert r["entitlement"]["job_protected"] is True
        assert any("A3451" in n for n in r["entitlement"]["notes"])

    def test_before_the_amendment_small_employer_has_no_protection(self):
        # Small employer fails NJFLA, and leave predates the FLI reinstatement right
        r = regime(determine(make_facts("NJ", start=date(2026, 3, 1), total=5)), "nj_fli")
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False
        assert any("no job protection" in n for n in r["entitlement"]["notes"])

    def test_before_the_amendment_njfla_still_protects_larger_employers(self):
        r = regime(determine(make_facts("NJ", start=date(2026, 3, 1), total=120)), "nj_fli")
        assert r["entitlement"]["job_protected"] is True
        assert any("New Jersey Family Leave Act" in n for n in r["entitlement"]["notes"])

    def test_low_earnings_are_unresolved_not_denied(self):
        # Below the earnings route, but the 20-base-week route can't be tested here
        r = regime(determine(make_facts("NJ", aww=200.0)), "nj_fli")
        assert r["eligible"] is None
        assert r["human_judgment"]
        finding = next(f for f in r["findings"] if f["key"] == "monetary_eligibility")
        assert finding["met"] is None
        assert "20 base weeks" in finding["detail"]

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("NJ", start=date(2025, 6, 1))), "nj_fli")
        assert r["applies"] is False
        assert any("outside the encoded range" in n for n in r["notes"])


class TestCoverageAndInteractions:
    def test_new_states_are_no_longer_reported_as_gaps(self):
        for state in ("WA", "MA", "NJ"):
            assert determine(make_facts(state))["coverage"]["complete"] is True

    def test_oregon_remains_a_declared_gap(self):
        result = determine(make_facts("OR"))
        assert result["coverage"]["complete"] is False
        assert "Oregon Paid Leave" in result["coverage"]["program"]

    def test_fmla_runs_concurrently_with_each_new_regime(self):
        for state, label in (("WA", "Washington"), ("MA", "Massachusetts"), ("NJ", "New Jersey")):
            interactions = determine(make_facts(state))["interactions"]
            assert any(label in n and "concurrently" in n for n in interactions), state

    def test_unprotected_nj_fli_reports_that_nothing_protects_the_job(self):
        # Pre-amendment small employer: FLI pays, and nothing protects the position.
        # NJFLA's thresholds (30 employees, 1,000 hours) are strictly easier than FMLA's
        # (50, 1,250), so FMLA can never be the protector NJ FLI falls back on — unlike
        # California, where CFRA covers small employers FMLA does not.
        result = determine(make_facts("NJ", start=date(2026, 3, 1), total=5, hire=date(2024, 1, 1)))
        assert any(
            "no job-protection regime was found eligible" in n for n in result["interactions"]
        )

    def test_california_by_contrast_does_pair_pay_with_protection(self):
        result = determine(make_facts("CA", total=10))
        assert any(
            "wage replacement" in n and "job protection" in n for n in result["interactions"]
        )

    def test_stacking_guidance_applies_to_new_paid_regimes(self):
        for state in ("WA", "MA", "NJ"):
            assert any("DOL" in n for n in determine(make_facts(state))["interactions"]), state
