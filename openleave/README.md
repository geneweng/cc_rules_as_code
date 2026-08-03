# OpenLeave

An executable, **citation-backed** encoding of U.S. employment law — employee leave, minimum
wage, overtime, exempt classification, and final pay — built on one thesis: **the LLM belongs at
the edges, a verified rules engine at the core.** Every conclusion the engine produces carries the
statute or regulation that produced it, open-textured questions are flagged for human judgment
(never fabricated), and every parameter is effective-dated so any determination can be evaluated
"under the law as of" any date.

> **Prototype.** Statutory values are web-researched and **not yet verified by counsel** — see
> [Verification manifest](#verification-manifest). Decision support, not legal advice.

---

## Install

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'      # engine + tests
# optional extras, mix as needed:
.venv/bin/pip install -e '.[mcp]'       # MCP server
.venv/bin/pip install -e '.[agent]'     # sample agent (Anthropic SDK + MCP)
.venv/bin/pip install -e '.[watcher]'   # LLM amendment pipeline
```

## Quick start

```python
from datetime import date
from openleave import determine, Employee, Employer, Facts, LeaveEvent, LeaveReason

# Leave: a New York bonding leave, evaluated under 2026 law.
result = determine(Facts(
    employee=Employee(work_state="NY", hire_date=date(2024, 1, 1),
                      hours_last_12mo=1600, average_weekly_wage=1500),
    employer=Employer(total_employees=100),
    event=LeaveEvent(type=LeaveReason.BONDING, start=date(2026, 9, 1)),
))
# -> per-regime eligibility, entitlement, benefit dollars, interaction notes, and a
#    coverage report — every finding tied to a citation.
```

```python
from datetime import date
from openleave.wagehour import assess_wage_hour, WageFacts

# Wage & hour: is $15/hour legal in California in 2026?
assess_wage_hour(WageFacts(work_state="CA", hourly_rate=15.00), date(2026, 2, 1))
# -> minimum_wage topic: applicable $16.90, rate_meets_minimum = False (a violation), cited.
```

## What's covered

**Leave** — federal FMLA plus **every comprehensive U.S. paid-family-leave program**: CA (CFRA +
PFL), CO, CT, DC, DE, MA, MD, ME, MN, NJ, NY, OR, RI, WA — sixteen regimes across fourteen
jurisdictions. (Own-disability-only TDI programs like Hawaii's are intentionally out of scope and
reported as such.)

**Wage & hour** (`openleave/wagehour/`) — the "market is employment law" expansion, for the federal
floor plus **California and Washington**:

- **Minimum wage** — state + federal, twelve encoded localities (Seattle, San Francisco, LA, …),
  and tip-credit handling (CA/WA prohibit it; the federal $2.13 rule applies elsewhere).
- **Overtime** — FLSA/WA weekly, California daily (1.5× over 8, 2× over 12) + 7th-day +
  non-pyramiding, with a blended regular rate.
- **Exempt classification** — the salary test is decided by rule; the **duties test is always
  returned as human judgment, never auto-decided**.
- **Final pay** — separation-timing deadlines, waiting-time-penalty exposure, and accrued-vacation
  payout.

## Design principles (the honesty invariants)

- **Every conclusion cites its source** — determinations are a justification tree of `Finding`s,
  each tied to a `Citation`.
- **Discretion is flagged, never compiled** — open-textured questions ("serious health condition",
  the exemption duties test) return `met: null` + a `human_judgment` entry.
- **Coverage is reported, never assumed** — a state or locality the engine doesn't encode comes
  back `complete: false` with a loud warning. Silent under-coverage is the most dangerous failure
  mode for a rules oracle, and the engine refuses it.
- **Effective-dated everything** — parameters are `[date, value]` series (`parameters.json`), so
  "law as of any date" is a first-class capability. A wage that clears CA's 2025 floor can fail its
  2026 floor; a program can be *enacted but not yet in force* (Maryland, 2028).

## The sample agent

`openleave/agent.py` is a runnable demonstration of the whole thesis: a **Claude agent that answers
natural-language employment-law questions by *calling* the MCP tools instead of recalling the
law.** It connects to the MCP server (below), lists its tools, and runs an Anthropic tool-use loop
— and it prints each tool call as it goes, so you can watch every legal conclusion originate in the
verified engine rather than the model.

```sh
.venv/bin/pip install -e '.[agent]'
export ANTHROPIC_API_KEY=sk-ant-...

# Ask one question:
.venv/bin/python -m openleave.agent "Is a $15/hour wage legal in California in 2026?"

# Run the built-in demo (leave, minimum wage, final pay, overtime/exemption, coverage):
.venv/bin/python -m openleave.agent

# Interactive REPL:
.venv/bin/python -m openleave.agent --interactive

# Verify the MCP wiring WITHOUT an API key (lists the tools and exits):
.venv/bin/python -m openleave.agent --list-tools
```

As it runs, tool calls stream to stderr so the sourcing is visible:

```
Q: Is a $15/hour wage legal in California in 2026?
  → calling openleave_check_wage_hour(work_state='CA', hourly_rate=15.0, as_of='2026-02-01')
  ← openleave_check_wage_hour returned: # Wage & hour — CA …
A: No. California's 2026 minimum wage is $16.90/hour (Cal. Lab. Code § 1182.12), so $15.00 is
   below the floor by $1.90 — a minimum-wage violation. …
```

Configuration:

- **`ANTHROPIC_API_KEY`** is required for the LLM turn (not for `--list-tools`).
- **Model** defaults to `claude-opus-4-8`; override with `--model <id>` or `OPENLEAVE_AGENT_MODEL`.
- The agent's system prompt forbids answering substantive questions from memory and instructs it to
  pass the tools' **citations, human-judgment flags, and incomplete-coverage warnings through
  unchanged** — so an "it depends on the duties test" stays "it depends," and a partial answer is
  labeled partial.

## MCP server

`openleave/mcp_server.py` exposes the engine as four read-only [Model Context
Protocol](https://modelcontextprotocol.io) tools, so any MCP-capable assistant can use the verified
oracle instead of recalling employment law.

```sh
.venv/bin/pip install -e '.[mcp]'
.venv/bin/python -m openleave.mcp_server         # stdio

# Register with Claude Code:
claude mcp add openleave -- /path/to/.venv/bin/python -m openleave.mcp_server
```

| Tool | Answers |
|---|---|
| `openleave_check_leave_eligibility` | Eligibility, entitlement, and benefit amount under every applicable leave law |
| `openleave_check_wage_hour` | Minimum wage (with tip credit & localities), overtime, exemption status, final-pay timing |
| `openleave_list_jurisdictions` | What's encoded — and which programs are knowingly *not* |
| `openleave_lookup_statutory_parameter` | Any rate/cap/threshold as of any date, with its source and verification status |

## REST API and browser checkers

`openleave/api.py` is a FastAPI app.

```sh
.venv/bin/uvicorn openleave.api:app        # http://127.0.0.1:8000
```

| Route | Purpose |
|---|---|
| `GET /` | Browser leave-eligibility checker |
| `POST /determinations` | Leave determination — `{facts, as_of?}` |
| `GET /wage-hour` | Browser wage & hour checker |
| `POST /wage-hour/determinations` | Wage & hour determination — `{facts, as_of?}` |
| `GET /health` | Liveness + engine version |

## Amendment watcher

`openleave/watcher/` is the maintenance pipeline: an LLM reads an amendment or agency notice, drafts
a structured encoding diff, the **full regression suite gates it**, and a human signs off before
anything is applied. Parameter updates are machine-appliable; structural changes are flagged
`requires_human_encoding` and never auto-applied.

```sh
export ANTHROPIC_API_KEY=...
.venv/bin/python -m openleave.watcher analyze samples/amendments/ny_saww_2027.txt --jurisdiction NY
.venv/bin/python -m openleave.watcher review <prop-id> --approve --reviewer "Your Name"
.venv/bin/python -m openleave.watcher apply <prop-id>
```

## Verification manifest

Every statutory value here is web-researched and **unverified by counsel** — the one thing that must
change before anyone relies on a determination. `references.json` is the worksheet for that review:
it maps all encoded parameters to a plain-English meaning, the governing statute, and the agency
page to check them against, with per-jurisdiction sign-off fields.

```sh
.venv/bin/python -m openleave.references check      # every parameter is documented (CI-gated)
.venv/bin/python -m openleave.references summary      # verification progress
.venv/bin/python -m openleave.references report worksheet.md   # reviewer worksheet
```

A test asserts the manifest documents **exactly** the encoded parameter set, so a rate can't be
added without a citation, and a jurisdiction can't be marked verified without a named reviewer and
date.

## Testing

```sh
.venv/bin/pytest        # the full scenario-based regression suite
```

## Layout

For the design rationale behind this layout — the layers, data flow, and the honesty invariants that
shape the core — see [`ARCHITECTURE.md`](../ARCHITECTURE.md).

```
openleave/
  engine.py          Finding / Citation / RegimeResult; the shared justification-tree types
  facts.py           leave input models (Employee / Employer / LeaveEvent / Facts)
  parameters.py      effective-dated parameter store (+ parameters.json)
  coverage.py        leave coverage reporting
  interactions.py    cross-regime concurrency / stacking rules
  regimes/           one module per leave regime (fmla, california, … washington)
  wagehour/          the wage & hour engine (minimum_wage, overtime, exemptions, final_pay,
                     localities, coverage; assess_wage_hour entry point)
  references.py      verification manifest tooling (+ references.json)
  watcher/           the LLM amendment pipeline
  mcp_server.py      MCP tools
  api.py             FastAPI app (+ checker.html, wage_checker.html)
  agent.py           the sample agent
```
