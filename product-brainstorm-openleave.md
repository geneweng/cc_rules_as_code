# Product Brainstorm: Rules as Code for a Narrow Domain

*July 2026. Companion to [`rules-as-code-survey.md`](rules-as-code-survey.md). Market research sources linked inline and listed at the end.*

## 1. Brainstorm: candidate products

Starting from the survey's conclusion — LLMs at the edges (translation, interface, maintenance), a verified rules engine at the core — five candidates were considered:

| # | Idea | Domain | Why / why not |
|---|------|--------|---------------|
| 1 | Policy2Code copilot for benefits agencies | SNAP/Medicaid eligibility | Real need, but public-sector sales cycles are long and the Beeck Center / PolicyEngine ecosystem is already crowding the space with grant-funded work. |
| 2 | Permit & zoning checker API | Building codes | Validated demand, but incumbents exist (Symbium, UpCodes) with years of encoding head start. |
| 3 | Legislative drafting copilot | Parliamentary counsel offices | Strategic but tiny buyer pool, multi-year procurement, needs institutional legitimacy a startup lacks. |
| 4 | Generic "LLM-to-rules" verification framework | Horizontal dev tool | Too abstract to sell; frameworks monetize poorly without a domain wedge. |
| 5 | **Executable encoding of U.S. employee leave law, sold as an API** | FMLA + state PFML + sick leave | Acute, *growing* pain; private-sector buyers with budget; no one sells the rules layer itself. **Selected.** |

**Selection rationale:** Idea 5 hits the RaC sweet spot identified in the survey — leave law is mostly *closed-texture* (thresholds, accrual rates, week counts, date arithmetic, eligibility conjunctions), which is exactly the kind of law that is safe and tractable to encode. And the domain is in regulatory churn *right now*, which is what makes a maintained encoding worth paying for.

## 2. The product: **OpenLeave** — the leave-law rules engine as a service

**One-liner:** An open-core, citation-backed, executable encoding of U.S. employee leave law (federal FMLA, all state paid family & medical leave programs, state/local paid sick leave), maintained by an LLM-assisted amendment pipeline with human legal review, and sold as an API to the companies that today each re-encode these rules by hand.

### What it does

Given a fact pattern —

```json
{
  "employee": {"work_state": "MN", "hire_date": "2025-03-01",
                "hours_last_12mo": 1400, "employer_size": 85},
  "event": {"type": "bonding", "start": "2026-09-01"}
}
```

— the API returns, for every applicable regime (FMLA, MN Paid Leave, employer policy overlay):

