# Workforce, inventory, fixed assets and debt

**Scope:** base scenario, 2027; complete declared table populations, all applicable reporting units. Public synthetic records. New PDF/Excel presentation remains subject to exact-file review.

Position IDs are synthetic planning records, not new named employees or actual 2026 headcount. Loaded costs are employer costs, not net pay. Core and industrial schedules are separate source systems. Stock quantities are retained in their original units. No payroll remittance, independent valuation, reserve certification, new ownership or covenant threshold is created.

## Open and trace the records

Open the CSV files below directly in Excel, or use `evidence.sqlite3` for the same exact extracted rows. Every original source column is preserved. Match native IDs; never combine comparison releases, unit subsets and enterprise rows as additional transactions. The [register](evidence-register.json) identifies exact archive/database/member hashes and filters.

| Table | Selected rows | Full release rows | Open CSV |
|---|---:|---:|---|
| workforce_positions | 591 | 591 | [CSV](source/workforce_positions.csv) |
| workforce_positions_history | 7092 | 106380 | [CSV](source/workforce_positions_history.csv) |
| workforce_assignments | 6114 | 92352 | [CSV](source/workforce_assignments.csv) |
| workforce_changes | 9 | 30 | [CSV](source/workforce_changes.csv) |
| asset_rollforward | 54 | 882 | [CSV](source/asset_rollforward.csv) |
| inventory_rollforward | 12 | 180 | [CSV](source/inventory_rollforward.csv) |
| management_cost_reconciliation | 12 | 180 | [CSV](source/management_cost_reconciliation.csv) |
| service_cost_pools | 48 | 720 | [CSV](source/service_cost_pools.csv) |
| service_consumption_allocations | 384 | 5760 | [CSV](source/service_consumption_allocations.csv) |
| industrial_assets | 264 | 13867 | [CSV](source/industrial_assets.csv) |
| industrial_debt | 12 | 180 | [CSV](source/industrial_debt.csv) |
| industrial_inventory | 12 | 180 | [CSV](source/industrial_inventory.csv) |
| industrial_payroll_batches | 60 | 900 | [CSV](source/industrial_payroll_batches.csv) |

## Reconciliation

| Check | Rows/groups | Maximum difference | Result |
|---|---:|---:|---|
| Core asset cost less accumulated depreciation | 54 | 0.0000 | PASS |
| Management allocation reconciliation | 12 | 0.0000 | PASS |
| Industrial term principal rollforward | 12 | 0 | PASS |
| Industrial replacement debt rollforward | 12 | 0 | PASS |

All monetary checks use decimal arithmetic with a $0.02 tolerance for released rounding. This does not hide an unexplained balancing entry. Complete values, including zero and adverse outcomes, remain in the source tables. See [machine-readable discrepancies](RECONCILIATION.json).

Other scenarios and 2028–2031 remain accessible in the immutable release but are not claimed as human-complete here. [Full release inventory](../coverage/README.md) explains the scope boundary.
