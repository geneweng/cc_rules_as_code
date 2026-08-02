# Wage & Hour Expansion — Scoping

*How OpenLeave grows from leave law into the broader employment-law market — what
reuses the engine we already have, what is genuinely new, and what to build first.*

Status: scoping document. No code yet. Companion to
[`product-brainstorm-openleave.md`](product-brainstorm-openleave.md).

---

## 1. Why this, why now

The investor and how-it-works decks make one claim about direction: **the wedge is
leave, the market is employment law.** Leave was the right beachhead — closed-texture
rules, a discrete event to reason about, buyers who already feel the pain. But a payroll
platform, an EOR, or an HR copilot that has integrated OpenLeave for leave has the same
unmet need one category over: **wage and hour.** It is the largest, most litigated, most
jurisdictionally fragmented corner of employment law, and — critically for us — most of it
is *closed-texture and numeric*, which is exactly what a rules engine does well.

The leave sweep is done: sixteen regimes, every comprehensive U.S. paid-leave program,
each determination citation-backed and effective-dated. That machinery is the asset. This
document is about pointing it at the next domain without rebuilding it and without
overreaching into the parts that are genuinely hard.

## 2. What "wage and hour" actually is

Eight sub-domains, ordered roughly by how cleanly they fit a rules engine:

| # | Sub-domain | Character | Fit |
|---|---|---|---|
| 1 | **Minimum wage** | Effective-dated rate by jurisdiction; tipped rate / tip credit; small-employer and youth variants | **Excellent** — pure effective-dated lookup |
| 2 | **Final-pay timing** | Deadline by state × (quit / fired); waiting-time penalties | **Excellent** — rules lookup |
| 3 | **Accrued-vacation payout** | On separation, is unused PTO earned wages? By state | **Good** — mostly a state flag |
| 4 | **Pay frequency** | Weekly / biweekly / semimonthly minimum, by state | **Good** — lookup |
| 5 | **Overtime** | 1.5× over 40/week (FLSA); daily & 7th-day rules (CA); blended regular rate | **Moderate** — real computation |
| 6 | **Meal & rest breaks** | Timing + premium pay for missed breaks (CA and others) | **Moderate** — schedule-dependent |
| 7 | **Exempt classification** | White-collar exemptions: salary-basis threshold **+ a duties test** | **Hard** — duties test is open-textured |
| 8 | **Tip pooling / credit rules** | Who may share tips; manager exclusion | **Hard** — fact-heavy |

Adjacent "separation" rules the same buyer asks about in the same breath (worth noting,
partly wage-and-hour, partly not): **WARN Act** mass-layoff notice (federal 60 days / 100+
employees, plus mini-WARN states), **final-pay penalties**, and **COBRA / mini-COBRA**
benefit continuation.

## 3. What carries over from the leave engine (the leverage)

Almost everything. This is the case for doing it at all:

- **Effective-dated parameters** (`parameters.json` / `parameters.py`). Minimum wage is the
  single best effective-dated fact in all of employment law — it changes on a schedule in
  most states (annual CPI indexing, legislated step-ups) and localities. "Law as of any
  date" is not a nice-to-have here; back-pay and penalty exposure are computed against the
  rate *in force on each day of the claim period*. Reuse wholesale.
- **Findings + citations.** Same `Finding` / `Citation` justification-tree shape.
- **Discretion → `null`.** The exempt-status **duties test** is the archetypal open-textured
  question — more so than "serious health condition." The pattern we already have (return
  `met: null` + a `human_judgment` entry, never a fabricated yes/no) is exactly right, and
  wage-and-hour is where it earns its keep most visibly.
- **Coverage reporting.** The locality problem (below) maps directly onto the
  `coverage.complete: false` + loud-warning pattern. A state-minimum-wage answer for a
  worker in San Francisco must announce that a higher local ordinance may apply, rather than
  silently understate the floor. Same failure mode we already guard against for leave, same
  guard.
- **The amendment watcher.** Minimum-wage changes are the highest-*frequency* amendments in
  employment law — dozens per year across states and localities, almost all pure parameter
  updates. The watcher pipeline (LLM drafts a diff → regression suite gates → human signs
  off) is *more* valuable here than for leave, not less.
- **The verification manifest.** Extend `references.json` to wage-and-hour keys; the
  drift-guard test generalizes unchanged.
- **MCP tools + FastAPI surface.** Add wage-and-hour tools alongside the three leave tools;
  the "LLM at the edges, verified engine at the core" story is identical.

**The exempt-threshold whipsaw is a ready-made showcase for the effective-dating + watcher
story.** The federal white-collar salary threshold was $684/week (2019 rule), the 2024 DOL
rule raised it to $844 (2024-07-01) then $1,128 (2025-01-01), a court **vacated** that rule
in November 2024, and DOL formally restored $684 in May 2026. Any engine that answers "was
this salaried worker exempt on [date]?" without effective-dated law and a change-tracking
pipeline gets this wrong for millions of workers across 2024–2026. We already have both.

