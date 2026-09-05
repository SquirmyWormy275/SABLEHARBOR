# Generation-run and scenario architecture

**State:** Stage 1 v0.1 accepted and merged; broader production and audit depth remains deferred.

**Epistemic classification:** every generated 2023–2026 number is synthetic scenario/calibration
data. The current shared-layer profile is `synthetic_common`. Physical database columns
`actual_dataset_id`, `actual_through`, and `actual_generation_run_id` survive only as deprecated
internal migration/storage aliases; application APIs and outputs expose synthetic-calibration names.
None of those fields assert observed company results or audited books.

Migrations `0008` through `0015` centralize normalized run identity and persist generator/source,
assumptions, canon-lock, source-commit, shared-dataset, synthetic-calibration-boundary,
forecast-start, and schema-head fields. The current synthetic calibration boundary is `2026-08-31`;
forecasts begin `2026-09-01`. Generation reads those dates
from the persisted run contract rather than treating them as generator control constants. Completed run identity is
immutable: a mismatched build fails instead of rewriting the completed record. The lifecycle marker
uses the profile-independent value `RUN`.

Migration `0009` also persists a content-addressed build ID and complete generation-input manifest
digest. Manifest entries use repository-relative paths and cover finance assumptions, scenario
configuration, release schemas, dependency lockfiles, migration/query sources, generator Python
sources, and every Git blob declared by the canon source lock. Every declared `commit:path` must
resolve, and each live controlling file must byte-match its pinned blob. Identity is therefore
independent of the checkout location and caller working directory. Generation and packaging do
require a full governed SABLEHARBOR Git checkout containing the pinned history; the v0.1 wheel is
not a standalone generation distribution, and shallow or source-only installations fail preflight
instead of silently omitting historical inputs. The run ID includes
the complete input-manifest digest, as does the shared-dataset identity, so changed content creates
a distinct run/build/calibration identity that can coexist with a completed predecessor for the same
profile, scenario, and seed. Explicit profile
contracts reject unknown profiles and incompatible scenarios before a run is recorded. Repeated
completion is an idempotent no-op and cannot rewrite the original completion timestamp.

## Ownership model

The platform uses an explicit shared synthetic pre-cutoff calibration layer plus self-contained
scenario forecast runs.

- One deterministic `synthetic_common` generation run exists for each seed and
  owns synthetic opening balances, workforce, fixed assets, production, inventory, freight,
  environmental obligations, and other pre-cutoff calibration records generated for that seed.
- Every supported profile/scenario invocation has its own `generation_run` row and run marker.
- Scenario runs reference their included shared calibration run through the preferred
  `shared_synthetic_calibration_run_id` API property (backed by a deprecated storage alias).
- Scenario-dependent journals and scenario values belong directly to the scenario run.
- Shared synthetic calibration periods through August 2026 use invariant multipliers. Scenario multipliers apply only
  to forecast periods beginning September 2026.
- Legal entities, books, periods, accounts, and sites are shared master dimensions. Generated
  customers and vendors are run-owned because they are synthetic scenario/calibration evidence,
  not established counterparties.

## Deterministic inclusion rule

`run_context(session, generation_run_id)` is the only supported read context. It resolves:

1. the selected scenario run; and
2. its referenced shared pre-cutoff calibration run, when present.

Reports, statements, named queries, workbooks, validation, and exports must use only those resolved
run IDs. A database containing multiple runs must reject an omitted selector. Direct unfiltered
aggregation is unsupported.

Determinism has a deliberately bounded meaning. For an unchanged input manifest, profile,
scenario, and seed, the platform produces stable run/build identifiers, synthetic business values,
record identifiers, and query ordering. Repackaging the same persisted run from an unchanged,
immutable source-database snapshot with the same controlled package timestamp is byte reproducible.
Shared master dimensions are not run-owned in v0.1, so mutating them means the source snapshot
changed even if the selected run ID did not. `started_at`, `completed_at`, journal `posted_at`, and the
recorded source commit are execution provenance: independent fresh materializations can legitimately
differ in those real fields and therefore in affected CSVs, workbooks, manifests, and checksums.
Cross-build byte identity is not claimed. A publisher that requires byte reproduction must retain
an immutable snapshot of the selected persisted database and pass the same controlled `generated_at` value.

## Installation and execution

Alembic is the schema installation authority. The current worktree requires migration head `0015`.
Normal generation and read commands verify that head and never call `Base.metadata.create_all()`.
Final fresh SQLite and PostgreSQL migration evidence for v0.1 passed and is recorded in
`PLATFORM_ACCEPTANCE_v0.1.md`.

Generate first, then pass the explicit run ID to every read command:

```bash
uv run alembic upgrade head
uv run shfin generate --profile standard --scenario base --seed 20260831
RUN_ID=$(uv run shfin run-id standard --scenario base --seed 20260831)
uv run shfin validate --generation-run-id "$RUN_ID"
uv run shfin statements --generation-run-id "$RUN_ID"
uv run shfin workbooks --generation-run-id "$RUN_ID"
```

