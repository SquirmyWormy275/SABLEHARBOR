# Exact native configuration admission to backup datasets

`company_backup_admission` connects an existing configuration export to a declared
backup dataset without generating source facts or starting an audit. This first
slice accepts `configuration_export` originals from the existing persistent
configuration runtime. Other native schemas are unsupported. Ordinary
`company_backup_runtime.append_dataset` remains unchanged.

## Operator contract

First inspect explicit reviewed native pins:

```python
selected = inspect_source(
    source_root,
    source_pin=export_native_six_field_pin,
    source_definition_pin=original_configuration_runtime_six_field_pin,
)
```

The reader never discovers latest records or initializes a missing database. It
requires canonical private disjoint paths at admission, exact positive integer
versions, content hashes, and a native `configuration_runtime` version 1 whose
bytes equal the source's private `RUNTIME.json`. The export must identify the same
native company/branch, target, runtime definition hash and raw target hash.

The returned `source_store_id` is derived from the physical canonical root digest
and exact native definition pin. It is `LOCAL_ROUTING_IDENTITY_NOT_PRODUCER_AUTHENTICATION`,
not an asserted global/company-issued ID. Copying a database elsewhere creates a
different routing identity. A caller cannot substitute an arbitrary producer label.

`metadata_sha256` hashes canonical `{original, definition}` metadata: each contains
native six-field identity, event time, availability, origin and exact provenance
string. Import time and mutable authority journals are excluded. Original and
definition content are separately checked against their native hashes. The full
metadata bundle is limited to 256 KiB; export content to the existing 16 MiB backup
record limit; definition bytes to 2 MiB. Selected record sizes are checked before
loading blobs. Source reads use SQLite read-only transactions and before/after
private-file identity checks, not a globally atomic producer/consumer snapshot.

A reviewed action explicitly supplies the captured identity/digest:

```python
result = admit_dataset(
    runtime,
    expected_runtime_sha256=consumer_definition_sha,
    expected_revision=consumer_revision,
    command_id=immutable_command_id,
    dataset_id=declared_dataset_id,
    operator_id=configured_local_operator,
    event_at=explicit_consumption_timestamp,
    source_root=source_root,
    source_store_id=selected["source_store_id"],
    source_pin=export_native_six_field_pin,
    source_definition_pin=original_configuration_runtime_six_field_pin,
    expected_source_metadata_sha256=selected["metadata_sha256"],
    previous_pin=None,  # exact previous dataset native pin for subsequent versions
)
```

Inspection is a reviewable capture, not permission to silently replace expected
pins after a conflict. The dataset must already exist in the immutable consumer
inventory. Use BYTES for raw configuration JSON; JSON_RECORDS still requires the
existing record-array schema. Producer company/branch identifiers remain exact;
consumption does not assert entity equivalence, common service hosting or corporate
ownership. Definition event/availability must precede the export event; export
event/availability must precede or equal consumption. No event dates are inferred.

## Atomicity and replay

Admission uses the backup runtime's existing `_execute` CAS and command namespace.
The exact dataset bytes, nested `source_admission` dependency provenance, command
receipt and revision commit in one transaction. The dependency preserves native
pins, physical routing digest, selected metadata, consumer definition/runtime/dataset
and consumption time. It also records the executing admission/backup source-file
hashes, rechecked before the transaction can complete; these are not loaded-binary
or complete dependency attestation. No extra source system or second journal is
introduced. The result returns the new `source_pin` and exact retained `dependency`.

Originals are reread before a new transaction completes. Exact command replay
rehashes and revalidates current upstream originals, identity, metadata and local
operator before returning the historical receipt. The admitted consumer original and its
exact dependency provenance are also reread in a read-only snapshot; a missing or
tampered retained row prevents a successful replay response. A final source recheck
prevents a mutation between initial validation and replay return from being hidden. It does not choose the current
producer target or change the selected historical version. Changed inputs under
an existing command, stale consumer revision, wrong prior dataset, aliases, future
sources and source replacement fail. A failure inside the write transaction rolls back the entire consumer batch.
A failure during the final post-commit integrity check does not undo an already
committed operation: inspect it and replay the unchanged command after resolving
the integrity issue. Never infer rollback from the absence of a returned receipt. Existing source grants/access/collections are not changed.

These are trusted filesystem operator APIs, not authenticated service routes.
No grants, audit evidence, population acceptance, deployment, approved BIA/RPO,
whole-year completeness or professional testing credit is created. Event dates
remain authored local reference dates; actual import timestamps remain separate.

Tests generate genuine change/configuration sources and exports, then exercise
exact bytes and provenance, shared command collision, replay integrity, stale and
future pins, local operator/routing/schema isolation, prior-version correction,
source change during capture and rollback after native insertion.
