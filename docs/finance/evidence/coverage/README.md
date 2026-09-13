# Finance evidence: scope and source access

This work covers the complete declared **base-scenario 2027** populations in five finance packages, with **base-2026 acquisition/tax** kept separate. It does not claim every scenario and future year has a new human document. The immutable source is business-operations-v1.0.0 at `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`; the ZIP hash is pinned in [SCOPE.json](SCOPE.json).

[RELEASE_INVENTORY.json](RELEASE_INVENTORY.json) inventories every CSV member, full population count, columns, scenario/year coverage and hash across the parent and all seven unit exports. Comparison/business-v1 and scoped unit copies are explicitly nonadditive. The original archive remains downloadable from the [release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/business-operations-v1.0.0); it is not duplicated into Git.

| Family | Reader entry | Scope and limitation |
|---|---|---|
| Billing, receipts, credits, revenue | [Customer evidence](../customer/README.md) | All selected 2027 contracts/invoices/events, aging and deferred rollforwards; no fabricated bill or bank original |
| Procurement/AP/Treasury | [Treasury evidence](../treasury/README.md) | Industrial PO/receipt/invoice chains and Core obligation histories; terminal master values are not month-end exposure |
| Close/allowance/consolidation | [Close evidence](../close/README.md) | Entire 2027 unit/legal trial balances and statements, complete Core and enterprise journals kept separate |
| Workforce/inventory/assets/debt | [Supporting schedules](../supporting-schedules/README.md) | All selected source populations; employer cost and cash paid remain distinct |
| Acquisition/tax | [Tax and transaction evidence](../tax-transaction/README.md) | Separate 2026 acquisition cash bridge and tax allocation; current legal source boundaries remain explicit |

The extracted CSV and SQLite tables preserve every selected source column. CSV files open directly in Excel; SQLite is a convenience mirror and each table retains its native identity. Every `tables/` population is compared, in full, with the released `enterprise.sqlite3` population before filtering. Industrial forecast/transaction CSVs not present as native database tables retain their archive-member identity and are mirrored in the family database without claiming they originated in enterprise.sqlite3.

Invoice, payable and Treasury obligation masters carry terminal lifecycle values. Selection by issue/accrual year does not make those values December 2027 balances. Dated aging, subledger and history tables control the period balance. Static contracts/positions are input records, not additional economic events. Unit books and legal books are alternate presentations, not a consolidation union.

No personal bank details, supplier signatures, tax return, independent valuation or additional legal terms were created. Other scenarios and 2028–2031 have native-release access, with no claim of completed new PDF/Excel coverage. Historical finance-platform statements of limitations are not imported to erase newer accepted industrial records.

Reproduce source and verify:

```bash
python docs/finance/evidence/coverage/build.py --archive /path/to/sable-harbor-business-operations-v1.0.0.zip
python docs/finance/evidence/coverage/validate.py
python -m pytest -q docs/finance/evidence/coverage/test_extracts.py
```

Source/code/Markdown and reconciliations are committed independently of new presentation binaries. Draft PDF/Excel files and review renders require exact-file owner review; no current source checkpoint approves those designs.
