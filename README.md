# Rules as Code

A survey of **Rules as Code (RaC)** — the practice of publishing an official, machine-executable version of legislation, regulation, and policy alongside the natural-language text — with particular attention to the opportunities (and risks) that AI and large language models bring to the field.

## Contents

| File | Description |
|---|---|
| [`rules-as-code-survey.md`](rules-as-code-survey.md) | The survey in Markdown, with ~30 linked sources |
| [`rules-as-code-survey.pdf`](rules-as-code-survey.pdf) | The same survey rendered as a PDF |
| [`product-brainstorm-openleave.md`](product-brainstorm-openleave.md) | Product brainstorm + market validation for **OpenLeave**, a leave-law rules engine |
| [`openleave/`](openleave/) | Working prototype of the OpenLeave MVP (see below) |
| [`tests/`](tests/) | Scenario-based regression suite for the encodings (204 tests) |
| [`wage-hour-expansion-scope.md`](wage-hour-expansion-scope.md) | Scoping doc for the wage-and-hour expansion (the "market is employment law" thesis) |

## OpenLeave prototype

An executable, citation-backed encoding of U.S. employee leave law: federal **FMLA** plus **California** (CFRA + PFL), **Colorado** (FAMLI), **Connecticut** (Paid Leave), **DC** (Paid Family Leave), **Delaware** (Paid Leave), **Maine** (PFML), **Maryland** (FAMLI), **Massachusetts** (PFML), **Minnesota** (Paid Leave), **New Jersey** (FLI), **New York** (PFL), **Oregon** (Paid Leave), **Rhode Island** (TDI + TCI), and **Washington** (PFML) — **every comprehensive U.S. paid-leave program**: sixteen regimes across fourteen jurisdictions. Design principles from the survey, made concrete:

- **Every conclusion carries its citation** — determinations return a justification tree, each finding tied to the statute or regulation that produced it.
- **Discretion is flagged, never compiled** — open-textured questions (e.g. "serious health condition") return `met: null` and a `human_judgment` entry instead of a fabricated answer.
- **Effective-date time travel** — statutory parameters (SAWW, benefit caps, program launch dates) are effective-dated, so any determination can be evaluated under the law as of any date.
- **Interaction rules** — FMLA/state concurrency, CA PFL pay + CFRA protection pairing, and the 2026 DOL no-forced-stacking guidance are first-class outputs.
- **Coverage is reported, never assumed** — every comprehensive paid-family-leave program is now encoded, but the engine still reports its own limits: a state whose only program is own-disability TDI that this engine doesn't model (Hawaii) is flagged `complete: false` with an explicit warning. Silent under-coverage is the most dangerous failure mode for a rules oracle, so the engine refuses to let a partial answer read as a whole one.
- **Outside the encoded range ≠ no entitlement** — most state programs have paid benefits for years, but their rates are encoded only from 2025/2026 onward. A determination dated earlier says so explicitly rather than returning a denial.
- **Enacted ≠ in force** — Maryland's FAMLI is law but does not pay benefits until 2028-01-03. A 2026 determination returns a *pending-program* notice with the start date, not a benefit (which can't be claimed yet) and not a denial (the entitlement is coming). This is the mirror image of the encoded-range case, and it keeps the program from reading as either a false "no benefit" or silent under-coverage.

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                                # 204-scenario regression suite
.venv/bin/uvicorn openleave.api:app            # then open http://127.0.0.1:8000
```

`GET /` serves a browser eligibility checker; `POST /determinations` takes `{facts, as_of?}` and returns per-regime eligibility, entitlement, benefit estimates, and interaction notes. The wage-and-hour engine (below) has parallel surfaces: `GET /wage-hour` (browser checker) and `POST /wage-hour/determinations`.

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
- **The regression suite is the gate.** Proposed diffs run against the full regression suite via a parameter-override mechanism (`OPENLEAVE_PARAM_OVERRIDES`). Forward-dated changes pass; a diff that rewrites an in-force historical value breaks pinned determinations and is rejected — as is any hallucinated parameter key.
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

Four read-only tools:

| Tool | What it answers |
|---|---|
| `openleave_check_leave_eligibility` | Eligibility, entitlement, and benefit amount under every applicable leave law, each conclusion citing its statute |
| `openleave_check_wage_hour` | The applicable minimum wage (with tip-credit handling) and, on separation, final-pay timing and accrued-vacation payout — each with its citation |
| `openleave_list_jurisdictions` | What's encoded — and which states have programs that are **not**, so the assistant knows when an answer is partial |
| `openleave_lookup_statutory_parameter` | A single rate, cap, or threshold as it stood on any date, with its source and verification status |

The tool descriptions instruct the model to call rather than recall ("leave law differs by state and its rates change every year; model recall is unreliable for it"), and the three outcomes an assistant must distinguish — a determined answer, `eligible: null` requiring human judgment, and `coverage.complete: false` meaning the answer is partial — are documented in the tool schema itself.

> **Prototype disclaimer:** statutory parameter values are approximations for demonstration; verify against agency publications. Decision support, not legal advice.

### Verification manifest — the gate before real use

Every statutory value here is web-researched and **unverified by counsel** — the single most important thing to fix before anyone relies on a determination. `openleave/references.json` is the worksheet for that review: it maps **all 124 encoded parameters** (leave and wage-and-hour) to a plain-English meaning, the governing statute, and the agency page a reviewer checks them against, grouped by jurisdiction with sign-off fields (`verified` / `verified_by` / `verified_on`) and a list of structural claims (eligibility logic, formulas, job-protection rules) that aren't single numbers.

```sh
.venv/bin/python -m openleave.references check     # every parameter is documented (CI-gated)
.venv/bin/python -m openleave.references summary    # verification progress
.venv/bin/python -m openleave.references report references-worksheet.md   # reviewer worksheet
```

The manifest can't drift: a test asserts it documents **exactly** the set of encoded parameters, so adding a rate without a citation breaks the build, and a jurisdiction can't be marked `verified` without a named reviewer and date. The MCP parameter-lookup tool returns each value's citation, source, and verification status alongside the number, so an assistant can cite it and flag that it's still pending review. The generated [`references-worksheet.md`](references-worksheet.md) is the artifact an employment lawyer works through, one jurisdiction at a time.

### Wage & hour (`openleave/wagehour/`) — the next domain, Phase 1

The [scoping doc](wage-hour-expansion-scope.md) lays out the "wedge is leave, market is employment law" expansion. This is its **Phase 1 vertical slice**: **minimum wage** (with tip-credit handling) and **final-pay-on-separation** timing (with accrued-vacation payout), for the federal floor plus **California** and **Washington**. It's a sibling capability that reuses the leave engine's substrate — the effective-dated `parameters`, the `Finding`/`Citation` justification tree, and the coverage-reporting reflex.

```python
from datetime import date
from openleave.wagehour import assess_wage_hour, WageFacts, Separation, SeparationType

