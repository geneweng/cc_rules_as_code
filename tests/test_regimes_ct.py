"""Connecticut Paid Leave encoding.

Connecticut is here because it is the only regime whose benefit schedule is
pegged to the *minimum wage* rather than a state average weekly wage, and whose
job protection comes from a *separate* statute (CT FMLA) that reaches employers
with a single employee. Both are exercised below, including the 2026 minimum-wage
increase flowing straight through to the benefit cap.
"""

from datetime import date

import pytest

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, determine


def make_facts(
    state="CT",
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


class TestConnecticut:
    def test_bonding_eligible_and_protected(self):
        r = regime(determine(make_facts()), "ct_pfml")
        assert r["eligible"] is True
        assert r["entitlement"]["weeks"] == 12
        assert r["entitlement"]["job_protected"] is True

    def test_tier1_low_earner_at_breakpoint(self):
        # 40x the $16.94 minimum wage is $677.60/wk; at or below it, 95% applies.
        r = regime(determine(make_facts(aww=677.60, start=date(2026, 3, 1))), "ct_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(643.72)

    def test_tier2_high_earner(self):
        r = regime(determine(make_facts(aww=1000.0, start=date(2026, 3, 1))), "ct_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(837.16)

    def test_benefit_capped_at_sixty_times_minimum_wage(self):
        r = regime(determine(make_facts(aww=2000.0, start=date(2026, 3, 1))), "ct_pfml")
        assert r["entitlement"]["weekly_benefit"] == pytest.approx(1016.40)

    def test_minimum_wage_increase_flows_through_the_cap(self):
        # The cap is 60x the minimum wage: $981.00 at $16.35 (2025), $1,016.40 at
        # $16.94 (2026). The benefit schedule moves with no separate announcement.
        before = regime(determine(make_facts(aww=2000.0, start=date(2025, 3, 1))), "ct_pfml")
        after = regime(determine(make_facts(aww=2000.0, start=date(2026, 3, 1))), "ct_pfml")
        assert before["entitlement"]["weekly_benefit"] == pytest.approx(981.00)
        assert after["entitlement"]["weekly_benefit"] == pytest.approx(1016.40)

    def test_job_protection_reaches_a_single_employee_employer(self):
        r = regime(determine(make_facts(total=1)), "ct_pfml")
        assert r["entitlement"]["job_protected"] is True

    def test_under_three_months_is_paid_but_unprotected(self):
        r = regime(
            determine(make_facts(hire=date(2026, 8, 1), start=date(2026, 9, 1))), "ct_pfml"
        )
        assert r["eligible"] is True
        assert r["entitlement"]["job_protected"] is False

    def test_below_high_quarter_earnings_is_ineligible(self):
        # $100/wk => ~$1,300 in a quarter, short of the $2,325 minimum.
        r = regime(determine(make_facts(aww=100.0)), "ct_pfml")
        assert r["eligible"] is False

    def test_before_encoded_range_is_flagged_not_denied(self):
        r = regime(determine(make_facts(start=date(2024, 6, 1)), date(2024, 6, 1)), "ct_pfml")
        assert r["eligible"] is None
        assert any("outside the encoded range" in n for n in r["notes"])


class TestCoverageAndInteractions:
    def test_connecticut_is_no_longer_reported_as_a_gap(self):
        assert determine(make_facts())["coverage"]["complete"] is True

    def test_fmla_runs_concurrently(self):
        interactions = determine(make_facts())["interactions"]
        assert any("Connecticut Paid Leave" in n and "concurrently" in n for n in interactions)
