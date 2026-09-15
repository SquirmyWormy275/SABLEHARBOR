# Billing, collections and deferred revenue

**DRAFT — exact-file review pending.** Base scenario, 2027-01 through 2027-12. Synthetic reconstruction, not independent audit evidence.

Invoice master rows are end-of-model snapshots for invoices issued in 2027; collected/remaining fields include later lifecycle activity and are NOT December 2027 balances. Period aging and subledger rows control month-end balances. Events include complete 2027 populations, not only invoice events. Contracts without scenario/time fields are shared source inputs, not extra transactions. Whole historical industrial customer/contract reference registers are retained as source inputs, never added as 2027 revenue. Industrial sales invoices and contract revenue are included separately, with modeled journal lineage through Treasury. These are reconstructed model records, not original customer bills, signed acceptances, independent bank confirmations or tax invoices.

## What is included

Complete declared source populations are in working-papers.xlsx and the source CSV/SQLite tables. The workbook Guide maps every table to its complete sheet and source file. Values beyond Excel’s 15-digit numerical precision remain text. Printed previews show leading rows and columns only; they do not limit the Excel population.

The workbook contains 14 complete source tables (5,390 rows), plus its Guide and Checks sheets. Repeated tables across packages are convenience mirrors, not additional transactions.

## Financial measures

| Measure | USD |
|---|---:|
| Core gross receivables at December close | 2,703,459.20 |
| Core allowance at December close | 54,069.18 |
| Core deferred revenue at December close | 8,655,600.00 |

These measures use the stated Core, Treasury, consolidated or industrial view; they are not interchangeable populations. Source columns remain in the complete workbook.

## Reconciliation and review

3 independently computed checks passed: population/source identity, decimal rollforwards and the applicable ledger or document joins. RECONCILIATION.json preserves each result; the workbook Checks sheet makes the tolerance test visible. No balancing adjustment was added.

## Provenance

Release business-operations-v1.0.0, source 57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e. The evidence register pins archive, native database, each CSV and extracted database hashes. Other scenarios and later years remain in the native release and are not claimed human-complete by this package.
