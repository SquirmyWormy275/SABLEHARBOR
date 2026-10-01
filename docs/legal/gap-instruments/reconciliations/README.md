# Reconciliation practice

Five bounded checks using accepted public model rows. Start with [blank.xlsx](blank.xlsx); compare [worked.xlsx](worked.xlsx) only after completing your calculations and evidence requests. New designs remain draft for exact-file review.

[Exact selected rows and source pins](source.json) · [SQLite mirror](reconciliations.sqlite3) · [Separate worked explanation](WORKED.md).

| Case | Population | Checks |
|---|---|---:|
| Bank clearing bridge | ARU_GROUP \| industrial forecast model \| January 2027 | 3 |
| Receivables aging to subledger | Atlas Meridian \| Core forecast model \| January 2027 | 1 |
| Payables journal to subledger | Atlas Meridian \| Core forecast model \| January 2027 | 1 |
| Debt principal movements | ARU_GROUP \| industrial forecast model \| January 2027 | 3 |
| Asset carrying value | Willow / FORT-TEST-RIG \| Core forecast model \| January 2027 | 1 |

## Source access

Filters and every original selected column are preserved in source.json. Workbook locators use one-based row positions within those selections. Source hashes pin the complete accepted extracted CSVs. The [finance coverage record](../../../finance/evidence/coverage/README.md) identifies the immutable release.

- E01: [industrial_bank_reconciliations.csv](../../../finance/evidence/treasury/source/industrial_bank_reconciliations.csv) — 1 selected rows.
- E02: [receivable_aging.csv](../../../finance/evidence/customer/source/receivable_aging.csv) — 2 selected rows.
- E03: [subledger_rollforward.csv](../../../finance/evidence/customer/source/subledger_rollforward.csv) — 1 selected rows.
- E04: [journal.csv](../../../finance/evidence/close/source/journal.csv) — 2 selected rows.
- E05: [subledger_rollforward.csv](../../../finance/evidence/treasury/source/subledger_rollforward.csv) — 1 selected rows.
- E06: [industrial_debt.csv](../../../finance/evidence/supporting-schedules/source/industrial_debt.csv) — 1 selected rows.
- E07: [asset_rollforward.csv](../../../finance/evidence/supporting-schedules/source/asset_rollforward.csv) — 1 selected rows.

Core and industrial systems remain separate. Terminal invoice/payable master values are not used as month-end balances. Bank evidence is modeled clearing, not an independent statement.

Build: `python tools/legal_gaps/reconciliations.py build`. Check complete regenerated JSON/Markdown/workbook bytes and SQLite schema/rows: `python tools/legal_gaps/reconciliations.py validate`. Render native workbooks: `python tools/legal_gaps/reconciliations.py render`. SQLite physical headers may vary across engines; complete logical contents must match.