- **Eligibility** (boolean per regime, with the failing/passing conditions enumerated)
- **Entitlement** (weeks, benefit amount where statutory, job protection y/n)
- **Interaction rules** (which leaves run concurrently, what can/can't be stacked — per 2026 DOL guidance, employers cannot automatically require stacking of employer paid leave with state PFML ([IRIS](https://www.irisglobal.com/blog/employer-guide-fmla-paid-family-leave-compliance/)))
- **A justification tree**: every conclusion linked to the statutory/regulatory citation that produced it — the RaC "explainability" property incumbents' internal engines don't expose

### Product surfaces

1. **Open-source core** — the encodings themselves (a Catala- or OpenFisca-style ruleset per jurisdiction) plus the test suites, published openly. Open source is the trust strategy: a leave determination you can audit line-by-line against the statute is the differentiator versus every black-box incumbent, and it recruits employment lawyers as contributors/reviewers.
2. **Hosted API (the SaaS)** — versioned, SLA-backed determinations; webhook alerts when an amendment changes any determination your org has previously made ("this rule change affects 14 of your open leaves"); effective-date time travel (evaluate under the law as of any date — essential for audits and litigation).
3. **AI maintenance pipeline (the moat in operation)** — per the survey §5.1/5.3: an LLM watches state legislative feeds and agency rulemaking, drafts encoding diffs for each amendment, runs them against the regression test suite, and queues them for human legal sign-off. Provenance (which model, which source text, which reviewer) is recorded per clause. This is what makes "coverage of 50 states + 1,000 localities" a maintainable promise rather than a heroic one.
4. **LLM-facing interface** — an MCP server / tool schema so that the HR copilots now being deployed everywhere can call an authoritative engine instead of hallucinating leave law — the survey's §5.4 "LLM interface, RaC oracle" pattern, and a second sales channel (sell to the AI assistants, not just the platforms).

### Who buys it

| Segment | Why they pay | Example targets |
|---|---|---|
| Leave-management platforms | They each maintain the same 200+ statutory policies in-house ([AbsenceSoft claims exactly this](https://www.myshortlister.com/cocoon/vendor-reviews)); outsourcing the rules layer cuts their largest non-differentiating cost | Cocoon, Sparrow, Tilt, AbsenceSoft |
| HRIS / payroll / EOR platforms | Leave compliance is a checkbox they must offer in all 50 states but don't want to own | Rippling, Gusto, Deel, PEOs |
| Insurers & absence-management TPAs | Carriers administering PFML/disability need determinations at scale ([Guardian publishes PFML guidance itself](https://www.guardianlife.com/absence-management/blog/pfml-in-2026-what-your-org-needs-to-know)) | Guardian, Unum, MetLife TPA arms |
| Employment law firms & HR consultancies | White-label calculators, audit tooling | Littler, Jackson Lewis tech arms |
| Large self-administering employers | Direct API use inside internal HR systems | 5k+ employee multi-state companies |

## 3. Market research: does the problem justify the product?

### 3.1 The regulatory complexity is real and compounding

- **Thirteen states plus D.C.** now have mandatory paid family & medical leave programs. **Minnesota and Delaware went live January 2026**; Maryland and Virginia requirements land in 2027–28 ([Epstein Becker Green](https://www.ebglaw.com/insights/publications/2026-family-and-medical-leave-law-updates-what-employers-in-seven-states-need-to-know), [OnPay](https://onpay.com/insights/paid-family-leave-by-state/), [Vicente LLP](https://vicentellp.com/insights/employer-compliance-guide-state-family-medical-leave-laws-effective-2026/)).
- Every program differs on eligibility, benefit weeks, wage-replacement rates, funding, and FMLA interaction; benefit parameters also change *annually* within each state ([HR Dive](https://www.hrdive.com/news/state-paid-family-leave-benefit-changes-in-2026/809625/), [Paycor](https://www.paycor.com/resource-center/articles/states-laws-for-paid-family-leave/)).
- A single remote employee in a state triggers that state's program — so with distributed workforces, effectively *every* mid-size employer is a multi-state employer ([IRIS](https://www.irisglobal.com/blog/employer-guide-fmla-paid-family-leave-compliance/)).
- 2026 federal DOL guidance on FMLA↔PFML interaction added a new interpretation layer that every vendor had to re-implement simultaneously — a natural experiment in the duplicated-encoding waste OpenLeave eliminates.

### 3.2 The market has money in it

- The absence & leave management software market is valued around **$0.85–1.4B (2024–26) growing at ~9.5% CAGR**, with regulatory compliance and increasing complexity explicitly cited as top growth drivers ([Verified Market Research](https://www.verifiedmarketresearch.com/product/absence-leave-management-software-market/), [Global Growth Insights](https://www.globalgrowthinsights.com/market-reports/absence-leave-management-software-market-104242); broader absence-management definitions run to $18B+ ([Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/absence-management-software-market))).
- A venture-funded cohort (Cocoon, Sparrow, Tilt) plus an established vertical player (AbsenceSoft) all compete in leave administration — evidence buyers pay for this problem ([Aidora's 2026 category roundup](https://getaidora.com/blog/best-leave-management-software-2026)).

### 3.3 The specific gap: everyone builds the rules layer; no one sells it

- Incumbents advertise the encoding as internal capability: Cocoon "codifies FMLA and ever-changing state leave laws" ([cocoon.com](https://www.cocoon.com/)); AbsenceSoft manages "200+ statutory policies." Each vendor duplicates this work, each opaquely — the private-sector mirror of the interpretation-drift problem RaC was invented for.
- Adjacent compliance platforms stop at *documents*, not *determinations*: SixFifty generates compliant leave **policy text** and Mosey tracks obligations across "all US states and 1,000+ localities," but neither exposes an executable eligibility/entitlement engine ([SixFifty](https://www.sixfifty.com/blog/paid-leave-policy-creator/), [Mosey](https://mosey.com/)).
- Searches for a leave-law rules engine API / compliance-as-code vendor in this domain return no direct competitor — the closest analogues are in other verticals (PolicyEngine in tax/benefits, Symbium in permitting), which also serve as proof the "open encoding + hosted API" model works.

### 3.4 Why now (the AI angle)

Two survey findings make this product newly feasible and newly necessary:

1. **Feasible:** LLM-assisted encoding with human review collapses the cost of building and — more importantly — *maintaining* 60+ jurisdiction encodings (Beeck Center's Policy2Code result: LLMs can draft policy-to-code translations reliably when paired with RAG over authoritative sources and human oversight ([Beeck Center](https://beeckcenter.georgetown.edu/report/ai-powered-rules-as-code-experiments-with-public-benefits-policy/))). Maintenance cost was precisely why no one built this as a standalone business before.
2. **Necessary:** HR copilots and chatbots are being deployed across the industry and will confidently answer leave questions wrong. An authoritative, citation-backed oracle they can call is the emerging architecture pattern (survey §5.4) — and regulators are simultaneously scrutinizing AI in employment decisions ([Lexology 2026 overview](https://www.lexology.com/library/detail.aspx?g=bb0a51a8-4a1f-4592-83a2-3de69f22d075)), which favors deterministic, auditable determinations over model output.

### 3.5 Honest risks

- **Build-vs-buy resistance:** incumbents may view their rules encoding as differentiating IP rather than commodity cost. Mitigation: start with the buyers for whom it's clearly a cost center (payroll/HRIS platforms, EORs, law-firm tech arms), and let the open-source core create gravity.
- **Liability:** a wrong determination has legal consequences. Mitigation: position as decision *support* with citations (the customer's counsel remains the decision-maker), contractually cap reliance, and lead with the justification tree — the product is *more* defensible than incumbents' black boxes, not less.
- **Discretionary edges:** "serious health condition," ADA-interactive-process questions, and undue-hardship judgments are open-textured. Scope discipline: encode the closed-texture core (eligibility, entitlement, accrual, interaction, deadlines), and have the API explicitly return `requires_human_judgment` with the relevant factors for the rest — the survey's "flag and route discretion, don't compile it" principle as a product feature.
- **Open-source free-riding:** competitors could take the encodings. Mitigation: the value is the *maintenance stream*, SLA, effective-date history, and alert infrastructure — the same open-core logic as OpenFisca/PolicyEngine, and standard for infra companies.

## 4. MVP and validation plan

**MVP (a quarter of focused work):**
1. Encode **FMLA + 3 states** — California (largest), Minnesota (newest, cleanest statute), New York (most idiosyncratic) — in a declarative ruleset with per-clause citations.
2. Build the regression test suite from agency-published scenarios and DOL opinion letters (also the eval set for the LLM pipeline).
3. Stand up the LLM amendment-watcher on those four jurisdictions' legislative feeds; measure human-review burden per amendment — this number is the business model.
4. Ship the hosted API + a free public eligibility checker (top-of-funnel and encoding stress test).

**Validation gates before scaling to 50 states:**
- 10 design-partner interviews across the buyer table in §2 — the kill/scale question: *"What does maintaining leave rules cost you per year, and would you replace it with an API?"*
- One paid design partner from the payroll/EOR segment (they have the clearest cost-center motivation).
- LLM pipeline metric: >80% of amendment diffs accepted with only minor human edits (mirroring the Policy2Code finding); if human review costs more than manual encoding, the maintenance moat thesis fails and the business reverts to a consultancy.

## 5. Verdict

The research validates the core thesis: leave law is a fast-compounding compliance burden ($1B+ software category growing ~10%/yr on the back of 13-states-and-counting regulatory divergence), every vendor in the category duplicates an opaque internal encoding of the same rules, and no one sells the rules layer as a product. That is a textbook Rules-as-Code arbitrage. What changed to make it a viable *business* in 2026 is AI on both sides of the ledger: LLM-assisted maintenance makes 60+ jurisdictions affordable to keep current, and the spread of HR copilots creates a new class of customer that structurally needs a deterministic, citation-backed oracle. Recommended next step: run the MVP with the three-state scope and let the design-partner interviews decide scale-up.

## Sources

- [OnPay — States with paid family leave 2026](https://onpay.com/insights/paid-family-leave-by-state/)
- [Epstein Becker Green — 2026 family and medical leave law updates in seven states](https://www.ebglaw.com/insights/publications/2026-family-and-medical-leave-law-updates-what-employers-in-seven-states-need-to-know)
- [Vicente LLP — Employer compliance guide to state FML laws effective 2026](https://vicentellp.com/insights/employer-compliance-guide-state-family-medical-leave-laws-effective-2026/)
- [HR Dive — State paid family leave benefit changes in 2026](https://www.hrdive.com/news/state-paid-family-leave-benefit-changes-in-2026/809625/)
- [Guardian — PFML in 2026: what employers need to know](https://www.guardianlife.com/absence-management/blog/pfml-in-2026-what-your-org-needs-to-know)
- [IRIS — FMLA & paid leave employer compliance guide](https://www.irisglobal.com/blog/employer-guide-fmla-paid-family-leave-compliance/)
- [Paycor — Paid family leave by state](https://www.paycor.com/resource-center/articles/states-laws-for-paid-family-leave/)
- [Verified Market Research — Absence and leave management software market](https://www.verifiedmarketresearch.com/product/absence-leave-management-software-market/)
- [Global Growth Insights — Absence & leave management software market 2026–2035](https://www.globalgrowthinsights.com/market-reports/absence-leave-management-software-market-104242)
- [Mordor Intelligence — Absence management software market](https://www.mordorintelligence.com/industry-reports/absence-management-software-market)
- [Aidora — Best leave management software 2026](https://getaidora.com/blog/best-leave-management-software-2026)
- [Cocoon](https://www.cocoon.com/) · [Shortlister — Cocoon reviews](https://www.myshortlister.com/cocoon/vendor-reviews) · [CB Insights — Sparrow competitors](https://www.cbinsights.com/company/sparrow-2/alternatives-competitors)
- [SixFifty — Paid leave policy creator](https://www.sixfifty.com/blog/paid-leave-policy-creator/) · [SixFifty — HR compliance software for multi-state employers](https://www.sixfifty.com/blog/hr-compliance-software-for-multi-state-employers/)
- [Mosey — corporate compliance platform](https://mosey.com/) · [Mosey — multi-state employment guide](https://mosey.com/blog/multi-state-employment-guide/)
- [Experian — AI, employee data & paid leave: building a compliance engine for 2026](https://www.experian.com/blogs/employer-services/ai-employee-data-paid-leave-building-a-cross%E2%80%91functional-compliance-engine-for-2026/)
- [Lexology — 2026 overview of AI use in employment decisions](https://www.lexology.com/library/detail.aspx?g=bb0a51a8-4a1f-4592-83a2-3de69f22d075)
- [Beeck Center — AI-powered Rules as Code experiments](https://beeckcenter.georgetown.edu/report/ai-powered-rules-as-code-experiments-with-public-benefits-policy/)