assess_wage_hour(WageFacts(work_state="CA", hourly_rate=15.00), date(2026, 2, 1))
# -> minimum_wage topic: applicable $16.90, rate_meets_minimum = False (violation), each finding cited
```

What the slice demonstrates:

- **Effective-dated compliance** — a $16.60 wage clears California's 2025 floor ($16.50) and **fails** its 2026 floor ($16.90). Compliance is a function of the date, not a static lookup.
- **The tip credit, done honestly** — California and Washington prohibit it (full minimum in cash, tips on top; `Cal. Lab. Code § 351`, `RCW 49.46.020(3)`); the federal rule permits a $2.13 cash wage if tips reach $7.25. The engine flags "only CA/WA tip rules are encoded" for other states rather than guessing.
- **Locality-aware, and honest about its edges** — the minimum wage is the highest of the federal, state, and (where encoded) local floor. A Seattle worksite gets its **$21.30** local rate (`Seattle Municipal Code 14.19`), not the $17.13 state figure — twelve marquee WA and CA localities (Seattle, Tukwila, Renton, San Francisco, Los Angeles city/county, Oakland, San Jose, …) are encoded. A worksite in an *unencoded* locality still returns `coverage.complete: false`, because the engine can't rule out a local ordinance it doesn't know — silent locality under-coverage is the wage-and-hour analogue of returning "FMLA only." SeaTac is deliberately left unencoded and warned, because its $20.74 applies only to hospitality/transportation workers, not city-wide.
- **Final pay with real teeth** — California's immediate-on-firing deadline, the 72-hour rule for a no-notice quit, waiting-time-penalty exposure for late payment, and mandatory accrued-vacation payout (valued: 40 hrs × $30 = $1,200) — contrasted with Washington's next-pay-period rule and policy-dependent vacation (returned as `met: null`, a human-judgment point).

The slice has full surface parity with leave: the `openleave_check_wage_hour` MCP tool, a `POST /wage-hour/determinations` API endpoint, and a browser checker at `GET /wage-hour` (linked from the leave checker).

Deliberately deferred to Phase 2 (see the scope doc): **overtime** math and **exempt classification** — the latter because its duties test is open-textured and the liability of getting it wrong is misclassification. Encoding the salary threshold and flagging the duties test for human judgment is the honest design; auto-answering it is not.

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
