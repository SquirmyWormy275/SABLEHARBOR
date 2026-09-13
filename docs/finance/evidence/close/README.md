# Close, allowance and legal-book reconciliation

**Scope:** base scenario, 2027; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.

Unit reporting and legal books are alternative views, not populations to add together. Core journal and enterprise replacement journal are different scopes: never concatenate them. Reporting clearing and legal management allocation retain their released classifications. Close validation checks complete monthly books, not an independent audit opinion.

## Open and trace the records

Open the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.

| Table | Selected rows | Full release rows | Open CSV |
|---|---:|---:|---|
| journal | 4864 | 84922 | [CSV](source/journal.csv) |
| enterprise_journal | 6097 | 108114 | [CSV](source/enterprise_journal.csv) |
| unit_trial_balance | 1867 | 31146 | [CSV](source/unit_trial_balance.csv) |
| legal_trial_balance | 1616 | 27754 | [CSV](source/legal_trial_balance.csv) |
| monthly_statements | 108 | 1944 | [CSV](source/monthly_statements.csv) |
| legal_statements | 96 | 1728 | [CSV](source/legal_statements.csv) |
| credit_allowance | 136 | 3174 | [CSV](source/credit_allowance.csv) |
| subledger_rollforward | 72 | 1080 | [CSV](source/subledger_rollforward.csv) |
| industrial_eliminations | 12 | 180 | [CSV](source/industrial_eliminations.csv) |
| industrial_intercompany | 216 | 3240 | [CSV](source/industrial_intercompany.csv) |

## Reconciliation

| Check | Rows/groups | Maximum difference | Result |
|---|---:|---:|---|
| journal every journal balances | 2425 | 0.0000 | PASS |
| enterprise_journal every journal balances | 2698 | 0.0000 | PASS |
| unit_trial_balance every monthly book balances | 108 | 0.0000 | PASS |
| legal_trial_balance every monthly book balances | 84 | 0.0000 | PASS |
| monthly_statements balance sheet | 108 | 0.0000 | PASS |
| monthly_statements cash bridge | 108 | 0.0000 | PASS |
| legal_statements balance sheet | 96 | 0.0000 | PASS |
| legal_statements cash bridge | 96 | 0.0000 | PASS |
| Core gross_ar_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core allowance_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core deferred_revenue_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core vendor_ap_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core host_payable_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core inventory_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core gross_ppe_usd to cumulative journal | 72 | 0.0000 | PASS |
| Core accumulated_depreciation_usd to cumulative journal | 72 | 0.0000 | PASS |
| Unit to legal account/month bridge | 897 | 0.0000 | PASS |
| Core to enterprise replacement source/account bridge | 4863 | 0.0000 | PASS |

All monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).

Other scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.
