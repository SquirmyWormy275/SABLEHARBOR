# Generation-run and scenario architecture

**State:** implemented Stage 1 correctness architecture; broader platform remains review blocked.

Migrations `0008` through uncommitted `0012` centralize normalized run identity and persist generator/source, assumptions,
canon-lock, source-commit, actual-dataset, cutoff, forecast-start, and schema-head fields. The
current model cutoff is `2026-08-31`; forecasts begin `2026-09-01`. Generation reads those dates
from the persisted run contract rather than treating them as generator control constants. Completed run identity is
immutable: a mismatched build fails instead of rewriting the completed record. The lifecycle marker
uses the profile-independent value `RUN`.

Migration `0009` also persists a content-addressed build ID and complete generation-input manifest
digest. Manifest entries use repository-relative paths and cover finance assumptions, scenario
configuration, the canon source lock, migration sources, and generator Python sources. Identity is
therefore independent of the checkout location and caller working directory. The run ID includes
the complete input-manifest digest, as does the actual-dataset identity, so changed content creates
a distinct run/build/actual identity that can coexist with a completed predecessor for the same
profile, scenario, and seed. Explicit profile
contracts reject unknown profiles and incompatible scenarios before a run is recorded. Repeated
completion is an idempotent no-op and cannot rewrite the original completion timestamp.

## Ownership model

The platform uses an explicit common-actual layer plus self-contained scenario forecast runs.

- One deterministic `actual_common` generation run exists for each seed and owns opening
  balances, workforce, fixed assets, production, inventory, freight, environmental obligations,
  and other observed or opening operational facts generated for that seed.
- Every base, low, high, stress, baseline, full, full-history, or benchmark-safe run has its own
  `generation_run` row and run marker.
- Scenario runs reference their included common-actual run through
  `generation_run.actual_generation_run_id`.
- Scenario-dependent journals and scenario values belong directly to the scenario run.
- Actual periods through August 2026 use invariant multipliers. Scenario multipliers apply only
  to forecast periods beginning September 2026.
- Shared legal entities, books, periods, accounts, sites, customers, and vendors are master
  dimensions. They do not represent scenario facts and are not duplicated by run.

## Deterministic inclusion rule

`run_context(session, generation_run_id)` is the only supported read context. It resolves:

1. the selected scenario run; and
2. its referenced common-actual run, when present.

Reports, statements, named queries, workbooks, validation, and exports must use only those resolved
run IDs. A database containing multiple runs must reject an omitted selector. Direct unfiltered
aggregation is unsupported.

## Installation and execution

Alembic is the schema installation authority. Normal generation and read commands verify the
database is at migration head and never call `Base.metadata.create_all()`.

Generate first, then pass the explicit run ID to every read command:

```bash
uv run alembic upgrade head
uv run shfin generate --profile standard --scenario base --seed 20260831
RUN_ID=$(uv run shfin run-id standard --scenario base --seed 20260831)
uv run shfin validate --generation-run-id "$RUN_ID"
uv run shfin statements --generation-run-id "$RUN_ID"
uv run shfin workbooks --generation-run-id "$RUN_ID"
```

The public release implementation remains review blocked because its SQLite snapshot mechanism is
not yet the required new-empty-database, versioned table-and-column allowlist construction and its
generated-artifact safety scan is incomplete.

Migration `0010` scopes generated operational natural keys to their owning run and namespaces
common-actual primary keys by seed. A migration-backed SQLite test proves two standard/base seeds
coexist, retain duplicate human-readable worker numbers in separate actual runs, and link each
scenario run to its own actual layer. Because revision `0009` requires those keys to be globally
unique, `0010` explicitly refuses a populated downgrade before changing any constraint when
cross-run duplicates exist; the migration test verifies the data and `0010` schema remain intact.

Migration `0011` makes generation ownership non-null for every generated operational, ledger,
lineage, validation, and artifact table. Composite foreign keys reject generated parent/child links
whose run IDs differ, including nullable links when populated. Scenario-to-common-actual links use a
composite `(id, actual_dataset_id)` key, so a scenario cannot attach an actual layer from an
incompatible seed/build dataset. SQLite application connections explicitly enable foreign-key
enforcement. A lifecycle check permits only `RUNNING` with no completion timestamp or `COMPLETED`
with one, and backend-specific database triggers prevent mutation of completed identity and
lifecycle fields. Semantic tests directly attempt null ownership, cross-run linkage, incompatible
actual attachment, invalid completion, and completed identity mutation.

Migration `0012` closes every run included by a reporting context, including its common-actual
layer, so later postings cannot change either half of a closed context. Posting and reversal also
validate explicitly populated journal ownership against the active session context; a scenario
session may write only its own run or its attached common-actual run. Semantic tests attempt new
postings against both closed layers and cross-run posting and reversal. Existing compatible close
markers are idempotent: sibling scenarios with the same seed may close independently while sharing
one already-closed common-actual layer. On upgrade, revision `0012` converts every legacy globally
closed fiscal period into a marker for every existing generation run and retains the legacy state
as a posting guard for later runs. Downgrade first projects uniformly closed run state back to the
legacy global state and refuses any mixed per-run state that the older schema cannot represent.

Standard-profile monthly accounting controls and their revenue/cost driver values are partitioned
at the persisted cutoff: periods ending on or before `actual_through` are written once to the
common-actual run, while periods beginning at `forecast_from` are owned by the selected scenario
run. The common-actual lifecycle remains `RUNNING` until those records are written; sibling
scenarios reuse the completed layer. Semantic tests reject scenario-owned pre-cutoff monthly
records and actual-owned post-cutoff monthly records. Every profile that completes the
common-actual layer first materializes the same monthly actual superset and its persisted
standard-actual completion marker. Baseline→standard and standard→baseline therefore reuse the
same immutable layer and produce equivalent standard results.

`compare_trial_balances` provides the first explicit semantic multi-run comparison contract. It
requires two distinct completed selectors and rejects profile, actual-dataset, cutoff,
forecast-start, or schema mismatches. This keeps a scenario delta attributable to forecast facts
instead of silently comparing different seeds or actual layers. A base/stress regression proves a
nonzero scenario delta and direct rejection of same-run and cross-seed comparisons.

The dated production, freight-movement, and inventory registers now obey the same cutoff contract:
January through August production and movements belong to `actual_common`; September through
December production, movements, and the December ending-inventory lot belong to each scenario
run. A semantic two-scenario regression rejects post-cutoff actual ownership and pre-cutoff
scenario ownership for every one of these registers. A separate December 31 boundary regression
proves the ending-inventory lot moves into `actual_common` when its date is within the persisted
actual cutoff and is not duplicated in the selected scenario.

The PostgreSQL 16 CI job now includes an uncommitted `0009`–`0012` matrix covering supported
profiles, base/low/high/stress coexistence, two seeds, duplicate natural keys, null ownership,
cross-run generated links, incompatible actual attachment, completed-run immutability, and dated
fact cutoff ownership. The private benchmark profile uses an explicit
`SHFIN_PRIVATE_BENCHMARK=1` opt-in for PostgreSQL because a repository-relative private SQLite
path is not meaningful for a server database. This matrix has passed a local SQLite backend
surrogate but remains unaccepted until the PostgreSQL 16 CI job runs it. Stage 1 is still open:
broader comparison coverage beyond trial balances and remote PostgreSQL evidence remain pending. Effective-dated master
and commitment records (workers, contracts, and fixed assets) remain whole records rather than
periodic facts and are therefore not split at the reporting cutoff.