## 4. What's genuinely new or harder (the three real challenges)

Only three things don't fall out of the existing engine. They are the substance of the
scoping decision.

### 4a. The locality dimension — the one real architectural change

Leave law is state-level (plus federal). Wage-and-hour is **state + county + city**: Seattle,
NYC, Chicago, Denver, Flagstaff, and ~40 California cities set minimum wages above their
state floor, and some set their own paid-sick and scheduling rules. Our `Facts` model has
only `work_state`.

This is the single biggest change and the key scoping fork (§5, Decision 2). Two honest
options: (a) **state-level first**, with localities declared as explicit coverage gaps —
reusing the exact `coverage` pattern that already keeps leave answers honest; or (b) build
locality into the key scheme and fact model from day one. Recommendation below.

### 4b. The fact model shifts from *event* to *ongoing state*

Leave reasons about a **discrete event** — a `LeaveEvent` with a start date. Wage-and-hour
reasons about **ongoing employment**: hours worked in a week, a pay rate, a pay period, a
classification, a separation. These do not fit `LeaveEvent`. They want a **new fact type**
(`WageFacts` or similar) and a **new determination entry point**, sitting beside `determine()`
rather than inside it. Leave and wage-hour become sibling capabilities of one engine, sharing
`parameters`, `engine` (Finding/Citation), `coverage`, and the manifest.

### 4c. Overtime math and the duties test carry real complexity and real liability

- **Overtime** is not a lookup: the *regular rate* must fold in nondiscretionary bonuses
  (a blended rate), and California layers daily OT (1.5× over 8, 2× over 12), seventh-
  consecutive-day rules, and their interaction with the weekly 40-hour rule. Correct, but
  intricate — and worth encoding carefully rather than quickly.
- **Exempt classification** is where a rules oracle is most tempting and most dangerous. The
  salary-basis *threshold* is a clean effective-dated number; the **duties test** is a
  multi-factor judgment that decides most misclassification cases. Encoding the threshold and
  flagging the duties test for human judgment is the honest design. Encoding a yes/no on
  duties would be exactly the "plausible-but-wrong, laundered-interpretation" failure the
  survey warns about. This is why exemptions are sequenced **last**, not first.

## 5. Key scoping decisions

Three forks. Each stated with a recommendation; all are the user's call.

### Decision 1 — MVP wedge: what to encode first

**Recommendation: minimum wage (state-level) + final-pay-on-separation timing.** Together
these are the two cleanest fits (§2 rows 1–2), reuse ~100% of the engine, and tell a coherent
"is this worker being paid legally, and paid out correctly when they leave?" story — a
complete small product, not a fragment. **Defer overtime + exemptions + breaks to Phase 2**,
precisely because that is where the computation and the interpretation risk live.

Alternative if a single sharper wedge is preferred: **minimum wage alone**, as a pure
"floor as of any date, anywhere" service — thinner, but the strongest standalone showcase of
the effective-dated engine and the watcher.

### Decision 2 — Locality strategy

**Recommendation: state-level first, localities as declared coverage gaps, then add the top
localities in a fast follow.** Ship state + federal minimum wage with a loud
`coverage.complete: false` whenever the worksite is in a locality known to set its own higher
rate (Seattle, NYC, SF, LA, Chicago, Denver, DC, and the CA-city cluster). This is honest on
day one and reuses the coverage machinery verbatim. Then encode the ~15 highest-population
local ordinances in Phase 1.5. Building full national locality coverage up front is the wrong
first move — the long tail is dozens of small-city ordinances with tiny populations and no
buyer urgency.

### Decision 3 — Fact model & entry point

**Recommendation: a new `WageFacts` type and a new `assess_wage_hour()` entry point**, sibling
to `determine()`, under a new `openleave/wagehour/` package. Do **not** overload `LeaveEvent`
or the leave `Facts`. Shared substrate (`parameters`, `engine`, `coverage`, `references`) is
imported by both. This keeps each domain's fact surface honest to its own shape and lets the
two ship and version independently.

## 6. Proposed architecture (sketch, not built)

```
openleave/
  engine.py          # shared: Finding, Citation, resolve_*, encoded_range_note ... (reused)
  parameters.py      # shared, effective-dated (reused; new keys added)
  coverage.py        # shared pattern; add a locality-coverage assessor
  references.py      # shared manifest tooling (reused; new entries)
  regimes/           # leave (unchanged)
  wagehour/          # NEW sibling package
    facts.py         #   WageFacts: jurisdiction (state + optional locality), employer size,
                     #   pay_rate/basis, weekly & daily hours, tipped?, claimed_exemption?,
                     #   separation (type + date)
    minimum_wage.py  #   assess_minimum_wage(facts, as_of)
    final_pay.py     #   assess_final_pay(facts, as_of)  (+ accrued-vacation payout)
    overtime.py      #   Phase 2
    exemptions.py    #   Phase 2 (threshold encoded; duties test -> human_judgment)
    breaks.py        #   Phase 2
    __init__.py      #   assess_wage_hour(facts, as_of) -> aggregated determination
```

