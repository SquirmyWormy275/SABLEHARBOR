# Workforce, inventory, fixed assets and debt

**DRAFT — exact-file review pending.** Base scenario, 2027-01 through 2027-12. Synthetic reconstruction, not independent audit evidence.

Position IDs are synthetic planning records, not new named employees or actual 2026 headcount. Loaded costs are employer costs, not net pay. Validate costs against PAYROLL_REQUEST journals before Cradle capitalizes direct labor into inventory; net BIZ_PAYROLL expense is not gross payroll. Core and industrial schedules are separate source systems. Stock quantities are retained in their original units. No payroll remittance, independent valuation, reserve certification, new ownership or covenant threshold is created.

## What is included

Complete declared source populations are in working-papers.xlsx and the source CSV/SQLite tables. The workbook Guide maps every table to its complete sheet and source file. Values beyond Excel’s 15-digit numerical precision remain text. Printed previews show leading rows and columns only; they do not limit the Excel population.

The workbook contains 14 complete source tables (16,236 rows), plus its Guide and Checks sheets. Repeated tables across packages are convenience mirrors, not additional transactions.

## Financial measures

| Measure | USD |
|---|---:|
| Core December asset net book value | 1,365,452.38 |
| Core 2027 allocated employer cost | 74,491,666.56 |
| ARU December legacy term principal | 19,875,000.00 |

These measures use the stated Core, Treasury, consolidated or industrial view; they are not interchangeable populations. Source columns remain in the complete workbook.

## Reconciliation and review

4 independently computed checks passed: population/source identity, decimal rollforwards and the applicable ledger or document joins. RECONCILIATION.json preserves each result; the workbook Checks sheet makes the tolerance test visible. No balancing adjustment was added.

## Provenance

Release business-operations-v1.0.0, source 57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e. The evidence register pins archive, native database, each CSV and extracted database hashes. Other scenarios and later years remain in the native release and are not claimed human-complete by this package.
