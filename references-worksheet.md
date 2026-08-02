# OpenLeave — Statutory Verification Worksheet

*Every value in this repo is web-researched and UNVERIFIED by counsel. `verified: false` on a jurisdiction means no employment lawyer has signed off yet. This manifest is the worksheet for that review, not evidence it has happened.*

**How to use:** A reviewer works one jurisdiction at a time: open the source pages, check each parameter's value(s) and effective date(s) against the agency's published figures and the cited statute, check each structural claim, then set verified/verified_by/verified_on. Run `python -m openleave.references check` to confirm the manifest still covers every encoded parameter.

**Progress:** 0/15 jurisdictions verified; 105/105 parameters documented.

## CA — California Paid Family Leave (PFL) and CFRA

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** Cal. Unemp. Ins. Code §§ 3300-3306 (PFL); Cal. Gov. Code § 12945.2 (CFRA)
- **Sources:** https://edd.ca.gov/en/disability/paid-family-leave/, https://calcivilrights.ca.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `ca.saww` | State average weekly wage used in the PFL benefit tiers ($) | 1642.0 [2025-01-01]; 1704.0 [2026-01-01] |
| ☐ | `ca.pfl.weeks` | PFL benefit duration (weeks) | 8 [2025-01-01] |
| ☐ | `ca.pfl.max_weekly_benefit` | PFL maximum weekly benefit ($) | 1681.0 [2025-01-01] |
| ☐ | `ca.pfl.low_earner_rate` | Wage-replacement rate below the SAWW breakpoint (fraction) | 0.9 [2025-01-01] |
| ☐ | `ca.pfl.standard_rate` | Wage-replacement rate above the SAWW breakpoint (fraction) | 0.7 [2025-01-01] |
| ☐ | `ca.pfl.min_base_period_earnings` | Minimum base-period earnings to qualify ($) | 300.0 [2025-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ PFL provides wage replacement only; CFRA supplies the job protection (5+ employees).
- ☐ The 2025 rate change raised the low-earner rate to 90% and standard rate to 70%.

## CO — Colorado Family and Medical Leave Insurance (FAMLI)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** C.R.S. Title 8, Article 13.3
- **Sources:** https://famli.colorado.gov/, https://famli.colorado.gov/individuals-and-families/how-famli-works

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `co.saww` | State average weekly wage ($) | 1534.94 [2026-01-01]; 1608.91 [2026-07-01] |
| ☐ | `co.max_weekly_benefit` | Maximum weekly benefit, = 90% of SAWW ($) | 1381.45 [2026-01-01]; 1448.02 [2026-07-01] |
| ☐ | `co.min_base_period_earnings` | Minimum wages earned in Colorado to qualify ($) | 2500.0 [2026-01-01] |
| ☐ | `co.weeks` | Base leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `co.pregnancy_complication_weeks` | Additional weeks for pregnancy/childbirth complications | 4 [2026-01-01] |
| ☐ | `co.combined.weeks` | Maximum combined weeks including the pregnancy addition | 16 [2026-01-01] |
| ☐ | `co.job_protection.min_service_days` | Days of service for job protection | 180 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Eligibility is a $-earned floor across any employer, not an hours or tenure test.
- ☐ Job protection has NO employer-size threshold (unlike FMLA).
- ☐ Max weekly benefit changed mid-year on 2026-07-01 ($1,381.45 -> $1,448.02).

## CT — Connecticut Paid Leave, with CT FMLA job protection

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** Conn. Gen. Stat. § 31-49e et seq. (paid leave); § 31-51kk et seq. (CT FMLA)
- **Sources:** https://ctpaidleave.org/, https://www.ctdol.state.ct.us/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `ct.minimum_wage` | State minimum wage; the whole benefit schedule is pegged to it ($/hr) | 16.35 [2025-01-01]; 16.94 [2026-01-01] |
| ☐ | `ct.pfml.cap_hours` | Cap as a multiple of the hourly minimum wage (hours) | 60 [2025-01-01] |
| ☐ | `ct.pfml.tier_break_hours` | Tier breakpoint as a multiple of the hourly minimum wage (hours) | 40 [2025-01-01] |
| ☐ | `ct.pfml.tier1_rate` | Wage-replacement rate below the breakpoint (fraction) | 0.95 [2025-01-01] |
| ☐ | `ct.pfml.tier2_rate` | Wage-replacement rate above the breakpoint (fraction) | 0.6 [2025-01-01] |
| ☐ | `ct.pfml.min_high_quarter_earnings` | Highest-quarter base-period earnings to qualify ($) | 2325.0 [2025-01-01] |
| ☐ | `ct.weeks` | Base leave duration (weeks) | 12 [2025-01-01] |
| ☐ | `ct.pregnancy_extra_weeks` | Additional weeks for pregnancy incapacity | 2 [2025-01-01] |
| ☐ | `ct.combined.weeks` | Maximum combined weeks | 14 [2025-01-01] |
| ☐ | `ct.fmla.min_tenure_months` | Months of service for CT FMLA job protection | 3 [2025-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Cap = 60x and breakpoint = 40x the hourly minimum wage; both move when the wage moves.
- ☐ The 2026-01-01 minimum-wage rise ($16.35 -> $16.94) raised the cap $981.00 -> $1,016.40.
- ☐ Job protection is the SEPARATE CT FMLA, which reaches employers with a single employee.

## DC — DC Paid Family Leave, with DC FMLA job protection

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** D.C. Code § 32-541.01 et seq. (paid leave); § 32-501 et seq. (DC FMLA)
- **Sources:** https://dcpaidfamilyleave.dc.gov/, https://does.dc.gov/page/dc-paid-family-leave

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `dc.minimum_wage` | DC minimum wage; the benefit threshold is pegged to it ($/hr) | 17.95 [2025-07-01]; 18.4 [2026-07-01] |
| ☐ | `dc.pfl.max_weekly_benefit` | Maximum weekly benefit set by DOES ($) | 1190.0 [2025-09-28] |
| ☐ | `dc.pfl.threshold_multiple` | Tier-1 ceiling as a multiple of (min wage x 40 hrs) | 1.5 [2025-09-28] |
| ☐ | `dc.pfl.tier1_rate` | Wage-replacement rate below the threshold (fraction) | 0.9 [2025-09-28] |
| ☐ | `dc.pfl.tier2_rate` | Wage-replacement rate above the threshold (fraction) | 0.5 [2025-09-28] |
| ☐ | `dc.weeks` | Leave duration per type (parental/family/medical, weeks) | 12 [2025-09-28] |
| ☐ | `dc.pfl.prenatal_weeks` | Additional prenatal leave (weeks) | 2 [2025-09-28] |
| ☐ | `dc.combined.weeks` | Maximum combined weeks including prenatal | 14 [2025-09-28] |
| ☐ | `dc.fmla.min_employees` | Employer-size threshold for DC FMLA job protection | 20 [2025-09-28] |
| ☐ | `dc.fmla.min_tenure_months` | Months of service for DC FMLA job protection | 12 [2025-09-28] |
| ☐ | `dc.fmla.min_hours` | Hours in prior year for DC FMLA job protection | 1000 [2025-09-28] |

**Structural claims to verify (not single numbers):**

- ☐ DC PFL has NO earnings, hours, or tenure minimum for benefits.
- ☐ Job protection is the NARROWER DC FMLA (20+ employees), so DC pays more workers than it protects.
- ☐ DC minimum wage rises $17.95 -> $18.40 on 2026-07-01, widening the 90% band.
- ☐ Max weekly benefit is $1,190 for leave dates on or after 2025-09-28.

## DE — Delaware Paid Leave (Healthy Delaware Families Act)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** 19 Del. C. ch. 37
- **Sources:** https://labor.delaware.gov/delaware-paid-leave, https://laborfiles.delaware.gov/main/pfl/Employer_and_TPAs_Guide_to_DPL.pdf

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `de.wage_replacement_rate` | Wage-replacement rate (fraction) | 0.8 [2026-01-01] |
| ☐ | `de.max_weekly_benefit` | Maximum weekly benefit, 2026-2027 ($) | 900.0 [2026-01-01] |
| ☐ | `de.min_weekly_benefit` | Minimum weekly benefit, 2026-2027 ($) | 100.0 [2026-01-01] |
| ☐ | `de.parental.weeks` | Parental (bonding) leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `de.medical_family.weeks` | Medical/family leave duration per 24 months (weeks) | 6 [2026-01-01] |
| ☐ | `de.combined.weeks` | Maximum combined weeks per application year | 12 [2026-01-01] |
| ☐ | `de.parental.min_employees` | Employer size to owe parental leave | 10 [2026-01-01] |
| ☐ | `de.medical_family.min_employees` | Employer size to owe medical/family leave | 25 [2026-01-01] |
| ☐ | `de.eligibility.min_months` | Months of service to qualify | 12 [2026-01-01] |
| ☐ | `de.eligibility.min_hours` | Hours in prior 12 months to qualify | 1250 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Coverage depends on employer size AND reason: <10 not covered, 10-24 parental-only, 25+ all reasons.
- ☐ Benefits began 2026-01-01; max $900 / min $100 is fixed for 2026 and 2027.
- ☐ Delaware provides job restoration to eligible employees.

## FMLA — Federal Family and Medical Leave Act

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** 29 U.S.C. §§ 2601-2654; 29 C.F.R. Part 825
- **Sources:** https://www.dol.gov/agencies/whd/fmla

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `fmla.weeks` | Leave entitlement in a 12-month period (weeks) | 12 [1993-08-05] |
| ☐ | `fmla.min_hours` | Hours worked in prior 12 months to qualify | 1250 [1993-08-05] |
| ☐ | `fmla.min_worksite_headcount` | Employees within 75 miles for employer coverage | 50 [1993-08-05] |

**Structural claims to verify (not single numbers):**

- ☐ Employee must have worked 12 months for the employer (need not be consecutive).
- ☐ Leave is unpaid and job-protected; runs concurrently with state paid leave for the same reason.

## MA — Massachusetts Paid Family and Medical Leave (PFML)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** M.G.L. c. 175M
- **Sources:** https://www.mass.gov/orgs/department-of-family-and-medical-leave

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `ma.saww` | State average weekly wage ($) | 1922.48 [2026-01-01] |
| ☐ | `ma.max_weekly_benefit` | Maximum weekly benefit, = 64% of SAWW ($) | 1230.39 [2026-01-01] |
| ☐ | `ma.min_base_period_earnings` | Minimum base-period earnings to qualify ($) | 6300.0 [2026-01-01] |
| ☐ | `ma.family.weeks` | Family leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `ma.medical.weeks` | Medical leave duration (weeks) | 20 [2026-01-01] |
| ☐ | `ma.combined.weeks` | Maximum combined weeks per benefit year | 26 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Two-tier benefit (80% then 50%) capped at 64% of SAWW.
- ☐ Eligibility includes a self-referential 30x-weekly-benefit earnings test.
- ☐ Job protection is built into c. 175M itself; no companion statute needed.
- ☐ 7-day unpaid waiting period at the start of leave.

## MD — Maryland FAMLI (Time to Care Act) - NOT YET IN FORCE

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** Md. Code, Lab. & Empl. § 8.3-101 et seq.
- **Sources:** https://paidleave.maryland.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `md.eligibility.min_hours` | Hours worked in Maryland in prior 4 quarters to qualify | 680 [2028-01-03] |
| ☐ | `md.weeks` | Base leave duration (weeks) | 12 [2028-01-03] |
| ☐ | `md.extended.weeks` | Maximum weeks when combining bonding + own serious health condition | 24 [2028-01-03] |
| ☐ | `md.pfl.max_weekly_benefit` | Maximum weekly benefit ($) | 1000.0 [2028-01-03] |
| ☐ | `md.pfl.min_weekly_benefit` | Minimum weekly benefit ($) | 50.0 [2028-01-03] |
| ☐ | `md.job_protection.min_employees` | Employer-size threshold for job restoration | 15 [2028-01-03] |

**Structural claims to verify (not single numbers):**

- ☐ Benefits are NOT payable until 2028-01-03 (HB 102, 2025); contributions begin 2027-01-01.
- ☐ The launch-year SAWW is set annually by the Secretary of Labor and is not yet published.
- ☐ This encoding returns weekly_benefit=None on/after the in-force date rather than a fabricated figure.

## ME — Maine Paid Family and Medical Leave (PFML)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** 26 M.R.S. ch. 7, subch. 6-A (§ 850-A et seq.)
- **Sources:** https://www.maine.gov/paidleave/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `me.saww` | State average weekly wage; also the benefit cap ($) | 1198.0 [2026-05-01]; 1249.12 [2026-07-01] |
| ☐ | `me.tier1_rate` | Wage-replacement rate below the breakpoint (fraction) | 0.9 [2026-05-01] |
| ☐ | `me.tier2_rate` | Wage-replacement rate above the breakpoint (fraction) | 0.66 [2026-05-01] |
| ☐ | `me.tier_threshold_fraction` | Breakpoint as a fraction of the SAWW | 0.5 [2026-05-01] |
| ☐ | `me.eligibility_saww_multiple` | Base-period earnings floor as a multiple of the SAWW | 6 [2026-05-01] |
| ☐ | `me.weeks` | Leave duration (weeks) | 12 [2026-05-01] |
| ☐ | `me.combined.weeks` | Maximum combined weeks per benefit year | 16 [2026-05-01] |
| ☐ | `me.job_protection.min_service_days` | Days of service for job protection | 120 [2026-05-01] |

**Structural claims to verify (not single numbers):**

- ☐ Second tier is 66% (not the usual 50%), capped at 100% of the SAWW.
- ☐ Benefits began 2026-05-01; the SAWW/cap rose $1,198 -> $1,249.12 on 2026-07-01.
- ☐ Eligibility is 6x the SAWW earned in the base period.

## MN — Minnesota Paid Leave

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** Minn. Stat. ch. 268B
- **Sources:** https://paidleave.mn.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `mn.saww` | State average weekly wage ($) | 1423.0 [2026-01-01] |
| ☐ | `mn.wage_threshold_fraction_of_saaw` | Earnings floor as a fraction of the SAWW | 0.053 [2026-01-01] |
| ☐ | `mn.family.weeks` | Family leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `mn.medical.weeks` | Medical leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `mn.combined.weeks` | Maximum combined weeks per benefit year | 20 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Benefits begin 2026-01-01; paid and job-protected after 90 days.
- ☐ Note the parameter key spelling 'saaw' is a typo carried in the data; verify it maps to the SAWW.

## NJ — New Jersey Family Leave Insurance (FLI), with NJFLA job protection

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** N.J.S.A. 43:21-25 et seq. (FLI); N.J.S.A. 34:11B-1 et seq. (NJFLA)
- **Sources:** https://www.nj.gov/labor/myleavebenefits/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `nj.fli.weeks` | FLI benefit duration (weeks) | 12 [2026-01-01] |
| ☐ | `nj.fli.wage_replacement_rate` | Wage-replacement rate (fraction) | 0.85 [2026-01-01] |
| ☐ | `nj.fli.max_weekly_benefit` | FLI maximum weekly benefit ($) | 1119.0 [2026-01-01] |
| ☐ | `nj.fli.min_base_year_earnings` | Base-year earnings to qualify ($) | 15500.0 [2026-01-01] |
| ☐ | `nj.fli.base_week_earnings` | Weekly earnings that count as a 'base week' ($) | 310.0 [2026-01-01] |
| ☐ | `nj.njfla.min_employees` | Employer size for NJFLA job protection | 30 [2026-01-01] |
| ☐ | `nj.njfla.min_hours` | Hours in prior 12 months for NJFLA job protection | 1000 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ FLI pays 85% but historically carried no job protection of its own.
- ☐ A3451 adds FLI reinstatement from 2026-07-17; before that, protection is NJFLA-only.
- ☐ NJFLA thresholds (30 employees, 1,000 hours) are strictly easier than FMLA's, so FMLA is never NJ FLI's sole fallback protector.
- ☐ Low earners meeting only the 20-base-week alternative return eligible=null (needs week-level data).

## NY — New York Paid Family Leave (PFL)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** N.Y. Workers' Comp. Law art. 9
- **Sources:** https://paidfamilyleave.ny.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `ny.saww` | State average weekly wage ($) | 1757.19 [2025-01-01]; 1839.34 [2026-01-01] |
| ☐ | `ny.pfl.weeks` | PFL benefit duration (weeks) | 12 [2021-01-01] |
| ☐ | `ny.pfl.wage_replacement_rate` | Wage-replacement rate (fraction) | 0.67 [2021-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Benefit is 67% of the employee's average weekly wage, capped at 67% of the SAWW.
- ☐ PFL is job-protected.

## OR — Paid Leave Oregon

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** ORS ch. 657B
- **Sources:** https://paidleave.oregon.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `or.saww` | State average weekly wage ($) | 1363.8 [2026-01-01]; 1410.13 [2026-06-28] |
| ☐ | `or.max_weekly_benefit` | Maximum weekly benefit, = 120% of SAWW ($) | 1636.56 [2026-01-01]; 1692.16 [2026-06-28] |
| ☐ | `or.min_weekly_benefit` | Minimum weekly benefit, = 5% of SAWW ($) | 68.19 [2026-01-01]; 70.51 [2026-06-28] |
| ☐ | `or.min_base_year_earnings` | Base-year earnings to qualify ($) | 1000.0 [2026-01-01] |
| ☐ | `or.weeks` | Leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `or.pregnancy_extra_weeks` | Additional weeks for pregnancy-related conditions | 2 [2026-01-01] |
| ☐ | `or.combined.weeks` | Maximum combined weeks per benefit year | 14 [2026-01-01] |
| ☐ | `or.job_protection.min_service_days` | Days of service for job restoration | 90 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Low earners (<= 65% of SAWW) are replaced at 100% of wages, then 50% above.
- ☐ Job restoration applies at EVERY employer size (the 25-employee line is about premiums).
- ☐ Benefit-year figures update ~late June; $1,692.16 cap applies from 2026-06-28.

## RI — Rhode Island Temporary Disability (TDI) + Temporary Caregiver (TCI) Insurance

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** R.I. Gen. Laws ch. 28-41
- **Sources:** https://dlt.ri.gov/individuals/temporary-disability-caregiver-insurance

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `ri.benefit_rate_of_high_quarter` | Weekly benefit as a fraction of highest base-period quarter | 0.0462 [2026-07-01] |
| ☐ | `ri.aww_cap_fraction` | Benefit ceiling as a fraction of the average weekly wage | 0.85 [2026-07-01] |
| ☐ | `ri.max_weekly_benefit` | Maximum weekly benefit before dependency allowance ($) | 1150.0 [2026-07-01] |
| ☐ | `ri.min_weekly_benefit` | Minimum weekly benefit ($) | 148.0 [2026-07-01] |
| ☐ | `ri.min_base_period_earnings` | Base-period earnings for the primary eligibility test ($) | 19200.0 [2026-07-01] |
| ☐ | `ri.tci.weeks` | Temporary Caregiver Insurance duration (weeks) | 8 [2026-07-01] |
| ☐ | `ri.tdi.weeks` | Temporary Disability Insurance duration (weeks) | 30 [2026-07-01] |

**Structural claims to verify (not single numbers):**

- ☐ Benefit is 4.62% of the highest base-period quarter, not to exceed 85% of the AWW.
- ☐ TCI (bonding/family) is job-protected; TDI (own disability) is not.
- ☐ Military-exigency leave is not a covered reason.
- ☐ A dependency allowance (up to $1,552 with five dependents) is NOT modeled by the engine.
- ☐ Max $1,150 / min $148 effective 2026-07-01.

## WA — Washington Paid Family and Medical Leave (PFML)

- **Status:** UNVERIFIED — pending counsel review
- **Statute:** RCW Title 50A
- **Sources:** https://paidleave.wa.gov/

| ✓ | Parameter | Meaning | Encoded value(s) [effective date] |
|---|---|---|---|
| ☐ | `wa.saww` | State average weekly wage ($) | 1830.0 [2026-01-01] |
| ☐ | `wa.max_weekly_benefit` | Maximum weekly benefit ($) | 1647.0 [2026-01-01] |
| ☐ | `wa.min_hours` | Hours in the qualifying period to be benefit-eligible | 820 [2026-01-01] |
| ☐ | `wa.family.weeks` | Family leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `wa.medical.weeks` | Medical leave duration (weeks) | 12 [2026-01-01] |
| ☐ | `wa.combined.weeks` | Maximum combined weeks per claim year | 16 [2026-01-01] |
| ☐ | `wa.job_protection.min_employees` | Employer size for job protection (from 2026) | 25 [2026-01-01] |
| ☐ | `wa.job_protection.min_service_days` | Days of service for job protection (from 2026) | 180 [2026-01-01] |

**Structural claims to verify (not single numbers):**

- ☐ Eligibility is 820 hours across ANY Washington employer, not tenure with the current one.
- ☐ Job protection is a separate test that expanded on 2026-01-01 (50->25 employees, 12mo->180 days, 1,250-hr rule removed).
- ☐ Two-tier benefit: 90% up to 50% of SAWW, then 50%.
