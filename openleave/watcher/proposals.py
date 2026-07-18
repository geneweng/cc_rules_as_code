"""Proposal store: one JSON file per proposal, with full provenance.

Lifecycle: pending_review -> approved | rejected -> applied.
Every transition records who/when; the LLM's raw analysis, the source document
hash, and the validation result travel with the proposal for audit.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "proposals"

STATUSES = ("pending_review", "approved", "rejected", "applied")


def store_dir() -> Path:
    d = Path(os.environ.get("OPENLEAVE_PROPOSALS_DIR", DEFAULT_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def create(
    analysis: dict,
    *,
    jurisdiction: str,
    source_name: str,
    source_text: str,
    validation: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    proposal = {
        "id": f"prop-{now.strftime('%Y%m%d')}-{secrets.token_hex(3)}",
        "status": "pending_review",
        "jurisdiction": jurisdiction,
        "source": {
            "name": source_name,
            "sha256": hashlib.sha256(source_text.encode()).hexdigest(),
        },
        "analysis": analysis,
        "validation": validation,
        "created_at": now.isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "applied_at": None,
    }
    save(proposal)
    return proposal


def save(proposal: dict) -> None:
    path = store_dir() / f"{proposal['id']}.json"
    path.write_text(json.dumps(proposal, indent=2) + "\n")


def load(proposal_id: str) -> dict:
    path = store_dir() / f"{proposal_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No proposal {proposal_id!r} in {store_dir()}")
    return json.loads(path.read_text())


def list_all() -> list[dict]:
    return sorted(
        (json.loads(p.read_text()) for p in store_dir().glob("prop-*.json")),
        key=lambda p: p["created_at"],
    )


def review(proposal_id: str, *, approve: bool, reviewer: str) -> dict:
    proposal = load(proposal_id)
    if proposal["status"] != "pending_review":
        raise ValueError(f"Proposal {proposal_id} is {proposal['status']}, not pending_review")
    proposal["status"] = "approved" if approve else "rejected"
    proposal["reviewed_by"] = reviewer
    proposal["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    save(proposal)
    return proposal


def overrides_from(analysis: dict) -> dict[str, list[list]]:
    """Convert an analysis's parameter_changes into the overrides-file shape."""
    overrides: dict[str, list[list]] = {}
    for change in analysis.get("parameter_changes", []):
        overrides.setdefault(change["key"], []).append([change["effective_date"], change["new_value"]])
    return overrides
