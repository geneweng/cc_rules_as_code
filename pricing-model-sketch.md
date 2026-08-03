# OpenLeave — Pricing Model (Sketch)

*A first-draft pricing model for OpenLeave. Companion to
[`business-model-and-deployment.md`](business-model-and-deployment.md), which argues the model is
API-first, usage-based, B2B, open-core. The tier table below is also rendered as a one-page visual
sheet: [`pricing-sheet.pdf`](pricing-sheet.pdf) (source: [`pricing-sheet.html`](pricing-sheet.html)).*

> **All dollar figures below are illustrative placeholders** — anchors for a conversation, not
> validated prices. Real pricing comes from design-partner willingness-to-pay and unit economics
> (see [§7](#7-open-questions-to-validate)). Treat the *structure* as the proposal; treat the
> *numbers* the way the investor deck's ask numbers are treated — invented, replace before use.

---

## 1. Pricing principles

- **Meter on determinations; package on the buyer's unit.** A determination is the true cost and
  value driver, so it's the internal meter. But buyers forecast in their own units — platforms in
  *per-covered-employee-per-month* (PEPM), AI copilots in *per-call*, insurers in *per-claim*. Same
  meter underneath; different wrapper on top. Don't force everyone into "per API call."
- **Price scales with value, not seats.** Value is determinations × jurisdictions × currency, never
  named users. Avoid seat licenses.
- **Land and expand — two axes.** By **domain** (start with leave, add wage & hour) and by
  **jurisdiction breadth** (a few states, then national). Small first commit, room to grow.
- **Never gate the moat.** Currency and amendment alerts are *the reason to pay* — gating them
  guts the value proposition. Gate SLA, support, breadth, enterprise controls, and indemnification
  instead.
- **Predictability for the buyer.** Platforms hate variable COGS. Offer committed bundles / PEPM
  with generous included volume and transparent overage, not pure pay-as-you-go surprise bills.

## 2. The open-core line (free vs paid)

The encodings and engine are already open source — that is distribution and trust, not the product.
The line:

| | **Free (self-host)** | **Paid (hosted)** |
|---|---|---|
| The engine + encodings | ✓ (Apache/MIT-style) | ✓ |
| Run it yourself | ✓ | — (we run it) |
| **Counsel-verified content** | ✗ ("as is", web-researched) | ✓ |
| **Always current** (amendment feed) | ✗ (you track the law) | ✓ webhooks + versioned updates |
| **SLA / support** | ✗ | ✓ |
| **Indemnification** | ✗ | ✓ (paid tiers) |

The one-liner (already on the landing page): *the code is free; being current is the product.*

## 3. Tiers

| Tier | For | Metering | Verified content | SLA | Support | Illustrative price |
|---|---|---|---|---|---|---|
| **Community** | self-hosters, evaluation | — (self-run) | ✗ | — | community / GitHub | **$0** |
| **Developer** | prototyping, SMB, indie apps | metered per determination | ✓ (shipped jurisdictions) | 99.5% | email | **~$99–$499/mo** incl. volume, then per-determination overage |
| **Platform** | payroll / HRIS / EOR / leave-mgmt / copilots | **PEPM** or committed determination bundles | ✓ | 99.9% | priority email + Slack | **partner-priced** in design phase; then a PEPM (e.g. **~$0.25–$1.00 PEPM**) or annual commit |
| **Enterprise** | large platforms, insurers, regulated | committed volume + custom | ✓ + **priority verification queue** | 99.95% + credits | dedicated CSM | **custom annual** (e.g. **$50k+**), incl. VPC / data-residency, SSO/SCIM, indemnification, custom jurisdictions |

What moves *up* the tiers: SLA %, support depth, jurisdiction/domain breadth, amendment-webhook
delivery, audit-log retention, indemnification cap, deployment controls (VPC, residency, SSO/SCIM),
and a say in the verification queue.

## 4. Channel-specific packaging (same meter, different wrapper)

- **Platforms (payroll / HRIS / EOR / leave-mgmt).** They resell to employers, so **PEPM** matches
  how they price. Determinations are episodic (a few per employee per year for leave; more frequent
  for wage/OT at each payroll run) — a modest PEPM with an included-determination allowance and
  overage forecasts cleanly.
- **AI HR copilots.** They think in tool-calls. **Metered per MCP/API call**, with volume tiers;
  the pitch is "a fraction of a cent to not hallucinate leave law, with a citation." Low friction,
  self-serve start.
- **Insurers / TPAs.** They think in claims. **Per-claim / per-determination** with audit-trail
  retention as a first-class, priced feature (they need the provenance).

## 5. Add-ons (à la carte)

- **Additional jurisdictions or domains** beyond a tier's base set (e.g. + wage & hour, + a state
  cluster).
- **Priority verification** — jump the counsel-verification queue for a jurisdiction you need.
- **Self-host commercial license + support** — for buyers who must run it in their own VPC but want
  the verified content, amendment feed, and support (open-core "commercial self-managed").
- **Higher indemnification cap.**
- **White-label / co-brand** the browser checker or determinations UI.

## 6. Design-partner pricing (the on-ramp)

Ties to the [design-partner one-pager](design-partner-onepager.pdf): early partners get
**partner-priced (free-to-deep-discount) access** to the Platform tier and a say in which
jurisdictions get counsel-verified first, in exchange for real use cases, candid feedback, and a
reference once earned. This is deliberate under-pricing to buy learning and logos, not the
steady-state model.

## 7. Open questions to validate

- **PEPM vs per-determination as the headline unit** — which do the first 3 platform buyers actually
  want to be billed in? (Ask them; don't guess.)
- **Willingness to pay** for "current + verified + indemnified" vs. self-hosting the free engine —
  the whole model rests on this gap being real.
- **Determination frequency** per employee per year, by domain — sets the PEPM math.
- **Where indemnification starts** (which tier) and its cap — a legal + insurance question, not a
  pricing one alone.
- **Free-tier abuse / cannibalization** — does open source erode paid, or feed it? (Open-core
  companies land on the latter, but watch it.)

## 8. Caveats

- **The numbers are placeholders.** Structure is the deliverable; prices are anchors to test.
- **Pricing here assumes the accuracy/liability foundation from the business-model doc is in place**
  — counsel verification, E&O insurance, and a TOS with liability caps. You cannot sell
  indemnification you don't carry.
- **Validate with real design partners before publishing a price.** The fastest way to a wrong price
  is to set it in a document instead of a sales conversation.
