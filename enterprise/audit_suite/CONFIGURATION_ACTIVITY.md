# Configuration inventory and drift from original release records

`company_configuration_activity.generate(destination, *, repository, source_root,
recipe)` creates a NEW private source store. `ConfigurationRecipe` contains
`company_id`, `source_store_id`, `source_versions_sha256`, `branch_ids` (tuple),
`checkpoints` (ordered tuple of explicit-offset timestamps), and `local_asset_id`.
`read_originals(source_root)` returns verified source rows and the version-set digest
for a trusted operator to freeze. It opens the existing private SQLite source in
read-only mode, performs no schema initialization, and creates no grants or audits.

The adapter consumes exact original change source records: peer approval, approved
build/package and configuration, plus the latest release, released build and
configuration available at each checkpoint. Every nested original reference must
resolve by system/record/version/SHA and event/availability time. Package hashes and
release active-configuration hashes must match original configuration bytes. Input
versions are pinned before and after generation; changed input fails before publication.
There is no copying of hidden scenario material and no mode-based drift conclusion.

At12:30UTC in the February1 local change example, both branches have an actual
approval for the corrected40ms configuration. The first already runs it; the second
still runs the50ms bypassed configuration until13:00. The generated field comparison
therefore records50 versus40 and the actual150ms combined retry calculation. At14:00
both match the120ms desired configuration. The earlier drift snapshot is preserved.
The initial baseline has no asserted approval; comparison starts only after an actual
approved package exists. Missing/future approval or release prevents generation.

Each checkpoint produces original inventory, desired-state and drift JSON records.
Upstream links retain source-store/company/branch/system/record/version/SHA identities;
local drift records link the exact generated inventory and desired-state records.
Current CFG001/002 owner AS-P007 and operating reviewer AS-P008 are resolved from the
scoped organization snapshot and remain proposed contact assignments. Original
Reno/Boise not-deployed site statuses and SVC-developer design-only qualifications
remain explicit. Event time is the simulated checkpoint; import time is real.

The inventory is one in-memory reference target, not enterprise hardware/SaaS
completeness or actual deployment. No patch/lifecycle or secret management source
activity is exercised (CFG003/004), no corporate policy is approved, and no audit
sufficiency or materiality conclusion is computed. Existing source bytes/versions,
access journals and grants remain unchanged. Publication is a new private staged
store; same-destination repetition is rejected rather than overwritten.
