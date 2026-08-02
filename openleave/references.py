"""The verification manifest: every encoded parameter mapped to the primary
source a reviewer checks it against.

Every statutory value in this repo is web-researched and unverified by counsel.
That is the load-bearing caveat, and this module is the tool for discharging it:
it pairs each parameter key with a citation and an agency URL, tracks per-
jurisdiction sign-off, and — crucially — is guarded by a test so the manifest
cannot drift out of sync with the parameters it documents. Adding a parameter
without a citation breaks the build.

Usage:
    python -m openleave.references check     # verify manifest covers every parameter
    python -m openleave.references summary    # verification progress
    python -m openleave.references report      # write a reviewer worksheet (markdown)
"""

from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

from . import parameters

DATA_FILE = Path(__file__).parent / "references.json"


@functools.lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DATA_FILE.read_text())


def jurisdictions() -> dict:
    return load()["jurisdictions"]


def parameter_index() -> dict[str, tuple[str, str]]:
    """Map each documented parameter key to (jurisdiction_code, description)."""
    index: dict[str, tuple[str, str]] = {}
    for code, juris in jurisdictions().items():
        for key, description in juris.get("parameters", {}).items():
            index[key] = (code, description)
    return index


def citation_for(key: str) -> dict | None:
    """Provenance for a single parameter key: its jurisdiction, statute, source
    URLs, and whether that jurisdiction has been verified by counsel. Returns
    None if the key is not documented."""
    index = parameter_index()
    if key not in index:
        return None
    code, description = index[key]
    juris = jurisdictions()[code]
    return {
        "jurisdiction": code,
        "description": description,
        "statute": juris["statute"],
        "sources": juris["sources"],
        "verified": bool(juris.get("verified")),
    }


def coverage_gaps() -> dict[str, list[str]]:
    """Compare the manifest against the live parameter set.

    `missing` = encoded parameters with no manifest entry (the dangerous case:
    an unsourced value). `orphan` = manifest entries for parameters that no
    longer exist (stale documentation).
    """
    documented = set(parameter_index())
    encoded = set(parameters.known_keys())
    return {
        "missing": sorted(encoded - documented),
        "orphan": sorted(documented - encoded),
    }


def summary() -> dict:
    js = jurisdictions()
    verified = [code for code, j in js.items() if j.get("verified")]
    return {
        "jurisdictions": len(js),
        "jurisdictions_verified": len(verified),
        "verified_list": sorted(verified),
        "parameters_documented": len(parameter_index()),
        "parameters_encoded": len(parameters.known_keys()),
        "gaps": coverage_gaps(),
    }


def _status(juris: dict) -> str:
    if juris.get("verified"):
        who = juris.get("verified_by") or "unnamed reviewer"
        when = juris.get("verified_on") or "date not recorded"
        return f"VERIFIED by {who} on {when}"
    return "UNVERIFIED — pending counsel review"


def report() -> str:
    """Render a per-jurisdiction reviewer worksheet as Markdown.

    Each parameter is shown with its full effective-dated series pulled live from
    parameters.json, so the reviewer checks the actual encoded values (not a copy
    that could drift)."""
    data = load()
    meta = data["_meta"]
    series = parameters.current_entries()
    gaps = coverage_gaps()

    lines: list[str] = []
    lines.append("# OpenLeave — Statutory Verification Worksheet")
    lines.append("")
    lines.append(f"*{meta['disclaimer']}*")
    lines.append("")
    lines.append(f"**How to use:** {meta['how_to_use']}")
    lines.append("")
    s = summary()
    lines.append(
        f"**Progress:** {s['jurisdictions_verified']}/{s['jurisdictions']} jurisdictions verified; "
        f"{s['parameters_documented']}/{s['parameters_encoded']} parameters documented."
    )
    if gaps["missing"]:
        lines.append("")
        lines.append(f"> ⚠️ Undocumented parameters (no source): {', '.join(gaps['missing'])}")
    if gaps["orphan"]:
        lines.append("")
        lines.append(f"> ⚠️ Stale manifest entries (no such parameter): {', '.join(gaps['orphan'])}")
    lines.append("")

    for code in sorted(jurisdictions()):
        juris = jurisdictions()[code]
        lines.append(f"## {code} — {juris['program']}")
        lines.append("")
        lines.append(f"- **Status:** {_status(juris)}")
        lines.append(f"- **Statute:** {juris['statute']}")
        lines.append(f"- **Sources:** {', '.join(juris['sources'])}")
        lines.append("")
        lines.append("| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |")
        lines.append("|---|---|---|---|")
        for key, description in juris.get("parameters", {}).items():
            entries = series.get(key, [])
            rendered = "; ".join(f"{v} [{d}]" for d, v in entries) or "— (not in data!)"
            lines.append(f"| ☐ | `{key}` | {description} | {rendered} |")
        lines.append("")
        claims = juris.get("claims", [])
        if claims:
            lines.append("**Structural claims to verify (not single numbers):**")
            lines.append("")
            for claim in claims:
                lines.append(f"- ☐ {claim}")
            lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "summary"

    if command == "check":
        gaps = coverage_gaps()
        if gaps["missing"] or gaps["orphan"]:
            if gaps["missing"]:
                print(f"MISSING (encoded but undocumented): {', '.join(gaps['missing'])}")
            if gaps["orphan"]:
                print(f"ORPHAN (documented but not encoded): {', '.join(gaps['orphan'])}")
            return 1
        print(f"OK — all {len(parameters.known_keys())} parameters documented.")
        return 0

    if command == "summary":
        s = summary()
        print(
            f"Jurisdictions verified: {s['jurisdictions_verified']}/{s['jurisdictions']}"
            f" ({', '.join(s['verified_list']) or 'none yet'})"
        )
        print(f"Parameters documented: {s['parameters_documented']}/{s['parameters_encoded']}")
        return 0

    if command == "report":
        out = report()
        target = argv[1] if len(argv) > 1 else None
        if target:
            Path(target).write_text(out)
            print(f"Wrote worksheet to {target}")
        else:
            print(out)
        return 0

    print(f"Unknown command {command!r}. Use: check | summary | report [path]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
