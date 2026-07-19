# OpenLeave Prototype — Demo Video Script

**Target runtime:** ~6 minutes · **Narration pace:** ~150 wpm
**Audience:** design-partner prospects and investors who have seen the pitch
**Promise of the video:** every claim in the deck, demonstrated live in the working prototype.

---

## Pre-flight checklist (before recording)

```sh
cd ~/cc_projects/cc_rules_as_code
git status                                  # clean tree — apply step will modify parameters.json
.venv/bin/pytest -q                         # expect: 37 passed
.venv/bin/uvicorn openleave.api:app --port 8000 &   # checker at http://127.0.0.1:8000
export ANTHROPIC_API_KEY=...                # needed for Scene 5's live LLM call (see fallback)
export OPENLEAVE_PROPOSALS_DIR=/tmp/demo-proposals  # keep demo proposals out of the repo
```

- Terminal: dark theme, ≥18 pt font, window sized to ~100×30 so JSON is readable on screen.
- Browser: one tab open at `http://127.0.0.1:8000`, zoom ~125%.
- Have `samples/amendments/ny_saww_2027.txt` open in an editor tab for Scene 5.

**Teardown after recording:** `git checkout openleave/parameters.json && rm -rf /tmp/demo-proposals` (Scene 6 modifies the parameter file on purpose).

---

## Scene 1 — Cold open: the problem (0:00 – 0:35)

**Screen:** The eligibility checker page, cursor idle. Title card overlay: *"OpenLeave — leave law, as code."*

**Say:**
> "Thirteen states and D.C. now run their own paid family leave programs, and every one of them changes its rates every year. Today, every HR platform and insurer re-codes those same statutes by hand, into black boxes that disagree with each other. This is OpenLeave: the rules layer itself, executable, citation-backed, and maintained by an AI pipeline with a lawyer in the loop. Let me show you the whole thing in five minutes."

---

## Scene 2 — A determination, with its reasoning (0:35 – 1:40)

**Screen:** The checker. Fill the form deliberately, mouse visible:

| Field | Value |
|---|---|
| Work state | `MN` |
| Hire date | `2025-03-01` |
| Hours last 12 months | `1400` |
| Average weekly wage | `1100` |
| Employer total employees | `85` |
| Leave reason | Bonding with a new child |
| Leave start | `2026-09-01` |

Click **Check eligibility**. Slowly scroll the results.

**Say:**
> "A Minnesota employee, hired eighteen months ago, full time, at an eighty-five-person company, wants bonding leave. One click." *(click)*
> "Two laws apply, and the system found both. Federal FMLA: eligible — and look at *why*. Each condition is its own line: twelve months of tenure, twelve-fifty hours, the fifty-employee worksite test — each with the exact statutory citation. Twenty-nine U-S-C twenty-six-eleven. This isn't a verdict, it's a justification tree."
> *(scroll to MN card)* "Minnesota Paid Leave: eligible, twelve weeks, job-protected — and a weekly benefit computed to the cent from the statute's progressive formula. And down here, the interaction rules: these two leaves run concurrently, and under the 2026 DOL guidance an employer can't force paid-leave stacking. Nobody's chatbot guessed any of this."

---

## Scene 3 — Honest about "no," and about "not knowing" (1:40 – 2:30)

**Screen:** Change **Hours last 12 months** to `900`. Re-check. Point at the FMLA card.

**Say:**
> "Now the failure case. Drop the hours to nine hundred." *(click)*
> "FMLA flips to not eligible — and you can see exactly which condition failed. Two green checks, one red X: hours of service, nine hundred against the required twelve-fifty, citation attached. When you deny someone leave, this is the difference between defensible and indefensible."

**Screen:** Set hours back to `1400`, change **Leave reason** to *Own serious health condition*. Re-check. Point at the amber "needs human judgment" badge.

**Say:**
> "One more. Change the reason to the employee's own health condition — and the system does something most software won't: it says *I don't know*. Whether this is a 'serious health condition' is open-textured law — it needs medical certification and a human. So eligibility comes back null, flagged for judgment, with the governing regulation cited. We encode what compiles. We route what doesn't."

---

## Scene 4 — Time travel (2:30 – 3:20)

**Screen:** Switch to terminal. Run, one after the other (pre-typed in shell history):

```sh
curl -s -X POST http://127.0.0.1:8000/determinations -H 'Content-Type: application/json' -d '{
  "facts": {"employee": {"work_state": "NY", "hire_date": "2024-01-01",
                          "hours_last_12mo": 1800, "average_weekly_wage": 5000},
            "employer": {"total_employees": 200},
            "event": {"type": "bonding", "start": "2026-09-01"}},
  "as_of": "2025-06-01"}' | python3 -c "import json,sys; d=json.load(sys.stdin); \
  ny=[r for r in d['regimes'] if r['regime']=='ny_pfl'][0]; \
  print(d['as_of'], '→ weekly benefit:', ny['entitlement']['weekly_benefit'])"
```

