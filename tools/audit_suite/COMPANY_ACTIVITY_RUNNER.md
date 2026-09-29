# Independent company activity runner

Run explicit local exercise recipes before creating an audit:

```bash
PYTHONPATH=. .venv/bin/python -m tools.audit_suite.generate_company_activity incident \
  --recipe /private/incident-recipe.json \
  --destination /private/new-incident-run
```

The maintained runner currently accepts `mover`, `identity-period`, `incident`, `backup`, `training`, `change`, `configuration`, `security-logging`, `provider-intake`, `identity-lifecycle`, `nonhuman-identity`, `risk-assessment` `access-remediation` and `access-review-continuation`.
Recipe fields follow `TransferRecipe`, `PeriodRecipe`, `IncidentRecipe`, `BackupRecipe`, `TrainingRecipe`, `ChangeRecipe`, `ConfigurationRecipe`, `LoggingRecipe` and `ProviderIntakeRecipe` in the
corresponding company activity modules. For an identity period, `movers` is a JSON
array of transfer recipes. Training uses arrays of `TrainingMember` objects in
`cohort` and `TrainingCourse` objects in `courses`, with `role_ids` as an array. All assumptions, people, branch identities and dates are
explicit; the runner supplies no default corporate policy or invented appointments.
The existing generator validates the recipe against its pinned repository sources.

Configuration activity also requires `--source-root /private/original-change/company`.
Its recipe explicitly pins `source_store_id`, `source_versions_sha256`, `branch_ids`
and `checkpoints` (the last two are JSON arrays). It reads existing original change
approvals, releases and configuration bytes to compute inventory/drift records;
it does not regenerate or modify those inputs. Output must be outside the original
source root.

Security logging also requires an explicit original change `--source-root`. Its
`LoggingRecipe` pins the source store/version digest, one upstream branch, two new
logging branches, a local source identifier and the local ingestion-lag threshold.
The generator applies a collector filter to an original release-authorization feed,
reconciles its sequence and hashes, then retains later backfill without erasing the
initial gap. Publisher sequences and lag requirements belong to the local exercise;
they do not assert a deployed logging platform or corporate coverage.

Identity lifecycle requires an explicit existing identity `--source-root`. Its
`LifecycleRecipe` uses JSON arrays for `branch_ids` and `source_refs`; every reference
contains exact `company`, `branch`, `system`, `record`, `version` and `sha256` fields.
The recipe pins the metadata digest of those selected originals, a separate fictional
worker, an existing sponsor, bounded lifecycle dates and explicit local requirements.
Native requests, approvals, grants, probes and revocation records preserve the initial
cached-session omission and later correction. This is a local data exercise, with no
canonical hiring or vendor deployment. The V1 multi-job plan does not yet support this
selected-identity dependency contract; use the explicit single-activity command.
Kinds without source dependencies reject the source-root argument.

Non-human identity activity uses the same exact-reference arrays and selected metadata
digest, with `NonhumanIdentityRecipe` and an existing backup `--source-root`. Four
original backup records are explicitly selected. A separate fictional workload,
inert credential versions, constrained source/target permissions and one explicit
calendar quarter govern actual byte-copy attempts. A missed consumer update causes
an authorization denial; later correction retains the failure and successful new
copy. The copied dataset's historical payload stays unchanged, with new copy-event
time and identity in outer provenance. No original human principal becomes a service
account. This selected-reference activity is also excluded from the V1 multi-job plan.

Risk assessment requires `--source-roots /private/source-roots.json`, an explicit
private JSON map from `incident`, `provider`, `log` and `change` to four distinct
absolute company-store paths. It cannot be combined with `--source-root`.
`RiskAssessmentRecipe` declares `source_groups`, each with exact native reference
arrays and its selected metadata digest, two `scenarios`, branch IDs and a bounded
quarter. The generator validates relationships among the nine originals, retains
their exact bytes and recomputes an assessment omission and later backfill. Recorded
observations, hypothetical risks and proposed treatments remain distinct. The
manifest records each selected group's store label, root and metadata digest.
The V1 multi-job plan does not support this multi-store dependency contract; use
the explicit standalone command. See
[the risk source contract](../../enterprise/audit_suite/RISK_ASSESSMENT_ACTIVITY.md).

Provider intake pins the original canonical runtime-site JSON through
`source_sites_sha256` and requires explicit start, review-due and backfill dates.
It computes local planned-provider inventory, provisional tiers, missing diligence
requests and internal review coverage. Existing DRAFT contracts, nonoperating
services and unavailable third-party support remain explicit. It sends no external
requests and accepts no provider. No separate source-root argument is used.

Keep the recipe private (0600), and use a new destination under an existing private
0700 parent. Symlinked or hard-linked recipes and existing destinations are rejected.
Generation uses a temporary private directory. Invalid recipes and failed generation
leave no final company store. Successful runs retain `company/company.sqlite3`, the
original recipe bytes, the generator receipt and a manifest of counts and hashes.
A failed final-directory write is rolled back using the private-directory helper.
This does not provide a globally atomic capture of other running company stores.

The runner verifies every new native source hash and confirms zero grants and zero
collections. It creates no engagement, evidence request, prepared audit world, model
call or service process. Source stores can subsequently be connected by the explicit
local company operator and ordinary scoped audit collection. That later collection
must retain its own receipts; generation is not proof that a control operated
successfully, that a population is complete, or that an auditor tested it.

The focused operator tests exercise a real paired source generation, exact recipe
retention, private files, rejection of existing/public/aliased inputs, and cleanup
following an injected partial-generation failure. Generator-specific chronology,
causality and canonical-boundary checks remain in their own test suites.

For multiple jobs consuming exact existing operator outputs, use the
[existing-source linked runner](COMPANY_ACTIVITY_LINKED_PLAN.md). It validates
explicit selected references and source availability before creating the run;
its separate V2 contract does not extend the V1 whole-change-store plan.

For one ordered producer/consumer run, the
[V3 producer plan](COMPANY_ACTIVITY_PRODUCER_PLAN.md) supports explicit selected
metadata capture after a producer completes, plus the existing whole-change-store
contract for configuration and logging. Caller-specified native content hashes
remain mandatory for selected dependencies.

Access remediation consumes five exact IAM review/application/HR originals through
`--source-root`, with a selected metadata hash and `input_at` cutoff. Its new
qualified continuation branches apply the same removal request, preserve actual
local permission state and independently check the resulting authorization.
Earlier quarterly reviews stay unchanged. Operating verification does not claim
professional assurance or enterprise population completeness. See the
[access remediation activity contract](../../enterprise/audit_suite/ACCESS_REMEDIATION_ACTIVITY.md).


`access-review-continuation` accepts the exact three-group source-root map described
in [the native continuation contract](../../enterprise/audit_suite/ACCESS_REVIEW_CONTINUATION.md).
The identity group has five originals; the initial and final removal groups
partition eleven originals from the same removal store. It creates three new
company review records, preserving unsupported cohort members and prior gaps.