The public release implementation now builds a new empty database from a versioned table/column
allowlist and scans generated artifacts recursively. The v0.1 publication gates passed; formal
publication remains a separate immutable tag/release action. These controls do not elevate synthetic
calibration into company history.

Migration `0010` scopes generated operational natural keys to their owning run and namespaces
shared-calibration primary keys by seed. A migration-backed SQLite test proves two standard/base
seeds coexist, retain duplicate human-readable worker numbers in separate calibration runs, and
link each scenario run to its own pre-cutoff layer. Because revision `0009` requires those keys to be globally
unique, `0010` explicitly refuses a populated downgrade before changing any constraint when
cross-run duplicates exist; the migration test verifies the data and `0010` schema remain intact.

Migration `0011` makes generation ownership non-null for every generated operational, ledger,
lineage, validation, and artifact table. Composite foreign keys reject generated parent/child links
whose run IDs differ, including nullable links when populated. Scenario-to-calibration links use a
composite run/dataset key, so a scenario cannot attach a pre-cutoff layer from an
incompatible seed/build dataset. SQLite application connections explicitly enable foreign-key
enforcement. A lifecycle check permits only `RUNNING` with no completion timestamp or `COMPLETED`
with one, and backend-specific database triggers prevent mutation of completed identity and
lifecycle fields. Semantic tests directly attempt null ownership, cross-run linkage, incompatible
calibration attachment, invalid completion, and completed identity mutation.

Migration `0012` closes every run included by a reporting context, including its shared calibration
layer, so later postings cannot change either half of a closed context. Posting and reversal also
validate explicitly populated journal ownership against the active session context; a scenario
session may write only its own run or its attached calibration run. Semantic tests attempt new
postings against both closed layers and cross-run posting and reversal. Existing compatible close
markers are idempotent: sibling scenarios with the same seed may close independently while sharing
one already-closed calibration layer. On upgrade, revision `0012` converts every legacy globally
closed fiscal period into a marker for every existing generation run and retains the legacy state
as a posting guard for later runs. Downgrade first projects uniformly closed run state back to the
legacy global state and refuses any mixed per-run state that the older schema cannot represent.

Migration `0013` widens persisted cutoff-marker period codes without allowing a lossy populated
downgrade. Migration `0014` adds run-owned debt-repayment records. The current `0015` target adds
run ownership for generated customer/vendor masters, same-run relationships, ledger equations and
period/book/date constraints, completed-run content guards, and database-side completion checks.
Those `0015` controls describe the current implementation target; final clean SQLite and PostgreSQL
upgrade/downgrade/generation evidence passed for the accepted v0.1 integration state.

Standard-profile monthly accounting controls and their revenue/cost driver values are partitioned
at the persisted cutoff: synthetic periods ending on or before `synthetic_calibration_through` are
written once to the `synthetic_common` calibration run, while periods beginning at `forecast_from`
are owned by the selected scenario run. The shared calibration lifecycle remains
`RUNNING` until those records are written; sibling
scenarios reuse the completed layer. Semantic tests reject scenario-owned pre-cutoff monthly
records and calibration-owned post-cutoff monthly records. Every profile that completes the
shared layer first materializes the same monthly synthetic pre-cutoff superset and its persisted
completion marker. Baseline→standard and standard→baseline therefore reuse the
same immutable layer and produce equivalent standard results.

`compare_trial_balances` provides the first explicit semantic multi-run comparison contract. It
requires two distinct completed selectors and rejects profile, shared-dataset, cutoff,
forecast-start, or schema mismatches. This keeps a scenario delta attributable to forecast facts
instead of silently comparing different seeds or calibration layers. A base/stress regression proves a
nonzero scenario delta and direct rejection of same-run and cross-seed comparisons.

The dated production, freight-movement, and inventory registers now obey the same cutoff contract:
synthetic January through August production and movements belong to the `synthetic_common`
calibration run; September through
December production, movements, and the December ending-inventory lot belong to each scenario
run. A semantic two-scenario regression rejects post-cutoff calibration ownership and pre-cutoff
scenario ownership for every one of these registers. A separate December 31 boundary regression
proves the ending-inventory lot moves into `synthetic_common` when its date is within the persisted
calibration cutoff and is not duplicated in the selected scenario.

The PostgreSQL 16 CI definition covers supported public profiles, base/low/high/stress coexistence,
two seeds, duplicate natural keys, null ownership, cross-run generated links, incompatible
calibration attachment, completed-run immutability, and dated-fact cutoff ownership. A legacy
evaluator-only profile and its environment switch have been removed; PR #9 exposes no active private
evaluator-generation interface. Prior checkpoint evidence does not establish the current `0015`
worktree. Final SQLite/PostgreSQL execution closed v0.1 Stage 1 acceptance; broader comparison
coverage beyond trial balances remains deferred. Effective-dated master
and commitment records (workers, contracts, and fixed assets) remain whole records rather than
periodic facts and are therefore not split at the reporting cutoff.
