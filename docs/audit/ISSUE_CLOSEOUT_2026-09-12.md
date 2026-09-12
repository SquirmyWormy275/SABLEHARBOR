# Outstanding issue review — September 12, 2026

Inspected main: `79437a778d4a4d5097a3cdaa36d7d8ab13217536`.
Worktree: `/home/kingoftheeast/Projects/SABLEHARBOR-issue-closeout`.
Branch: `cleanup/outstanding-issues-2026-09-12`.
This is a delivery/disposition record, not a canon decision or evidence of external execution.

## Delivered administration work

- Reopened #18 after finding it closed despite its residual acceptance criteria and latest
  comment explicitly requiring it to remain open. No tax/legal documents were changed.
- Set and read back repository description: “Sable Harbor: a synthetic enterprise and
  business-world sandbox with source-linked institutional records, models, and publications.”
- Set and read back topics: `business-simulation`, `institutional-memory`,
  `synthetic-enterprise`, `worldbuilding`. The public synthetic classification agrees with
  the existing [public repository policy](../governance/PUBLIC_REPOSITORY_AND_WIKI_POLICY.md).
- Restored `.github/workflows/publish-wiki.yml` with a dedicated export validator and
  manually dispatched publication from main. The [operator instructions](../../tools/wiki/README.md)
  describe prerequisites, exact revision links, page hashes, preservation of unmanaged
  pages, and post-push retrieval verification. The existing reader generators and
  validation workflow are untouched.

Live administration inspection: Wiki enabled; description/topics initially empty; no
rulesets; main protection endpoint returned “Branch not protected”; automatic branch
retirement disabled; no configured Actions secrets. The Wiki Git endpoint still returned
“Repository not found”. Main protections and branch retirement are not claimed complete.
Only this cleanup session's branch and CI runs may be managed under the current coordination
boundary; no other branch was deleted, reset, rebased or merged. Automatic branch deletion
was left disabled because branch archaeology is incomplete.

## Complete issue disposition

| Issue | Evidence and remaining acceptance | Disposition |
|---|---|---|
| [#11](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/11) | Metadata completed; Wiki exporter/workflow implemented. Live Wiki initialization, write credential and rendered-page verification remain. Main protection/check selection and branch archaeology require coordinated administration outside this session's own-branch boundary. | OPEN; partial implementation delivered here |
| [#18](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/18) | Issue body and latest comment retain parent-tax decisions and external execution. PR #142 supplied reading records, not executed instruments or elections. | Restored OPEN; legal publication mutations deferred to #145 owner |
| [#19](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/19) | [Accepted six appointments](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md); residual ROLE-39/41/50/55 occupants and exact appointment/biography histories lack separate approval. | OPEN; no names or dates invented |
| [#21](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/21) | [PR119 disposition](../../enterprise/runtime/DISPOSITION.md), R119-27: selected architecture/reference implementation, deployment qualification gated. [CCF audit](../internal/development/CCF_PREBUILD_REPOSITORY_AUDIT_2026-09-11.md) explicitly retains this issue's boundary. | OPEN; coordinated CCF/runtime work overlaps active session |
| [#22](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/22) | Same accepted reference implementation/audit; production source rights and integrated entitlement enforcement remain distinct. | OPEN; defer overlapping mutations |
| [#24](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/24) | [Generated-record lifecycle](../governance/GENERATED_RECORDS_LIFECYCLE.md) expressly excludes Alexandria retention/hold policy; CCF audit retains implementable lifecycle schedule and enforcement work. | OPEN; defer overlapping mutations |
| [#34](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/34) | PR119 reference security tests do not establish deployed Daedalus inference-leakage enforcement; the CCF audit retains the gate. | OPEN; defer overlapping mutations |
| [#88](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/88) | Exact approved HQ hash `2bf5a1209b9c3ece435271f2fbf5a3c827bbbccf242ea4ee60535749ccee9d92` remains missing. Recovery search below found no match. | OPEN; no substitute image generated or accepted |
| [#106](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/106) | [Program closeout matrix](../../geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md): precise sites/occupancy and Klein/Fort history remain incompletely evidenced. Current facility designs do not establish missing historical occupancy or survey rights. | OPEN; no evidence-backed whole-issue closure identified |
| [#107](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/107) | Same matrix: early coal/1954/abandoned alignments and detailed engineering remain. Accepted synthetic present-day railway is not historical route evidence. | OPEN; current geometry cannot be back-projected |
| [#108](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/108) | Same matrix: full semantic adjudication, raster evidence review, temporal asset histories and remaining map program are unfinished. Discovery counts are not completed adjudication. | OPEN; program acceptance not demonstrated |

This snapshot supersedes stale current-state interpretations of the September 3
[branch/PR register](BRANCH_AND_PR_REGISTER.md), while preserving its historical inventory.
PR #9 merged; #10 and #13 were superseded; #93/#105/#110/#118/#119 and #142 merged.
No ancestry-only branch deletion was attempted, and no historical source/binary audit
was represented as completed.

## Concurrent work preserved

- PR #146, `feature/ccf-evidence-intake-workflow`, its worktree and `enterprise/ccf/`
  remain with the CCF session. Private generated evidence packages were not inspected.
- PR #145, `review/overnight-human-evidence-2026-09-12`, its 56-source legal manifest,
  legal publications, reader generators and validation workflow remain with their owner.
- Billing PR #138 remains unapproved and unchanged.
- Compliance-Atlas was not modified or used for copying.
- Approved visual files and shared reader/catalog artifacts were not changed or regenerated.

## Exact HQ asset recovery

Hashed 606 image candidates from this refreshed checkout, Downloads and Pictures,
plus image members of `RED_WASH_APPROVED_VISUAL_ASSETS.zip`,
`SABLE_HARBOR_CODEX_CAMPUS_ATLAS_CLOSEOUT_R01.zip` and the downloaded
`sable-harbor-logo-system-v0.1.0.zip`. No matching binary was found. CCF directories,
private packages and other sessions' worktrees were excluded. This is a bounded recovery
search, not proof that the file does not exist in an external source or unsearched archive.

## Validation

The export produced 56 pages including `_Sidebar.md`, and converted 1,967 local links.
Five focused tests passed for navigation/image/reference conversion, fragments, code
preservation, invalid paths, deterministic output, source-checkout protection, page-name
collisions, checksum tampering, manifest path traversal and preservation of unmanaged pages.
Live Wiki publication remains unexecuted for the prerequisites above.
