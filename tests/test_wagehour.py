"""Phase 1 wage-and-hour slice: minimum wage + final pay for federal / CA / WA."""

from datetime import date

import pytest

from openleave.wagehour import Separation, SeparationType, WageFacts, assess_wage_hour


def topic(result, name):
    matches = [t for t in result["topics"] if t["topic"] == name]
    return matches[0] if matches else None


def finding(t, key):
    matches = [f for f in t["findings"] if f["key"] == key]
    return matches[0] if matches else None


class TestMinimumWage:
    def test_california_applicable_minimum_2026(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=20.0), date(2026, 2, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["applicable_minimum"] == pytest.approx(16.90)
        assert finding(mw, "rate_meets_minimum")["met"] is True

    def test_effective_dating_same_rate_different_years(self):
        # $16.60 clears the 2025 floor ($16.50) but not the 2026 floor ($16.90).
        assert assess_wage_hour(WageFacts(work_state="CA", hourly_rate=16.60), date(2025, 6, 1))[
            "topics"][0]["data"]["rate_compliant"] is True
        assert assess_wage_hour(WageFacts(work_state="CA", hourly_rate=16.60), date(2026, 6, 1))[
            "topics"][0]["data"]["rate_compliant"] is False

    def test_below_minimum_flags_violation(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=15.0), date(2026, 2, 1))
        assert finding(topic(r, "minimum_wage"), "rate_meets_minimum")["met"] is False

    def test_washington_is_highest_state_rate(self):
        r = assess_wage_hour(WageFacts(work_state="WA", hourly_rate=17.13), date(2026, 2, 1))
        assert topic(r, "minimum_wage")["data"]["applicable_minimum"] == pytest.approx(17.13)

    def test_federal_floor_when_state_not_encoded(self):
        r = assess_wage_hour(WageFacts(work_state="TX", hourly_rate=7.25), date(2026, 2, 1))
        assert topic(r, "minimum_wage")["data"]["applicable_minimum"] == pytest.approx(7.25)


