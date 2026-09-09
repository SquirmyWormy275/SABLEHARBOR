# Current business and publication alignment delivery

**As of:** September 9, 2026
**Baseline:** `aa0cf80467c25616ad04f6c76168db1eecaecbaa` (merged Geo PR #105)
**Acceptance:** The accepting pull request and its main merge commit are the delivery boundary. Branch existence alone is not closeout.

## Delivered source scope

- Seven current business dossiers and a structured legal/reporting-line register.
- Scoped Advisory/Atlas continuity record preserving the source-summary limitation, outcome-billing direction and J2 authority boundary.
- Twelve explicit business/history/Finance portal source contracts and nine local implementations of existing common controls, without asserting runtime deployment or operating effectiveness.
- Historical/external entity boundaries and current-source versus frozen-release crosswalk.
- Current-status repairs for PR #9/#13, RWH legal name, SHMS, Internal Audit maturity, Wiki presentation and Geo follow-up work.
- Explicit tracked-generated-artifact lifecycle decision for issue #37.
- Twenty-four changed controlled publications: seven dossiers, source/boundary/interface/direction/lifecycle documents, current industrial legal-name erratum, missing headquarters/ESS/People/IT/authority/SHMS/J2-establishment publications and four board approval records. The earlier industrial v2.0.0 publication remains preserved; current erratum is v2.0.1.

## Board/source/publication reconciliation

| Approval path | Source record | Derivative evidence |
|---|---|---|
| 2021 growth financing | board-records/2021-06-18_harrison-vale-growth-financing-minutes.md | Record ID SH-BRD-MIN-2021-06-18, controlled PDF and catalog row |
| 2022 industrial financing | board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md | Record ID SH-BRD-MIN-2022-10-28, controlled PDF and catalog row |
| 2024 Chair/committees | board-records/2024-02-15_independent-chair-and-committee-architecture-minutes.md | Record ID SH-BRD-MIN-2024-02-15, controlled PDF and catalog row |
| 2026 governance/J2/Alexandria | board-records/2026-09-02_governance-j2-alexandria-ratification-written-consent.md and Exhibits A–D | Record ID SH-BRD-CONSENT-2026-09-02, controlled PDF and catalog row |

All table source paths are relative to `docs/governance/`. The existing `board_approval_records.json` remains the canonical structured approval chronology. The September 2 consent ratifies its named instruments and exhibits; it does not approve later unresolved institutional choices by implication. Later accepted closeouts govern their stated changes. Source approval history precedes and controls generated publication, never the reverse.

## Validation

The build regenerated the publication manifest and institutional JSON/SQLite catalog. Governance, catalog, organization, repository hygiene and business-record validators check source relationships and hashes. The publication unittest suite checks normalization and retained financial content. The full repository pytest suite passed (five environment-dependent PostgreSQL skips); all eight publication tests and all five applicable validators passed. The accepting PR records remote CI results.

Visual review covered all 59 pages in the 24 new/changed publications. Text and tables remained within the approved US-Letter layout; the later headquarters status correction was regenerated. The catalog contains 107 objects at this revision; acceptance relies on source pairing and useful search rather than that incidental total.

## Scoped completion and remaining work

This package supplies #33 publication reconciliation, #37 repository catalog lifecycle, #38 business-source interfaces and #44 Finance-source boundaries. Their GitHub closure follows accepted merge. The #88 doctrine/publication portion is complete; its exact approved Sacramento HQ image binary remains absent and must not be recreated as if it were the approved hash.

The business-driven financial engine, granular unit evidence and remaining #12 acceptance criteria are the next implementation package, not completed by these dossiers. Runtime/entitlements/deletion/Daedalus implementation (#21/#22/#24/#34), permanent J2 naming (#19), residual legal mechanics (#18), administration (#11) and source-specific Geo work (#106–108) retain their explicit boundaries. No stale branch was deleted or repository protection claimed without evidence.
