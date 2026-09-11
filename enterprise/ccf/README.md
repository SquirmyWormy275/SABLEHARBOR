# Native CCF preparation

This package normalizes the accepted CCF and local designs into a versioned, queryable preparation register, then executes public synthetic finance, identity and recovery examples. It implements the first preparatory tranche from the [September 11 audit](../../docs/internal/development/CCF_PREBUILD_REPOSITORY_AUDIT_2026-09-11.md). It is not a complete implemented CCF or an operating-effectiveness conclusion.

## Source authority and contents

Canonical Markdown and the existing business/runtime/service source registers remain authoritative. `registry.json`, SQLite, coverage reports and example outcomes are generated views. Do not hand-edit those outputs or treat their repetition as approval. `source/preparation.json` contains explicitly proposed engineering additions, policy dispositions and the decision queue; `source/examples.json` contains public synthetic actors, schedules and evidence. Neither source creates real appointments or institutional decisions.

The importer preserves 166 common control IDs, 124 objective IDs, 16 enterprise objectives, 27 risk IDs and 36 domains. It imports ten business local designs, 39 runtime local designs, and adds one proposed corporate identity implementation. Business scopes remain multiple references to the same local ID. The source service graph adds 57 services, 49 components, 49 dependencies and six named/selected counterparties, including the runtime successor's selected colocation brands. Selection is not contract execution or installation.

The 1,660 control/boundary applicability rows expand the existing ten-boundary domain matrix. Every row remains `PENDING_LOCAL_REVIEW`; even an inherited source `N/A` is a proposed scope disposition, not a permanent exemption. Control statements retain all required logical fields as values or explicitly reported unresolved fields. Fifteen controls have no explicit risk mapping in the existing partial traceability matrix; coverage names them. No missing risk rationale, control nature, key designation or professional conclusion is invented to complete a row.

Role IDs identify exact source role labels, including compound labels. They are not additional positions, named appointments or a new organizational structure. Normalized drafts cannot become approved/effective through this preparation adapter. Actual activation requires accepted authority and a later scoped implementation change.

## Run

From a full repository checkout with the existing Python development dependencies:

```bash
uv sync --frozen --all-extras
uv run python -m enterprise.ccf validate
uv run python -m pytest -q --import-mode=importlib enterprise/ccf/tests
uv run python -m enterprise.ccf build --output /tmp/sable-ccf-preparation
uv run python -m enterprise.ccf verify --output /tmp/sable-ccf-preparation
uv run python -m enterprise.ccf query --database /tmp/sable-ccf-preparation/registry.sqlite3 --as-of 2026-09-11 --known-on 2026-09-11
```

Build requires a new output directory and writes atomically after source and example validation. Outputs are `registry.json`, `registry.sqlite3`, `exercises.json`, `COVERAGE.md`, `MANIFEST.json` and `SHA256SUMS.txt`. Verification reimports native sources, reexecutes examples, compares complete database logical content and checks every member/hash. Rehashing a falsified PASS does not make it acceptable. Byte reproducibility is checked between clean builds on the same Python/SQLite runtime; SQLite byte identity across different engine versions is not promised.

A package is a complete scoped record/query export, not a standalone installation of the enterprise or a replacement for its governing source repository. Use the exact source checkout and implementation manifest for reproduction. Existing financial workbooks, source locks and release bytes are not rewritten; this preparation package does not author a financial workbook.

## Schema, history and joins

`schema.json` is the strict machine-readable v0.1.0 preparation contract. Envelope fields retain identity, version, effective interval, recorded date, source references, classification and unresolved fields; `data` maps logical business fields into typed relationships. Common-control `objective_ids` expands source shorthand into many-to-many native objective IDs. Risk `statement` preserves the original cause/event/impact narrative; separately structured cause/event/impact and scoped residual ratings stay unresolved. A derived observation date is not a claim that these normalized records were available in an earlier historical period.

`migrations/001_registry.sql` installs the append-only SQLite index. `database.append` requires a new record version for changed content, a later recorded date for a new snapshot, and retention of historical identities. Future-effective versions do not hide the previous version before their effective date. `database.historical(as_of, known_on)` separates effective time from knowledge time and retains retired records as addressable versions; an explicit end does not resurrect an older record. Unsupported/nonempty databases are rejected rather than overwritten. Database triggers block updates/deletes, and snapshot edges enforce native parent references.

The index is a derived query tool, not an authenticated production record service. Direct filesystem/database-administrator authority is outside its security boundary. The actor checks in the exercises model authorization with source-defined synthetic grants; they do not authenticate live users.

## Complete examples

[Procedures](PROCEDURES.md) explain source scope and actor separation.

| Example | Existing parent / implementation | Demonstrated negative behavior |
|---|---|---|
| Finance close | `SH-REV-003` / `LC-REVENUE` | Existing business assertions reject an unbalanced invoice journal. |
| Identity lifecycle | `SH-IAM-004` / proposed `SH-IAM-004-CORP-PREP-01` | Terminated/expired workers, mover access and orphan identities cannot pass lifecycle reconciliation. |
| Runtime recovery | `SH-BCM-003` / existing Reno runtime design | Backup hashes, restored content, dependency order, exercise RTO/RPO and deleted/held data suppression are evaluated. |

Each example has an independent expected population, a complete positive reference, a substantive negative reference, and a separate missing-attachment lifecycle. The latter produces NOT_RUN, an approved synthetic waiver, expiry/escalation, remediation submission, rejected self-review, and independent original-period re-performance. Restoring the original attachment can close that finding. The substantive failed case remains failed; this package does not rewrite late disablement or an unsuccessful restore into historical success. Review and closure retain original evidence identities. Waiver expiry remains visible while remediation awaits validation.

These are three bounded examples, not live vendor integrations or the full 7,560-occurrence business exercise. The finance adapter reuses `enterprise.operations.controls.evaluate`; recovery reuses the runtime restore/tombstone function. Production source connectors, authenticated workflow storage, all-domain policy population, actual owner review, longitudinal assurance and exact external mappings are subsequent tranches.

## Decisions and next tranche

The generated coverage report contains twelve policy dispositions and six decision packets covering material authority thresholds, risk appetite, information access/retention, legal execution, appointments and deployment commitments. None requires an answer to run this preparatory build. Routine technical mechanics remain delegated. Future work should refine each material decision into a scoped proposal when its implementation reaches that gate.

Next: review the 15 unmapped controls against native business risks; enrich accountable-role relationships and control-level applicability; populate richer policy/obligation/local-risk records; extend the source adapters to further business controls; then add assessment and external mapping layers. Keep actual contracts, tax elections, information policy and operating evidence in their explicit acceptance tracks.
