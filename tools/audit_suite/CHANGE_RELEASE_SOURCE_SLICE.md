# Local change/release source slice

The bounded source generator is `enterprise/audit_suite/company_change_activity.py`;
its API and limits are documented in `enterprise/audit_suite/CHANGE_ACTIVITY.md`.
A private paired example is retained under
`enterprise/generated/audit-suite/company-change-2026-09-14/`: RECIPE.json,
RECEIPT.json, VALIDATION.json, TESTS.xml, the `v1/` company store, and a separate
`collection-v1/` audit-state rehearsal with COLLECTION_RECEIPT.json.

Both branches start with the same configuration/build/test originals. One enforces
peer review; the other explicitly bypasses it, retains the resulting over-budget
local calculation, and later corrects it. Actual in-memory state transitions and
arithmetic produce the release and rollback records. This is a reference exercise,
not a production deployment, observed corporate operation, accepted policy, or
complete engineering change population. SH-ENG-005 emergency authority is not
exercised or implied by the bypass. Current contact assignments remain proposed.

Generation produced 32 immutable original versions in18 systems with zero grants
or collections. A separate fresh Engine rehearsal activated company-source mode,
issued PBC requests, denied future release access, and collected all15/17 originals
with exact native-byte/hash and replay checks. It created no generated world,
workpapers, findings, or testing credit. Source versions remained unchanged and the
rehearsal's temporary grants were revoked. Existing company/audit stores and local
services were not modified.

The source recipe is reproducible with the public `ChangeRecipe`/`generate_pair`
API into a NEW private destination. Existing destinations fail rather than overwrite.
No scheduled runner or HTTP generator is introduced by this slice.
