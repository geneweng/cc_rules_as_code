# Session State — OpenLeave / Rules-as-Code

*Handoff note so work can resume after a restart. Last updated after the DE + ME + RI encodings
completed the paid-leave sweep.*

## What this project is

A "Rules as Code" exploration that grew into **OpenLeave**: an executable, citation-backed
encoding of U.S. employee leave law, sold (in concept) as an API — the survey's "LLM at the
edges, verified rules engine at the core" thesis made concrete. Everything is committed to
`main` and pushed to `github.com/geneweng/cc_rules_as_code`.

The arc so far: internet survey → validated product brainstorm → working engine → AI
amendment pipeline → go-to-market collateral (decks, video, landing page) → MCP server →
expanded jurisdiction coverage.

## Current state (all committed, tree clean, 167 tests passing)

**The engine** (`openleave/`) — sixteen regimes across fourteen jurisdictions. **Every
comprehensive U.S. paid-family-leave program is now encoded.**
- Federal FMLA; CA (CFRA + PFL); CO (FAMLI); CT (Paid Leave); DC (Paid Family Leave);
  DE (Paid Leave); ME (PFML); MD (FAMLI); MA (PFML); MN (Paid Leave); NJ (FLI); NY (PFL);
  OR (Paid Leave); RI (TDI + TCI); WA (PFML).
- CT and DC pin their benefit to the **minimum wage** (not a SAWW). CT's job protection
  comes from the *broader* CT FMLA (1+ employee, 3 months); DC's from the *narrower* DC FMLA
  (20+ employees, 12 months, 1,000 hours) — so DC pays far more workers than it protects.
- **MD is enacted but not payable until 2028-01-03.** Its regime returns a *pending-program*
  notice (via `engine.not_yet_in_force_note`) for any earlier date — `applies=False` + note,
  so it stays out of interactions but coverage still reports `complete: true`. This is the
  mirror of `encoded_range_note`. MD's launch-year SAWW isn't published, so its in-force
  (2028+) path returns `weekly_benefit: None` with the statutory bounds ($50–$1,000) rather
  than a fabricated figure.
- **DE** gates coverage on employer size *and* reason together: <10 employees not covered,
  10–24 parental-only, 25+ all reasons. **ME** has a 66% (not 50%) second benefit tier capped
  at the full SAWW. **RI** is two programs in one regime (`ri_tci_tdi`): TCI (bonding/family,
  8 wks, job-protected) vs TDI (own disability, 30 wks, not protected); military-exigency
  uncovered; benefit is a UI-style 4.62% of the highest base-period quarter.
- **Remaining declared gap: Hawaii's own-disability-only TDI** (in `UNENCODED_PROGRAM_STATES`).
  The comprehensive PFML sweep is done; own-disability-only TDI programs are intentionally not
  modeled. `coverage.assess("HI")` still returns `complete: false` — the warning machinery
  stays honest and tested.
- Design invariants: every finding cites its statute; open-textured questions return
  `eligible: null` + `human_judgment` (never fabricated); effective-dated parameters enable
  "law as of any date"; cross-regime interaction rules; **coverage reporting** — a state with
  a paid-leave program we don't encode returns `coverage.complete: false` with a loud warning
  (never silent under-coverage); `encoded_range_note` distinguishes "before our encoded rates"
  from "no entitlement".
- Parameters live in `openleave/parameters.json` (effective-dated `[date, value]` series).
- Regime modules in `openleave/regimes/`; coverage in `openleave/coverage.py`; interactions in
  `openleave/interactions.py`.

**The verification manifest** (`openleave/references.json` + `references.py`) — maps all 105
parameters to statute + agency URL + a plain-English meaning, grouped by jurisdiction with
`verified`/`verified_by`/`verified_on` sign-off fields and structural "claims" (logic/formulas
that aren't single numbers). This is the worksheet for the counsel-verification pass — the #1
gate before real use. Guarded by `tests/test_references.py`: it must document *exactly* the
encoded parameter set (adding a rate without a citation fails CI), and nothing can be marked
verified without a named reviewer + date. `python -m openleave.references {check,summary,report}`;
the generated `references-worksheet.md` is the lawyer-facing artifact. The MCP parameter-lookup
tool now returns each value's citation/source/verified status. **Nothing is verified yet (0/15).**
Note the manifest already flagged one real data issue: the `mn.wage_threshold_fraction_of_saaw`
key has a 'saaw' typo.

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
.venv/bin/pytest -q                                   # 167 tests
.venv/bin/uvicorn openleave.api:app                   # checker at http://127.0.0.1:8000
.venv/bin/python -m openleave.mcp_server              # MCP over stdio
.venv/bin/python -m openleave.watcher --help          # amendment pipeline CLI
```

Tooling installed in `.venv`: fastapi, uvicorn, pytest, httpx, anthropic, mcp[cli],
playwright (+chromium), imageio-ffmpeg. macOS `say`/`afconvert` used for the demo narration.
Video/render scratch work lived under the session scratchpad (not in the repo).

## Important truths to preserve

- **The disclaimer is load-bearing.** Every surface says statutory parameters are
  "approximations pending counsel review." All 16 regimes' figures came from web research
  (2025-2026 rates) and have NOT been verified by an employment lawyer. This must happen before
  anyone relies on a determination. This is the #1 gate before real use. Every state regime
  docstring cites its sources inline (ctpaidleave.org, dcpaidfamilyleave.dc.gov,
  famli.colorado.gov, oregon.gov, paidleave.maryland.gov, labor.delaware.gov, maine.gov/paidleave,
  dlt.ri.gov, etc.) — the seed of the per-jurisdiction reference manifest that verification needs.
- **The investor deck's ask numbers ($2.5M, hiring plan, 18mo) are invented placeholders** —
  replace with real intentions before showing an actual investor.
- **The demo video narration is synthetic TTS** — fine for a prototype, re-record with a human
  voice for anything customer-facing. Scene 5's LLM `analyze` step was narrated without
  claiming that specific run was live (no API key).
- **Traction is internal only** — 167 tests and a working pipeline are engineering traction, not
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

1. **More jurisdictions — essentially DONE.** Every comprehensive paid-family-leave program is
   encoded. The only remaining `UNENCODED_PROGRAM_STATES` entry is Hawaii's own-disability-only
   TDI, intentionally not modeled (the engine is about family/medical leave, not pure disability).
   Adding own-disability TDI (HI, plus the NJ/NY/CA disability halves) would be a deliberate scope
   expansion, not a gap-fill. The bigger frontier now is #2.
2. **Wage-and-hour / termination-rules expansion** — the "wedge is leave, market is
   employment law" thesis from the deck.
3. **Accuracy verification pass** — the per-jurisdiction reference manifest now EXISTS
   (`references.json` + `references-worksheet.md`, 0/15 verified). What remains is the human
   step: get an employment lawyer to work the worksheet and record sign-off. Still the prereq
   for real use — the tooling is built, the review hasn't happened.
4. If pivoting to a real venture: design-partner interview prep, real ask numbers, a
   due-diligence packet.

## Conventions

- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Push after each meaningful increment; keep the tree clean.
- Decks are HTML rendered to PDF via headless Chrome (`--print-to-pdf`, 1280×720 `@page`);
  docs are pandoc + xelatex. Verify visually (screenshot/Read) before committing renders.
