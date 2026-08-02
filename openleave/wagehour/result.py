"""Result type for a single wage-and-hour topic (minimum wage, final pay, ...).

Deliberately parallel to the leave engine's `RegimeResult`: a list of
citation-bearing `Finding`s, a `data` bag of computed values, open-textured
points surfaced in `human_judgment`, and free-text `notes`. Reuses the shared
`Finding`/`Citation` types so both domains speak the same justification-tree
language.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..engine import Finding


@dataclass
class WageTopic:
    topic: str  # short id, e.g. "minimum_wage"
    name: str
    findings: list[Finding] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    human_judgment: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "topic": self.topic,
            "name": self.name,
            "findings": [f.as_dict() for f in self.findings],
            "data": self.data,
            "human_judgment": self.human_judgment,
            "notes": self.notes,
        }
