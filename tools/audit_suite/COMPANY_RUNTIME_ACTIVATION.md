# Initialize company source runtimes

Initialize a writable company source before connecting any audit:

```bash
.venv/bin/python -m tools.audit_suite.activate_company_runtime \
  --capsule /private/completed-producer/jobs/change \
  --manifest-sha256 SHA256_FROM_THE_VERIFIED_PRODUCER_RECEIPT \
  --destination /private/company-runtimes/change
```

The capsule is an existing preserved activity-operator output containing
`MANIFEST.json` and `company/company.sqlite3`. The destination must be new, outside
the capsule, under an existing private parent. The operator verifies the expected
manifest and original members, copies exact registered systems and immutable source
versions into a fresh application-owned schema, and publishes privately.

The runtime contains `company.sqlite3` and a separate `ACTIVATION.json` receipt.
Original event, availability and import timestamps, provenance, record/version
identities and command digests remain unchanged. Initialization time and the
runtime instance identity belong to the activation receipt. No source SQL schema,
triggers, grants, collections or access history are imported. This does not grant
access, create an engagement, populate audit artifacts or invoke a model.

Point the company registry at the new runtime directory. Existing owner-scoped
grants, discovery and collection then operate on that company store. Auditors
retrieve original records through the normal company connector; the audit retains
copies only after collection. Subsequent authorized access journals can change the
runtime database. The receipt's seed database hash describes initialization only;
it is not a permanent hash of a writable system. The original capsule remains
sealed and independently verifiable.

Keep distinct source components and their native company/branch identities distinct.
An activation receipt establishes initialization lineage, not deployment, employment,
PHI processing, canonical acceptance, a complete company year or audit sufficiency.
Existing synthetic and retrospective custody qualifications remain attached to
their original records. A previously used source database is not a pristine capsule;
use the existing company store or its appropriate recovery workflow instead of
resetting its authority or history through initialization.
