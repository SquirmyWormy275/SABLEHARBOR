# Local configuration change and release source pair

`company_change_activity.generate_pair(destination, *, repository, recipe)` accepts a
`ChangeRecipe(company_id, gated_branch, bypass_branch, cycle_id, period_start,
period_end_exclusive, local_requirement_basis)`. The destination must be new, under
an existing private nonsymlink directory. Source creation needs no engagement and
creates no grant. Reusing a destination is rejected; it never silently overwrites
or rerolls prior originals. Staged publication uses the existing durable private
publication helper.

The exact scoped owner/custodian is currently P005 and operating reviewer P002,
resolved from SH-ENG-001/002/003/004/006 assignments rather than invented people.
Assignments retain their proposed status. The public native control catalog and
runtime RT-OPS-02 change/patch/rollback design section are pinned references;
the latter explicitly says delegated design, not deployed. SVC-developer and the
Reno/Boise source site states are retained as design references only. The local
retry-budget rule is not an accepted corporate policy or professional test method.

Both branches share exact baseline, candidate, package/build and initial-test bytes.
The candidate configuration is 50ms ×3 attempts against a 120ms local limit. Actual
schema checks pass; their record explicitly says the combined-budget check was
omitted. Actual arithmetic peer review returns CHANGES_REQUESTED. One branch
blocks the candidate; the other explicitly bypasses the peer-review gate, applies
the candidate to an in-memory configuration target, and records its 150ms result.
Later review preserves that release and its observation. A 40ms correction gains
an exact-artifact review and combined-limit test before release. Rollback rehearsals
actually replace the local target with the pinned 30ms baseline, evaluate it, then
restore the corrected target. Nothing executes external code or touches a service,
network, system configuration, repository source, or production environment.

Records are original JSON with exact source/build hashes, typed source links,
dated event/availability times, actual import timestamps, code/recipe/source pins,
and explicit local-exercise/canonical-site qualifiers. Per-source identities and
all past releases remain immutable. This single change is not an enterprise or
full-period change population. SH-ENG-005 is explicitly NOT_EXERCISED: an ordinary
gate bypass is not recast as an approved emergency. No hidden case answers or
professional audit findings are generated.

Tests independently recompute package/configuration hashes and arithmetic, verify
all referenced originals and availability order, exercise wrong-artifact and
blocked-target protection, compare paired shared inputs, deny future releases,
and use real Engine activation/PBC/discovery/collection with exact-command retry.
The collection helper revokes only its newly created grants after completion;
source version rows remain identical and no generated world or testing credit is
created. Collection is a separate optional exercise, not part of generation.