class TestTipCredit:
    def test_california_prohibits_tip_credit(self):
        r = assess_wage_hour(
            WageFacts(work_state="CA", hourly_rate=16.90, is_tipped=True), date(2026, 2, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["tip_credit_allowed"] is False
        assert mw["data"]["cash_floor"] == pytest.approx(16.90)  # full minimum in cash
        assert "351" in finding(mw, "tip_credit")["citation"]["ref"]

    def test_federal_tip_credit_allows_lower_cash_wage(self):
        r = assess_wage_hour(
            WageFacts(work_state="TX", hourly_rate=2.13, is_tipped=True), date(2026, 2, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["tip_credit_allowed"] is True
        assert mw["data"]["cash_floor"] == pytest.approx(2.13)
        # $2.13 cash "meets" the tipped cash floor, but the engine flags the tips-make-up caveat.
        assert finding(mw, "rate_meets_minimum")["met"] is True
        assert any("cash + tips" in n for n in mw["notes"])


class TestLocalityCoverage:
    def test_unencoded_locality_is_flagged_incomplete(self):
        # A WA city with no encoded ordinance: we can't rule out a local minimum.
        r = assess_wage_hour(
            WageFacts(work_state="WA", hourly_rate=17.13, work_locality="Tacoma"), date(2026, 2, 1))
        assert r["coverage"]["complete"] is False
        assert any("Tacoma" in w for w in r["coverage"]["warnings"])

    def test_state_without_locality_notes_the_risk_but_stays_complete(self):
        r = assess_wage_hour(WageFacts(work_state="WA", hourly_rate=17.13), date(2026, 2, 1))
        assert r["coverage"]["complete"] is True
        assert any("localities" in n for n in r["coverage"]["notes"])

    def test_unencoded_state_is_incomplete(self):
        r = assess_wage_hour(WageFacts(work_state="TX", hourly_rate=7.25), date(2026, 2, 1))
        assert r["coverage"]["complete"] is False
        assert any("No state minimum wage is encoded" in w for w in r["coverage"]["warnings"])

    def test_california_industry_carveout_noted(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=20.0), date(2026, 2, 1))
        assert any("fast-food" in n for n in r["coverage"]["notes"])


class TestLocalMinimumWage:
    def test_seattle_local_rate_governs_and_is_complete(self):
        r = assess_wage_hour(
            WageFacts(work_state="WA", hourly_rate=20.0, work_locality="Seattle"), date(2026, 2, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["applicable_minimum"] == pytest.approx(21.30)
        assert mw["data"]["governing_level"] == "local"
        assert mw["data"]["rate_compliant"] is False  # $20 < Seattle's $21.30
        assert r["coverage"]["complete"] is True  # Seattle is encoded — a real answer now

    def test_san_francisco_uses_july_dated_rate(self):
        r = assess_wage_hour(
            WageFacts(work_state="CA", hourly_rate=19.18, work_locality="San Francisco"), date(2026, 2, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["applicable_minimum"] == pytest.approx(19.18)
        assert mw["data"]["local_name"] == "San Francisco"

    def test_king_county_alias_normalizes(self):
        # "unincorporated King County" must resolve to the king_county slug.
        r = assess_wage_hour(
            WageFacts(work_state="WA", hourly_rate=18.0, work_locality="unincorporated King County"),
            date(2026, 2, 1))
        assert topic(r, "minimum_wage")["data"]["applicable_minimum"] == pytest.approx(20.82)

    def test_local_rate_before_its_effective_date_falls_back_to_state(self):
        # SF's rate is encoded from 2025-07-01; earlier, the state floor applies and
        # coverage says the local rate had not taken effect.
        r = assess_wage_hour(
            WageFacts(work_state="CA", hourly_rate=16.50, work_locality="San Francisco"), date(2025, 3, 1))
        mw = topic(r, "minimum_wage")
        assert mw["data"]["governing_level"] == "state"
        assert mw["data"]["applicable_minimum"] == pytest.approx(16.50)
        assert r["coverage"]["complete"] is False
        assert any("had not taken effect" in w for w in r["coverage"]["warnings"])

    def test_seatac_is_deliberately_not_encoded_and_warns(self):
        r = assess_wage_hour(
            WageFacts(work_state="WA", hourly_rate=17.13, work_locality="SeaTac"), date(2026, 2, 1))
        assert r["coverage"]["complete"] is False
        assert any("hospitality and transportation" in w for w in r["coverage"]["warnings"])


class TestFinalPayCalifornia:
    def _fire(self, **kw):
        return WageFacts(work_state="CA", hourly_rate=30.0,
                         separation=Separation(type=SeparationType.FIRED, last_day=date(2026, 3, 2), **kw))

    def test_fired_deadline_is_immediate(self):
        r = assess_wage_hour(self._fire(), date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert fp["data"]["deadline"] == "2026-03-02"

    def test_late_payment_flags_penalty_exposure(self):
        r = assess_wage_hour(self._fire(final_pay_date=date(2026, 3, 7)), date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert finding(fp, "final_pay_timely")["met"] is False
        assert any("willful" in hj for hj in fp["human_judgment"])

    def test_quit_without_notice_is_seventy_two_hours(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=30.0,
            separation=Separation(type=SeparationType.QUIT_WITHOUT_NOTICE, last_day=date(2026, 3, 2))),
            date(2026, 3, 2))
        assert topic(r, "final_pay")["data"]["deadline"] == "2026-03-05"

    def test_accrued_vacation_must_be_paid_out_and_valued(self):
        r = assess_wage_hour(self._fire(accrued_vacation_hours=40), date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert fp["data"]["vacation_payout_required"] is True
        assert fp["data"]["vacation_payout_owed"] == pytest.approx(1200.0)  # 40 * $30


class TestFinalPayWashington:
    def test_next_pay_period_rule(self):
        r = assess_wage_hour(WageFacts(work_state="WA", hourly_rate=25.0,
            separation=Separation(type=SeparationType.FIRED, last_day=date(2026, 3, 2))),
            date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert "next established pay period" in fp["data"]["deadline"]

    def test_vacation_payout_is_policy_dependent_not_statutory(self):
        r = assess_wage_hour(WageFacts(work_state="WA", hourly_rate=25.0,
            separation=Separation(type=SeparationType.FIRED, last_day=date(2026, 3, 2), accrued_vacation_hours=40)),
            date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert fp["data"]["vacation_payout_required"] is False
        assert finding(fp, "accrued_vacation_payout")["met"] is None  # depends on policy
        assert fp["human_judgment"]


class TestFinalPayUnencodedState:
    def test_unencoded_state_does_not_pretend_there_is_no_deadline(self):
        r = assess_wage_hour(WageFacts(work_state="TX", hourly_rate=10.0,
            separation=Separation(type=SeparationType.FIRED, last_day=date(2026, 3, 2))),
            date(2026, 3, 2))
        fp = topic(r, "final_pay")
        assert fp["data"]["deadline"] is None
        assert any("not encoded" in n for n in fp["notes"])


class TestStructure:
    def test_no_separation_means_no_final_pay_topic(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=20.0), date(2026, 2, 1))
        assert topic(r, "final_pay") is None
        assert topic(r, "minimum_wage") is not None

    def test_result_carries_disclaimer_and_version(self):
        r = assess_wage_hour(WageFacts(work_state="CA", hourly_rate=20.0), date(2026, 2, 1))
        assert r["disclaimer"]
        assert r["engine_version"]
        assert r["jurisdiction"]["state"] == "CA"
