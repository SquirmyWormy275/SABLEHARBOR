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
discovery, automatic retries or overwrites are provided.

The output retains `REPORT.json`, `PLAN.json` and a hash manifest. It distinguishes
exact dependency matches, missing selected targets, temporal conflicts, role support,
inventory differences and unplanned intervals. Missing selected support does not
mean the company has no such evidence. A narrow declared population remains narrow
even when all selected quarterly roles are present. Company-year coherence remains
`NOT_ESTABLISHED`; population acceptance, sampling, testing and effectiveness are
separate work. Original company records and formal audit history are preserved.
