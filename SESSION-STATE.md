# Session State — OpenLeave / Rules-as-Code

*Handoff note so work can resume after a restart. Last updated after the Colorado + Oregon encodings.*

## What this project is

A "Rules as Code" exploration that grew into **OpenLeave**: an executable, citation-backed
encoding of U.S. employee leave law, sold (in concept) as an API — the survey's "LLM at the
edges, verified rules engine at the core" thesis made concrete. Everything is committed to
`main` and pushed to `github.com/geneweng/cc_rules_as_code`.

The arc so far: internet survey → validated product brainstorm → working engine → AI
amendment pipeline → go-to-market collateral (decks, video, landing page) → MCP server →
expanded jurisdiction coverage.

## Current state (all committed, tree clean, 113 tests passing)

**The engine** (`openleave/`) — ten regimes across eight states:
- Federal FMLA; CA (CFRA + PFL); CO (FAMLI); MA (PFML); MN (Paid Leave); NJ (FLI);
  NY (PFL); OR (Paid Leave); WA (PFML).
- Design invariants: every finding cites its statute; open-textured questions return
  `eligible: null` + `human_judgment` (never fabricated); effective-dated parameters enable
  "law as of any date"; cross-regime interaction rules; **coverage reporting** — a state with
  a paid-leave program we don't encode returns `coverage.complete: false` with a loud warning
  (never silent under-coverage); `encoded_range_note` distinguishes "before our encoded rates"
  from "no entitlement".
- Parameters live in `openleave/parameters.json` (effective-dated `[date, value]` series).
- Regime modules in `openleave/regimes/`; coverage in `openleave/coverage.py`; interactions in
  `openleave/interactions.py`.

**The AI amendment pipeline** (`openleave/watcher/`) — LLM drafts a parameter/logic diff from
an amendment doc → regression suite gates it (`OPENLEAVE_PARAM_OVERRIDES`) → human approves →
apply. Nothing ships without passing tests + explicit sign-off. Uses `claude-opus-4-8` via
structured outputs. The `analyze` step needs `ANTHROPIC_API_KEY` (not set in the dev sessions
so far — the demo used an offline-drafted proposal of the same shape).

**The MCP server** (`openleave/mcp_server.py`) — three read-only tools
(`openleave_check_leave_eligibility`, `openleave_list_jurisdictions`,
`openleave_lookup_statutory_parameter`) so an AI assistant calls the verified oracle instead of
recalling leave law. Verified end-to-end over stdio with a real MCP client.

**Surfaces:** FastAPI at `openleave/api.py` (`GET /` = browser checker `openleave/checker.html`,
`POST /determinations`). Landing page at `docs/index.html`, **live at
https://geneweng.github.io/cc_rules_as_code/** (GitHub Pages, `main`/`/docs`).

**Collateral (all in repo root):** `rules-as-code-survey.{md,pdf}`,
`product-brainstorm-openleave.md`, `sales-pitch.{md,pdf}`, `investor-deck.{html,pdf}`,
`how-it-works.{md,pdf}`, `how-it-works-deck.{html,pdf}`, `demo-script.md`, `demo-video.mp4`.

## How to run things

```sh
cd ~/cc_projects/cc_rules_as_code
.venv/bin/pytest -q                                   # 113 tests
.venv/bin/uvicorn openleave.api:app                   # checker at http://127.0.0.1:8000
.venv/bin/python -m openleave.mcp_server              # MCP over stdio
.venv/bin/python -m openleave.watcher --help          # amendment pipeline CLI
```

Tooling installed in `.venv`: fastapi, uvicorn, pytest, httpx, anthropic, mcp[cli],
playwright (+chromium), imageio-ffmpeg. macOS `say`/`afconvert` used for the demo narration.
Video/render scratch work lived under the session scratchpad (not in the repo).

## Important truths to preserve

- **The disclaimer is load-bearing.** Every surface says statutory parameters are
  "approximations pending counsel review." The CO/OR/WA/MA/NJ (and all) figures came from web
  research (2026 rates) and have NOT been verified by an employment lawyer. This must happen
  before anyone relies on a determination. This is the #1 gate before real use. The CO and OR
  regime docstrings cite their sources inline (famli.colorado.gov, oregon.gov) — the seed of
  the per-jurisdiction reference manifest that verification will need.
- **The investor deck's ask numbers ($2.5M, hiring plan, 18mo) are invented placeholders** —
  replace with real intentions before showing an actual investor.
- **The demo video narration is synthetic TTS** — fine for a prototype, re-record with a human
  voice for anything customer-facing. Scene 5's LLM `analyze` step was narrated without
  claiming that specific run was live (no API key).
- **Traction is internal only** — 113 tests and a working pipeline are engineering traction, not
  market traction. No real design partner, lawyer, or dollar has touched this yet.

## Decisions already made (don't relitigate)

- Direction chosen: **option 3 — keep building the prototype without external validation yet**
  (vs. treating it as done, or pursuing it as a real venture). MCP server and 3 new
  jurisdictions were the last two increments under this.
- Product pick was leave law (closed-texture, private-sector buyers, growing regulatory
  divergence, nobody sells the rules layer). See `product-brainstorm-openleave.md`.
- Python engine + Python MCP server (imports the engine directly, no HTTP hop).
- Statute-book visual identity across all decks/landing (ink/paper/oxblood/gold;
  Baskerville/Charter/Menlo).

## Natural next steps (open, not started)

1. **More jurisdictions.** Declared gaps still warned about: CT, DC, DE, MD, ME, RI.
   `openleave_list_jurisdictions` / `coverage.UNENCODED_PROGRAM_STATES` is the worklist.
2. **Wage-and-hour / termination-rules expansion** — the "wedge is leave, market is
   employment law" thesis from the deck.
3. **Accuracy verification pass** — get an employment lawyer to check the encoded figures
   against primary sources; add a per-jurisdiction reference list. (Prereq for real use.)
4. If pivoting to a real venture: design-partner interview prep, real ask numbers, a
   due-diligence packet.

## Conventions

- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Push after each meaningful increment; keep the tree clean.
- Decks are HTML rendered to PDF via headless Chrome (`--print-to-pdf`, 1280×720 `@page`);
  docs are pandoc + xelatex. Verify visually (screenshot/Read) before committing renders.
