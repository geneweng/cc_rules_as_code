"""Amendment-watcher CLI.

    python -m openleave.watcher analyze <document> --jurisdiction NY
    python -m openleave.watcher list
    python -m openleave.watcher show <proposal-id>
    python -m openleave.watcher review <proposal-id> --approve|--reject --reviewer "Name"
    python -m openleave.watcher apply <proposal-id>

`analyze` drafts a proposal with the LLM and validates it against the
regression suite. `apply` merges an approved, validation-passing proposal's
parameter diffs into parameters.json. Logic changes are never applied
automatically — they stay flagged on the proposal for a human encoder.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import parameters
from . import proposals, validator


def _print_proposal(p: dict, verbose: bool = False) -> None:
    a = p["analysis"]
    v = p.get("validation") or {}
    print(f"{p['id']}  [{p['status']}]  {p['jurisdiction']}  source={p['source']['name']}")
    print(f"  summary: {a.get('summary', '')}")
    for c in a.get("parameter_changes", []):
        print(f"  param:   {c['key']} -> {c['new_value']} effective {c['effective_date']}  [{c['citation']}]")
    for c in a.get("logic_changes", []):
        print(f"  LOGIC:   {c['description']}  (regimes: {', '.join(c['affected_regimes'])})  [{c['citation']}] — requires human encoding")
    print(f"  validation: {'PASSED' if v.get('passed') else 'FAILED' if v else 'not run'}")
    if p.get("reviewed_by"):
        print(f"  reviewed: {p['status']} by {p['reviewed_by']} at {p['reviewed_at']}")
    if verbose:
        print(json.dumps(p, indent=2))


def cmd_analyze(args) -> int:
    from .analyzer import ClaudeAnalyzer

    text = Path(args.document).read_text()
    print(f"Analyzing {args.document} ({args.jurisdiction}) with the LLM...")
    analysis = ClaudeAnalyzer().analyze(text, args.jurisdiction)
    overrides = proposals.overrides_from(analysis)
    print("Running regression suite against the proposed diff...")
    validation = validator.validate(overrides)
    proposal = proposals.create(
        analysis,
        jurisdiction=args.jurisdiction,
        source_name=Path(args.document).name,
        source_text=text,
        validation=validation,
    )
    _print_proposal(proposal)
    return 0


def cmd_list(args) -> int:
    items = proposals.list_all()
    if not items:
        print("No proposals.")
    for p in items:
        _print_proposal(p)
    return 0


def cmd_show(args) -> int:
    _print_proposal(proposals.load(args.id), verbose=True)
    return 0


def cmd_review(args) -> int:
    p = proposals.review(args.id, approve=args.approve, reviewer=args.reviewer)
    _print_proposal(p)
    return 0


def cmd_apply(args) -> int:
    p = proposals.load(args.id)
    if p["status"] != "approved":
        print(f"Refusing to apply: proposal is {p['status']}, needs approved.", file=sys.stderr)
        return 1
    if not (p.get("validation") or {}).get("passed"):
        print("Refusing to apply: validation did not pass.", file=sys.stderr)
        return 1
    overrides = proposals.overrides_from(p["analysis"])
    if not overrides:
        print("Nothing to apply: no parameter changes (logic changes need a human encoder).")
        return 0

    data = json.loads(parameters.DATA_FILE.read_text())
    for key, entries in overrides.items():
        merged = dict(data.get(key, []))
        merged.update({d: v for d, v in entries})
        data[key] = [list(item) for item in sorted(merged.items())]
    # One key per line, matching the file's committed style, so an applied
    # amendment shows up in review as a one-line diff.
    lines = ",\n".join(f'  "{k}": {json.dumps(v)}' for k, v in data.items())
    parameters.DATA_FILE.write_text("{\n" + lines + "\n}\n")

    from datetime import datetime, timezone

    p["status"] = "applied"
    p["applied_at"] = datetime.now(timezone.utc).isoformat()
    proposals.save(p)
    print(f"Applied {args.id} to {parameters.DATA_FILE}.")
    if p["analysis"].get("logic_changes"):
        print("NOTE: proposal also contains logic changes — those still need a human encoder.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openleave.watcher", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze", help="Draft + validate a proposal from an amendment document")
    p.add_argument("document")
    p.add_argument("--jurisdiction", required=True)
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("list", help="List proposals")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Show one proposal in full")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("review", help="Approve or reject a proposal")
    p.add_argument("id")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_true")
    group.add_argument("--reject", dest="approve", action="store_false")
    p.add_argument("--reviewer", required=True)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("apply", help="Merge an approved proposal into parameters.json")
    p.add_argument("id")
    p.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)
