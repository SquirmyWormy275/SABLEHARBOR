# Explicit source dependency and period reconciliation

Run a private structural report against existing audit and company records:

```bash
.venv/bin/python -m tools.audit_suite.reconcile_source_dependencies \
  --config /absolute/private/reconciliation-config.json \
  --output /absolute/private/new-report
```

The configuration has exactly these string fields: `audit_root`, `actor_id`,
`engagement_id`, `company_registry`, `company_profile`, `company_bindings` and `plan`.
Paths must be absolute existing private inputs. `actor_id` names an existing principal;
the tool enforces its current engagement and source grants. It does not accept a
replacement role, grant access, create an engagement or call a model. Use an existing
private output parent and a new output directory outside every input store.
The operator uses a read-only audit connection with SQLite query-only mode and no
store/artifact initialization. Even an invalid empty input database is left untouched.

The plan pins `registry_sha256` and `scope_sha256`, names exact `source_refs`, and
supplies explicit `adapters` and `period_contracts`. Refer to the maintained
`enterprise.audit_suite.source_dependency_reconciliation` schema and tests for the
exact typed structures. Supported adapters inspect logging/configuration upstream
references; producer labels are explicitly mapped to physical portfolio components.
They are not assumed to equal component IDs. IAM review roles require their actual
native source schemas. Expected slots are authored UTC half-open intervals, not
inferred requirements or proof of operation throughout those intervals.

Configuration and plan files must be private regular JSON, at most 512 KiB each;
duplicate keys, non-finite values, aliases and changing input files are rejected.
The report supports at most 64 selected sources, with per-component snapshots and
final authority, registry, revision and scope checks. No arbitrary queries, directory
discovery, automatic retries or overwrites are provided. Native JSON bodies also
reject duplicate keys at any depth and non-finite numbers before analysis; a
matching raw-byte hash does not resolve ambiguous semantic fields.

The output retains `REPORT.json`, `PLAN.json` and a hash manifest. It distinguishes
exact dependency matches, missing selected targets, temporal conflicts, role support,
inventory differences and unplanned intervals. Missing selected support does not
mean the company has no such evidence. A narrow declared population remains narrow
even when all selected quarterly roles are present. Company-year coherence remains
`NOT_ESTABLISHED`; population acceptance, sampling, testing and effectiveness are
separate work. Original company records and formal audit history are preserved.

An optional `iam_review_contracts` array checks exact quarterly membership hashes,
decision-to-member references, selected application rights and listed HR originals.
All supporting references share the existing 64-source budget; omitted support is
reported without searching for substitutes. Recorded removal decisions remain
separate from execution, which that contract does not verify. See the
[native review contract](../../docs/internal/development/audit-suite/AQ_IAM_NATIVE_REVIEW_RECONCILIATION_2026-09-14.md)
for fields, cutoff semantics and validation evidence. Omitting this optional array
preserves the previous report shape.

The optional `access_remediation_contracts` array adds observations about selected
local removal requests, execution attempts, permission state and operating probes.
It accepts at most four contracts within the same 64-source budget and requires
SH-IAM-007 in the assigned control scope. Results appear in
`access_remediation_reconciliation`; the native parent review and unresolved
population limitations remain separate. Both optional contract arrays may coexist.
See the [local removal observation contract](../../docs/internal/development/audit-suite/AQ_ACCESS_REMEDIATION_RECONCILIATION_2026-09-14.md).

The manifest retains the original `module_sha256` string and adds
`analysis_modules_sha256` for the active analysis modules, including transitive
IAM checks used by removal observations and the maintained strict JSON parser. Their source-file hashes are captured
before analysis and rechecked immediately before publication. These are maintained
source-file observations, not loaded-binary attestation or a complete Python
dependency inventory. A change during analysis prevents publication. Earlier
reports retain their original manifest shape and bytes.
