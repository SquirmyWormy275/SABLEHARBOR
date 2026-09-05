# Backlog

## Completed v0.1 merge gates

1. Proved the `0015` migration and accounting-integrity tranche with fresh SQLite and PostgreSQL
   16.6/18.6 upgrade/downgrade, populated upgrade, generation, isolation, concurrency, and validation
   runs at implementation evidence commit `3fb7fc7`.
2. Ran and reviewed the six-workbook, seven scoped unit-package, public-release, checksum, bridge,
   same-snapshot determinism, and recursive artifact-safety gates against completed `standard` runs.
3. Merged PR #9 through a provenance-preserving merge commit, passed post-merge `main` CI, reconciled
   live acceptance guidance, and moved finance CI to immutable Node 24 action pins with one PR run
   per candidate and one push run on `main`. Uploaded review archives retain generated ownership
   markers so their internal manifests and checksum inventories remain complete after download.

## Deferred, nonblocking depth

1. Extend comparison coverage beyond trial balances and deepen the subledger/reporting areas called
   out in `KNOWN_LIMITATIONS.md`, including AP due dates and classified cash flow.
2. Keep valuation, acquisition terms, legal names/jurisdictions, any still-open site assignments,
   and other unresolved facts explicitly limited or model-proposed until controlling canon resolves
   them.
3. Continue hardening PostgreSQL integration, performance, documentation, privacy, and CI without
   promoting historical checkpoint evidence to current acceptance evidence.
