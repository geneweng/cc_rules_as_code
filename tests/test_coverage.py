"""Coverage reporting: the engine must never let silent under-coverage read as
a complete answer."""

from datetime import date

from openleave import Employee, Employer, Facts, LeaveEvent, LeaveReason, coverage, determine


def facts_for(state):
    return Facts(
        employee=Employee(work_state=state, hire_date=date(2024, 3, 1),
                          hours_last_12mo=1600, average_weekly_wage=1200),
        employer=Employer(total_employees=120),
        event=LeaveEvent(type=LeaveReason.BONDING, start=date(2026, 9, 1)),
    )


class TestAssess:
    def test_encoded_state_is_complete(self):
        c = coverage.assess("MN")
        assert c["encoded"] is True and c["complete"] is True
        assert c["warnings"] == []

    def test_unencoded_program_state_warns_and_is_incomplete(self):
        c = coverage.assess("OR")
        assert c["encoded"] is False
        assert c["complete"] is False
        assert c["program"] == "Oregon Paid Leave"
        assert any("not yet encoded" in w for w in c["warnings"])
        assert any("Oregon Paid Leave" in w for w in c["warnings"])

    def test_no_program_state_is_complete_with_a_note(self):
        c = coverage.assess("TX")
        assert c["complete"] is True
        assert c["encoded"] is False
        assert any("No state paid-leave program" in w for w in c["warnings"])

    def test_lowercase_input_normalizes(self):
        assert coverage.assess("or")["complete"] is False

    def test_every_encoded_state_is_absent_from_the_unencoded_list(self):
        assert not (coverage.ENCODED_STATES & set(coverage.UNENCODED_PROGRAM_STATES))


class TestDeterminationCoverage:
    def test_uncovered_state_determination_is_flagged_incomplete(self):
        result = determine(facts_for("OR"))
        # FMLA still answers, but the result must not read as the whole picture
        assert any(r["regime"] == "fmla" and r["eligible"] for r in result["regimes"])
        assert result["coverage"]["complete"] is False
        assert result["coverage"]["warnings"]

    def test_texas_determination_is_complete(self):
        result = determine(facts_for("TX"))
        assert result["coverage"]["complete"] is True

    def test_minnesota_determination_is_complete(self):
        result = determine(facts_for("MN"))
        assert result["coverage"]["complete"] is True
        assert result["coverage"]["warnings"] == []

    def test_encoded_jurisdictions_listed_for_discovery(self):
        rows = coverage.encoded_jurisdictions()
        assert len(rows) == 8
        assert all(r["citation"] for r in rows)
