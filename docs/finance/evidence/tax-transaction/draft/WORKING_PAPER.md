# Transaction cash and conditional tax support

**DRAFT — exact-file review pending.** Base scenario, 2026-01 through 2026-12. Synthetic reconstruction, not independent audit evidence.

This separate base-2026 bridge is not added to base-2027 activity. ARU filing-ready is not IRS filing or acceptance. Tax/book PPA assumptions remain conditional current industrial source records, not an election, return or valuation opinion. Red Wash escrow/holdback are included in purchase consideration rather than extra price.

## What is included

Complete declared source populations are in working-papers.xlsx and the source CSV/SQLite tables. The workbook Guide maps every table to its complete sheet and source file. Values beyond Excel’s 15-digit numerical precision remain text. Printed previews show leading rows and columns only; they do not limit the Excel population.

The workbook contains 7 complete source tables (143 rows), plus its Guide and Checks sheets. Repeated tables across packages are convenience mirrors, not additional transactions.

## Financial measures

| Measure | USD |
|---|---:|
| ARU stock consideration | 48,000,000.00 |
| Residual book goodwill | 14,762,500.00 |
| Independent tax goodwill basis | 13,000,000.00 |

These measures use the stated Core, Treasury, consolidated or industrial view; they are not interchangeable populations. Source columns remain in the complete workbook.

## Reconciliation and review

1 independently computed checks passed: population/source identity, decimal rollforwards and the applicable ledger or document joins. RECONCILIATION.json preserves each result; the workbook Checks sheet makes the tolerance test visible. No balancing adjustment was added.

## Provenance

Release business-operations-v1.0.0, source 57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e. The evidence register pins archive, native database, each CSV and extracted database hashes. Other scenarios and later years remain in the native release and are not claimed human-complete by this package.

The additional acquisition PPA, opening accounts, tax, debt and asset sheets reproduce current industrial sources separately. CURRENT_SOURCE_BRIDGE.json records their distinct current-source hashes. Filing-ready remains distinct from filed or accepted.
