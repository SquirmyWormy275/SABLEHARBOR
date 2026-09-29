# Local quarterly risk-input assessment

`company_risk_assessment_activity.generate_pair(destination, repository=..., source_roots=..., recipe=...)`
creates two independent, explicitly fictional company branches before an audit exists. The destination must be new, private, and outside every input store. It creates no grants, audit, workpapers, risk acceptance, signatures, or board action. Reusing a destination is rejected; existing outputs are immutable history.

`RiskAssessmentRecipe` declares four `RiskSourceGroup` objects (`incident`, `provider`, `log`, `change`). Each group binds a separate physical source root, explicit producer label, exact `RiskSourceRef` native identities/versions/SHA256 values, and the selected metadata digest returned by `company_lifecycle_activity.read_inputs`. Producer labels are distinct from semantic group IDs. Nine original JSON records are retained byte-for-byte: incident monitoring/review, planned dependency inventory/vendor entry, publisher event/alert, and original release gate/release/later allowed gate. Reads use independent bounded read-only transactions; this is not a cross-store atomic snapshot.

The input ledger distinguishes observations from hypothetical risks. Unknown incident cause does not establish supplier outage. Selected providers remain nonoperating with no executed contract claim. The recorded later allowed release gate remains visible; a hypothetical recurrence is not described as an existing unremediated bypass. Publisher payload hashes are recomputed, alert links and producer/native identities validated, vendor membership checked against its exact inventory, and referenced chronology checked. Unselected support is not reconstructed or presented as obtained.

Both branches share the same ledger, two explicitly assumed `RiskScenario` objects and local ordinal method. Branch A imports both inputs. Branch B's importer configuration omits the internal-change input. Reconciliation compares actual imported input IDs with the independent ledger, records the missing input, and causes a dated configuration update and recomputed assessment. Original configuration, assessment and discrepancy remain. A's scheduled repetition explicitly reaffirms its unchanged selection rather than claiming a backfill. Each branch has six systems and ten immutable versions.

Likelihood/impact are strict integer factors 1–5; bools/floats are rejected. Their product is a local ordinal score, not an empirical probability. Projected residual scores remain conditional on proposed treatments; neither implementation nor acceptance is demonstrated. One UTC calendar quarter is supported, with ordered input/assessment/review/correction/quarter-end checkpoints. The slice covers two selected local inputs, not the enterprise risk universe.

Management assignments are explicit local bindings to the scoped technology/change contacts. Martin coordinates records, Helena performs record-quality reconciliation, and Rowan remains an independent assurance contact with no performed assurance action. Canonical pending appointment and operating-management authority qualifications are retained; no corporate policy or risk appetite is invented. Only SH-ERM-001 activity is represented.

Validation: `tests/audit_suite/test_company_risk_assessment_activity.py` exercises actual upstream generators, factor/domain rejection, native-link contradictions, source preservation and causal backfill. `test_company_risk_assessment_collection.py` activates fresh isolated engagements, issues owner-routed requests, denies future records, collects all initial and later exact versions, verifies replay, revokes temporary grants, and grants no procedure/testing credit.

The private September 14 run retains initial mixed-branch `v1` as historical. `aligned-v2/company` uses the existing incident-messy/provider-omission/logging-omission/change-release-b sources with input availability April 6; the assessment period remains April 1–June 30. These aligned component choices do not establish one coherent operating year. Its isolated collection receipt is `aligned-v2/collection-v1/RECEIPT.json`. Original inputs and previous audits are unchanged. Reproduction requires authorized local source roots and exact pins from its private RECIPE/SOURCE_ROOTS records; no private source content is included in this documentation.

## Prevented-attempt observation input

`RiskAssessmentRecipe.change_observation` defaults to `OVERRIDE_THEN_ALLOWED`.
The additive `BLOCKED_THEN_ALLOWED` option consumes the same nine-reference,
four-store contract with these changed native roles: the logging source supplies
`publisher_events/EVENT-1` and `detection_alerts/BLOCKED-OBS-1`; the change source
supplies `release_gate/GATE-PROPOSED`, `release_gate/GATE-CORRECTED`, and
`local_releases/RELEASE-CORRECTED`. All versions and native hashes remain explicit.
The logging producer must itself have consumed the same blocked gate, including
its exact producer label, native identity, content hash and publisher event hash.

This path requires a BLOCKED gate, later ALLOWED gate, informational blocked
observation and corrected release referencing the exact allowed artifact/gate.
The allowed authorization must be available before release; its embedded
availability reference must match the native instant. It does not substitute a
proposed release or invent an override alert. The ledger records a prevented
local attempt and no observed bypass. Future prevention failure remains an
explicit hypothetical scenario; likelihood/impact and projected treatment
scores remain local assumptions, not measured probabilities or acceptance.

Incident cause remains unknown and separate from planned, nonoperating provider
references. Both downstream assessment branches still receive the same input
ledger: the actual importer omission and later reconciliation/backfill supply
their difference. This extension does not generate actual sources by itself or
establish a coherent company year, employment, deployment or assurance.
