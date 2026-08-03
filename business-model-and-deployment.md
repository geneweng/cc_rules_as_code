# OpenLeave — Business Model & Deployment

*Strategy notes for turning the OpenLeave prototype into a business: what to sell, how to price it,
and how to deploy it. Companion to [`product-brainstorm-openleave.md`](product-brainstorm-openleave.md)
and [`ARCHITECTURE.md`](ARCHITECTURE.md).*

> **Framing.** For OpenLeave, hosting / auth / payments are the easy 10%. The business is really a
> *legal-accuracy* business wearing a software costume — and that reframing drives most of what
> follows. Take the technical plumbing as a solved problem; spend your judgment on accuracy,
> liability, and distribution.

---

## 1. Business model — infrastructure, not an app

OpenLeave is **infrastructure, not an application**: a rules engine with an API and an MCP surface.
The landing-page thesis already captures it — *the encodings are open; what you pay for is the
guarantee.* So the model that fits is:

**API-first, usage-based, B2B — sold to platforms, distributed to AI, on an open-core license.**

- **Who buys.** Payroll / HRIS / EOR platforms, leave-management vendors, insurers / TPAs, and AI
  HR copilots — they *embed* your determinations as a line item. You are the layer *beneath* the HR
  app, not another HR app. The direct-to-HR-team market is crowded and weak; the "rules layer nobody
  wants to maintain" is empty and defensible.
- **Why not seat-based SaaS.** Value scales with *determinations and jurisdictions*, not named
  users. A per-seat model misprices infrastructure.
- **Pricing shapes.** Metered per determination, or per-covered-employee-per-month, with tiers and
  volume commits. Usage-based aligns price with value and is how modern API infrastructure sells.
- **Open-core is a genuine advantage here.** The encodings + engine are already open source. Lean
  into it: open source is *distribution and trust* (buyers audit every line against the statute);
  the commercial product is the **hosted, SLA-backed, counsel-verified, always-current** service +
  the amendment feed. "Audit the code free; pay for the maintained guarantee" is credible and
  differentiated.
- **The AI channel is real and already built.** The MCP server is a distribution wedge — HR copilots
  can call the verified oracle instead of hallucinating leave law. An emerging, low-friction
  go-to-market most competitors lack.

## 2. What outranks all of it: accuracy + liability

This makes or breaks the company, and it is not technical.

- **Counsel verification is a business prerequisite, not a quality nicety.** You sell legal
  determinations. Every figure in the repo is currently "unverified by counsel" — fine for a
  prototype, fatal for a product. You need employment-law counsel in the loop and a *lawyer-verified,
  versioned* content pipeline. The effective-dating, provenance, and the drift-guarded verification
  manifest are already the scaffolding — a real head start.
- **Liability & UPL (unauthorized practice of law).** Keep "decision support, not legal advice" in
  every response (already done, programmatically). Add a **TOS with liability caps**, an
  **indemnification structure**, and **E&O / professional-liability insurance**. Shape this with
  counsel before the first paying customer.
- **The moat is being correct and current, with an audit trail** — not the code. "Law as of any
  date" + provenance is a *sales asset* to compliance buyers who must prove why a determination was
  made on a given date.

Treat this as the #1 workstream. Everything below is comparatively solved-problem plumbing.

## 3. Hosting / deployment

The core determination is **stateless, CPU-only, fast, with no external calls** (pure Python +
in-memory parameters). It is trivially scalable, cache-friendly, and runs almost anywhere. See the
one-page reference topology: [`deployment-architecture.pdf`](deployment-architecture.pdf) (source:
[`deployment-architecture.html`](deployment-architecture.html)).

| Stage | Recommendation | Why |
|---|---|---|
| **Pre-revenue / design partners** | **Render** or **Fly.io** | Deploy the FastAPI app in an afternoon; Fly gives easy multi-region for low global latency |
| **Scaling / enterprise** | **Google Cloud Run** (or **AWS Fargate / Lambda**) | Containerized (matches the repo), **scales to zero**, pay-per-use, enterprise-credible for SOC 2 / VPC / BAAs |
| **Marketing site + browser checker** | **Vercel / Netlify / GitHub Pages** | Static; keep it separate from the API |

