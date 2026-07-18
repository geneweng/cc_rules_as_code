"""LLM analysis of legislative/agency amendment documents.

Given the text of an amendment (statute change, agency benefit-rate notice,
rulemaking), the analyzer drafts a structured change proposal:

- parameter_changes: diffs to effective-dated parameters the engine already
  knows (new SAWW, new benefit cap, new week counts) — machine-appliable after
  validation and human sign-off.
- logic_changes: changes that alter rule *structure* (new eligibility
  condition, new covered reason) — never auto-applied; routed to a human
  encoder. This is the "discretion doesn't compile" principle applied to the
  maintenance pipeline itself.

The LLM only ever drafts; nothing it produces takes effect without passing the
regression suite and explicit human approval recorded on the proposal.
"""

from __future__ import annotations

import json
from typing import Protocol

from .. import parameters

MODEL = "claude-opus-4-8"

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One-paragraph summary of what the document changes"},
        "parameter_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "An existing parameter key from the provided list"},
                    "new_value": {"type": "number"},
                    "effective_date": {"type": "string", "format": "date"},
                    "citation": {"type": "string", "description": "Statute/notice cited for this change"},
                    "source_quote": {"type": "string", "description": "Verbatim quote from the document supporting the value"},
                },
                "required": ["key", "new_value", "effective_date", "citation", "source_quote"],
                "additionalProperties": False,
            },
        },
        "logic_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "affected_regimes": {"type": "array", "items": {"type": "string"}},
                    "citation": {"type": "string"},
                },
                "required": ["description", "affected_regimes", "citation"],
                "additionalProperties": False,
            },
        },
        "requires_human_encoding": {
            "type": "boolean",
            "description": "True when any change cannot be expressed as a parameter diff",
        },
    },
    "required": ["summary", "parameter_changes", "logic_changes", "requires_human_encoding"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are the amendment analyzer for OpenLeave, an executable encoding of U.S. \
employee leave law (FMLA, CA CFRA/PFL, MN Paid Leave, NY PFL). You read a legislative amendment or \
agency notice and draft a structured change proposal for the encoding.

Rules:
- A parameter_change may only use a key from the provided known-parameters list, and only when the \
document states the new value explicitly. Quote the exact supporting sentence in source_quote.
- Anything that changes rule structure — a new eligibility condition, a new covered reason, changed \
interaction rules, a formula whose shape changes — is a logic_change, never a parameter_change, even \
if it also mentions numbers. When in doubt, prefer logic_change: a human encoder reviews those.
- Never invent values, dates, or citations not present in the document. If the document changes \
nothing relevant to the encoding, return empty lists.
- Dates must be ISO format (YYYY-MM-DD)."""


class Analyzer(Protocol):
    def analyze(self, document_text: str, jurisdiction: str) -> dict: ...


class ClaudeAnalyzer:
    """Drafts change proposals with Claude via structured outputs."""

    def __init__(self, client=None, model: str = MODEL):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client
        self.model = model

    def analyze(self, document_text: str, jurisdiction: str) -> dict:
        known = json.dumps(parameters.current_entries(), indent=1, sort_keys=True)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Jurisdiction: {jurisdiction}\n\n"
                        f"Known parameters (key -> [[effective_date, value], ...]):\n{known}\n\n"
                        f"Amendment document:\n<document>\n{document_text}\n</document>"
                    ),
                }
            ],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Model declined to analyze this document")
        text = next(b.text for b in response.content if b.type == "text")
        analysis = json.loads(text)
        analysis["_provenance"] = {"model": response.model, "usage": response.usage.to_dict()}
        return analysis
