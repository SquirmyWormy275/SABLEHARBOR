# Explicit persistent configuration export

`company_configuration_export.export_current` explicitly copies the currently selected persistent target file into a new immutable CompanyStore original. The content is the exact raw file bytes: the native six-field pin's SHA equals the file SHA, not a JSON envelope digest. Export context lives in separate provenance and the command receipt.

This supplements earlier configuration operation records. Those records retain hashes and comparisons; they must not be described as copies of the target file. Existing originals remain unchanged.

The trusted local API requires `runtime`, `expected_runtime_sha256`, `expected_revision`, `command_id`, `expected_current_sha256`, `operator_id`, `event_at`, and `rationale`. The export uses the same configuration database transaction, global command namespace and optimistic revision as APPLY/DRIFT/ROLLBACK/RECONCILE. It registers `configuration_export`, appends one raw original and its receipt, and advances revision/event time atomically. It leaves the target file, file pointer and current SHA unchanged. Provenance distinguishes `prior_runtime_operation_at` from `exported_at`; the former may describe an earlier reconciliation, not a target change.

Exact replay returns the retained export after verifying its original bytes and current runtime integrity. Later target changes do not substitute a newer target for that original. Different command content, stale revision/hash, wrong operating identity, earlier event time, changed source pins, corrupt target bytes, or a mid-operation target/code change fail closed. The original file is reread independently before committing. Native source rows retain the usual immutable-version constraints and ordinary CompanyStore grant/read behavior; the exporter creates no grants, collections, audit records or model state.

This is an explicitly authorized local **export**, not release approval, emergency authority, deployment evidence or a professional conclusion. It neither corrects the target nor closes tickets. Operator identity is a trusted local API parameter, not an authenticated network principal.

## Maintained standalone CLI

Run `python -m tools.audit_suite.company_configuration_export --runtime <private-runtime> --action <private-action.json> --output <new-private-receipt>`.

The action has exactly `{kind: "EXPORT_CURRENT", parameters: {...}}`; parameters are the seven required API fields other than the runtime path. The receipt format is `COMPANY_CONFIGURATION_EXPORT_RECEIPT_V1`. Preserve committed outputs if separate receipt publication fails; exact replay must use the identical action and a new receipt destination.

Implementation pins for an actual run include this exporter, the configuration runtime, the export CLI, the configuration CLI (whose strict field set is imported), and the shared backup receipt writer, together with their maintained source-reading/publication dependencies. No actual export has been executed merely by adding this module or its temporary-fixture tests.
