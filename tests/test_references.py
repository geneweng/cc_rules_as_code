"""The verification manifest must stay in lockstep with the encoded parameters.

The whole point of the manifest is that no statutory value goes undocumented.
If someone adds a parameter without a citation, or removes one and leaves stale
documentation behind, these tests fail — the manifest can't silently drift out
of sync with what the engine actually relies on.
"""

from openleave import parameters, references


def test_every_encoded_parameter_is_documented():
    gaps = references.coverage_gaps()
    assert gaps["missing"] == [], f"encoded but undocumented: {gaps['missing']}"


def test_no_stale_manifest_entries():
    gaps = references.coverage_gaps()
    assert gaps["orphan"] == [], f"documented but no longer encoded: {gaps['orphan']}"


def test_manifest_documents_exactly_the_encoded_parameters():
    assert set(references.parameter_index()) == set(parameters.known_keys())


def test_every_jurisdiction_has_a_citation_and_a_source():
    for code, juris in references.jurisdictions().items():
        assert juris.get("statute"), f"{code} has no statute citation"
        assert juris.get("sources"), f"{code} has no source URL"
        # Sign-off fields must exist so the review workflow can fill them in.
        assert "verified" in juris and "verified_by" in juris and "verified_on" in juris, code


def test_nothing_is_marked_verified_without_a_reviewer_and_date():
    # A jurisdiction may only claim verified status with attribution — no silent sign-off.
    for code, juris in references.jurisdictions().items():
        if juris.get("verified"):
            assert juris.get("verified_by"), f"{code} verified with no reviewer named"
            assert juris.get("verified_on"), f"{code} verified with no date"


def test_report_renders_every_jurisdiction():
    out = references.report()
    for code in references.jurisdictions():
        assert f"## {code} —" in out
    # And it surfaces the honest progress line.
    assert "parameters documented" in out


def test_summary_counts_are_consistent():
    s = references.summary()
    assert s["parameters_documented"] == s["parameters_encoded"]
    assert 0 <= s["jurisdictions_verified"] <= s["jurisdictions"]
