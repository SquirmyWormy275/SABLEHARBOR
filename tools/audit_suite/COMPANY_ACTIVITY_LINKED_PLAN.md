# Existing-source linked activity plan V2

Run locally with:

```sh
.venv/bin/python -m tools.audit_suite.run_company_activity_linked_plan \
  --plan /private/PLAN.json --destination /private/new-run
```

The plan and its containing operator files are private. Output must be new and outside every source operator directory. Nothing is sent remotely. The runner creates neither grants nor audits, and invokes no model. Existing V1 plans and their whole-change-store dependency contract remain unchanged.

The exact V2 shape is:

```json
{
  "format": "PRIVATE_COMPANY_ACTIVITY_LINKED_PLAN_V2",
  "inputs": {
    "backup": {
      "root": "/private/completed-backup-operator/company",
      "manifest_sha256": "<exact 64-character lowercase SHA256>"
    }
  },
  "jobs": [{
    "id": "local-credential-cycle",
    "kind": "nonhuman-identity",
    "depends_on": [],
    "recipe": {"...": "complete maintained recipe including exact source_refs and selected metadata SHA"},
    "sources": {"source": "backup"}
  }]
}
```

This example illustrates the routing shape; the recipe placeholder is deliberately not runnable. Supply the complete typed native recipe. Existing inputs must be genuine completed `PRIVATE_COMPANY_ACTIVITY_RUN_V1` operator outputs with their original `company` child, exact member hashes, and zero original grants/collections. The original operator manifest must still match: later grants or collection journals change the SQLite bytes and invalidate that initial input pin. This initial contract therefore supports preserved operator outputs, not arbitrary previously used company stores. Direct-generator legacy directories are unsupported; do not manufacture wrapper manifests to promote them. Independently reproducing a recipe through the operator creates new originals with new import metadata; pin them explicitly rather than pretending they are the historical source.

Selected dependent kinds are `identity-lifecycle`, `nonhuman-identity`, `access-remediation`, and `risk-assessment`. The first three use `sources.source`; risk uses the four explicit keys `incident`, `provider`, `log`, and `change`. Each complete recipe retains its native six-field source references and expected selected-metadata digest. Only those exact versions are resolved; there is no discovery, newest-version substitution, or automatic derived metadata. Lifecycle cutoff is `request_at`, nonhuman cutoff is `period_start`, and access remediation and risk cutoffs are `input_at`. Source event and availability must both be known and no later than the declared cutoff.

Independent kinds are mover, identity-period, incident, backup, training, change, and provider-intake, with an empty sources object. `depends_on` names distinct earlier jobs and verifies their retained outputs, but does not route their generated records as inputs. `source_job` is explicitly rejected before creating output. Prior-output routing needs an explicit contract for binding the newly completed producer manifest. The selected metadata digest covers native identity, event/availability, origin and provenance; it excludes imported_at. The complete database and operator manifest still record a distinct reproduction. Configuration and security-logging whole-store consumers remain in V1; this is not a complete producer/consumer DAG implementation.

The entire plan structure and all existing input bindings validate before output. Each consumer then verifies exact input manifests/selected records before and after execution. Every completed output and earlier consumer input is rechecked after later jobs. Producer labels remain explicit per-consumer claims; different consumers may use different labels for one physical input. Risk groups must identify distinct stores. No label creates company authority or proves cross-store causal coherence.

The run retains exact original PLAN bytes, resolved recipes, source-binding receipts, job events and member hashes. On failure it stops, retains prior outputs and marks later jobs NOT_RUN; it never resumes or overwrites. A published output whose member verification or later postcheck fails remains identified in the parent inventory; when its manifest can be read safely, its exact bytes remain pinned with `POSTCHECK_FAILED_NOT_DEPENDENCY`. Earlier COMPLETE receipts describe their successful point-in-time checks; a later failure revalidating their source prevents a final COMPLETE result. Generic failure text excludes native source details.

Snapshots and manifest checks are per source, not one global transaction. The runner establishes exact reproduction inputs and bounded local activity execution, not an accepted corporate policy, coherent operating year, risk acceptance, audit sufficiency, or professional validation.

Tests: `tests/audit_suite/test_company_activity_linked_plan.py` covers actual operator sources, nonhuman and four-group risk execution, private mutation/tamper, before-output rejection, immutable failure inventory, per-consumer labels, and later-job invalidation. Resolver tests cover its bounded read-only native/manifest contract separately.