**Pick:** start on **Render/Fly** to move fast; plan to land on **Cloud Run or AWS** once selling to
platforms that demand enterprise compliance and data-residency controls. Don't over-engineer
Kubernetes early — a stateless container on Cloud Run / Fargate autoscaling is more than enough.

## 4. User management / auth

Two auth surfaces:

- **Machine-to-machine (the platforms):** **API keys** with scopes + rotation, fronted by an **API
  gateway** (Cloud / AWS API Gateway, or Kong) that also does rate limiting and usage metering.
- **Human dashboard / SSO:** a managed IdP — **WorkOS** (purpose-built for B2B enterprise
  SSO / SAML / SCIM, which enterprise buyers *will* demand), or **Auth0 / Clerk** for a faster
  generic start. Don't roll your own auth.

## 5. Payments / billing

Because the model is usage-based:

- **Start with Stripe** (subscriptions + metered/usage billing) — fastest to revenue.
- **Graduate to Orb, Metronome, or Lago** (open source) once per-determination pricing, commits,
  and overages get complex — these are built specifically to meter API usage.

## 6. Cybersecurity & compliance

The design move that turns the biggest liability into a feature:

- **Minimize / eliminate stored PII.** Determinations can be computed **statelessly and
  ephemerally** — wages, hire dates, and health-adjacent leave reasons need not be persisted. Not
  storing it slashes both breach surface and compliance scope. Log determinations by
  hashed/tokenized reference, not raw PII. Architect for this now; it is a real competitive and
  security advantage.
- **SOC 2 Type II is table stakes** for selling to platforms/enterprises. Get there fast with
  **Vanta / Drata / Secureframe**.
- **Watch the data types.** Leave reasons brush against health information. You are likely not a
  HIPAA covered entity / business associate, but confirm with counsel; assume **CCPA / CPRA** (and
  **GDPR** if EU) apply. Baseline: DPAs with customers, encryption in transit + at rest, a secrets
  manager, least-privilege IAM, dependency/vuln scanning, WAF, and audit logging.
- **The disclaimer-in-every-response pattern is a liability control** — keep it programmatic, not
  just in the TOS.

## 7. Scalability

- **Technically a non-issue.** Deterministic, stateless determinations are horizontally scalable and
  **cacheable** (same facts + date + engine version → same result → CDN/edge-cacheable). Autoscaling
  absorbs spikes.
- **The real scaling challenge is content, not compute** — keeping encodings current and *verified*
  across a growing set of jurisdictions and domains. That is a lawyer-in-the-loop authoring pipeline;
  the amendment watcher + manifest are the start of it. Budget effort there, not on infra.

---

## Recommended starting stack

| Concern | Start with | Scale to |
|---|---|---|
| Compute | Render / Fly.io | Google Cloud Run or AWS Fargate / Lambda |
| Auth (M2M) | API keys + gateway | API Gateway usage plans + WorkOS for SSO |
| Billing | Stripe (metered) | Orb / Metronome |
| Security / compliance | Vanta / Drata → SOC 2 | + DPAs, pen tests, E&O insurance |
| Data | Stateless / no-PII by design | Tokenized audit log (Postgres) |
| Distribution | Public API + MCP server | Platform partnerships, marketplace listings |

## What to do first (order matters)

1. **Engage employment-law counsel** and verify one or two jurisdictions end to end — turns the
   prototype into something sellable and de-risks liability.
2. **Land 1–2 design partners** (a small payroll / EOR / leave platform, or an AI HR copilot via
   MCP) — validate the embed model before building billing infrastructure. The pitch is in
   [`design-partner-onepager.pdf`](design-partner-onepager.pdf) (source:
   [`design-partner-onepager.html`](design-partner-onepager.html)).
3. **Ship a thin hosted API** on Render / Fly with API keys + Stripe metered billing.
4. **Start SOC 2** (Vanta) and stand up E&O insurance in parallel.
5. Everything else (Cloud Run migration, WorkOS SSO, Orb) is a "when a real customer asks" upgrade.

---

## Caveats

- This is an opinionated engineering / go-to-market view. The **legal-liability, UPL, and
  compliance-scope questions need actual professionals** — employment counsel and a security auditor.
  Do not treat this document as the final word there.
- OpenLeave today is a strong, honest **prototype**. The gap to "product" is mostly the
  counsel-verification and the compliance / liability wrapper — not the code.
