# Rules as Code

A survey of **Rules as Code (RaC)** — the practice of publishing an official, machine-executable version of legislation, regulation, and policy alongside the natural-language text — with particular attention to the opportunities (and risks) that AI and large language models bring to the field.

## Contents

| File | Description |
|---|---|
| [`rules-as-code-survey.md`](rules-as-code-survey.md) | The survey in Markdown, with ~30 linked sources |
| [`rules-as-code-survey.pdf`](rules-as-code-survey.pdf) | The same survey rendered as a PDF |
| [`product-brainstorm-openleave.md`](product-brainstorm-openleave.md) | Product brainstorm + market validation for **OpenLeave**, a leave-law rules engine |
| [`openleave/`](openleave/) | Working prototype of the OpenLeave MVP (see below) |
| [`tests/`](tests/) | Scenario-based regression suite for the encodings |

## OpenLeave prototype

An executable, citation-backed encoding of U.S. employee leave law: federal **FMLA** plus **California** (CFRA + PFL), **Minnesota** (Paid Leave, live Jan 2026), and **New York** (PFL). Design principles from the survey, made concrete:

- **Every conclusion carries its citation** — determinations return a justification tree, each finding tied to the statute or regulation that produced it.
- **Discretion is flagged, never compiled** — open-textured questions (e.g. "serious health condition") return `met: null` and a `human_judgment` entry instead of a fabricated answer.
- **Effective-date time travel** — statutory parameters (SAWW, benefit caps, program launch dates) are effective-dated, so any determination can be evaluated under the law as of any date.
- **Interaction rules** — FMLA/state concurrency, CA PFL pay + CFRA protection pairing, and the 2026 DOL no-forced-stacking guidance are first-class outputs.
- **Coverage is reported, never assumed** — a determination for a state with a paid-leave program this encoding doesn't implement (WA, MA, NJ, …) is flagged `complete: false` with an explicit warning. Silent under-coverage is the most dangerous failure mode for a rules oracle, so the engine refuses to let a partial answer read as a whole one.

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                                # 30-scenario regression suite
.venv/bin/uvicorn openleave.api:app            # then open http://127.0.0.1:8000
```

`GET /` serves a browser eligibility checker; `POST /determinations` takes `{facts, as_of?}` and returns per-regime eligibility, entitlement, benefit estimates, and interaction notes.

### LLM amendment-watcher pipeline

The maintenance moat from the brainstorm doc, working end-to-end: an LLM reads an amendment or agency notice, drafts a structured encoding diff, the regression suite validates it, and a human signs off before anything is applied.

```sh
export ANTHROPIC_API_KEY=...   # the analyze step calls Claude (claude-opus-4-8)
.venv/bin/python -m openleave.watcher analyze samples/amendments/ny_saww_2027.txt --jurisdiction NY
.venv/bin/python -m openleave.watcher list
.venv/bin/python -m openleave.watcher review <prop-id> --approve --reviewer "Your Name"
.venv/bin/python -m openleave.watcher apply <prop-id>
```

Pipeline guarantees, enforced in code and covered by tests:

- **Parameter diffs vs. logic changes.** The LLM classifies every change: effective-dated parameter updates (a new SAWW, a new benefit cap) are machine-appliable; anything that changes rule *structure* (new eligibility conditions, changed formulas — see `samples/amendments/mn_sf_2199_2027.txt`) is flagged `requires_human_encoding` and never auto-applied.
- **The regression suite is the gate.** Proposed diffs run against the 30-scenario suite via a parameter-override mechanism (`OPENLEAVE_PARAM_OVERRIDES`). Forward-dated changes pass; a diff that rewrites an in-force historical value breaks pinned determinations and is rejected — as is any hallucinated parameter key.
- **Nothing applies without a human.** `apply` refuses unless the proposal is both validation-passing and explicitly approved, and records reviewer + timestamp.
- **Provenance per proposal.** Each proposal (`proposals/*.json`) carries the source document's SHA-256, the model that drafted it, token usage, validation output, and the full review trail.

### MCP server — the oracle behind an AI assistant

The survey's central architectural claim, made concrete: **LLMs at the edges, a verified rules engine at the core.** `openleave_mcp` exposes the engine as MCP tools so an assistant handles the conversation while every substantive legal conclusion comes from the deterministic, citation-backed engine instead of model recall.

```sh
.venv/bin/pip install -e '.[mcp]'
.venv/bin/python -m openleave.mcp_server      # stdio
```

Register it with Claude Code (`claude mcp add openleave -- /path/to/.venv/bin/python -m openleave.mcp_server`) or in Claude Desktop's config:

```json
{ "mcpServers": {
    "openleave": {
      "command": "/path/to/cc_rules_as_code/.venv/bin/python",
      "args": ["-m", "openleave.mcp_server"]
    } } }
```

Three read-only tools:

| Tool | What it answers |
|---|---|
| `openleave_check_leave_eligibility` | Eligibility, entitlement, and benefit amount under every applicable law, each conclusion citing its statute |
| `openleave_list_jurisdictions` | What's encoded — and which states have programs that are **not**, so the assistant knows when an answer is partial |
| `openleave_lookup_statutory_parameter` | A single rate, cap, or threshold as it stood on any date |

The tool descriptions instruct the model to call rather than recall ("leave law differs by state and its rates change every year; model recall is unreliable for it"), and the three outcomes an assistant must distinguish — a determined answer, `eligible: null` requiring human judgment, and `coverage.complete: false` meaning the answer is partial — are documented in the tool schema itself.

> **Prototype disclaimer:** statutory parameter values are approximations for demonstration; verify against agency publications. Decision support, not legal advice.

## What's covered

1. **What Rules as Code is** — definition, core claims, and the OECD "Cracking the Code" framing
2. **Origins and global landscape** — New Zealand (Better Rules), France (OpenFisca), NSW Australia, Canada (Blawx), Jersey, and U.S. public-benefits work
3. **Tools and technical approaches** — microsimulation libraries, logic programming, and legal DSLs (Catala)
4. **Standing challenges** — open texture and discretion, interpretation authority, encoding cost, accountability
5. **The AI opportunity** — the survey's focus:
   - LLMs as encoders (policy-to-code translation, e.g. the Beeck Center's Policy2Code experiments)
   - Neurosymbolic hybrids: LLMs at the language edges, verified rule engines at the core
   - AI as verifier and legislative drafting copilot
   - Conversational interfaces backed by authoritative encodings
   - New risks: plausible-but-wrong encodings, laundered interpretation, over-encoding discretion
6. **Outlook** — why AI strengthens, rather than replaces, the case for Rules as Code

## Regenerating the PDF

```sh
pandoc rules-as-code-survey.md -o rules-as-code-survey.pdf \
  --pdf-engine=xelatex -V mainfont="Helvetica" -V geometry:margin=1in \
  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  --metadata title="Rules as Code: A Survey" --metadata date="July 2026"
```

---

*Compiled July 2026 from public web sources; see the Sources section of the survey for the full reference list.*