**Parameter key scheme** (extends `parameters.json`):

```
minwage.federal                         7.25   [2009-07-24]
minwage.CA                              ...     (state floor, effective-dated)
minwage.CA.san_francisco                ...     (locality overrides state when present)
minwage.federal.tipped_cash             2.13   [1991-04-01]
minwage.federal.tip_credit_max          5.12
ot.federal.weekly_threshold_hours       40
ot.CA.daily_threshold_hours             8
ot.CA.double_time_daily_hours           12
exempt.federal.salary_weekly            684    [2020-01-01]  # ← the whipsaw lives here
finalpay.CA.fired_deadline_hours        0      # immediately
finalpay.CA.quit_no_notice_hours        72
vacation_payout.CA                      true   # earned wages, must pay out
```

**Determination output** mirrors the leave shape: per-topic findings each carrying a citation,
a `coverage` block (now locality-aware), open-textured points flagged `null`, and the standing
decision-support disclaimer.

## 7. Phased plan

| Phase | Scope | Reuses | New work | Showcase it unlocks |
|---|---|---|---|---|
| **1** | State + federal **minimum wage** (incl. tipped / tip credit) and **final-pay timing** + accrued-vacation payout, for a starter set of states (federal, CA, WA, NY, TX). Locality gaps declared. | params, engine, coverage, manifest, MCP | `WageFacts`, `wagehour/` package, `assess_wage_hour()`, locality-coverage assessor | "Minimum wage & separation pay, as of any date" — a working second product |
| **1.5** | Top ~15 **local** minimum-wage ordinances (Seattle, NYC, SF, LA, Chicago, Denver, DC, CA-city cluster). | Phase 1 | locality key scheme populated; coverage gaps shrink | Locality accuracy where it matters most |
| **2** | **Overtime** (FLSA weekly + CA daily/7th-day, blended regular rate), **exempt classification** (salary threshold encoded, duties test → `human_judgment`), **meal/rest breaks**. | Phase 1 | real OT computation; the duties-test discretion surface | The misclassification-risk story — the highest-value, highest-liability piece, done carefully |
| **3** | National minimum-wage completeness; **WARN / mini-WARN**; pay-frequency; the amendment watcher pointed at wage boards. | all | breadth | "Every U.S. minimum wage, always current" — the maintenance moat at full stretch |

Rough sizing (relative to a leave regime ≈ one focused session): Phase 1 is the biggest lift
because it stands up the new package and fact model (~3–4 sessions); each later phase is
mostly parameter volume + one or two new evaluators on an established base.

## 8. Risks & honesty guardrails

- **Locality under-coverage is the dangerous silent failure** — the wage-and-hour analogue of
  returning "FMLA only." A San Francisco worker told the minimum wage is the California floor
  has been given a wrong, lower number. Mitigation: the `coverage.complete: false` warning must
  fire **loudly** for any known-locality worksite from day one; never let a state answer read as
  a local one. We already have this reflex.
- **The exemption duties test must never be auto-resolved.** Encode the salary threshold;
  flag the duties analysis for human judgment. Auto-answering it is the survey's "laundered
  interpretation" failure and, in this domain, direct misclassification liability. This is the
  reason exemptions are Phase 2, not Phase 1.
- **Volume & freshness is the real operating cost.** Minimum wage changes constantly across
  50 states + localities. Encoding it once is easy; keeping it current is the actual product.
  This is precisely what the amendment watcher exists for — and the argument for it is far
  stronger here than for leave. Any wage-and-hour value shown without a current-as-of date is
  a liability.
- **UPL / advice framing tightens.** "Are you paying this person legally?" reads closer to
  legal advice than a leave-eligibility estimate. Keep the decision-support disclaimer, keep
  every conclusion citation-backed, keep discretion flagged — and the manifest/verification
  gate matters even more before any real use.

## 9. Recommended first increment

A **vertical slice**, mirroring how the leave engine started: **federal + CA + WA minimum
wage, state-level, effective-dated, with tipped/tip-credit handling and loud locality coverage
warnings, plus final-pay-on-separation timing (and accrued-vacation payout) for those three
jurisdictions.** CA and WA are chosen deliberately — both index their minimum wage annually
(a genuine effective-dated test), both prohibit the tip credit (a clean contrast to the
federal $2.13 tipped wage), both have strong final-pay rules (CA's immediate-on-firing +
waiting-time penalty is the sharpest example in the country), and both are dense with local
ordinances (so the coverage-warning path is exercised immediately, not theoretically).

That slice proves the new fact model, the new entry point, the locality-coverage guard, and
the effective-dated wage lookup end-to-end — the same "make one vertical real, then widen"
move that got leave from zero to sixteen regimes — while deferring every genuinely hard or
high-liability piece (overtime math, the duties test) to a deliberate later phase.

---

*Prototype-stage planning. Any figures cited here are illustrative and, like everything in
this repo, would be web-researched and pass the verification manifest before real use.*
