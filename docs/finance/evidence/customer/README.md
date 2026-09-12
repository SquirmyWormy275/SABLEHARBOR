# Billing, collections and deferred revenue

**Scope:** base scenario, 2027; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.

Invoice master rows are end-of-model snapshots for invoices issued in 2027; collected/remaining fields include later lifecycle activity and are NOT December 2027 balances. Period aging and subledger rows control month-end balances. Events include complete 2027 populations, not only invoice events. Contracts without scenario/time fields are shared source inputs, not extra transactions. Whole historical industrial customer/contract reference registers are retained as source inputs, never added as 2027 revenue. Industrial sales invoices and contract revenue are included separately, with modeled journal lineage through Treasury. These are reconstructed model records, not original customer bills, signed acceptances, independent bank confirmations or tax invoices.

## Open and trace the records

Open the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.

| Table | Selected rows | Full release rows | Open CSV |
|---|---:|---:|---|
| contracts | 75 | 75 | [CSV](source/contracts.csv) |
| contract_versions | 62 | 938 | [CSV](source/contract_versions.csv) |
| invoices | 127 | 1975 | [CSV](source/invoices.csv) |
| credit_history | 128 | 1958 | [CSV](source/credit_history.csv) |
| credit_notes | 5 | 18 | [CSV](source/credit_notes.csv) |
| receivable_aging | 136 | 3174 | [CSV](source/receivable_aging.csv) |
| credit_allowance | 136 | 3174 | [CSV](source/credit_allowance.csv) |
| commercial_deferred_rollforward | 900 | 13500 | [CSV](source/commercial_deferred_rollforward.csv) |
| subledger_rollforward | 72 | 1080 | [CSV](source/subledger_rollforward.csv) |
| events | 2777 | 47060 | [CSV](source/events.csv) |
| industrial_sales_invoices | 570 | 7948 | [CSV](source/industrial_sales_invoices.csv) |
| industrial_contract_revenue | 348 | 5220 | [CSV](source/industrial_contract_revenue.csv) |
| industrial_customer_register | 25 | 25 | [CSV](source/industrial_customer_register.csv) |
| industrial_contract_register | 29 | 29 | [CSV](source/industrial_contract_register.csv) |

## Reconciliation

| Check | Rows/groups | Maximum difference | Result |
|---|---:|---:|---|
| Contract deferred rollforward | 900 | 0.0000 | PASS |
| Deferred schedule to unit subledger | 24 | 0.0000 | PASS |
| Aging to gross AR | 72 | 0.0000 | PASS |

All monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).

Other scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.

## Contract, receipt and journal joins

Match contract_versions.contract_id to contracts.contract_id. The selected model starts product histories in 2027; no pre-2027 product-version population is omitted. Match credit_history.invoice_id to invoices.invoice_id, then credit_history.source_id to events.event_id and [the complete Core journal](../close/source/journal.csv) source_id. Receipts are released history/event rows, not a separate authentic bank receipt. The cross-family validator rejects dangling contract, invoice, event or invoice-event journal joins. Core INVOICE events use source_id (not their empty invoice_id field) to join invoices.invoice_id; performance_source matches invoices.source_id, and event_id joins the Core journal. Industrial invoices join source_id/event_id/journal_id to the full industrial lineage in the Treasury package; contract revenue uses its own supported source_id. Earlier/later commercial sources are not silently imported as new transactions.
