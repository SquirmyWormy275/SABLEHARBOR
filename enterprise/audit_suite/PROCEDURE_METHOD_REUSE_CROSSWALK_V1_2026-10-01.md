# Historical procedure-method reuse crosswalk

The old A1939/B2066 review packet and frozen P1 pair have the same 409 task
IDs on each side. Their task kinds, titles, test clauses, control IDs,
boundaries, and other scope fields align. Two gate tasks per side have a
different `fieldwork_start`: January 1 in the old packet and December 31,
2027 in P1. The crosswalk flags these tasks for scope review rather than
carrying an old gate result forward.

The read-only crosswalk exposes 407 authored procedure texts per side as
**method candidates**. It also provides historical workpaper and sample
locators for finding prior calculation and selection methods, without copying
their observations or evidence. The old packet has 275 linked workpaper
versions and 70 linked sample executions per side. Its 92 `COMPLETE`, 182
`IN_PROGRESS`, and 135 `NOT_STARTED` task states per side are historical
context only. Old A has 272 `LIMITATION` and two `FAIL` conclusions; old B has
214 `LIMITATION` and 60 `FAIL`. Both have 135 `NOT_RUN` conclusions. The frozen
P1 pair remains 409 `NOT_STARTED`/`NOT_RUN` tasks per side.

The crosswalk pins the old packet, its manifest and independent review, both
P1 engagement databases and the 538-file P1 inventory, and the reviewed V16
source-route ledger. V16 covers 283 documentary/activity routes per side; a
selected route lead is not a tested conclusion. Every new task still needs
fresh company-native originals, population and sample definition, procedure
performance, exception disposition, and independent review. Historical
evidence, conclusions and instructor Key are not transferable.

Run `python -m enterprise.audit_suite.procedure_method_reuse_crosswalk_v1`
with `--repository`, `--private-root`, and `--output`. It reads existing inputs
and creates only a private crosswalk report at an unused output path. It does
not create an audit pair, migrate state, grant credit, or alter Atlas.
