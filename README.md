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

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                                # 30-scenario regression suite
.venv/bin/uvicorn openleave.api:app            # then open http://127.0.0.1:8000
```

`GET /` serves a browser eligibility checker; `POST /determinations` takes `{facts, as_of?}` and returns per-regime eligibility, entitlement, benefit estimates, and interaction notes.

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
