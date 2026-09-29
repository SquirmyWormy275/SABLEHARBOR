# Local dataset quality and correction

`company_data_quality_runtime.py` performs real, fixed-schema transformations of a newly supplied nonpersonal fixture dataset. It validates rows, joins an independently declared reference inventory, separates intentional date-window exclusions, groups accepted units, retains failed rows, and records explicit source corrections. It creates company originals independently of any audit. It does not create a prepared evidence pack, source acceptance, human approval, professional testing conclusion, or an enterprise population.

The directly exercised slices are SH-DAT-004, SH-REC-002 and SH-REC-003. Actor/time/command records support the local SH-REC-001 slice. Stewardship and nonpersonal classification are explicitly local declarations supporting a bounded SH-DAT-001 slice; they do not accept corporate classification policy or prove the enterprise dataset inventory.

## Independent declaration

`initialize(new_destination, repository=..., plan=..., raw_records=bytes)` requires a new canonical private directory. The exact plan fields are:

- `runtime_id`, `company`, `branch`, `dataset_id`, `owner_id`;
- `declared_at`, `input_at`, and `event_window: {start,end}` with explicit timezone offsets;
- `expected_record_ids`, explicitly the expected IDs **inside this half-open UTC window**;
- `reference_rows: [{entity_id,category}]`, an independently declared unique-key inventory;
- `maximum_units`, an exact positive integer local rule, and `local_rule_basis`.

The scoped canon assignment must identify the declared owner for all five cited controls. This is a local operator/steward assertion, not a manager's approval of data accuracy. Initialization pins the organization sources and maintained implementation files. Those source-file pins do not attest loaded binaries or every Python dependency.

Raw input is a finite, duplicate-key-free JSON array of 1–128 objects, at most 64 KiB. Each in-scope row should have exactly `record_id`, `entity_id`, `units`, and `observed_at`. Invalid row fields are retained and reported. Ambiguous JSON syntax or non-finite values are rejected before initialization. No production data, personal data, external data paths, SQL, expression language or dynamically imported transformation code is accepted.

## Operations

`execute(root, expected_runtime_sha256=..., expected_revision=..., command_id=..., actor_id=..., operation=..., event_at=..., rationale=..., parameters=...)` supports two operations:

- `TRANSFORM` takes `{input_pin}`: exact current native company/branch/system/record/version/SHA. It requires the query window to have ended. It validates every in-window row, rejects every row sharing a duplicate record ID, checks exact integer units (booleans/floats/strings are not integers), joins the reference entity/category, and retains source indices and row hashes. Valid out-of-window records are separately counted as intentional exclusions; other attributes of those excluded records are not asserted to have passed. Missing expected in-window IDs remain distinct from intentional exclusions. Future-dated source values are failures.
- `CORRECT` takes `{input_pin,replacements:[{index,before_row_sha256,replacement}]}`. The exact prior row hash and unique index handle duplicate IDs without choosing an arbitrary occurrence. There are at most 16 explicit replacements. The source row count is preserved, old raw bytes remain intact, and a new raw version is retained. Correction serializes all rows to canonical JSON: unchanged values remain unchanged, but whitespace/formatting may differ. A correction is a local operator assertion with rationale. It neither proves business accuracy nor reruns the transform automatically.

The initial and corrected raw records have native event and availability timestamps. A corrected version cannot be read before its correction time. Declared event/availability time is separate from actual import time, which is retained and verified against the command receipt. This distinction does not attest wall-clock truth or turn a fictional future period into historical production activity.

## Partial results and lineage

Derived rows, aggregate totals and the operation report all retain `PARTIAL_UNRELIABLE` when any in-scope row fails or an expected in-window ID is missing. Totals are named `accepted_rows_only_total`; failure exclusion never silently creates a complete total. `LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE` means only that the explicit local rules and declared denominator reconcile.

Reports retain input/reference/definition native pins, exact query window/timezone, raw/accepted/failed/excluded counts, failure indices and row hashes, missing raw expected IDs and missing usable expected IDs. Separate native systems retain definition, reference rows, raw bytes, normalized output, aggregate output and operation metadata. Historical failures and superseded transformations remain available. Correcting a source clears the current transform pointer until a separate new transform runs.

Every operation atomically commits all native products, immutable command receipt, current state and revision in one SQLite transaction. Exact replay verifies the full retained history, original metadata and result bytes, returns the existing receipt and produces nothing new. History validation independently recomputes transformations and corrections; a re-hashed false total does not become authoritative merely because its hash chain was updated. CAS, current source pin, configured actor, monotonic logical/actual import times, and final definition/code pins are checked.

Count, per-column, aggregate-byte and per-record limits are checked before materialization and after writes. A failed batch or final code/definition check rolls back the whole operation. No source grants, audit actions, model calls, policy delivery, acknowledgments, corporate decisions or automatic population acceptance are performed.

`inspect(root, expected_runtime_sha256=..., as_of=...)` validates the complete bounded history and returns current revision/state only if the cutoff is at or after that state's event. It is not a historical-state substitute. Ordinary CompanyStore access remains available with explicit current grants and its native as-of checks.

## Validation

`uv run --extra audit-suite pytest tests/audit_suite/test_company_data_quality_runtime.py`

Disposable tests exercise actual joins/totals and correction lineage; duplicate/unknown/missing rows; boolean/float/string unit rejection; exact UTC exclusions; partial-result preservation; corrected-version visibility; replay/CAS; failed batch rollback; malformed JSON; native/code/source tampering; re-pinned false result rejection; and bounded SQL metadata reads. No actual company or audit runtime is mutated by the tests.
