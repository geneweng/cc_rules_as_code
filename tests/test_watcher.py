"""Watcher pipeline tests: proposal lifecycle, validation gate, apply step.

The LLM is faked here — analyzer output is a plain dict, and the pipeline's
guarantees (regression gate, human sign-off, no auto-applied logic changes)
must hold regardless of what the model produces.
"""

import json

import pytest

from openleave.watcher import proposals, validator
from openleave.watcher.cli import main as cli_main

GOOD_ANALYSIS = {
    "summary": "NYSDOL sets the 2027 NYSAWW at $1,925.14 effective 2027-01-01.",
    "parameter_changes": [
        {
            "key": "ny.saww",
            "new_value": 1925.14,
            "effective_date": "2027-01-01",
            "citation": "NYSDOL 2027 NYSAWW notice",
            "source_quote": "Effective January 1, 2027, the New York State Average Weekly Wage is $1,925.14.",
        }
    ],
    "logic_changes": [],
    "requires_human_encoding": False,
}

REWRITES_HISTORY = {
    **GOOD_ANALYSIS,
    "parameter_changes": [
        {
            "key": "ny.saww",
            "new_value": 999.0,
            "effective_date": "2026-01-01",  # overwrites the in-force 2026 value
            "citation": "bogus",
            "source_quote": "bogus",
        }
    ],
}

HALLUCINATED_KEY = {
    **GOOD_ANALYSIS,
    "parameter_changes": [
        {
            "key": "ny.pfl.new_invented_threshold",
            "new_value": 100.0,
            "effective_date": "2027-01-01",
            "citation": "bogus",
            "source_quote": "bogus",
        }
    ],
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENLEAVE_PROPOSALS_DIR", str(tmp_path / "proposals"))
    return tmp_path


class TestValidation:
    def test_forward_dated_change_passes(self):
        result = validator.validate(proposals.overrides_from(GOOD_ANALYSIS))
        assert result["passed"], result["detail"]

    def test_rewriting_history_fails_regression(self):
        # Changing the in-force 2026 SAWW breaks pinned historic determinations
        result = validator.validate(proposals.overrides_from(REWRITES_HISTORY))
        assert not result["passed"]

    def test_hallucinated_key_rejected_without_running_tests(self):
        result = validator.validate(proposals.overrides_from(HALLUCINATED_KEY))
        assert not result["passed"]
        assert "Unknown parameter" in result["detail"]

    def test_logic_only_proposal_validates_trivially(self):
        result = validator.validate({})
        assert result["passed"]


class TestLifecycle:
    def test_full_flow_provenance(self, store):
        p = proposals.create(
            GOOD_ANALYSIS,
            jurisdiction="NY",
            source_name="ny_saww_2027.txt",
            source_text="doc text",
            validation={"passed": True, "detail": ""},
        )
        assert p["status"] == "pending_review"
        assert p["source"]["sha256"]

        p = proposals.review(p["id"], approve=True, reviewer="Jane Counsel")
        assert p["status"] == "approved"
        assert p["reviewed_by"] == "Jane Counsel"

        with pytest.raises(ValueError):
            proposals.review(p["id"], approve=True, reviewer="Second Reviewer")

    def test_apply_requires_approval_and_validation(self, store, tmp_path, monkeypatch, capsys):
        # Point the apply step at a scratch copy of parameters.json
        from openleave import parameters

        scratch = tmp_path / "parameters.json"
        scratch.write_text(parameters.DATA_FILE.read_text())
        monkeypatch.setattr(parameters, "DATA_FILE", scratch)

        p = proposals.create(
            GOOD_ANALYSIS,
            jurisdiction="NY",
            source_name="ny_saww_2027.txt",
            source_text="doc",
            validation={"passed": True, "detail": ""},
        )
        # Not yet approved -> refused
        assert cli_main(["apply", p["id"]]) == 1

        proposals.review(p["id"], approve=True, reviewer="Jane Counsel")
        assert cli_main(["apply", p["id"]]) == 0

        data = json.loads(scratch.read_text())
        assert ["2027-01-01", 1925.14] in data["ny.saww"]
        assert ["2026-01-01", 1839.34] in data["ny.saww"]  # history untouched
        assert proposals.load(p["id"])["status"] == "applied"

    def test_failed_validation_blocks_apply(self, store):
        p = proposals.create(
            REWRITES_HISTORY,
            jurisdiction="NY",
            source_name="bad.txt",
            source_text="doc",
            validation={"passed": False, "detail": "regression failures"},
        )
        proposals.review(p["id"], approve=True, reviewer="Jane Counsel")
        assert cli_main(["apply", p["id"]]) == 1
