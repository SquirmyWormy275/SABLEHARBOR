# Blackridge Build Report v0.1.0

Build date: 2026-09-01  
Schema/dataset: 0.1.0  
Seed: 20150112

The deterministic foundation generator produced a full-scale public database and SQL-derived
workbook. Validation passed SQLite integrity, foreign-key, balanced-journal, derived-impairment,
and public-oracle leakage checks. The derived impairment is $52.05 million (carrying amount
$312.40 million less recoverable amount $260.35 million).

Key generated counts include 1,000,000 canonical events, 151,000 haul cycles, 105,600 generated
journal-domain records, 76,000 inventory transactions, 30,500 maintenance labor bookings, 12,000
SKUs, 10,500 receipts, 6,200 work orders, 3,000 assets, 1,600 serialized components, 575 people,
and all 8,760 plant hours. The database is approximately 295 MiB and is intentionally excluded
from ordinary Git history for release-asset publication. The M00 database and workbook are compact.

## Honest acceptance status

All Part I engineering outputs are materialized and builder-validated. Acceptance gates are marked
`REVIEW_READY`, not independently `ACCEPTED`; specialist review and later Part II workstreams are
outside this builder-validation claim.

## Continuation evidence

The continuation added all seven cutoff databases, complete domain CSV exports, manifest hashing,
and corruption/snapshot-leakage tests. The test suite now has four passing tests. These additions
reduce but do not eliminate the remaining acceptance gaps above.

Migration upgrade/downgrade/upgrade, M00 deterministic replay, execution of all 75 cookbook SQL
statements, and automated QA across all 135 workbook sheets also pass. The test suite now contains
five passing tests.

Material, contained-copper, contained-gold, and fuel rollforwards now conserve for every month.
AP, AR, payroll, inventory, fixed-asset, and CIP subledgers tie to their control balances for every
month. Two-shift assignments for exactly 27 trucks, 54 operators, and 1,600 serialized components
pass overlap/exclusivity validation. A deliberate conservation mutation is rejected. The test suite
now contains six passing tests.

Additional corruption tests now prove rejection of negative inventory, impossible availability
timestamps, a damaged impairment lineage equation, and overlapping resource assignments. The
suite now contains ten passing tests and the full database passes all eleven validation categories.

The corruption suite now covers every mutation named by Part I, including orphaned PO linkage,
missing haul destination, truncated vendor export, workbook/database hash mismatch, and missing
subledger reconciliation. The suite contains fifteen passing tests.

Enterprise population remediation increased the workforce to 500 employees plus 75 contractors,
650 positions and assignments, 100,000 scheduled shifts, 98,500 actual shifts, 2,750 accounting
fixed assets, 75,000 meter readings, 250,000 sensor readings, 18,000 laboratory samples, 20,000
assays, 1,200 meetings, and 7,500 meeting-attendee records. These sit alongside the previously
reported target-scale operations and master populations.

Final ledger closeout replaced the earlier 74-line detailed proof with 105,600 enforceably balanced
double-entry lines tied to 52,776 source references. Per-period subledger transaction/reversal pairs
net to zero without unexplained statement residual, and the $52.05 million impairment is reflected
in December net income, assets, and equity as well as its balanced journal.