Then re-run with `"as_of": "2026-09-01"` (arrow-up, edit the date).

**Expected output:** `2025-06-01 → weekly benefit: 1177.32`, then `2026-09-01 → weekly benefit: 1232.36`.

**Say:**
> "Same employee, same facts — a high earner in New York. But watch the `as_of` field: evaluated under the law as of mid-2025, the benefit cap is eleven-seventy-seven. Evaluated under 2026 law, twelve-thirty-two. Every rate in the engine is effective-dated, so you can reconstruct any past determination for an audit — or price next year's liability today. Statutes are data with dates, not constants in code."

---

## Scene 5 — The moat: an amendment becomes a reviewed diff (3:20 – 5:10)

**Screen:** Editor tab showing `samples/amendments/ny_saww_2027.txt`. Scroll it briefly.

**Say:**
> "Here's the part that makes this a business. This is a New York DOL notice: the 2027 average weekly wage, nineteen-twenty-five fourteen, effective January first. In every incumbent, a human reads this and re-codes a system. Watch what happens here instead."

**Screen:** Terminal:

```sh
.venv/bin/python -m openleave.watcher analyze samples/amendments/ny_saww_2027.txt --jurisdiction NY
```

*(Wait for output; point at each line as you narrate.)*

**Say:**
> "The pipeline hands the notice to Claude, which drafts a structured change: parameter `ny.saww`, new value nineteen-twenty-five fourteen, effective 2027, with the supporting sentence quoted verbatim. Then — this is the important part — the proposal runs against our regression suite of pinned historic determinations. Forward-dated change, history untouched: validation passes. If the model had hallucinated a key, or tried to rewrite the 2026 value, this gate fails closed. We have tests proving both."

**Screen:** Terminal:

```sh
.venv/bin/python -m openleave.watcher apply <prop-id>        # refused — not approved
.venv/bin/python -m openleave.watcher review <prop-id> --approve --reviewer "Demo Counsel"
.venv/bin/python -m openleave.watcher apply <prop-id>
git diff openleave/parameters.json
```

**Say:**
> "Try to apply it before anyone signs off — refused. Nothing the model writes ever ships on its own. An attorney approves — recorded, with name and timestamp — and *now* it applies. The diff to the encoding is one line: the 2027 rate, appended. History untouched."

**Screen:** Arrow-up to the Scene 4 curl; change `as_of` to `"2027-02-01"`. Run.

**Expected output:** `2027-02-01 → weekly benefit: 1289.84`

**Say:**
> "And the payoff: the same API call, evaluated under 2027 law — the new cap, twelve-eighty-nine eighty-four. The law changed this morning; the API already knows. That's the webhook your platform gets, instead of a compliance project."

> **Contingency (no API key on the demo machine):** skip the `analyze` call and open the committed example `proposals/prop-20260718-072a7b.json` instead — narrate the same structure (drafted change, quoted source, validation result, provenance), then continue from `review` using a fresh proposal created with the offline snippet in the repo history.

---

## Scene 6 — The contract that holds it together (5:10 – 5:40)

**Screen:** Terminal:

```sh
.venv/bin/pytest -q
```

**Expected output:** `37 passed`.

**Say:**
> "Underneath all of it, thirty-seven pinned scenarios — eligibility edges, benefit formulas, time travel, and the pipeline's refusal gates. This suite is the contract: no amendment, human or AI, can silently change what the law said yesterday."

---

## Scene 7 — Close (5:40 – 6:00)

**Screen:** Back to the checker results from Scene 2. Title card overlay: *"Stop re-coding the law. Start calling it."* with the repo URL.

**Say:**
> "Raw rule, coded rule, your facts, a cited answer — one chain, kept closed as the law moves. That's OpenLeave. The encodings are open source; the repo link is on screen. If you'd rather call an API than maintain a rules team, talk to us."

---

## Shot list summary

| # | Time | Screen | Beat |
|---|---|---|---|
| 1 | 0:00 | Checker, idle | Problem hook |
| 2 | 0:35 | Checker, MN bonding | Justification tree + $/week |
| 3 | 1:40 | Checker, 900 hrs / own health | Failed condition; human judgment |
| 4 | 2:30 | Terminal, curl ×2 | Effective-date time travel |
| 5 | 3:20 | Editor + terminal | LLM diff → gate → sign-off → apply → 2027 answer |
| 6 | 5:10 | Terminal, pytest | 37-test contract |
| 7 | 5:40 | Checker + title card | Close + CTA |
