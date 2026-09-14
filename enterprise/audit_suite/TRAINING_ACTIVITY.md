# Local role-based training source pair

`company_training_activity.generate_pair(destination, repository=..., recipe=TrainingRecipe(...))`
creates a **new private company store**, independent of audits. Existing destinations
are rejected. Source construction is staged and uses private publication rollback;
it creates no principal, grant, engagement, population, test or finding.

The recipe specifies two branches, one bounded cycle (at most 93 days), an explicit
2–24-person cohort with exact scoped snapshot role IDs, 1–8 local courses and their
required cohort roles, due/follow-up/completion times, and one assigned late target.
It requires at least two roles. IDs/roles must match actual organization snapshot
records. The current adapter requires an explicit `org_role_id` on each person;
it does not infer roles from names/titles or invent missing role assignments.

Public TRN-001 requires a role/worker-class course matrix and assignments. TRN-002
requires completion monitoring and overdue escalation. The source pair implements
these narrow record relationships using separate roster, matrix, assignment,
completion, monitoring and follow-up systems. Ownership follows scoped TRN-001,
TRN-002 and roster PPL-001 primary assignments. Snapshot identity/assignment status
is retained; it is not a real employment history or appointment acceptance.

Both branches have identical cohort/matrix bytes and role-derived assignments.
Monitoring occurs at the same two scheduled times: one hour after the due time and
one hour after the late completion time. The late branch has one outstanding course
at the first checkpoint, a subsequent dated follow-up, and a later completion. The
closeout still records that the completion was late. Each report references exact
source IDs, versions and hashes; it uses only completions available at that checkpoint.
The separate cohort supports reconciliation of assigned members against requirements,
not a claim of complete enterprise workforce coverage. Source content contains no
mode labels, hidden rubric, audit finding or professional conclusion.

All course rules, deadlines and activity are explicitly local synthetic exercise
assumptions, not accepted enterprise policy or real training completion. Company
source origin is `AUTHORED_TRAINING_SOURCE`; public source files, organization,
generator and recipe are pinned. Real import time remains separate from event and
availability time. No external training provider, accepted certification or paid
service is asserted. The initial retained pair covers one cycle; broader annual,
onboarding, course-change and joiner/leaver populations need separately scoped work.
