# Procurement, payables and Treasury

**DRAFT — exact-file review pending.** Base scenario, 2027-01 through 2027-12. Synthetic reconstruction, not independent audit evidence.

Treasury is illustrative FIFO allocation within cash-flow class, not employee/vendor bank-payment proof. Obligation and payable master funded/unpaid fields are terminal snapshots, not month-end balances; history and reconciliation rows control dated exposure. Industrial invoice terminal settlement fields have the same boundary. Complete industrial PO/receipt/invoice joins are present; Core vendor originals and independent daily bank confirmations are not supplied. Industrial bank transactions/reconciliations are retained as modeled clearing records, not bank-issued evidence. Native industrial document lineage is a model support chain, not independent corroboration.

## What is included

Complete declared source populations are in working-papers.xlsx and the source CSV/SQLite tables. The workbook Guide maps every table to its complete sheet and source file. Values beyond Excel’s 15-digit numerical precision remain text. Printed previews show leading rows and columns only; they do not limit the Excel population.

The workbook contains 14 complete source tables (12,223 rows), plus its Guide and Checks sheets. Repeated tables across packages are convenience mirrors, not additional transactions.

## Financial measures

| Measure | USD |
|---|---:|
| Operating unpaid requests at December close | 0.00 |
| Investing unpaid requests at December close | 0.00 |
| Financing unpaid requests at December close | 0.00 |

These measures use the stated Core, Treasury, consolidated or industrial view; they are not interchangeable populations. Source columns remain in the complete workbook.

## Reconciliation and review

5 independently computed checks passed: population/source identity, decimal rollforwards and the applicable ledger or document joins. RECONCILIATION.json preserves each result; the workbook Checks sheet makes the tolerance test visible. No balancing adjustment was added.

## Provenance

Release business-operations-v1.0.0, source 57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e. The evidence register pins archive, native database, each CSV and extracted database hashes. Other scenarios and later years remain in the native release and are not claimed human-complete by this package.
