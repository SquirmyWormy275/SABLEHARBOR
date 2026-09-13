# Transaction cash and conditional tax support

**Scope:** base scenario, 2026; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.

This separate base-2026 bridge is not added to base-2027 activity. ARU filing-ready is not IRS filing or acceptance. Tax/book PPA assumptions remain conditional current industrial source records, not an election, return or valuation opinion. Red Wash escrow/holdback are included in purchase consideration rather than extra price.

## Open and trace the records

Open the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.

| Table | Selected rows | Full release rows | Open CSV |
|---|---:|---:|---|
| acquisition_cashflow_bridge | 1 | 3 | [CSV](source/acquisition_cashflow_bridge.csv) |
| enterprise_tax_allocation_bridge | 72 | 1296 | [CSV](source/enterprise_tax_allocation_bridge.csv) |

## Reconciliation

| Check | Rows/groups | Maximum difference | Result |
|---|---:|---:|---|
| Acquisition consideration less acquired cash | 1 | 0.0000 | PASS |

All monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).

Other scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.

[Current industrial acquisition and tax support](TRANSACTION_SUPPORT.md) separately reproduces the accepted2026 PPA, full opening trial balance, twelve-month tax/debt/assets schedules and legal documentary limits. Its current-source identity is not the immutable operations archive.
