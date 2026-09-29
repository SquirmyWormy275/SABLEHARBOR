# Configuration source extension

The new `company_configuration_activity` adapter derives one local target's inventory,
approved desired configuration, and field-level drift from pinned original change
records. It does not invent company systems or infer drift from a branch label.

Actual private output is under
`enterprise/generated/audit-suite/company-configuration-2026-09-14/`: RECIPE.json,
RECEIPT.json, VALIDATION.json, TESTS.xml and the `v1/` company store. Its source is
the existing `company-change-2026-09-14/v1` store. The source database bytes and
all source-version pins remained unchanged. Output comprises12 originals in6 systems,
with no grants, collections, audit state, models, or live-service changes.

At the first checkpoint both source branches have approved the corrected package;
only one has released it. Actual comparison reports50ms versus approved40ms in the
other branch. The second checkpoint matches after its correction; the initial drift
remains retained. This is a single in-memory target and a local synthetic release
exercise, not enterprise inventory completeness or observed production behavior.
CFG001/002 documentary/source relationships are explicit. CFG003/004 patching and
secrets are not exercised. Owners come from current proposed scoped assignments.

See `enterprise/audit_suite/CONFIGURATION_ACTIVITY.md` for the API, private input
pins, chronology rules, and exact-source reference structure. Generation is an
operator action into a new private directory, independent of audits; no automatic
runner or HTTP source-creation route was added.
