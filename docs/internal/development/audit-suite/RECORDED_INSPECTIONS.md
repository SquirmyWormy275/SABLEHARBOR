# Explicit evidence inspection records

Open an available evidence original and choose **Record an inspection**. Specify the
passage, page or section inspected, describe what you observed, and optionally link
an active procedure. Saving appends an attributed record against that exact original,
version and SHA-256. Downloading, previewing or comparing a file does not create a
record automatically. The record is the author's assertion, not proof of reading,
understanding, adequate testing or a passing conclusion.

Inspection notes remain visible beside the original, with author, recording time,
revision and ID. Lists are paginated. A rejected save retains the form text. Earlier
records are immutable; a later observation can refer to an earlier inspection ID
without rewriting it. Inspector and learner records remain separately attributable.

## Command contract

Use the ordinary engagement command envelope with exact command ID and expected
revision, kind `artifact.inspection.record`, and this payload:

| Field | Meaning |
|---|---|
| `artifact_id` | Exact currently available learner original |
| `sha256` | Exact retained SHA-256 |
| `version` | Exact integer retained version, or explicit `null` if none is recorded |
| `locator` | Required authored passage/section reference, at most 1,000 characters |
| `observation` | Required authored observation, at most 4,000 characters |
| `task_id` | Optional existing active scoped procedure |

The server rejects extra fields, hidden/quarantined/future originals, changed pins,
invalid or excluded tasks, and altered bytes. It reads and verifies the original
before and after constructing the record within the command transaction. Ordinary
membership, CAS and exact-retry rules apply. Completed retries do not duplicate a
record, including at the 10,000-record engagement limit. Tasks, conclusions,
workpapers, findings and grades are unchanged.

The stored record contains the original pins, authored text, `SELF_REPORTED_INSPECTION`
classification, actor, recording/simulation times, command ID, payload digest and
recording revision. Existing histories project an empty list; no historical access
is invented. Formal engagement backup retains these records with the audit state.

## Historical instructor comparison

Comparison at an explicit revision links each retained inspection to its exact
verified command payload, actor and event hash. The streamed history retains bounded
inspection payloads for this purpose. Unresolved or changed links are counted
separately. A context mismatch withholds the inventory. The UI separates the audited
actor's records from other actors and validates counts, identities and revision pins.

The absence of a recorded assertion does not establish that an original was never
inspected. These records do not assess learner comprehension or replace substantive
audit procedures, review, scenario calibration or professional judgment.
