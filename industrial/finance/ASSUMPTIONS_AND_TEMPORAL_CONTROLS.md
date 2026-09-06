# Assumptions, reporting periods and evidence limits

**Document ID:** SH-IND-FIN-ASM-001
**Version:** 1.0.0
**Owner:** Industrial finance / case publication steward
**Effective:** 2026-09-05
**Record origin:** PUBLIC_SYNTHETIC_DIEGETIC
**Evidence state:** LOCKED_DERIVED_IMPLEMENTATION with explicitly labeled PROVISIONAL_ASSUMPTION inputs

The source has stable assumption IDs and explicit fact states. Locked handoff facts remain distinct from derived implementation and provisional budget/valuation inputs. Fictional contracts, named personnel and synthetic statements do not become observed real-world evidence because a calculation reconciles.

## Changes made to complete the financial chain

| Subject | Preserved decision | Derived or provisional completion |
|---|---|---|
| 2025 ARU scale | $42M revenue, $9.8M EBITDA, 131 FTE, $3.3M sustaining capex | 25 customers, 29 contracts, seasonal monthly units, 131 employee salaries/burden, explicit balance sheet and cash-sweep policy |
| Corporate allocation | $0.2M net corporate charge, 10 FTE | $2.18M gross cost and $1.98M disclosed charges to operating segments |
| Acquisition | $62M EV, $48M buyer stock consideration, $39M equity before fees | $4.5M NWC peg; winter closing stub; debt terms; fee treatment; PPA classes; reserve DTA and goodwill DTL; four-seller cap table |
| Railroad accountability | BS&T distinct company, 58 FTE, $15.5M revenue | Separate closing book, allocated owned balances and disclosed treasury current account; no assumption of standalone cash self-sufficiency |
| Future ARU performance | Independently viable group; no synergy quota or personnel purge | 2% external price growth, no volume growth, 3% cost index; 25% tax sensitivity; scheduled debt service and equity-funded capital |
| Red Wash cost method | Existing weighted-average inventory and proposed composite DD&A | Full opening trial-balance scenario and funding provenance; existing source inputs retained as baseline |
| Interface | 225-car planning allowance, 300-car design capacity, no guaranteed volume, $8.5M Phase 1 | 215 billable physical cars plus 10 unbilled buffer cars; derived quote below old target; 63-car 2026 ramp; $3.25M/$5.25M ownership split |
| ARO | $16M acquired liability, $25M current cost, 6.5% discount, 2.5% inflation | 167-day H2 carryforward; explicit calibrated timing; separately disclosed progressive 2026 settlement; no fabricated offset |
| Legal platforms | Pale Sun and Red Wash distinct owners/books | $1.5M platform service allocation inside unchanged aggregate $2.8M G&A; reciprocal investment/capital and service elimination |
| Supporting schedules | Net working capital and EBITDA remain controlled | Specific $80,000 AR allowance; parts/fuel/material inventory classes; zero unsupported earnings addbacks |

Expense-envelope allocations are explicitly provisional. They are used to distribute the selected synthetic case coherently, not to claim an independent bottom-up supplier quotation proving every selected margin. The interface unit-cost schedule, in contrast, records distinct physical movements and truck legs. Both methods identify their evidence limits.

## Period and availability semantics

Every generated CSV record includes `record_origin`, `fact_state`, `period_role`, `as_of_cutoff`, `effective_period_end` and `available_at`. Availability is the publication-case reconstruction date; individual contracts, source records and narrative artifacts retain their own earlier effective dates. This does not fabricate the existence of a real historical file.

- 2025 is `SYNTHETIC_HISTORICAL_CASE`.
- January–August 2026 monthly accounting is `SYNTHETIC_CALIBRATION`.
- September–December 2026 monthly accounting is `MANAGEMENT_FORECAST`.
- Full-year 2026 and normalized/future analyses are `MANAGEMENT_SCENARIO_AT_2026_09_05`, not annual actuals.
- January 7 acquisition opening is a synthetic dated opening balance, not a forecast of year-end assets.
- The September monthly period ends after the September 5 cutoff and is never promoted to calibration merely because its calendar month matches the cutoff month.

The reporting scopes differ intentionally: ARU's acquired consolidated period begins January 7; the mine case covers the calendar year. The January 1–6 seller period is shown separately. A mixed-scope industrial retrospective may display both with their labels; it must not imply ARU was owned for those six preclose days. Federal deemed-sale and tax short-year dates remain separate from management/economic ownership reporting.

The quoted interface prices, customer terms, tax scenario rates, loan terms, asset lives, opening balance allocations and closure timing are synthetic inputs. They do not require a fabricated government certificate, tariff, banking confirmation or regulator approval. The current official-source memoranda supply actual external legal/regulatory context and keep conditional fictional implementation separate.

## Validation scope

Tests check every journal, each trial balance, asset/liability/equity equality, cash rollforwards, contract aggregation and concentration, payroll totals, cap table, sources/uses, reciprocal invoices, treasury and ownership eliminations, no unused buffer billing, time labels and deterministic output hashes. Deliberate input changes must change results or fail relevant controls; tests do not merely compare a copied list of selected totals to itself.

These checks establish computational and accounting consistency. They do not independently prove rail capacity, site suitability, mine recovery, contract enforceability, cost competitiveness or audited accounting judgments. The physical operating model and cited tax/rail/environment memoranda provide separate support and preserve their own uncertainties. A passing old Red Wash validator does not certify this new successor; its changed bridges receive their own validation.
