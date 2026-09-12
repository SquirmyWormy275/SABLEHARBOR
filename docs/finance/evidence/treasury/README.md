# Procurement, payables and Treasury

**Scope:** base scenario, 2027; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.

Treasury is illustrative FIFO allocation within cash-flow class, not employee/vendor bank-payment proof. Obligation and payable master funded/unpaid fields are terminal snapshots, not month-end balances; history and reconciliation rows control dated exposure. Industrial invoice terminal settlement fields have the same boundary. Complete industrial PO/receipt/invoice joins are present; Core vendor originals and independent daily bank confirmations are not supplied. Industrial bank transactions/reconciliations are retained as modeled clearing records, not bank-issued evidence. Native industrial document lineage is a model support chain, not independent corroboration.

## Open and trace the records

Open the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.

| Table | Selected rows | Full release rows | Open CSV |
|---|---:|---:|---|
| payables | 705 | 12100 | [CSV](source/payables.csv) |
| treasury_obligations | 754 | 13554 | [CSV](source/treasury_obligations.csv) |
| treasury_obligation_history | 754 | 15270 | [CSV](source/treasury_obligation_history.csv) |
| treasury_reconciliation | 36 | 648 | [CSV](source/treasury_reconciliation.csv) |
| host_collection_settlements | 8 | 158 | [CSV](source/host_collection_settlements.csv) |
| subledger_rollforward | 72 | 1080 | [CSV](source/subledger_rollforward.csv) |
| industrial_purchase_orders | 300 | 4500 | [CSV](source/industrial_purchase_orders.csv) |
| industrial_receipts | 300 | 4500 | [CSV](source/industrial_receipts.csv) |
| industrial_supplier_invoices | 300 | 4500 | [CSV](source/industrial_supplier_invoices.csv) |
| industrial_document_journal_lineage | 7131 | 123716 | [CSV](source/industrial_document_journal_lineage.csv) |
| industrial_bank_transactions | 1754 | 26440 | [CSV](source/industrial_bank_transactions.csv) |
| industrial_bank_reconciliations | 24 | 360 | [CSV](source/industrial_bank_reconciliations.csv) |
| industrial_vendors | 25 | 25 | [CSV](source/industrial_vendors.csv) |
| industrial_work_orders | 60 | 900 | [CSV](source/industrial_work_orders.csv) |

## Reconciliation

| Check | Rows/groups | Maximum difference | Result |
|---|---:|---:|---|
| Treasury arrears rollforward | 36 | 0.0000 | PASS |
| Lifetime request allocation | 754 | 0.0000 | PASS |
| Complete supplier PO and receipt links | 300 | 0 | PASS |
| Supplier invoice to purchase order amount | 300 | 0 | PASS |
| Supplier invoice to receipt amount | 300 | 0 | PASS |

All monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).

Other scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.
