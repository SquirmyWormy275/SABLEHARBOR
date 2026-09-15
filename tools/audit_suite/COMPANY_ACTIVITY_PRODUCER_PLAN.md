# Selected producer routing V3

Use `.venv/bin/python -m tools.audit_suite.run_company_activity_producer_plan --plan /private/PLAN.json --destination /private/new-run`. V1 and V2 remain unchanged. The plan is private, the destination must be new, and jobs never create audits, grants, models, deployed services or risk acceptance.

The exact top-level format is `PRIVATE_COMPANY_ACTIVITY_PRODUCER_PLAN_V3`, with `inputs` and ordered `jobs` as in V2. Each job retains `id`, `kind`, `depends_on`, a complete typed `recipe`, and `sources`. Source slots now contain one explicit route object:

```json
{"source": {"input_id": "existing-backup"}}
```

Existing inputs retain the V2 contract: `inputs.existing-backup` contains a genuine completed operator `root` ending in `/company` and exact `manifest_sha256`. The recipe supplies both exact native six-field references and the expected `source_versions_sha256`. All such existing bindings validate before creating any output.

```json
{"source": {
  "source_job": "prior-backup",
  "metadata_mode": "CAPTURE_VERIFIED_PRODUCER"
}}
```

Selected producer routing is supported for identity-lifecycle, nonhuman-identity, access-remediation, and each risk-assessment group. The named source job must be an explicit, already earlier `depends_on` dependency. Its company must match the consumer. The recipe still supplies exact expected native company, branch, system, record, positive integer version and SHA256 for every selected record. Only the corresponding `source_versions_sha256` field must be **omitted**, never null or supplied. There is no latest-version selection or content-hash derivation.

After verifying the producer's completed operator manifest and all its original members, the capture helper reads those exact records, verifies their expected content hashes and consumer cutoff availability, then captures selected metadata once. The runner retains the capture receipt and a detached resolved recipe with that digest. Every later check uses the frozen resolved binding through the strict resolver; metadata is never silently recaptured. The original plan/recipe remains intact. Maintained selected metadata excludes `imported_at`; canonical provenance such as producer source revision can differ while native payload hashes remain equal. Capturing is an explicit contract choice, not an inevitable consequence of a new import timestamp. The full producer database manifest is pinned separately.

Risk uses the four explicit source slots `incident`, `provider`, `log`, and `change`, each independently routed. Existing and prior-produced sources may be combined only through their declared exact bindings. Different risk groups require distinct source stores. No cross-store coherence or global snapshot is inferred from successful routing.

## Whole-change mode

Configuration and security-logging reuse the existing V1 whole-change-store semantics with a separate explicit route:

```json
{"source": {
  "source_job": "prior-change",
  "metadata_mode": "CAPTURE_VERIFIED_CHANGE_STORE"
}}
```

Only a genuine prior `change` job in `depends_on` is accepted. The whole-store recipe omits its `source_versions_sha256`; there are no selected-source references in this different native recipe schema. The runner verifies the producer manifest, captures `read_originals`' complete metadata digest once, freezes it in the resolved recipe, and rechecks that digest plus producer member hashes afterward. Configuration checkpoint and logging event availability rules remain enforced by the native generators. This full source snapshot does not claim every source was available at one selected-source cutoff.

This permits a maintained ordered change → configuration/logging → risk chain without weakening the risk consumer's exact native reference expectations. Whole-change input routes, selected capture mode for a whole-change job, wrong producer kinds, and supplied/null derived digests are rejected before output.

## Retained execution and limits

All job structure, types, ordering, exact native reference shape and route modes validate before any output. Expected future source hashes are checked after the producer completes, before its consumer runs. New recipes are written once; failures retain their original plan, source receipts, successful outputs, and any published but unaccepted output manifest. Later jobs are NOT_RUN. A postcheck-failed output is never eligible as a dependency.

After every job, all completed producer outputs and every earlier consumer's frozen bindings are reverified. A later mutation prevents final COMPLETE while preserving earlier point-in-time receipts. Consumer destination checks use the actual sibling job output, not its enclosing plan directory. Files are private, bounded and nonsymlink; no overwrite, retry or resume occurs.

The retained run manifest pins exact plan bytes, resolved recipes, event receipts and job manifests. Source verification is per source and transaction; there is no cross-store atomicity, automatic company authority, complete operating year, audit sufficiency or professional validation claim.

Tests in `tests/audit_suite/test_company_activity_producer_plan.py` execute actual producer/consumer workflows, existing strict input routing, once-only capture, exact-reference failures, later source mutation, and a real change/configuration/logging/risk chain. They also reject malformed whole-change modes before output. The separate capture/resolver tests verify bounded native reads and source integrity.

To make the generated records available for ordinary company access and audit
collection, [initialize separate company runtimes](COMPANY_RUNTIME_ACTIVATION.md).
Their access journals can change while the original producer capsules stay sealed.
Do not point audit grants at a capsule and then claim its original database hash
still verifies.
