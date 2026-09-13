# Evidence collection and scheduling

Collection creates private draft packets for the existing independent population
registration and authenticated intake workflow. It neither tests controls nor
appoints reviewers. Missing manual criteria remain `NOT_RUN`.

Run a configured job from an operating-system scheduler:

```sh
uv run python -m enterprise.ccf.operations.collection /private/job.json \
  --state /private/collection.sqlite3 --output /private/packets
```

The SQLite state file and artifact directory must be private (0600 and 0700).
Repeated execution in a successfully reconciled schedule slot returns the retained artifact and readiness;
changed configuration under the same job/slot is rejected. Failed requests leave
that slot retryable. Unreconciled packets are retained with `RECONCILIATION_FAILED` and do not complete the slot; repair the source and retry. Missing or modified committed artifacts fail closed. Schedule
slots are calculated from `schedule_start` and `interval_seconds`; missed slots
are not silently backfilled. Configure a new assessment period/export and expiry
for each real collection window. The caller controls job execution frequency.
The optional Python `at` argument exists for deterministic scheduler tests; it is
not a source event timestamp or reviewer approval.

`collection.config_template(evidence_path, census_path, scope)` returns a runnable
synthetic local-export configuration. Replace all demonstration fields with
reviewed operating facts before using actual evidence. `scope` contains
`boundary_id`, `origin`, `period_start`, and `period_end` (timezone required).
Evidence JSON is an array of normalized operations records: `id`, `origin`,
`boundary_id`, `occurred_at`, `kind`, and typed `data`. CSV uses the same columns,
with the `data` column encoded as JSON. Census JSON is a separately supplied array
of objects containing `id`; CSV may contain an `id` column. Empty populations
require a separate manual applicability decision and are not marked ready.

The census connector requires `purpose: census`, a source query, and an
`independence_basis` explaining the authoritative roster, extraction actor and
separation from the observed evidence query. Two different files do **not** prove
independence. A reviewer must substantiate this basis, inspect exclusions and
source counts, and complete `population.criteria_review` before registering the
population. Collection never fills that field. The packet retains separate raw
export/page hashes, queries and locators; `source_export_sha256` additionally pins
the normalized census expected by the store. Original local exports and HTTP page bytes are retained as base64 in the private packet provenance alongside their SHA-256 hashes for re-performance. They are never copied into tracked code. Treat the entire packet as sensitive evidence.

A normalized authenticated source can replace either local connector:

```json
{
  "type": "https_json",
  "purpose": "census",
  "source_system": "REPLACE_WITH_SYSTEM",
  "query": "REPLACE_WITH_REVIEWED_ROSTER_QUERY",
  "independence_basis": "REPLACE_WITH_VERIFIABLE_EXTRACTION_BASIS",
  "endpoint": "https://evidence.example.invalid/v1/roster",
  "parameters": {"period": "REPLACE_WITH_PERIOD"},
  "credential": {"file": "/private/source-token"},
  "max_pages": 100,
  "max_bytes": 5000000,
  "timeout_seconds": 15
}
```

Alternatively use `credential: {"env": "CCF_SOURCE_TOKEN"}`. Only bearer
credentials are supported. They are loaded at execution time and are never
written to provenance. Credential files must be private regular files. Do not
put secrets in queries, source labels, IDs or export records. Query parameters
whose names suggest credentials are rejected; responses echoing the bearer
credential are rejected, including credentials hidden by JSON Unicode escaping. Duplicate source JSON keys are rejected before retention. No source credentials are distributed by this module.

Each HTTPS page must contain exactly `records` (array), `total` (stable integer),
and `next` (same endpoint URL, relative URL, or null). Pagination remains on the
exact scheme/host/port/path; redirects, proxies and private-network destinations
are forbidden. TLS certificate verification is required. DNS results are checked
and sockets pinned to validated public addresses to resist rebinding. Page,
aggregate byte and per-request timeout limits bound collection. Duplicate IDs,
changing totals, incomplete exports, repeated cursors, wrong periods, origins
and boundaries are rejected. Private-network sources need an explicitly reviewed
connector extension; there is no production HTTP/private-network bypass. Tests
alone use a code-only localhost HTTP option that the CLI/config cannot enable.

Vendor-specific authentication, payload translation, system permissions, and
verified source authority must be configured against the actual deployment.
This connector expects normalized exports; it does not claim native integrations
with vendors whose APIs have not been configured or exercised. Public HTTPS
behavior is exercised with an in-process HTTP test transport; deployment TLS and
provider access remain operational acceptance steps.
