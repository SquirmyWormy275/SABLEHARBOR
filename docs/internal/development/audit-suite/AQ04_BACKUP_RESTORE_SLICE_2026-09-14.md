# Backup execution and restore exercise — September 14, 2026

`company_backup_activity.BackupRecipe` and `generate_backup_pair(store, repository=..., recipe=...)` produce operational source records before an audit exists. The recipe explicitly identifies the company, two isolated branches, exercise, canonical service, source period and first scheduled backup instant. All instants require offsets. Existing source rows are accepted only for an exact replay; no earlier version is replaced.

## Procedure and authority basis

The authored procedures in `enterprise/ccf/assurance/design_data/control_procedures.json` require BCM002 to define schedules, retention/isolation, monitor jobs, ticket failures and reconcile protected datasets to inventory. BCM003 calls for risk-based selection, isolated restoration, measured recovery time/data age, integrity/usability checks and failure retests.

This slice uses canonical `SVC-compute` and the Reno-primary/Boise-recovery site references from the retained service and runtime-site sources. The native records preserve `PROVIDER_SELECTED_PROCUREMENT_PENDING`, nonoperating site flags and the reference-only deployment boundary. Scoped BCM003 primary and operating-review contacts are separate people; their provisional contact assignments do not establish accepted appointments or professional qualification. The approved reference scope is not evidence of a deployed service or PHI processing.

The local exercise defines one nonpersonal application dataset, daily checkpoints, a 24-hour checkpoint-age target, a 30-minute restoration target and seven-day retention configuration. These are explicit fictional exercise assumptions, not approved corporate BIA/RPO/RTO or a demonstrated retention mechanism.

## Computed causal records

Both branches retain identical inventory, schedule and two independently recorded source dataset snapshots. The second snapshot changes one object setting and adds another object. A local credential event differs: the second branch's write lease expires before the second job. The job derives its result from that credential state; it cannot create a backup object when writing is unavailable. The failure ledger, ticket and catalogue retain the resulting missing checkpoint.

Both restores apply the same rule: select the latest successfully catalogued checkpoint available at restore start. Actual retained dataset bytes are copied into backup-object versions and then separate restored-dataset versions. The reconciliation parses those bytes and computes missing, unexpected and changed IDs, row counts and copy hashes. Its event intervals are authored simulated timestamps, not measured production recovery duration; management review remains separately qualified.

The first clean restore has a 40-minute checkpoint age and matches the current source. The first messy restore has a 1,480-minute checkpoint age, lacks `OBJ-03`, and has the older `OBJ-02` setting. These are technical differences, not automatic audit findings. A subsequent grant-confirmation, new checkpoint and isolated retest recover the latest source bytes in both branches. Original jobs, failed checkpoint and first-restore results remain retained.

## Execution and validation

The separate private run is `enterprise/generated/audit-suite/company-backup-period-2026-09-14/v1/`, with `company/`, `RECIPE.json`, `RECEIPT.json`, `SUMMARY.json`, `TESTS.xml` and a reproducible `run.py`. It contains 51 source versions: 26 clean and 25 messy, across the same 13 source systems per branch. The missing failed-job backup object explains the different counts. No audit, model call, source grant or live service mutation was performed.

Seven focused tests cover byte-derived reconciliation, exact copies and source hashes, chronological lineage, preserved first results, idempotence, invalid-input no-write behavior, incompatible replay rejection, and future/revoked source access. These late-added tests have their own receipt and are not silently included in an earlier repository test run.

## Remaining limits

This is one explicitly inventoried local dataset and recovery path. JSON byte copies do not prove encryption, physical offsite recovery, immutable storage, credential isolation enforcement, seven-day retention expiry, or production application usability. The local reviewer inspects technical records; professional validation and whole-control effectiveness remain unassessed. All previous company stores, audit states and archived originals remain unchanged.


## Subsequent isolated audit collection

The standard Engine pathway collected these preexisting sources in two new isolated engagements, both scoped to BCM002/003 for March 2027. The private audit store and current command-path receipt are under `company-backup-period-2026-09-14/v1/collection-v1/`. The clean engagement `ENG-be5a2c68c43bada6e13d0928` retained 26 originals with 34 history events; messy engagement `ENG-6563a49a7a42e47c8b7481a9` retained 25 originals with 33 events.

Each uses explicit operator grants, `company.activate`, kickoff, ordinary PBC creation/issue, discovery and exact-version collection. Future discovery/collection and revoked access are denied. Every collection command is immediately replayed to verify idempotence and unchanged history. Collected native hashes equal the original source versions; parsed source and restored JSON independently reproduce the recorded missing/changed IDs. The retest bytes match the current source dataset in both branches.

Collection creates no prepared world, model call, procedure-test status change or automatic audit conclusion. All temporary grants were revoked. The original source version/hash membership remains unchanged; grant and access journal changes are intentional, so the post-collection SQLite file as a whole does not equal the earlier pre-collection file hash. Earlier source validation and newer collection receipts remain separately retained.

Eight focused source/collection tests pass in the new `collection-v1/TESTS.xml`; these remain distinct from root's earlier checkpoint suite.


## Persistent scheduled-operation successor

The separate [backup runtime](../../../../enterprise/audit_suite/BACKUP_RUNTIME.md)
now executes actual filesystem copies against persistent native datasets and an
exact independent operating-period declaration. The private local run is
`company-backup-runtime-2026-09-14/run-v1/`, produced at implementation commit
`ad6ad4ab`. Its seven explicitly declared occurrences span two invented local
datasets; these do not establish corporate backup cadence or production inventory.

The run retains 21 native versions across eight source systems at command
revision13. Six declared copy/restore occurrences completed, one remains missing
after its due date, and a failed attempt remains in history after a corrected
retry. The exact older copy restores successfully while content reconciliation
still exposes differences from the selected current dataset. This runtime
measures actual local copy elapsed time separately from authored business time.
Its initial seven-missing report and later reconciliation remain separate,
hash-verified artifacts; the source declaration database remained unchanged.

Thirty focused implementation, operator and independent review tests passed.
The private run's VERIFICATION.json and MANIFEST.json retain exact native pins,
command receipts and checks. Initial execution created no audit, grants or model
calls. Later collection, if performed, has its own receipt and does not establish
control effectiveness, accepted recovery objectives or a coherent operating year.
