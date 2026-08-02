"""Delaware Paid Leave, Maine PFML, and Rhode Island TDI/TCI encodings.

Each exercises something new: Delaware gates coverage on employer size *and*
reason together (10-24 employees get parental leave only); Maine's second benefit
tier is 66% rather than the usual 50%, capped at the full SAWW; and Rhode Island
is really two programs (TCI vs TDI) with a UI-style quarterly-wage benefit and
different job-protection answers.
"""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state,
    hire=date(2022, 3, 1),
    total=120,
    hours=1600,
    reason=LeaveReason.BONDING,
    start=date(2026, 8, 1),
    aww=1000.0,
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


class TestDelaware:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("DE")), "de_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_eighty_percent_benefit_capped(self):
        assert regime(determine(make_facts("DE", aww=1000.0)), "de_pfml")[
            "entitlement"
        ]["weekly_benefit"] == pytest.approx(800.0)
        assert regime(determine(make_facts("DE", aww=2000.0)), "de_pfml")[
            "entitlement"
        ]["weekly_benefit"] == pytest.approx(900.0)  # cap

    def test_medium_employer_gets_parental_only(self):
        # 10-24 employees: bonding is covered, own-health is not.
        bonding = regime(determine(make_facts("DE", total=15)), "de_pfml")
        assert bonding["eligible"] is True
        medical = regime(
            determine(make_facts("DE", total=15, reason=LeaveReason.OWN_SERIOUS_HEALTH)), "de_pfml"
        )
        assert medical["eligible"] is False

    def test_large_employer_gets_medical(self):
        r = regime(determine(make_facts("DE", reason=LeaveReason.FAMILY_CARE)), "de_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 6  # medical/family cap

    def test_below_ten_employees_program_does_not_apply(self):
        r = regime(determine(make_facts("DE", total=5)), "de_pfml")
        assert r["applies"] is False

    def test_insufficient_tenure_is_ineligible(self):
        r = regime(
            determine(make_facts("DE", hire=date(2026, 5, 1), start=date(2026, 8, 1))), "de_pfml"
        )
        assert r["eligible"] is False


class TestMaine:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts("ME")), "me_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is True

    def test_second_tier_is_sixty_six_percent(self):
        # SAWW $1,249.12, threshold $624.56; $1,000 earner: 90% of threshold +
        # 66% of the rest = 562.10 + 247.79.
        r = regime(determine(make_facts("ME", aww=1000.0, start=date(2026, 8, 1))), "me_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(809.89)

    def test_capped_at_full_saww(self):
        r = regime(determine(make_facts("ME", aww=2000.0, start=date(2026, 8, 1))), "me_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1249.12)

    def test_saww_is_effective_dated(self):
        before = regime(determine(make_facts("ME", aww=2000.0, start=date(2026, 6, 1))), "me_pfml")
        assert before["entitlement"]["weekly_benefit"] == pytest.approx(1198.00)

    def test_below_earnings_multiple_is_ineligible(self):
        # 6x SAWW ~ $7,495; $100/wk => ~$5,200 base period, short.
        r = regime(determine(make_facts("ME", aww=100.0)), "me_pfml")
        assert r["eligible"] is False

    def test_short_tenure_is_paid_but_unprotected(self):
        r = regime(
            determine(make_facts("ME", hire=date(2026, 7, 1), start=date(2026, 8, 1))), "me_pfml"
        )
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False


class TestRhodeIsland:
    def test_tci_bonding_is_eight_weeks_and_protected(self):
        r = regime(determine(make_facts("RI")), "ri_tci_tdi")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 8
        assert r["entitlement"]["job_protected"] is True

    def test_tdi_own_health_is_thirty_weeks_and_unprotected(self):
        r = regime(
            determine(make_facts("RI", reason=LeaveReason.OWN_SERIOUS_HEALTH)), "ri_tci_tdi"
        )
        assert r["entitlement"]["weeks"] == 30
        assert r["entitlement"]["job_protected"] is False

    def test_benefit_is_quarterly_wage_based_and_capped(self):
        # 4.62% of a quarter (aww x 13): $1,000 -> $600.60; a high earner hits the
        # $1,150 cap.
        assert regime(determine(make_facts("RI", aww=1000.0)), "ri_tci_tdi")[
            "entitlement"
        ]["weekly_benefit"] == pytest.approx(600.60)
        assert regime(determine(make_facts("RI", aww=3000.0)), "ri_tci_tdi")[
            "entitlement"
        ]["weekly_benefit"] == pytest.approx(1150.00)

    def test_military_exigency_is_not_covered(self):
        r = regime(determine(make_facts("RI", reason=LeaveReason.MILITARY_EXIGENCY)), "ri_tci_tdi")
        assert r is None  # applies is False, no note -> absent from output

    def test_below_earnings_floor_is_ineligible(self):
        r = regime(determine(make_facts("RI", aww=100.0)), "ri_tci_tdi")
        assert r["eligible"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts("RI", start=date(2026, 1, 1)), date(2026, 1, 1)), "ri_tci_tdi")
        assert r["eligible"] is None
        assert any("outside the encoded range" in n for n in r["notes"])


class TestCoverage:
    def test_new_states_are_no_longer_gaps(self):
        for state in ("DE", "ME", "RI"):
            assert determine(make_facts(state))["coverage"]["complete"] is True
