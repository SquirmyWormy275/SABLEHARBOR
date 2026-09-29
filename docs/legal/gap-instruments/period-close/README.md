# ARU Group — January 2027 period close

**SH-CLOSE-ARU-2027-01 · DRAFT FOR EXACT-FILE REVIEW · Conditional forecast, base scenario.**

Reconstruct one complete native industrial reporting book: 22 opening balances, all 274 January activity rows, five reconciliation areas, no new adjustment entries, and all 34 closing accounts. ARU_GROUP is a reporting scope, not an assertion of one statutory company.

Start with [blank.xlsx](blank.xlsx). Work through Opening → Activity → Bank / receivables / payables / Debt / PPE → Adjustments → Closing TB → Statements. Compare [worked.xlsx](worked.xlsx) and [WORKED.md](WORKED.md) afterward. Yellow cells are responses; existing source values remain visible.

## Evidence and limits

The [input register](inputs.json) pins the immutable business-operations-v1.0.0 release and exact member hashes. All selected native columns survive in the eight source CSVs listed below and [SQLite tables](close.sqlite3). [case.json](case.json) preserves checks and source rows. The [closing TB CSV](closing_trial_balance.csv) is a derivative. Month 0 is used once as opening balances; it is excluded from activity.

- ARU_GROUP is the native industrial reporting scope, not a claim of a single statutory legal entity. Do not add Core, enterprise replacement or allocated legal books.
- Bank records are modeled clearing events. Obtain a bank-issued statement and subsequent clearing evidence before concluding independent cash existence.
- Account 1100 is external receivables net of allowance. This case supplies complete ledger movement, not independent gross aging or allowance adequacy evidence.
- Account 2000 is trade payables including forecast settlement flows. Obtain a dated supplier open-item schedule and subsequent disbursements; terminal invoice masters are not month-end balances.
- PPE schedule covers accounts 1400/1490; finance-lease ROU accounts 1500/1590 remain separately visible in the complete trial balance. Physical existence, title, useful lives and executed debt terms require additional evidence.
- These are public source-derived learning examples, not private assessment keys, audited results or a completed corporate close.

## Reader deliverable

Submit the completed workbook, an explanation for each difference, any evidence-supported proposed journal, and requests for missing independent support. A zero source tie-out is not a signed close or audit conclusion. The public worked example leaves all proposed adjustments at zero because the supplied records contain no unexplained numerical discrepancy.

## Reproduce

`python tools/legal_gaps/period_close.py build` regenerates the derivatives. `validate` checks source hashes, complete row populations, per-journal balance, account rollforwards, 18 reconciliations, workbook bytes and full SQLite content. `render` creates native LibreOffice review pages; manual review must be recorded separately.

## Individual native files

- [Opening balances](source/opening_balances.csv): 22 rows.
- [Journal](source/journal.csv): 274 rows.
- [Trial balances](source/trial_balances.csv): 34 rows.
- [Monthly statements](source/monthly_statements.csv): 1 rows.
- [Assets](source/assets.csv): 8 rows.
- [Debt](source/debt.csv): 1 rows.
- [Industrial bank reconciliations](source/industrial_bank_reconciliations.csv): 1 rows.
- [Industrial bank transactions](source/industrial_bank_transactions.csv): 33 rows.

Verify original extraction with `python tools/legal_gaps/period_close.py verify-archive --archive /path/to/sable-harbor-business-operations-v1.0.0.zip`. The command compares every selected column and row with the hash-pinned archive. `verify-formulas` independently recalculates all 270 worked spreadsheet formulas in LibreOffice. `validate-qa` checks both exact workbook hashes and all retained manual-review pages.
