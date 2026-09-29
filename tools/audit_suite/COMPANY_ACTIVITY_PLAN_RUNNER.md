# Private ordered company activity plans

V1 supports the nine activity kinds documented below. The single-activity operator's
`identity-lifecycle`, `nonhuman-identity`, `access-remediation`,
`access-review-continuation` and `risk-assessment` kinds require selected
original references and are explicitly excluded from this change-store dependency format.

`run_company_activity_plan` runs an explicitly authored list of native company operations through the maintained single-activity operator. It creates no engagement, source grant, collection, model invocation, hosted service or world. Generated branches remain independent fictional records; ordering jobs does not establish a coherent operating year or canon approval.

```bash
.venv/bin/python -m tools.audit_suite.run_company_activity_plan \
  --plan /absolute/private/plan.json \
  --destination /absolute/private/new-run
```

The plan file must be a private regular file (0600, no symlink/hardlink), and the new destination must have an existing private parent (0700). An existing destination is rejected even after failure. There is no resume or retry mode. The API is `enterprise.audit_suite.company_activity_plan.run(plan_path, destination, *, repository)`, returning the retained summary. The CLI exits 1 for a completed failure report.

The exact root fields are `format: "PRIVATE_COMPANY_ACTIVITY_PLAN_V1"` and `jobs`. Each of 1–24 jobs has `id`, `kind`, `depends_on`, and `recipe`; dependent jobs additionally require `source_job`. IDs are unique lowercase slugs, starting with a letter, at most 48 characters. Dependencies must be distinct **earlier** job IDs. The order is explicit, so cycles and forward references are rejected rather than automatically reordered. Unknown fields, duplicate JSON keys, nonfinite values, wrong scalar types, oversized plans (512 KiB) and oversized recipes (64 KiB) are rejected before any output is created.

Kinds use the maintained operator's exact allowlist: mover, identity-period, incident, backup, training, change, configuration, security-logging and provider-intake. Recipes use their exact maintained dataclass fields; nested tuple fields are explicit JSON arrays. Company, branch, dates and local requirement assumptions remain authored recipe fields. The runner does not derive or merge them.

For `configuration` and `security-logging`, `source_job` must name an earlier **change** job, also listed in `depends_on`. Both consume that change job's original release records; a configuration output is not substituted as a release-gate source. Omit `source_versions_sha256` from these recipes: supplying one is an error. Keep `source_store_id` explicit as a local label. The runner verifies the completed job's manifest members, calls the maintained `read_originals` on exactly `jobs/<source_job>/company`, and fills the verified version-set hash. The dependency receipt records the job ID, resolved source root, local store label, source-version count/hash and source job manifest hash. Thus a store label cannot silently route to an unrelated directory. No source paths, imports, scripts, commands, globs or directory discovery are accepted in the plan.

For example, an ordered plan can contain:

1. `change-a`, kind `change`, no dependencies, complete change recipe.
2. `configuration-a`, kind `configuration`, `depends_on: ["change-a"]`, `source_job: "change-a"`, explicit branches/checkpoints and local asset.
3. `logging-a`, kind `security-logging`, `depends_on: ["change-a", "configuration-a"]`, `source_job: "change-a"`, explicit original branch, output branches and local source identifier.

The extra configuration dependency in step 3 controls ordering only; it does not change the logging source.

Each run retains exact original `PLAN.json`, resolved `recipes/`, `jobs/<id>/` operator outputs with native receipts/manifests, immutable `events/` start/dependency/result records, final `RECEIPT.json`, and a run `MANIFEST.json`. The top manifest pins known run members and each completed job manifest; job manifests transitively pin original files. No scanning of unrelated directories occurs. Files use exclusive creation, 0600 permissions and file/directory fsync. Source code hashes of the runner and operator accompany the summary. Reproduction means replaying explicit inputs into a new output with the corresponding implementation; paths and operational metadata need not be byte-identical across runs.

Structural/type validation covers the entire plan first. Native generator-specific semantic validation runs per job. On the first native failure, the runner retains earlier completed outputs and available resolved inputs/dependency records, records `FAILED` with a sanitized stage/type, and marks remaining jobs `NOT_RUN`. The existing operator discards its own failed unpublished temporary generation; this runner does not claim those unpublished bytes are retained. Process interruption or storage failure may leave a start record without a result/final manifest; treat that run as interrupted, inspect retained events, and explicitly author a new run. Never infer completion from directory existence.

Tests exercise a real change→configuration/security-logging chain, exact source pins, complete manifest rereads, privacy, structural preflight, duplicate/nonfinite JSON, wrong source kinds, dependency tampering, failure retention and no overwrite. These validate orchestration and native integrity; they do not professionally assess the fictional controls.

Independent integrity review tightened preflight and completion: within one plan,
each explicit source label identifies exactly one source job and each consumed
source job has one label. Dependent company identity must agree with the source
recipe before generation begins. All declared dependencies are reverified and
their manifest hashes retained in `dependency_manifest_sha256`; ordering-only
dependencies still do not become source data. The published manifest must exactly
match the operator result, and all previously completed outputs are reverified
after each subsequent native job. A discrepancy stops the plan and retains prior
receipts without rewriting their historical completion records. These checks are
at discrete verification points, not a filesystem lock or cross-store transaction;
later external edits invalidate retained pins and must never be treated as a
successful rerun. Interrupted filesystem publication can leave partial immutable
events, as described above; it does not enable resume.
