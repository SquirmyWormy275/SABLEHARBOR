# Company-source implementation checkpoint

The owner authorized execution of the overnight queue, preserving company canon, source locks, history and design intent. Work is in progress. This document describes implemented mechanics, not completion of all queued jobs or professional acceptance.

The [execution closeout](EXECUTION_CLOSEOUT.md) defines the finite remaining work:
exact procedure reconciliation, recorded inspection links, one combined paired
journey, company-period reconciliation and a consolidated acceptance packet. The
sections below retain successive implementation checkpoints; an earlier “queued”
or “not yet implemented” statement is historical when a later section records its
implementation. The structured queue controls current job status.

## Independent source ownership and migration

`company_store.py` retains private company/branch/system/record identities independently of engagements. Immutable versions preserve source bytes, provenance, event/availability timestamps and separately recorded import time. Explicit scoped grants govern discovery and exact retrieval; collections retain receipts. Corrections do not rewrite earlier source versions. The local operator CLI supports registration, grants, discovery, exact collection and verified backup/restore into new private directories. Restore revokes copied grants.

`company_migration.py` verifies retained legacy originals and unit pins before documentary import. It excludes hidden facts, actor beliefs, recipes and rubrics from the migration projection. Unknown business dates remain null. Documentary migration does not establish underlying operational activity or pretend historical source-system collection occurred.

`operating_source_bridge.py` reuses existing business/operations source inputs and model tables. The current bounded bridge imports commercial changes, service incidents, workforce changes and contract versions into explicitly isolated model-scenario branches. Monthly source periods remain intervals; conservative availability after month close is a disclosed bridge rule. Conditional forecast/planning qualifiers, original IDs, source hashes and provisional local custody remain explicit. This does not establish corporate SOC 2/HIPAA applicability for every imported business-unit row.

`company_population.py` exports a typed, source-scoped population in one consistent database snapshot, preserving exact record/version membership and row/native hashes. Source versions and distinct source records have separate counts. Pagination and independent manifest verification cannot silently omit earlier versions. Completeness is bounded to imported source records, not an independently accepted company population.

## Audit collection

The optional service connection uses operator-supplied `--company-root` and private `--company-bindings` JSON, mapping engagement IDs to company/branch. No caller supplies a filesystem path, alternative company, branch or simulation clock. Active grants and authenticated engagement membership remain necessary.

An instructor can issue `company.activate` on a configuring, ungenerated, bound engagement with no evidence, requests or selected scenario plans. It retains the binding, moves to readiness for kickoff and generates no evidence world. Existing generated engagements are not silently converted. Ordinary kickoff and issued PBC requests then support explicit discovery and `company.collect`, which retrieves a real source version and retains its original in audit evidence storage. Repeated collection of the same version for a request is deduplicated; corrections retain both versions. Binding changes require explicit reconciliation.

The browser PBC workspace exposes permitted company systems and source versions. Collected originals remain available through the existing evidence viewer/download and workpaper paths. `company_impact.py` compares observable current source versions with retained copies and reports only explicit downstream references; it does not automatically invalidate a conclusion. Company-persona context is bounded by both auditor grants and the meeting person's registered source ownership, with qualified original-source extracts and explicit sampling limits. It excludes prepared scenario knowledge in company-source mode.

## Protected key and contextual workspace

`instructor_key.py` migrates original scenario definitions into version-pinned explanatory records and an independently verified archive. Existing missing causal links and unvalidated professional judgments remain explicit. Service reads require engagement `instruct` permission; learner/reviewer access is denied. The current UI is an **unbound reference library**, not the active engagement's answer key or a learner grading system. Exact engagement/branch/history binding, completed causal authoring and professional calibration remain queued.

Navigation helpers validate links against authorized state, preserve bounded in-memory view context and clear it across authority/scope changes. The UI displays scope/period/role orientation, rejects stale async engagement responses, and provides grouped search and previews over permitted fetched records. It never searches hidden keys through learner context. Personal note/workpaper drafts now persist separately from formal engagement history. Debounced saves use current permission/scope checks and optimistic versions; reload recovers text, conflicts require an explicit choice, and formal saves clear the matching draft. Real local-service browser checks passed. Drafts have a separately invoked private backup/restore companion; ordinary engagement backups exclude them. Comprehensive saved workspaces and complete UX acceptance journeys remain in progress.

## Retained execution evidence

Private run root: `enterprise/generated/audit-suite/overnight-company-source-2026-09-13/`. `CHECKPOINT.json` links source, migration, browser, instructor and test receipts. The earlier owner walkthrough remains separate. The new source-workroom runs locally on port 8782; its access file is private. No external deployment or Atlas write occurred.

The initial operating-company-v1 browser receipt and stricter operating-company-v2 import/population receipts are separate snapshots; neither supersedes the other's executed evidence. Initial tests include 387 audit-suite cases passing, plus later focused checks for additions. Exact receipts, timestamps and source hashes govern what was exercised. Do not describe a reference archive, inventory or passing software check as a completed audit or an accepted professional rubric.

## Paired activity and latest verification

The [bounded mover lifecycle](AQ04_MOVER_SOURCE_COLLECTION_2026-09-14.md) creates company records before audit creation. Matched isolated audits collect ten original versions each; swapped mode labels do not change the observable rights discrepancy. This covers one transfer, not full-period or whole-control sufficiency.

The frontend has 70 passing helper tests after authorized source-reference navigation was added. Earlier real-browser receipts verify source collection, protected reference browsing and durable-draft recovery; later code changes require their own verification. Repository governance, organization and hygiene checks passed at this checkpoint. No professional review or owner usability acceptance is inferred from software checks.

## Bound explanations, workpaper inspection and background work

`explanation_binding.py` retains new private instructor snapshots pinned to exact company source identities/hashes and engagement scope, simulation time, revision and event history. Captured source access is distinct from retained audit copies. Authored claims/expectations remain separate, unvalidated interpretation; later work makes the snapshot historical, never silently rebound. The optional `--instructor-bindings` private configuration serves the protected bound explorer. Actual local-browser checks exercised source filtering, distinct event/availability/import timelines, retained-copy visibility and learner denial. The original unbound archive remains separate and unchanged.

`instructor_access.py` records authenticated key accesses in a separate private hash-chained log with exact successful pins and sanitized failure identities. Log or archive integrity failures prevent key delivery. This does not claim resistance to a privileged operator replacing both log and head, nor that access proves understanding.

The workpaper editor now places scoped procedures and retained evidence alongside its draft. Explicit original-text preview verifies the retained SHA and byte count, never executes native HTML, and falls back to original download for unsupported types. References are appended only by explicit user action and deduplicated. Actual browser checks verified preview, draft preservation, reload recovery, unchanged formal history and narrow layout. Table query/sort/page context persists in memory within the current viewer/engagement/scope; filtered record inspection supports previous/next without losing list position. Durable saved investigation contexts remain separate work.

`background_jobs.py` retains explicit meeting-message jobs privately, with bounded concurrency, immutable command identity, current authorization and observable pending/running/completed/failed/conflicted/interrupted states. The optional `--background-jobs` service flag preserves existing synchronous behavior otherwise. Reload can inspect the original queued question through an actor-owned route. Retries preserve the original command/revision; conflicts do not automatically rebase. Interrupted model computation can repeat after explicit retry, while ordinary command receipts prevent duplicate audit mutations. Mock-browser and real Engine route checks passed; the live-model background run has separate completion evidence and is not implied by these checks.

The identity-period generator also ran four complete 2027 quarters over two explicitly declared privileged scenario accounts in `company-identity-period-2026-09-14/full-year-v1/`. This is bounded source history, not a complete employee census or whole-enterprise control conclusion. Existing Q1/Q2 and mover snapshots remain unchanged.

The integrated audit-suite checkpoint ran 420 tests without failure; later binding/background and frontend additions have their own focused receipts. Broader repository checks ran 234 cases: 231 passed and 3 skipped. No owner feedback, professional calibration or full-scope audit acceptance has been invented.


## Resumed integration: saved context, recorded work and recovery

`workspace_context.py` and the saved-investigation UI persist explicit personal questions, next steps and exact record pins separately from formal work. Optimistic versions protect edits. Scope, source binding, acquisition settings and permission digests identify changed or previously unrecorded context; explicit review is required before links reopen. The original question and pins are retained. Actual browser receipt `context-status-browser-v3-receipt.json` verifies reload, exact artifact preview, current basis and unchanged formal revision. Earlier selector failures remain retained as separate receipts.

`audit_readiness.py` exposes authorized administrative relationships rather than an audit verdict. The work-status view retains procedure exclusions in its denominator, shows unassigned tasks separately, and links recorded requests, sources and workpapers. It rejects stale or foreign engagement responses and changed artifact SHA metadata. Actual workroom verification counted 70 controls and 407 assigned procedures, with two unassigned/outside-scope tasks. Missing requests and evidence links are workflow dependencies, not adverse conclusions.

The actual local-model background reply completed in 177.753 seconds while submission took 64 milliseconds and navigation took 75 milliseconds in that particular run. The reply cited an existing company source and distinguished its model month from its unknown event timestamp. This is an observed run, not a latency guarantee or a professional review.

The [companion recovery contract](../../../../enterprise/audit_suite/COMPANION_RECOVERY.md) adds saved contexts, inert job history and instructor access logs to separately invoked recovery components. The populated-workroom smoke at `complete-recovery-smoke-v2/VALIDATION.json` passed engagement, company, draft and companion backup/restoration into new private directories. Prior credentials remain revoked, replacement ownership is explicit, original formal state remains unchanged, and no job resumes automatically. Each component has its own snapshot time; this does not claim a globally atomic restore or a deployed disaster-recovery capability.

The [incident/continuity slice](AQ04_INCIDENT_CONTINUITY_SLICE_2026-09-14.md) supplements the bounded identity history with causally linked company records created independently of audits. Simulated response clocks and provider-selected/not-operating site qualifiers remain explicit. Broader operational coverage, instructor comparison/calibration and a fresh full-scope rehearsal remain unfinished.


The resumed integrated suite passed 484 tests with no failures, errors or skips (`integrated-resumed-tests-2026-09-14.xml`). Later documentary custody, instructor comparison and paired incident collection changes retain separate focused receipts until the next integrated run.

The [documentary custody import](../../../../enterprise/audit_suite/DOCUMENTARY_CUSTODY.md) now has an actual private 70-archive/359-original run at `documentary-custody-v2/VALIDATION.json`. Archive routing uses the original scoped control-owner assignments with explicit provisional custody qualifiers. Exact source hashes and null event timestamps were checked; the import created no collections or grants. This does not complete retroactive operating history. Subsequent collection rehearsals have distinct receipts.


A fresh 70-control SOC 2/HIPAA documentary rehearsal issued 70 requests to the scoped owners and collected all 359 company originals through the ordinary Engine/company collection path. Its separate receipt is `documentary-collection-rehearsal-1789424878848113435/RECEIPT.json`. Original source-version digests remained unchanged, no prepared world was generated, and no workpapers, findings, samples or testing credit were created. This validates documentary routing/collection, not the queued full operational audit rehearsal.

`instructor_comparison.py` and the protected comparison panel trace exact metadata links at an explicitly selected historical revision. Reports pin the original bound manifest and selected history/state separately, distinguish audited-actor commands from shared workspace activity, and withhold comparisons when scope/company context differs. The actual `comparison-browser-v1-receipt.json` verifies source links, expectation selection, learner denial and unchanged formal history. A selected revision is not labeled a submission; absent download events and typed expectation-to-procedure contracts mean inspection, understanding, judgment and grading remain unassessed.


The full repository checkpoint ran 742 cases: 739 passed, three skipped, zero failures/errors (`repository-resumed-checkpoint-2026-09-14.xml`). A subsequent focused route check verifies the new work-status capability advertisement; the browser hides that panel for older services that do not advertise it. The actual 359-artifact workroom check retained identical formal state/history at revision 501 while verifying pagination, search, preview navigation, opener focus restoration and narrow layout. Its receipt is `documentary-populated-browser-v1/receipt.json`. Training/backup source generators and explicit procedure-version links were added after that full-suite collection and require their own later checks.


## Source portfolio, explicit conversations and versioned procedure links

The [read-through portfolio](AQ_SOURCE_PORTFOLIO_READ_THROUGH_2026-09-14.md) connects independently retained documentary, identity, incident, backup and training stores through a private, pinned operator registry. The actual reference-v2 workroom exposes 107 source-system aliases and has retained 17 original copies through ordinary audit collection. Original physical company/branch/system/record/version/SHA identities remain distinct from aliases. The registry qualification explicitly states that these exercises do not establish a coherent full operating year. Cross-store populations and instructor snapshot binding remain unsupported until their semantics are implemented and verified.

Company conversations can now carry one to four explicit source-version/SHA pins selected from systems owned by the meeting contact and currently authorized for the auditor. Exact reads, bounded extraction and final pre-commit authority checks reject changed, future, revoked or unextractable records without substituting unrelated content. The default bounded sample remains available when no selection is supplied. A read-only check selected originals across all five source families at unchanged formal revision 33; it did not invoke a model. Background retries retain the original question and pins, while delayed completion and explicit restore protect newer composition. Separate real-model run evidence is recorded after completion, not inferred from unit or browser checks.

Workpaper versions now retain explicit same-control procedure IDs. An omitted update preserves links; an explicit empty list clears them on the new version. Historical links remain readable and do not complete a task or set an effectiveness conclusion. The isolated workpaper-procedure browser journey verified version changes and historical reporting while tasks stayed NOT_STARTED/NOT_RUN.

The [backup/restore slice](AQ04_BACKUP_RESTORE_SLICE_2026-09-14.md) and [training activity](../../../../enterprise/audit_suite/TRAINING_ACTIVITY.md) create additional original company records independently of an audit. The [activity operator](../../../../tools/audit_suite/COMPANY_ACTIVITY_RUNNER.md) runs explicit private recipes, checks native hashes, and creates no grants or audit records. The latest [coverage matrix](../../../../tools/audit_suite/CONTROL_SOURCE_READINESS.md) identifies explicit independent-activity references for ten of 70 scoped controls in the inspected stores. Sixty still lack such references; this is neither a failure conclusion nor a sufficiency determination.

The original port-8780 walkthrough was checked with a read-only browser harness. Absent backend capabilities now select a clearly labeled volatile draft fallback and omit unsupported procedure-link fields. The fallback preserves text while reopening within the same context but does not survive reload. Current services retain durable personal drafts. No old walkthrough state or source archive was converted.


The first [repository documentary sync](../../../../tools/audit_suite/REPOSITORY_DOCUMENTARY_SYNC.md) retained eight exact committed company documents in a new private company store. Original authority, revision/effective metadata and proposed collection custodians remain pinned. Business event dates are unknown and availability begins at ingestion; the run created no grants or audit collections. Native Markdown is now inspected and extracted as inert plain text, allowing original policies and charters to use the ordinary evidence and conversation paths. This does not establish policy execution.

Portfolio source-impact review now resolves exact physical/store/alias/registry identities, verifies the retained audit bytes, compares authorized old and later versions, and rechecks grants before returning results. It distinguishes unavailable comparisons from unchanged sources, preserves source-stated withdrawal/correction qualifiers and records per-source observation intervals. The UI rejects stale revision/context results and links exact retained originals. It does not claim a globally atomic snapshot or change previous conclusions.

The integrated source-portfolio checkpoint passed 575 audit-suite cases with no failures, errors or skips (`integrated-source-portfolio-2026-09-14.xml`). Repository-document ingestion, portfolio impact and timeout refinements have additional focused tests and are included in a later repository-wide run. The first real selected-training response reached the existing 180-second client cap while the shared local model was still generating, and no reply was committed. Local inference now permits an explicitly configured wait of up to 900 seconds while retaining the 120-second default; the portfolio uses a separate private 600-second configuration. Timeouts have a specific sanitized background status and never retry automatically. The original failed attempt is retained for the explicit retry record.


The explicit retry completed in 304.530 seconds (two sequential local model requests), committing revision 34 to 35. Its exact selected training-source citation was independently verified. The response correctly limited itself to the local assignment and the absence of completion/assessment fields, but omitted concrete course/cycle identifiers and dates. The existing conversation action handler also executed a scoped PBC follow-up, retained in the response receipt; that action did not inspect the other records it requested. Receipt `company-portfolio-2026-09-14/meeting-source-browser-v1/receipt.json` preserves both the timeout and successful attempt. The separate read-only source-impact browser compared 17 retained originals, reported eight later versions and zero unavailable comparisons, and left revision 34 unchanged. These checks do not establish professional response quality or whole-company coverage.


The later repository-wide run exercised 829 cases: 825 initially passed, three skipped, and one old capability assertion failed after portfolio impact became supported. That assertion was corrected to verify the supported pinned response and changed-registry denial; all seven targeted service/impact cases then passed. Both XML receipts are retained (`repository-portfolio-checkpoint-2026-09-14.xml` and `portfolio-service-impact-followup.xml`), with no unresolved failures; the full suite was not rerun after that test-only correction. The frontend has 100 passing tests, a passing production build and a passing full mocked-browser journey. Governance, organization, queue, catalog and repository-hygiene checks passed. Controlled publication generation retained all 133 verified originals without rendering changes.

## Original collection, reproducible censuses and factual conversations

The reference-v3 rehearsal collected 457 exact originals across 115 systems and six explicitly selected source components, without generating an audit world. The maintained [source-readiness inventory](AQ_SOURCE_READINESS_INVENTORY_2026-09-14.md) independently verified every retained original and all 690 historical states/events through revision 689. It separates 367 documentary originals from 90 qualified activity originals. Ten of the 70 scoped controls have explicit activity references in these selected components; the other 60 do not. These counts describe the selected corpus and recorded relationships, not sufficiency or a complete operating year. Later source exercises are not silently added to that inventory.

The [change exercise](../../../../enterprise/audit_suite/CHANGE_ACTIVITY.md) creates actual local configuration, build, test, approval, release and rollback records. The [configuration exercise](../../../../enterprise/audit_suite/CONFIGURATION_ACTIVITY.md) consumes those pinned originals to compare desired configuration with an observed local target at explicit checkpoints. Separate Engine rehearsals collected all 32 change originals and all 12 configuration originals; native hashes, future denial, replay and revoked temporary grants were checked. Their source records preserve proposed personnel assignments, local requirements and the absence of deployed infrastructure. The activity runner supports explicit recipes for both families; configuration requires an explicit existing source root and verifies its immutable version pin.

The [one-system census](AQ_SOURCE_RECORD_CENSUS_2026-09-14.md) queries a concrete company store through current audit authority, retains the exact original versions and records its query, cutoff, exclusions and manifest. A portfolio alias resolves to one physical store. Latest-version selection happens before event-window filtering; unknown event dates remain a separate undated stratum. Actual read-only exports returned four identity versions, two latest identity versions, and one undated repository document. The browser requires explicit review and provisional import. Optional background execution retains the exact query and command envelope across navigation and retry; it does not enable automatic import or acceptance. An actual background Engine test verifies retained original bytes, one completed attempt, replay and absence of population registration. Frontend verification passed 107 tests, the production build and the full mocked browser journey; actual browser collection has a separate receipt.

Conversation provenance now shows the exact saved question/source pins, citation identifiers and any scoped action actually executed by the Engine. Links resolve only to matching retained originals. The factual prompt asks for concrete source identifiers and dates before discussing limitations. One subsequent actual selected-source response completed in 318.492 seconds and correctly stated its local cycle, course, participant, recorded date, due date and absence of established completion. Its exact citation was verified. The existing action handler again recorded a scoped PBC follow-up; the reply did not inspect the requested additional records. This single run demonstrates an improvement for that question, not a general quality guarantee or professional acceptance.

The actual census browser rehearsal advanced reference-v3 from revision 689 to 690 for collection and to 691 for explicit import. Four original identity versions representing two distinct source records were verified byte-for-byte, alongside the retained command, manifest and complete 692-event history. The population remains provisional and audit task states are unchanged. Its receipt is `company-portfolio-2026-09-14/census-browser-v1/receipt.json`. The UI labels initial job acceptance as historical rather than leaving a stale pending-status claim after completion.

The first integrated census/configuration run exercised 667 cases: 666 passed and one private-mode fixture failed because the operator's restrictive umask prevented its intended public directory from being public. The fixture now explicitly sets that invalid permission. All 25 focused follow-up cases passed, including the corrected access-denial test, actual background census execution and independent census review. That review also hardened malformed timestamps/enums and their typed API errors, branch/principal isolation, metadata quotas, daylight-saving boundaries and retry after interrupted retention. Original failed receipts remain retained; later repository-wide validation is recorded separately.

A separate eight-component inventory explicitly adds one change branch and its dependent configuration branch, with their two existing collection engagements. Across these three audits it verifies 478 unique source versions (367 documentary and 111 qualified activity) and 482 retained artifact instances. The four extra instances are the identity census copies, not additional originals. Seventeen of 70 controls have explicit activity references in this selection; 53 do not. Zero retained originals are unmatched or ambiguous. Receipt `source-readiness-maintained-2026-09-14/run-v3-eight-components-review.json` reconciles the counts and confirms earlier inventory bytes and selected audit states remained unchanged. This inventory does not merge engagements or establish one coherent company period.

The subsequent [security-log exercise](AQ_SECURITY_LOG_COLLECTION_SLICE_2026-09-14.md) uses existing release-authorization originals to drive a local publisher and collector. A real filter omission produces a missing sequence and delayed detection; configuration correction and backfill preserve the earlier gap and 25,800-second delay. False claimed event hashes and altered bodies both fail reconciliation. The paired stores contain 32 versions across 20 systems, and separate Engine rehearsals collected all 32 originals with verified hashes/history and revoked temporary grants. The explicit recipe runner supports this source-dependent activity; 21 focused runner/source tests passed. This exercise addresses bounded SH-SEC-002 relationships, remains separate from the eight-component inventory, and does not establish deployed logging, clock synchronization or enterprise coverage.

The repository-wide census checkpoint passed 919 cases: 916 passed and three skipped, with no failures or errors (`repository-census-checkpoint-2026-09-14.xml`, 515.325 seconds). The earlier fixture failure and its corrected denial test are covered by this successful run. Later logging work has 23 passing focused integration cases, including actual paired Engine collection and rejection of output inside its original source tree. New lineage and portfolio-instructor work is tracked separately from this repository-wide checkpoint.

Population and sample-selection details now expose exact lineage: the recorded population version, hash-pinned original and query manifest, and workpaper versions that explicitly reference that original. Nested return paths preserve filters and unsent questions. Missing historical versions and changed hashes fail closed, including when refreshed authorized state changes an already-open detail. Shared evidence does not establish that selected items were tested. The frontend passed 111 tests, a production build and the full mocked browser journey; receipt `company-portfolio-2026-09-14/population-lineage-ui-implementation.json` records the checks without live audit mutations.

[Protected portfolio snapshots](../../../../enterprise/audit_suite/PORTFOLIO_EXPLANATION.md) now capture exact native source identities together with physical store, alias and registry pins. Capture retains separate source-operator authority, audited-actor visibility and retained-copy status, using per-component transactions and final access/routing checks. Instructor-only read/comparison routes distinguish colliding native identities across stores and reject changed routing. Twenty-two focused compatibility/access tests passed. A new private reference-v3 snapshot captured two existing sources at revision 691 with empty authored expectations; all audit/source databases, registry and live bindings remained byte-identical. This establishes source binding and access behavior, not a populated or calibrated answer key.

The [planned-provider intake exercise](AQ_PLANNED_PROVIDER_INTAKE_SLICE_2026-09-14.md) reads the exact canonical Reno/Boise provider-selection records. A configured omission produces missing diligence requests and a missed internal review; later backfill preserves the overdue review. Both branches retain draft contracts, nonoperating services, unresolved independence and zero obtained third-party support. No provider is accepted and no external request is sent. Forty-six original versions across 18 systems were collected through two isolated Engine rehearsals with verified histories and revoked temporary grants. The activity runner supports explicit provider recipes; 22 focused operator/source/collection cases passed. These records are pre-operating internal workflow, not vendor performance or assurance evidence.

The fresh reference-v4 rehearsal selects ten explicit components from the second reference branch and collects 520 originals across 146 systems. Its maintained inventory verifies all retained/native hashes and 815 history events at revision 814, separating 367 documentary from 153 qualified activity originals. Twenty-one of 70 scoped controls have activity references in this selection; 49 do not. Earlier source versions, registries and grants remain unchanged; additional grants belong only to this new engagement. The portfolio preserves independent-exercise qualifications and does not establish one coherent operating year. Receipts and the explicit inventory configuration are under `company-portfolio-2026-09-14/reference-v4/`.

The [private activity-plan runner](../../../../tools/audit_suite/COMPANY_ACTIVITY_PLAN_RUNNER.md) executes an explicitly ordered, bounded plan through the native activity operator. Dependent configuration/logging jobs consume the designated change job's verified originals, retaining resolved recipes and exact source/dependency hashes. Structural validation precedes generation; semantic failure preserves earlier completed outputs and marks remaining jobs unrun. There is no automatic retry or overwrite. Independent review added verification of every declared dependency, published-manifest identity and unambiguous source labels; 26 focused tests passed. The first private demonstration generated and independently verified 76 originals without an audit, grants, collection or model call. Its pre-review receipt remains historical; later runs preserve their own implementation pins.

New instructor expectations may explicitly name scoped task IDs. Snapshot binding validates those IDs against the issue's controls and current boundaries; comparison rechecks the selected historical scope and reports exact task-linked workpaper versions and source-artifact intersections. Legacy expectations remain unmapped, and source-only associations stay separate. Fifty-four focused backend tests passed. The protected UI displays full physical source/alias/registry pins, supports search by those fields and distinguishes authored procedure links from testing. Its 117 tests, production build and full mocked browser checks passed, including learner denial, incomplete-pin rejection and historical version matching.

The combined key/plan/provider integration passed 107 cases without failures, errors or skips (`integrated-key-plan-provider-2026-09-14.xml`). A second private activity-plan demonstration verified 76 new originals, 28 manifest members and 104 native reference occurrences using the reviewed runner; the earlier run remained byte-identical. Reference-v4 also now has a separately authored private logging explanation bound to 15 exact source versions and three existing SEC-002 procedures. Binding added no source grant or audit command and retained revision 814. It remains instructor-authored and unvalidated, with no grading or professional acceptance.

The [local worker lifecycle](../../../../enterprise/audit_suite/LIFECYCLE_ACTIVITY.md) consumes three explicitly pinned identity originals and creates a separate fictional worker's requests, approvals, account/grant transitions, expiry, access probes and correction records. Its 24 originals across ten branch/system registrations exercise bounded IAM-001/002/004 activity. A cached session survives directory disablement in one branch; explicit later revocation preserves the initial failure. Paired Engine collection retained all twelve originals per branch and revoked temporary grants. No canonical employment, vendor deployment or IAM-005/006 coverage is asserted. Independent review added post-read source identity/privacy checks and UTF-8 byte quotas; 18 focused tests passed. The single-activity CLI supports exact nested source references; the V1 multi-job plan explicitly excludes this different dependency contract.

[Streamed history inspection](IK_STREAMED_HISTORY_INSPECTION_2026-09-14.md) replaces full historical state-list retention only for instructor binding and comparison. Exact canonical history/prefix hashes, state/event integrity, selected historical versions and final authorization checks are preserved. The existing 815-event reference-v4 history matched its original key receipt in 32.78 seconds using about 111 MiB peak process memory. The public history API is unchanged. Actual read-only browser checks on port 8787 verified 15 bound sources, three authored procedure links, route-pin search and revision-814 comparison in 31.554 seconds, with learner denial and no formal state/history changes. This is measured engineering behavior, not instructor calibration or owner usability acceptance.

The integrated lifecycle/history/operator/plan/key checks passed 106 tests with no failures, errors or skips (`integrated-lifecycle-history-2026-09-14.xml`). The earlier operator/plan run retained one stale test expectation that every standalone activity must be a V1 plan kind; the test now checks the explicitly supported nine plan kinds, with a separate rejection test for the selected-identity dependency. All 46 operator/plan follow-up cases passed. No unsupported dependency was silently accepted to satisfy that assertion.

The protected Key now opens an exact retained audit original in the existing preview. Matching requires the listed artifact ID, available status, SHA, engagement receipt, native identity and complete portfolio routing pins. Back preserves search, source selection and focus. A read-only port-8787 check independently downloaded 1,178 bytes, verified the bound SHA and preserved all 815 formal history rows. The frontend passed 121 tests, production build and the full mocked browser journey. Private receipt `company-portfolio-2026-09-14/reference-v4-preview-browser/receipt.json` records this separately from the earlier comparison check. Captured native-source grants do not authorize present access; no new source fetch or grant occurs when inspecting a retained copy.

The maintained read-only inventory at `source-readiness-maintained-2026-09-14/run-v4-lifecycle/` combines the exact reference-v4 selection with the separately collected lifecycle-b branch. It verifies 532 originals and retained copies across eleven selected components: 367 documentary and 165 qualified activity versions, with activity references for 24 of 70 controls. All retained copies match, with zero unmatched or unmapped versions. This is a two-engagement inventory of independent exercises; reference-v4 itself remains at 520 originals and revision 814. No coherent operating year or procedure sufficiency is inferred.

The [non-human identity slice](../../../../enterprise/audit_suite/NONHUMAN_IDENTITY_ACTIVITY.md) creates a separately declared local backup-copy identity from four exact prior backup originals. Its constrained authenticator, credential rotation, consumer configuration, actual copied bytes, reconciliation and quarter-end checkpoint produce 35 native versions across sixteen branch/system registrations. An omitted consumer update causes an actual denied copy with no output; correction succeeds, and retired credentials remain denied. Paired collection retained all 18/17 branch versions through explicit observation times, then revoked temporary grants. Original human principals, inner dataset dates and deployment qualifiers remain unchanged. Fourteen source/collection tests passed; the standalone runner supports this selected-reference recipe while V1 plans remain explicitly limited to their existing dependency kinds.

The [dependency and declared-period report](AQ_SOURCE_DEPENDENCY_PERIOD_RECONCILIATION_2026-09-14.md) verifies explicit logging/configuration upstream links and native IAM review roles against exact selected sources. The [trusted read-only command](../../../../tools/audit_suite/SOURCE_DEPENDENCY_RECONCILIATION.md) uses existing scope, registry, actor and source grants, with no audit-store initialization or command path. Independent review fixed boolean/float versions matching integer source versions, caller-plan mutation causing inconsistent hashes, and the CLI's initial use of a schema-initializing store constructor. Regressions reject those cases and leave even an invalid empty audit database untouched. Current actual CLI output `reference-v4/dependency-period-cli-v4/` verifies 24 sources, eight exact links and consistent plan/report/manifest pins, with unchanged audit state and event metadata. Four quarterly role sets still cover only P014/P015; no full-year company coherence, row-level review reconciliation or population acceptance is inferred.

Source and Key panels now retain their visited state across ordinary navigation within the same viewer, engagement, scope, authority and source context. Initial visits remain lazy, so an unvisited private Key is not fetched. Initial source loading and pending comparisons have truthful accessible status messages. Actual read-only verification with 146 systems reproduced the earlier context loss and verified the fix, including keyboard traversal, source selection and an in-flight revision-814 comparison; formal history was unchanged. The frontend passed 121 tests, production build and the full mocked browser journey. The private before/after receipts are under `company-portfolio-2026-09-14/reference-v4-context-review/`.

The reviewed non-human/dependency/operator/plan integration passed 97 cases without failures, errors or skips (`integrated-nonhuman-dependency-reviewed-2026-09-14.xml`). Earlier 84-case and 22-case receipts remain separate historical checkpoints. Broader full-period operations, procedure execution and professional/owner acceptance remain open.

The subsequent maintained inventory `source-readiness-maintained-2026-09-14/run-v5-nonhuman/` adds the separately collected service-b branch. It verifies 549 native versions and exact retained originals: 367 documentary and 182 qualified activity versions, with explicit activity references for 25 of 70 controls. Twelve components and three audit snapshots remain independent; copy-output versions are not additional business identities. There are zero unmatched retained originals or unmapped source versions. Previous inventories and reference-v4's own collection remain unchanged.

The isolated repository checkpoint at `f3b4da4` passed 1,051 tests with three skips
and no failures or errors (1,054 cases, 644.011 seconds). Its private XML receipt is
`overnight-company-source-2026-09-13/repository-f3b4da4-isolated-2026-09-14.xml`.
Later changes have separate focused validation; this checkpoint is not a claim
that every subsequent working-tree revision received a repository-wide run.

The [native IAM review reconciliation](AQ_IAM_NATIVE_REVIEW_RECONCILIATION_2026-09-14.md)
adds optional exact member, decision, application and HR checks to the existing
read-only report. Current `reference-v4/dependency-period-v6/` selects 34 originals;
all four membership hashes and eight population-reference hashes match. Missing-person
sets are recomputed from explicitly listed support. Event time remains separate
from availability, and recorded removal decisions do not establish removal execution.
This remains the declared two-person inventory, without enterprise completeness,
population acceptance or procedure credit.

The [risk assessment exercise](../../../../enterprise/audit_suite/RISK_ASSESSMENT_ACTIVITY.md)
consumes nine exact incident, provider, logging and change originals. A configured
input omission produces an actual assessment discrepancy and later backfill while
preserving the earlier records. Its aligned private v2 retains 20 originals across
two branches, with all originals collected through separate engagements and temporary
grants subsequently revoked. The input ledger distinguishes unknown incident cause,
nonoperating providers, corrected historical change events, hypothetical future risks
and proposed treatments. Only SH-ERM-001 activity is represented; no risk acceptance,
implemented treatment or coherent operating year is inferred. The standalone runner
accepts an explicit private four-root map; the V1 plan retains its narrower supported
dependency contract.

The combined risk/IAM/readonly-operator/plan validation passed 125 tests,
without failures, errors or skips (`integrated-risk-iam-review-2026-09-14.xml`).
The actual trusted CLI also ran the 34-source IAM plan into a new
`reference-v4/dependency-period-cli-v6/` report, retaining exact plan/report pins
and unchanged audit database bytes. Its receipt is `DEPENDENCY_CLI_V6_RECEIPT.json`.

The maintained `source-readiness-maintained-2026-09-14/run-v6-risk/` inventory verifies
559 originals and retained copies across thirteen components and four independent
audit snapshots: 367 documentary and 192 qualified activity versions, with activity
references for 26 of 70 controls. All retained originals match; no source is unmapped.
An independent read-only verifier checked all selected native and retained bytes and
preserved the preceding inventory. Its private review receipt records a postpublication
wrapper return-shape error separately from the successfully verified output. These
counts do not merge component histories or establish a coherent operating year.

Independent operator review corrected normalized single-source output containment:
paths containing `..` now fail before recipe reads or staging inside an original
source directory. Five regressions preserve source bytes and directory timestamps;
all 72 focused operator, plan and risk checks passed after the fix. Multi-root
containment already rejected this case.

The [existing-source linked runner](../../../../tools/audit_suite/COMPANY_ACTIVITY_LINKED_PLAN.md)
adds explicit multi-source routing for lifecycle, non-human identity and risk recipes.
Its [selected-source resolver](AQ_LINKED_ACTIVITY_SOURCE_RESOLVER_2026-09-14.md)
checks original operator manifests, exact native versions/content/metadata and event
availability before the declared consumer cutoff. Earlier external inputs and
completed outputs are rechecked after later jobs. Failed published outputs remain
identified and, when safely readable, their manifest bytes remain pinned without
becoming accepted dependencies. Review fixed alternate path spellings, changing
plan reads, omitted failed-output inventory and late changes to prior inputs.

The reviewed linked-runner/resolver/V1 compatibility integration passed
58 tests without failures, errors or skips
(`linked-plan-reviewed-integration-2026-09-14.xml`). An actual trusted CLI run under
`linked-activity-workflow-2026-09-14/run-v1/` completed two consumers: 24 lifecycle
and 35 non-human identity originals. All run/job manifest members and original
producer members were independently verified. It used fresh operator reproductions
of the prior identity-period and backup recipes, with distinct operator manifests
and explicitly verified selected metadata; historical originals, previous recipes and audits were unchanged.
`VALIDATION_V1.json` preserves the receipt. No audit, grant, collection or model call
was created, and these uncollected copies do not change the maintained 559-original
inventory.

This V2 contract requires existing preserved operator outputs. It does not accept
legacy direct-generator directories or source-job references to future outputs;
configuration/logging whole-store dependencies remain in V1. Native producer-output
routing needs an explicit contract binding the newly completed producer manifest.
The selected metadata digest excludes imported_at and can match across reproductions;
it is distinct from the full database/manifest pin. Neither execution ordering nor
successful reproduction establishes a coherent company year.

The [V3 producer plan](../../../../tools/audit_suite/COMPANY_ACTIVITY_PRODUCER_PLAN.md)
now joins native producers and consumers in one ordered run. Selected consumers
retain caller-specified record/version/content hashes and explicitly opt into one
metadata capture after verified producer completion. Resolved recipes and metadata
are frozen for every later check. A separate whole-change mode reuses the V1
configuration/logging snapshot contract and native event/checkpoint timing rules.
The selected metadata includes origin/provenance but excludes imported_at; a changed
source revision can change that metadata while the native payload stays identical.
V1 and V2 retain their original contracts.

A comprehensive actual CLI run completed eleven activities and eight source edges,
producing 381 native versions across 174 paired branch/system registrations.
Independent checks verified every native content hash, run/job manifest member,
resolved recipe and unchanged historical recipe source. Initial output remains at
`linked-activity-workflow-2026-09-14/comprehensive-v3-run-v1/`. An explicit successor
aligns the lifecycle sponsor references to year-messy for reference-b: exact HR and
directory payloads remain the same, while the original application version retains
its additional right. The earlier clean-branch selection is preserved in the first
run. No source field or historical record was rewritten to hide that difference.

The successor `reference-b-v3-run-v2/` again completed all eleven jobs and 381
versions, with zero grants or collections. Its independent read-only verifier
recomputed all six selected-group metadata hashes and checked their intended
reference-b branches, alongside the two whole-change edges. The receipt is
`REFERENCE_B_V3_VALIDATION_V2.json`; the exact recipe adjustment is retained in
`REFERENCE_B_ALIGNMENT_RECIPE_V1.json`. These are company activity outputs before
an audit; they do not change the existing 559-original collected inventory. Paired
unselected variants, enterprise-period sufficiency and a coherent full company
year remain separate from this selected dependency alignment.

The integrated V3/capture/V2/resolver/V1 checks passed 87 tests with no
failures, errors or skips (`producer-plan-integrated-2026-09-14.xml`). Independent
review separately passed 29 current V3/capture cases and Ruff. All prior run and
validation receipts remain preserved.

[Company runtime initialization](../../../../tools/audit_suite/COMPANY_RUNTIME_ACTIVATION.md)
now preserves sealed activity capsules while providing writable company sources for
audit access. It verifies each exact capsule, reads native rows through a bounded
read-only snapshot and copies only original systems/versions into a fresh
application-owned schema. Original event/availability/import timestamps, provenance,
content and command digests remain exact. No source schema, triggers, grants,
collections, access history or audit state are copied. Initialization has its own
receipt and runtime identity, separate from the historical source fields.

The actual CLI batch initialized eleven private company stores from the aligned
V3 run: all 381 native versions and 174 paired systems matched every source field.
All runtime grants, collections and access journals were empty at initialization;
all sealed capsule members remained unchanged. The private receipt is
`company-runtimes-2026-09-14/reference-b-v1/BATCH_RECEIPT.json`. Its seed database
hashes are point-in-time observations; authorized runtime journals subsequently
change those writable databases. They do not invalidate the original capsule
manifests. Existing company connectors and owner-scoped collection use the runtime
paths, with no prepared audit world or model invocation.

The integrated initialization/collection/source-resolver/capture checks passed
44 tests without failures, errors or skips
(`runtime-activation-integrated-2026-09-14.xml`). Independent review separately
passed all 17 initialization/collection cases, including real Engine/federation
collection, future/revoked access denial, exact record preservation and unchanged
capsules after runtime journals changed. Source descriptor closure, unmanifested
SQLite sidecars and fresh-schema boundaries are verified. The source/runtime
separation creates no operating, employment, deployment or assurance conclusion.

The successor private `company-portfolio-2026-09-14/reference-v5/` collects from
the eleven writable company runtimes and two existing documentary archives. Its
single fresh engagement retained 559 exact source versions across 13 components
and 165 systems: 367 documentary originals and 192 qualified activity originals,
with 536 distinct content hashes. Equal bytes do not collapse distinct native
source identities. All 893 audit history events and successful command replays
verified; an early access attempt was denied, and the same source became
collectible after an explicit clock advance. The 2027 audit period was unchanged.

`RECEIPT.json`, `VALIDATION.json`, `FUTURE_DENIAL.json` and
`inventory-v1/MANIFEST.json` preserve that run. Independent verification confirmed
all 381 runtime native rows still match their sealed capsules, every capsule member
is unchanged, and prior grants were preserved. Authorized grants and collection
journals belong to the new runtime and engagement. This is a new collection from
company sources, not an audit evidence-pack import.

The inventory has explicit activity references for 26 of 70 scoped controls,
with zero unmatched retained originals or unmapped selected source versions.
These remain separate component exercises with different periods and declared
populations; a coherent operating year, population sufficiency, substantive
testing and professional acceptance are not established. Earlier inventories
and audits remain preserved.

The isolated full repository check at `0cf0934` passed 1,156 tests with three
skips and no failures or errors (`repository-0cf0934-isolated-2026-09-14.xml`).
The subsequent runtime initialization change at `41c3f8b` is covered by the
44-test integration result above; it is not included in that earlier full run.

Reference-v5's instructor snapshot binds 15 exact retained source versions and
three authored task links at revision 892. The actual read-only browser check
verified all 165 authorized systems, original-byte previews, exact portfolio
routing, retained panel context and Back focus. Learner access to the Key was
denied, with no automatic protected fetch or protected content in the page.
Compact audit state, history and membership remained unchanged. The private
receipts are `reference-v5/KEY_V1_VALIDATION.json` and
`reference-v5-browser/receipt.json` under `company-portfolio-2026-09-14/`.
The Key remains instructor-authored and unvalidated; linkage creates no grade
or assessment conclusion.

[Access-remediation activity](../../../../enterprise/audit_suite/ACCESS_REMEDIATION_ACTIVITY.md)
now extends one exact quarterly owner decision through local permission execution,
a distinct operating check, escalation and correction. Its two new continuation
branches retain 22 versions across 12 systems. A missing permission-name mapping
leaves the excess entitlement usable in the first check; the correction removes
it and a later check denies that permission. Both branches preserve the same
original decision and the unresolved population omission. Earlier quarter records
are not rewritten, and operating checks do not imply independent assurance.

The actual private operator run is
`company-access-remediation-2026-09-14/operator-v1/`, with independent native-byte,
lineage and authorization-probe checks in `VALIDATION_V1.json`. All five original
source inputs and the sealed identity capsule remain unchanged. The operator
created no grants or audit. Existing-source V2 and explicit producer V3 routing
use the recipe's `input_at` cutoff and preserve their exact-source contracts.

The routing regression batch passed 84 tests; the subsequent reviewed native,
operator, collection and runtime-initialization integration passed 40 tests.
Receipts are `access-remediation-routing-integration.xml` and
`access-remediation-reviewed-integration.xml`. Independent review found and
closed malformed population-query and chronology cases, including predecessors
published after the decisions that purported to use them. These checks validate
a bounded fictional continuation, not enterprise-period coverage or sufficiency.

The separate actual rehearsal initialized `runtime-v1/` from that capsule, then
collected all 22 historical versions through federation into two isolated local
Internal assessments. Future and revoked access were denied; exact command
replays added no duplicate collections. All temporary grants were revoked after
collection. Independent reopening verified every retained original hash and all
sealed capsule members. `collection-v1/RECEIPT.json` and
`collection-v1/POSTRUN_VERIFICATION.json` retain the checks. The existing
reference-v5 audit and its 559-original inventory were not changed by this run.

The optional [local removal reconciliation](AQ_ACCESS_REMEDIATION_RECONCILIATION_2026-09-14.md)
connects exact selected parent-review originals to request, resolver, execution,
state and operating-probe versions. Observations distinguish consistency,
missing selected support and unsupported metadata verification; they do not
close the parent review or accept its population. The actual trusted CLI report
under `company-access-remediation-2026-09-14/reconciliation-v1/report/` read
16 native versions without changing audit work. Independent SQL verification
compared all 86 parent/remediation runtime versions with sealed originals and
confirmed the remaining-access and corrected-state observations. Temporary
report-context grants were revoked.

The production report was published successfully. Its historical private wrapper
then used `MANIFEST.members` instead of the report's `MANIFEST.files`; that
post-publication error and original output remain preserved.
`POSTRUN_VERIFICATION.json` independently checks retained hashes and source facts,
with the initial audit-database comparison explicitly limited to the assertions
reached before that wrapper error. No separately retained initial digest is
invented. Later reports add active analysis/parser source-file pins and reject
changes before publication; historical reports keep their original manifests.

Native JSON parsing now rejects duplicate fields at every depth, non-finite
numeric constants and exponent overflow before analysis. Matching raw-byte hashes
do not resolve conflicting semantic fields. The shared strict parser preserves
ordinary finite JSON numbers; these are parsing checks, not model or grading calls.

The A reference path now has explicit blocked-attempt logging and risk support.
Logging consumes the blocked and later allowed gate, retains the exact corrected
release, and records an informational blocked observation only after actual
ingestion. Risk retains the prevented-attempt observation separately from an
authored hypothetical future failure. The override path remains supported; no
blocked attempt is relabeled as an observed bypass.

The new private `linked-activity-workflow-2026-09-14/reference-a-v1/run/` completed
eleven V3 jobs with 381 paired versions and eight verified dependency edges. Its
explicit A selection contains 189 versions, with clean-selected identity and
backup inputs and A-derived change/log/risk references. Genuine preparation
capsules and expected native hashes are retained; selected metadata is captured
once and then frozen. All 115 retained B predecessor files remained unchanged.
The receipts record base revision `9901aef` plus then-uncommitted logging/risk
extensions and exact source-file hashes, rather than claiming the extensions
were included in that earlier commit.

Eleven separate A company runtimes preserve all 381 native versions. The fresh
`company-portfolio-2026-09-14/reference-a-v1/` audit collected 556 exact originals
across 13 components and 165 systems: 367 documentary and 189 selected activity
versions. All 890 history events, future-access denial and exact command replays
verified. The inventory has explicit activity references for 26 of 70 controls
and zero unmapped or unmatched selected originals. Its receipts preserve source
capsules and prior context; the B audit remains separate. This establishes
selected dependency alignment, not coherent whole-year operations, full scoped
population coverage, professional assurance or owner acceptance.

The combined paired-source/remediation integration passed 192 tests before the
subsequent strict-parser followup. The isolated full repository run at `9901aef`
passed 1,197 tests with three skips and no failures or errors; that earlier
checkpoint excludes these later logging/risk/report changes. Receipts are
`paired-profile-remediation-integrated.xml` and
`repository-9901aef-isolated-2026-09-14.xml`.

The strict-parser/source-pin followup passed 34 integration tests; independent
review separately passed 59 current reconciliation/parser cases. These include
ordinary finite JSON, duplicate fields, non-finite constants and exponent
overflow. The final receipt is `strict-native-json-final-integration.xml`.

[Runtime session isolation](SERVICE_SESSION_ISOLATION_2026-09-14.md) gives each
private audit runtime a stable opaque cookie name, so local reference viewers
on different ports can remain signed in within one browser. Login/logout APIs,
HttpOnly/SameSite/secure settings, bearer access and CSRF checks remain in force.
Twelve focused service tests passed. Existing services were not implicitly
restarted; upgraded runtimes require sign-in with the existing credentials.


The A viewer now runs locally on port 8789 from backend checkpoint `cfa19ce`.
Its private instructor binding pins revision 889, fifteen exact security-log
originals and three authored procedure links. The binding remains instructor-authored
and unvalidated. Actual browser verification checked all 556 originals in the PBC
file table, 165 authorized systems, exact original download/preview, return focus
and search continuity. Learner access to the Key was denied, with no hidden
content fetch. Formal state, history and membership remained unchanged.
Private receipts and four reviewed screenshots are retained under
`company-portfolio-2026-09-14/reference-a-v1-browser/`. The original walkthrough
and B reference viewer remain available separately.


New company collections now record their intake as `COLLECTED_COMPANY_SOURCE`;
query and derivation packets use `COMPANY_SOURCE_DERIVED`. A dedicated trusted
adapter path supplies this classification after source validation. Generic
uploads cannot acquire that classification by supplying a source-kind field.
Native synthetic provenance remains separate. Historical artifact manifests
retain their original intake labels and bytes; the viewer labels intake and
native source provenance separately. Fifty-three focused collection, fault-path
and classification tests passed.

[Recorded evidence context](CONTEXTUAL_WORKSPACE_WORKFLOW.md#implemented-recorded-evidence-context--september-14)
now connects originals to requests, controls, procedures and exact workpaper
versions, with explicit personal-draft attachment and safe return navigation.
All 126 frontend tests, the production build and mocked-browser regressions
passed; the actual A viewer also passed read-only source-context navigation.


The [explicit operating-period ledger](AQ_SHARED_OPERATING_PERIOD_LEDGER_2026-09-14.md)
records a local inventory and individually declared scheduled occurrences before
the period. Due reports show missing observations independently of received
source records. Operators can preserve skips, source-backed assertions and later
corrections with exact predecessor pins and optimistic version checks. The
ledger does not execute the operation or infer that selected records establish
inventory relevance, completeness or effectiveness. A separate native business
adapter must produce and reconcile those results.

The trusted CLI creates only new private ledgers, appends explicit actions to
existing stores and publishes read-only reports outside source roots. Strict
input parsing, physical-route binding, separate declaration/occurrence history,
time visibility and immutable reporting are covered by focused and independent
review checks. This is a foundation for period coverage, not completion of AQ-04
or AQ-06.


The operating-period foundation passed 39 current focused tests: 24 core,
eight independent review cases and seven trusted-CLI checks. The isolated full
repository check at `cfa19ce` passed 1,260 tests with three skips and no failures
or errors (`repository-cfa19ce-isolated-2026-09-14.xml`). That full check covers
the earlier backend reconciliation/session checkpoint; the later evidence UI,
intake-classification and period-ledger changes have their separately identified
focused and browser checks.


The [selected-subject access-review continuation](../../../../enterprise/audit_suite/ACCESS_REVIEW_CONTINUATION.md)
validates sixteen exact parent/removal originals and replays the local entitlement
operations before deriving a later review population, decision and reconciliation.
It carries forward verified selected rights; it does not invent intervening
quarter activity. Prior omitted and unsupported people remain unresolved, and
missing authorized rights produce an unresolved decision instead of a retention
approval. Typed event links and computed results distinguish JSON booleans,
integers and floating-point values.

The maintained operator and V2/V3 workflows support the three explicit source
partitions. The initial/final removal partitions share the same original removal
store; identity remains separate. Existing source/capture pins and post-run
checks remain in force. Sealed three-record output and fresh runtime activation
passed in routing tests. Prior operator/workflow regressions and the new routes
passed 79 tests before the final strict native-type followup; the current core
eight and independent ten cases passed separately. Actual original corpus
execution is recorded only after its retained run receipts exist.


The current combined continuation/operator/ledger check passed 63 tests after
strict native-type corrections (`period-continuation-integrated.xml`). This
includes the actual operator → sealed capsule → fresh runtime route, V2/V3
selection/capture and independent source-chain and ledger cases.


Actual native review continuation subsequently ran at `a07294a7`: three originals
were generated from sixteen exact upstream records, activated into a fresh
company runtime and collected into a separate technical engagement. Its temporary
grants were revoked. One source-backed assertion was then recorded against the
independent two-occurrence period ledger; the other due occurrence remains
missing. Earlier source originals, declaration and initial report remain retained.
The private generation, collection and ledger verification receipts are indexed
in the overnight checkpoint. This is a selected-subject continuation, not a
whole-quarter review acceptance.

The [persistent backup operator](../../../../enterprise/audit_suite/BACKUP_RUNTIME.md)
adds actual scheduled filesystem copies, expiring local leases, explicit retries
and restore comparisons. Its local run and limits are recorded in the
[backup implementation note](AQ04_BACKUP_RESTORE_SLICE_2026-09-14.md).


A later bounded technical rehearsal used the backup originals already obtained
through company collection. Two new workpapers reference exact retained evidence
and the existing continuity procedures. The source database and all 21 originals
remained unchanged. The rehearsal recorded no independent review, population
acceptance, task completion or control effectiveness conclusion. Its private
execution receipt is indexed in the overnight checkpoint; the full-scope AQ-07
rehearsal remains open.

The [sample execution record](../../../../enterprise/audit_suite/SAMPLE_EXECUTION.md)
extends traceability from sample selection to explicitly authored item observations.
Each record pins the procedure, population, selection, workpaper version and actual
retained support. Corrections append history. Sampled and targeted items retain
their original basis, and missing support remains explicit. These records confer
no automatic testing credit or population acceptance.

Review comments can optionally anchor an exact passage in their already pinned
workpaper version. Server validation checks the precise Unicode offsets and text;
a later workpaper version does not move the comment. The existing independent
review and issue-resolution requirements continue to apply.


The first [explicit instructor assistance slice](IK05_EXPLICIT_RELEASE_CORE.md)
keeps named-learner hints and pointers outside the general engagement state.
An instructor previews exact content and explicitly confirms its release. The
learner chooses whether to open it; delivery and acknowledgment do not establish
understanding. Changed scope, source binding or Key pins suspend access, and
revocation prevents subsequent retrieval without claiming prior knowledge was
erased. No actual learner release was made during implementation.

Companion backup preserves sensitive preview drafts and assistance history as a
verified private archive. Restoration is inert: it does not recreate an active
release service, credentials, grants or recipient mappings.

[Selected explanation debriefs](../../../../enterprise/audit_suite/INSTRUCTOR_DEBRIEF.md)
now add ordered instructor-authored issue/procedure sections, annotated exact
originals and discussion prompts. The instructor selects a named learner and
historical shared-state revision, previews the complete document, then confirms.
Immutable corrections retain earlier releases. Portable exports require their own
file/byte preview and explicit confirmation; the browser verifies exact size and
SHA256 before download. Neither historical state nor assistance receipts establish
individual performance or understanding. Focused backend, HTTP and browser checks
cover selection isolation, changed authority, exact retries, attachments and inert
recovery. No actual learner release was made. Operational rehydration and qualified
calibration remain open parts of IK-05/IK-06.

An explicit [backup monitoring scan](AQ04_BACKUP_MONITOR_OPERATOR.md) subsequently
ran against the existing local backup runtime. It added four native originals
while preserving the prior 21 originals and operation history. A fresh technical
engagement then collected all 25 originals across 11 systems through source
grants and ordinary discovery. Future monitoring records remained unavailable
until an explicit audit-clock advance. Temporary grants were revoked, and the
earlier technical and reference audits remained unchanged. Monitoring retained
the missing-job and prior failure tickets; collection conferred no testing credit.

The [persistent configuration runtime](../../../../enterprise/audit_suite/CONFIGURATION_RUNTIME.md)
extends the existing change exercise with a separate data-only file target.
It validates seven exact upstream originals before local application, explicit
drift, correction or rollback. Reconciliation independently rereads the current
file. Immutable operations retain before/after hashes and the original approval
chain, with no inferred deployment approval or ticket closure. The trusted CLI
preserves private receipts and exact-command replay after receipt-write failure.
Core, independent review and CLI checks passed 19 tests. A subsequent reviewed
local run retained seven native originals from six operations: apply, authored
drift, independent reconciliation, correction, reconciliation and rollback.
Every command replay preserved the existing operation and current target. Original
source bytes and earlier audit histories remained unchanged; the target finished
at the pinned recovery baseline. Private receipts are indexed in the checkpoint.

The [explicit configuration export](../../../../enterprise/audit_suite/CONFIGURATION_EXPORT.md)
can retain the current file's exact bytes as an immutable company original,
separately from operation reports and receipt envelopes. It shares the runtime
revision and command namespace, preserves the target, and records export context
in provenance. Sixteen integrated core, independent-review and CLI checks passed.
A reviewed actual export retained the exact current file without changing the
target. A fresh technical engagement subsequently collected eight runtime
originals and seven upstream approval-chain originals across ten systems.
Future export retrieval was denied before an explicit clock advance; exact
replay, original-byte equality, temporary-grant revocation and preservation of
earlier audit histories passed. The collection ended at revision 38 and grants
no testing or professional acceptance credit.

The [persistent security-event workflow](../../../../enterprise/audit_suite/SECURITY_EVENT_RUNTIME.md)
consumes existing logging originals and an independent publisher checkpoint.
It separates intake, rule-based local triage, explicit handoff and retained-source
inspection. Reconciliation preserves the full declared subject population,
including subjects not yet handled. An acknowledgment ticket does not establish
response completion, and inspection does not establish remediation or incident
closure. Sixteen integrated core, independent-review and CLI checks passed.
Paired actual operations subsequently passed separate reviewed execution:
intake, triage, required handoffs, retained-source inspection and final
reconciliation completed for the declared subjects. Exact command replays added
no duplicate operations. Source capsules and earlier audits remained unchanged;
no source-access grants, audit mutations, model calls or external actions were
performed. These are local response workflows, not incident closure or proof of
whole-period effectiveness. Private execution receipts are indexed in the
checkpoint.

Evidence context now displays item observations citing the selected exact
artifact ID and SHA, including correction history and author-recorded locators.
Procedure and workpaper navigation requires matching server-provided version
pins. Actual retained backup observations passed desktop and narrow-screen
verification against the authorized projection without altering audit history
or original evidence. This adds context, not independent review or testing credit.

[Exact source-impact relationships](../../../../enterprise/audit_suite/SOURCE_IMPACT_REFERENCES.md)
now include sampled items, correction history, pinned human review comments and
explicit finding/remediation evidence. The viewer preserves historical workpaper
versions and shows unavailable or changed references without substituting newer
records. Impact is a reason for explicit review; it does not change a conclusion.

[Personal saved views](../../../../enterprise/audit_suite/PERSONAL_VIEWS.md) retain
explicit navigation and exact selected-record pins in a separate private store.
Current authority, scope and source context govern every restore. Saved filters,
table position and scroll hints do not pin a whole population or alter formal
work. Explicit companion recovery preserves historical bytes and records any
authorized principal remapping separately. Operational backup support does not
mean every existing workspace has already been backed up. Assignment handoff,
complete journey acceptance and owner usability evaluation remain separate gates.

A fresh technical correction journey subsequently exercised source collection,
a provisional record-version population, one targeted item, an initial observation
and workpaper, an anchored reviewer challenge, a separately retained correction,
an author response and explicit resolution by a distinct synthetic reviewer-role
principal. The response alone left the issue open. All twelve commands passed
exact replay and stale-revision checks, with earlier sources and nine selected
audit histories preserved. Saved-view reload and explicit principal-mapped
companion restoration preserved the original workpaper version. A desktop/narrow
check of the compiled workspace using the authorized retained projection and
recorded restore response passed. This was a bounded technical journey with one
untested population member; it is not a full-scope audit or qualified review.

[Explicit investigation handoffs](../../../../enterprise/audit_suite/INVESTIGATION_HANDOFFS.md)
share an authored question and chosen exact references between two authorized
audit-workspace members. Recipient acceptance and a coordination response retain
authorship and history. Changing shared authority hides the content; completing
the handoff does not complete a procedure or resolve an audit review. Private
drafts and investigations are never copied into an offer automatically. Companion
recovery retains a verified inert archive without reviving offers or permissions.

The [selected-source ownership and migration register](../../../../enterprise/audit_suite/COMPANY_SOURCE_REGISTER.md)
separates current registered owners, provisional documentary custody and historical
control assignments. Its actual A/B baseline run verified 359 original-to-company
documentary copies and preserved unknown event dates and historical ownership.
The successor register retained its predecessor manifest and unchanged earlier
audit histories. Accepted synthetic finance files and historical source locks
were checked as read-only references; no finance records were imported or changed.
The inventory does not establish complete operating history or evidence sufficiency.

## Retained handoff rehearsal and attributed company consultation

The exact corrected-evidence investigation now has a separate executed technical
coordination handoff. Its synthetic preparer offered the retained workpaper v1 to
the existing synthetic reviewer, who explicitly accepted and completed the
coordination request. All 13 audit events, source versions, memberships and
original bytes remained unchanged during execution. Exact replay, stale-version
rejection, nonparticipant denial and an inert companion restore passed. The
private receipt is `source-impact-rehearsal-preparation-2026-09-21/handoff-v1/result/RECEIPT.json`.
A full compiled-App check used the recorded participant projections to inspect
that exact historical version on desktop and narrow screens. This is a scripted
projection fixture, not live HTTP acceptance, human review or professional
assurance; later independent inspection distinguishes SQLite reader sidecars
from unchanged logical records.

[Company consultation](../../../../enterprise/audit_suite/COMPANY_CONSULTATION.md)
adds explicit learner-requested referrals and correction requests through the
existing meeting command and durable job path. Server-generated hashes pin the
original question and optional prior company reply. A referral addresses a
different current scoped contact; a correction request requires an exact prior
reply and may address the same contact. Original statements remain unchanged.
The responding contact records an attributed answer, clarification, correction
or inability to establish the fact. That relation is not verification of truth.
Only explicitly selected originals within the auditor/contact access intersection
supply source support; omitted support remains unknown. Current authority,
source identity, scheduled time and engagement state are checked before model
work and again before committing the reply. The existing attributed note path
retains the relation independently of its generated summary.

The composer, historical-message preview and queued-input inspector retain exact
consultation pins. Ambiguous submissions reuse the original command, while
changed recipients or authority clear the selection. Backend and browser checks
use mock providers and synthetic HTTP fixtures: this implementation checkpoint
makes no claim that a real company conversation or qualified assessment occurred.
The isolated repository run at commit `8f9b8eab` passed 1,573 tests with three skips;
subsequent handoff, register and consultation changes have separate focused checks.

## Explicit guidance, administrative batching and trace readiness

Administrative guidance has two independent gates: an instructor-recorded
`assistance.configure` policy, disabled by default, and each viewer's private
opt-in. Changing the policy records a new epoch and requires fresh opt-in.
Learners cannot inject the policy through engagement configuration. The controls
workspace records explicit disclosures for a chosen exact control, then permits
reasoned personal review or dismissal of exact suggestions. Suggestions derive
only from authorized recorded work relationships; they perform no source
discovery, model call, hidden-Key inspection or formal audit conclusion.
Current context and policy are rechecked before storage. Separate companion
recovery retains inactive history and never reactivates assistance.

The PBC workspace now supports explicit batches of at most 20 request read
notifications. Users preview selected rows versus the current filtered snapshot,
including excluded IDs, before confirmation. Each ordinary command preserves its
own optimistic revision and outcome. A failure or outside revision change stops
the remainder. An uncertain response retries only the exact original command;
remaining requests require a new preview. This does not issue or accept requests,
collect evidence, close reviews or complete tests.

[Procedure trace readiness](../../../../enterprise/audit_suite/PROCEDURE_TRACE_READINESS.md)
adds retained sample-execution relationships to the existing recorded-work report.
Exact historical workpaper, population, selection, procedure and evidence metadata
pins remain inspectable. Corrections contribute one current trace per lineage,
with old observations separately retained. Invalid or ambiguous relationships
produce unavailable counts, never a passing result. Population reliability,
source query and period qualifiers remain recorded assertions; the report neither
rereads original bytes nor establishes period completeness or professional
sufficiency. The bounded correction journey supplies two retained traces and one
current lineage in a private read-only report.

The narrow detail layout now wraps narrative text while containing wide tables in
their own horizontal scroll area. Checks at 320, 390 and 1,400 pixels retain all
columns. The actual recorded-projection workpaper fixture verifies that the modal
fits its viewport and the historical version remains unchanged.


### Bounded complete history exports

Ordinary and private reviewer exports now stream and verify each historical event
instead of materializing every prior full state. The canonical history payload and
learner redaction remain unchanged. Complete history must fit the remaining archive
budget; an oversized prefix is rejected without retaining a partial archive. A
100 MiB raw-event ceiling is checked before JSON decoding, connections close on
success and failure, and access is rechecked before returning history bytes. The
existing final ZIP inspection independently checks actual expanded member sizes.
This does not make very large engagements exportable as a single bounded archive;
it prevents them from exhausting memory before reporting the size limitation.


### Protected saved Key filters and expanded source selection

[Saved Key filters](../../../../enterprise/audit_suite/INSTRUCTOR_KEY_VIEWS.md)
now persist existing bound-source and archive filter states in a separate private
instructor store. Save and restore are explicit; restore verifies the exact Key,
current scope and source context. Changed context hides saved titles, queries and
selected IDs. Restoring archive filters does not fetch scenario detail, download an
original or start a comparison. Companion recovery retains only an inert private
archive and recreates no Key authority. This closes persistence for the existing
filters, not broader authored dimensions or qualified usability acceptance.

The private source ownership register now has an explicit version 4 successor.
It preserves the previous A/B selections and adds configuration, backup and both
security-response runtimes with their declared upstream component. Its selected
inventory contains 1,211 profile references to 831 unique physical versions; the
359 legacy documentary dispositions remain unresolved operating history. The new
selection is a custody/inventory expansion, not evidence of a coherent company year.
Read-only validation found no native database changes and preserved both selected
collection engagements and complete event chains. Older profiles and version 3
remain unchanged.

A private reference-year contract retains all 70 corporate SOC 2/HIPAA controls,
each authored procedure/test/cadence, additional duties, qualified owner routes and
exact historical A/B source references. Every procedure starts NOT_ASSESSED;
business populations and supported intervals require actual source analysis.
Missing selected support does not imply a missing business process. The contract
permits supported alternatives and explicit incomplete results without silently
removing procedures or inventing operational dates, employment, BIA/RPO or PHI.


### Authored assessment history

[Instructor assessments](../../../../enterprise/audit_suite/INSTRUCTOR_ASSESSMENTS.md)
separate six authored dimensions—discovery, evidence, testing, judgment,
documentation and follow-through—from the deterministic comparison inventory.
An instructor explicitly selects the historical shared-state revision, issues,
expectations and exact linked work references, then authors qualitative judgments
and rationales. Defensible alternatives, reasoned overrides and scenario-defect
flags retain their selected expectations/issues and support. No score, automatic
grade, individual submission, learner understanding or professional qualification
is inferred. Corrections create immutable new versions and preserve their exact
predecessor. Changed authority, Key or source context redacts protected content;
companion recovery retains only an inert private archive. No actual instructor
assessment or learner release was created during implementation.

The [native backup admission contract](../../../../enterprise/audit_suite/BACKUP_SOURCE_ADMISSION.md)
links a declared dataset to exact configuration-export bytes, producer definition,
metadata digest and physical routing identity. Original bytes, typed dependency,
consumer command and revision commit together. Explicit replay rechecks both
producer and consumer originals and the retained receipt. It creates no audit
artifact or source grant; collection remains a separate authorized audit action.


### Explicit source-change reassessment

[Source-impact dispositions](../../../../enterprise/audit_suite/SOURCE_IMPACT_DISPOSITIONS.md)
record a deliberate acknowledgment, reassessment need, selected-work exclusion or
link to existing follow-up work. The author selects the exact retained original,
workpaper version, sampled-item observation or other recorded impact reference.
Current source/context and work pins are checked again before an ordinary audit
command appends the decision. Corrections require the exact predecessor and retain
all previous decisions. Original test results and retained source bytes do not
change. The interface requires an explicit comparison and selection, preserves
ambiguous transport retries, and labels recorded history separately from a fresh
source check. Changed source/scope or unavailable exact targets redact historical
content. HTTP, native-source and browser checks cover these boundaries; integrated
workflow and human usability acceptance remain separate.

### Company-owned package scans and privileged sessions

The [package-manifest runtime](../../../../enterprise/audit_suite/VULNERABILITY_RUNTIME.md)
now maintains an explicit local asset/package inventory and attributed exact-version
rules. A package change does not clear a finding: a selected rescan records the new
observation, while unscanned assets retain their prior observation. Time-limited
local exceptions preserve detection and expose expiry. Paired private executions
have independent receipt and native-history verification. These are company-owned
local operations, without an audit engagement or evidence delivery. They do not
establish installed-host inventory, real CVE coverage or corporate remediation SLAs.

The [privileged-session runtime](../../../../enterprise/audit_suite/PRIVILEGED_RUNTIME.md)
uses exact existing fictional lifecycle originals to admit a bounded read right
over a new nonpersonal byte object. Explicit leases, sessions, reads, revocation,
expiry cleanup and scheduled reconciliation retain their own native history.
Expiry denies a read even before explicit cleanup; reconciliation can expose a
session awaiting cleanup or a missing declared occurrence. Retained implementation,
source metadata and command history are checked before inspection and mutation.
Twenty-six focused tests cover eligibility, actual reads, replay, tampering and
bounded loading. This adds a local source capability; it does not create host
accounts, establish enterprise privileged-account completeness or approve a control.

The [disposal runtime](../../../../enterprise/audit_suite/DISPOSAL_RUNTIME.md)
creates and removes only its own new nonpersonal fixture copies. Independent active
and backup inventory, explicit local authorization, retention dates and holds
constrain real unlink operations. Durable intent and verified inode quarantine
precede deletion; interrupted retries recheck current holds and authorization.
An unexplained missing copy retains a distinct uncertain outcome. Aborted
quarantined bytes remain inspectable, and exact completed replay cannot delete a
replacement. Thirty-five focused tests passed. Native originals retain metadata
and hashes without the disposed payload. Logical unlink does not establish secure
erasure or acceptance of a corporate/legal retention policy.

### Integrated context and reviewer journey

A separate private, real-backend technical workroom exercised investigation
save/resume, exact historical work previews, personal views, participant handoffs,
instructor assessment, selected debrief export and append-only source reassessment.
Six completed browser stages recorded 147 instrumented actions and 140 requests
with no unexpected HTTP failures or browser errors. Desktop and narrow layouts,
protected-route denial and inert companion restoration were checked. The retained
manifest independently verifies 126 evidence files, including earlier failed
attempts. These counts describe automated verification, not human usability.

That journey exposed a real interaction defect: opening a work preview unmounted
the underlying handoff and saved-view forms, losing unsaved text and opener focus.
Those forms now remain mounted, hidden and inert while the preview is open. Closing
the preview restores focus only to a still-valid opener in the same current
context. A permanent browser regression and the resumed actual journey passed.

Population, selection, workpaper and review setup in this small workroom was
helper-authored; only the two reassessment dispositions changed formal audit state
during the browser journey. This verification does not claim full-scope procedure
execution, model consultation quality, professional rubric calibration or owner
acceptance. The complete repository suite at frozen commit `1c3b4705` passed
1,834 tests with three skips; later features have their own focused checks and are
not silently included in that historical result.

### Dataset correction and adjacent review continuity

The [data-quality runtime](../../../../enterprise/audit_suite/DATA_QUALITY_RUNTIME.md)
validates a bounded nonpersonal dataset against independently declared record IDs,
an event window and reference entities. Joins and totals are computed from the
retained rows. Invalid, duplicate and missing records leave totals explicitly
partial and unreliable. Exact row-hash corrections append a new raw version,
preserve earlier inputs and outputs, and require a fresh transformation. Historical
command retries cannot rewind a later transformation. Twenty-seven focused checks
passed; local rule compliance does not establish business truth or source acceptance.

The [access-review successor](../../../../enterprise/audit_suite/ACCESS_REVIEW_SUCCESSOR.md)
verifies the original sixteen-record identity/remediation chain and its three-record
review before producing one adjacent quarterly review. It preserves the declared
subject, unresolved cohort and absence of intervening activity. Twelve focused
checks passed. A later quarter cannot be produced by silently skipping the prior
review or converting a limited cohort into a workforce census.

### Expanded collection and retained procedure observations

Two private full-control workrooms collected 605 and 632 exact company originals
through ordinary scoped source access. All temporary learner grants were revoked.
The retained originals were independently compared with their company source bytes.
Both workrooms retain 70 controls and 409 tasks; collection alone changes no task
conclusion. A subsequent technical procedure exercise added three provisional
populations, manual selections and workpapers per branch, with open technical
review comments and findings. Its six local recovery/configuration checks do not
represent completion of all audit procedures or a professional assessment.

A separate company-owned March–December exercise executed 46 and 47 explicit steps
against thirteen declared local recovery occurrences per branch. The second branch
retains a failed attempt, an explicit retry and one missed September checkpoint.
Each branch performed three byte-level restores. Independent read-only verification
confirmed native history, unchanged source inputs and zero audit-access journals.
The authored monthly schedule does not establish approved RPOs, production failover
or continuous enterprise coverage. These new operations are separate from the
605/632-original collection and require their own explicit collection profile.

### Navigable authored relationships

The protected instructor archive now groups facts, actors, events, artifacts and
discovery paths into selectable nodes. Selecting a node exposes its exact authored
source, incoming/outgoing references and a back trail. Search preserves the current
selection and identifies when it falls outside the filter. Trigger-relative event
timing retains source order; it does not invent a shared calendar or assert that
an event occurred. Unmapped narrative paths remain explicitly unlinked.

The display projection resolved all 1,110 preserved explanations, 12,959 nodes and
7,259 explicit edges without inventing relationships. Six new unit cases cover
pointer resolution, malformed graphs, unsupported semantics and timing. All 225
frontend unit tests, the build and the maintained desktop/narrow browser checks
passed. A real-backend browser also exercised the full archive, exact source
selection, relationship traversal/backtracking, filtering and trigger timing;
a learner request was denied. The archive remains unbound reference material,
separate from the six checks bound to each active workroom.

Separate full-workroom browser checks opened all ten destinations in both
70-control/409-task branches, verified narrow layout and completed exact historical
instructor comparisons. The full repository suite at frozen `6558459f` passed
1,929 tests with three skips; that result excludes the later data-quality,
access-review-successor and relationship-explorer additions, whose focused results
are recorded separately. Automated navigation does not substitute for owner
usability acceptance or qualified professional review.

### Explicit local document distribution

The [policy-delivery runtime](../../../../enterprise/audit_suite/POLICY_DELIVERY_RUNTIME.md)
admits exact committed document bytes and preserves literal source metadata. It
copies those bytes into private local mailboxes, verifies read-return bytes and
records simulated recipient assertions separately. Reconciliation distinguishes
missing, late, prior-version and withdrawn distributions against a declared
recipient inventory. None of these operations establishes human acknowledgment,
understanding, workforce completeness or a new policy approval.

Durable intent precedes the actual filesystem copy. Interrupted attempts remain
uncommitted and cannot be silently adopted as delivery; native command history,
file identity, exact bytes and current state are rechecked before commit. Twenty-two
focused tests passed, including interrupted-copy, exact-replay, withdrawal,
document-version, metadata-bound and publication-race cases. Actual paired company
execution and collection remain separate reviewed steps.


### Persistent local service identity continuity

The [nonhuman runtime](../../../../enterprise/audit_suite/NONHUMAN_RUNTIME.md)
replays exact prior-quarter originals before admitting their identity state into
an adjacent, independently declared period. Credential rotation, consumer updates,
actual local byte copies, stale-credential denials and separate quarterly reviews
persist in a transactional company store. Review reconciliation uses the declared
due inventory; successful copying cannot substitute for a missing review.

Thirty focused and independent tests passed, including source metadata tampering,
registered custody, bounded SQL reads, native history replay and writer/reader
quota agreement. These tests establish implementation behavior; paired prospective
company operations and ordinary audit collection remain separate steps.

The policy-delivery runtime also passed seven independent review tests (29 total).
Its reviewed paired local execution completed 23 steps, retaining 12 and 10 native
originals respectively, with exact delivered/read-return byte checks and historical
replay. Missing, late and withdrawn distributions remain distinguishable. Source
authority journals were empty at completion; this is company operation evidence,
not completed audit collection or human acknowledgment.


### Versioned authored inspection links

The protected archive builder accepts `--migration-version 2` to index the scenario
executor's exact `INSPECT:<artifact ID>` actions as `AUTHORED_INSPECTION_TARGET`
relationships. These identify an authored intended inspection; they do not establish
that evidence was available, an inspection occurred, or a conclusion was supported.
Only an exact existing artifact target qualifies. Narrative mentions, case changes,
extra whitespace and references to other node types remain unlinked.

The default migration remains version 1. Version 2 uses the same structural Key
schema with explicit migration metadata and requires a new private archive path.
Original scenario bytes, source hashes, earlier archives, saved-view pins and bound
learner comparisons remain intact. A new archive must be selected explicitly; no
running service is automatically rebound to it.


### Verified local continuations and future raw-source intake

Paired service-identity execution retained 14 and 15 runtime originals plus one
independent period declaration per branch. Independent read-only verification
matched all 21 operation originals to their declared command intents and confirmed
two exact byte copies per branch. The incomplete branch retains two stale-consumer
denials and its missing Q4 review. Earlier sources remained unchanged and authority
journals were empty before audit collection. Policy delivery independently verified
22 originals and five exact mailbox copies, with unchanged source and runtime files.

Future collection now assigns a text filename to four known unnamed raw-byte
systems: privileged objects, policy documents, nonhuman sources and copied datasets.
Explicit producer filenames remain controlling. Unknown systems still undergo JSON
validation; malformed JSON and invalid text remain quarantined. Fifteen focused
collection tests passed. Previously quarantined artifacts are preserved and do not
become available through this change.


### Expanded retained-original technical work and Key navigation

Supplemental company collection now includes a further 27 and 26 exact originals
from policy delivery, persistent service identity and independent period declarations.
All 53 byte comparisons and temporary-grant revocations were independently checked;
prior workrooms and protected archives remained unchanged. These selected references
are additional workroom records, not a unique enterprise-transaction census.

The preceding supplemental workrooms completed 38 and 47 technical procedure
commands respectively, covering nine and ten control groups with 37 and 39 selected
item observations. Independent verification matched every command intent and the
complete immutable history. Populations remain provisional; the two and seven local
technical findings remain open. Task states, original evidence, controls and reviews
were unchanged. Quarantined content was excluded and its limitation recorded.

The opt-in version 2 Key archive now preserves all 1,110 original definitions and
all earlier links while adding 4,714 exact authored inspection-target relationships.
Its 12,959 nodes and 11,973 edges describe authored references, not causal proof.
The prior archive remained byte-for-byte intact. Actual browser checks covered
explicit target traversal/back navigation, relative timing, narrow layout and
learner access denial; formal workroom state/history remained unchanged.

### Keyboard access and explicit personal change checkpoints

Compiled-App checks found and corrected modal Tab/Shift+Tab escape and a submission
error displayed behind the active form. Dialogs now keep focus within visible enabled
controls, expose their heading and retain accessible submission errors with draft
text. The targeted keyboard fixture and existing full browser suite passed. Measured
representative focus contrast was 4.05:1; tested text/status contrast was at least
6.28:1. This is a bounded scripted check, not a complete accessibility audit.

[Personal visit checkpoints](VISIT_CHECKPOINTS.md) add explicit comparison points
for six authorized record types, with private replacement history and exact-reference
navigation. Scope, permission or source changes withhold the entire comparison when
necessary. Saving never acknowledges reading or completes audit work. The service,
UI and inert companion-backup integration passed 93 backend tests and 235 frontend
tests, including a compiled-App retry/redaction/version-navigation journey.

A separate seven-sample read-only baseline measured local navigation/search medians
of approximately 50–100 ms under concurrent repository tests and preservation scans.
The first full-history comparison exceeded the 30-second client timeout; no successful
comparison percentile is claimed. These measurements identify a performance limit,
not an accepted responsiveness target or owner usability approval.

### History comparison and policy/identity procedure continuation

History inspection now canonicalizes each parsed state once and reuses those bytes
for event integrity and public history hashes. It still validates the entire chain,
including unselected later events, then rechecks current authority and revision.
Legacy noncanonical JSON retains the same parsed-value behavior and exact digest.
Independent review and 2,000 canonical-envelope comparisons found no digest change.
A single instrumented run on the 998-event workroom fell from 33.43 to 23.19 seconds;
this is not a controlled percentile or browser responsiveness guarantee. Retained
full states are bounded; compact activity metadata still grows with event count.

The policy/service-identity workrooms subsequently completed eight and ten technical
commands: two provisional populations, two selections, two workpapers and seven
item observations each. The incomplete branch retains two OPEN local-gap findings.
Due-time omissions, late delivery, withdrawal and credential denials remain distinct
observations. Neither these commands nor successful copies complete control tests,
establish human acknowledgment, or resolve unperformed enterprise-wide procedures.

The isolated repository run at `3cbe2d6d` finished with 2,027 tests passing and three
skipped. Later intake, Key, keyboard, checkpoint and history changes have separately
recorded focused/integration checks; that earlier full run does not cover them.

### Protected original inspection and populated checkpoint verification

The [instructor original inspector](INSTRUCTOR_ORIGINAL_INSPECTION.md) displays two
explicitly selected archived definitions with exact byte verification and retained
source pins. Bounded search covers the full archive without changing the selected
source. Closing inspection clears both originals and aborts pending reads; changing
scope, identity, role or revision also clears the protected workspace. No variant
ordering is treated as a predecessor relationship or scenario activation.

Thirty-eight backend integration tests and all 243 frontend tests passed. The
compiled browser fixture exercised 1,110 synthetic entries, corrupt/delayed
responses, close/context/role clearing, keyboard navigation and 390px layout. A
separate local HTTP check read the actual 1,110-source private archive and verified
two selected originals byte for byte, denied learner access, and preserved every
archive file. Its authorization workroom was an isolated minimal fixture, not a
full populated audit journey.

The personal checkpoint feature additionally passed an actual browser/API journey
using an isolated exact copy of the 605-original, revision-997 workroom. Two explicit
captures, exact retry, replacement history and comparison of 1,093 unchanged record
versions passed, with separate-principal isolation and exact original preview.
Formal history and all 18 company source roots remained unchanged. Changed/redacted
comparisons are covered by separate tests; no formal changes were fabricated for
this unchanged-data walkthrough. Neither automated journey supplies owner acceptance.

### Attributed original inspection and exact task reconciliation

[Explicit inspection records](RECORDED_INSPECTIONS.md) now retain an author's exact
original/version/hash, passage, observation and optional active procedure through
the ordinary command API. Current original bytes are checked twice; hidden,
quarantined, future, changed and invalidly linked originals are rejected. Recording
an inspection leaves task results and grades unchanged. Historical comparison
matches the exact recorded command payload and actor, separates other actors, and
preserves missing records as unknown rather than uninspected.

The scoped integration run passed 77 tests, followed by 26 final focused command
tests; 251 frontend tests passed. The compiled-App journey verified explicit
submission, frozen pins, retained text after rejection, attributed display, reload,
reviewer/legacy-capability gating and narrow layout. Formal audit/paired integration
is part of the consolidated closeout journey, not inferred from these fixtures.

A finite review of all 29 audit/company/Key/UX/context jobs identified remaining
substantive procedure reconciliation and combined acceptance work. Three prematurely
READY jobs now show IN_PROGRESS while their dependencies and actual review remain
unfinished. Existing workflow software and receipts are reused. Partial technical
observations are being reconciled to exact authored procedures for explicit,
evidence-supported task updates; the earlier helper-level task freeze is not a
permanent prohibition on supported simulated conclusions.

## Paired integration and substantive reconciliation

The consolidated paired technical journey now covers independent company file
operations, ordinary collection, explicit inspections, provisional sampling,
manual partial conclusions, a separate reviewer, historical workpaper restore,
private handoff/checkpoint, protected assessment and selected debrief export.
Its 36 scripted audit commands and 12 native operations are distinct from the
58 measured browser actions and 70 responses. Six additional protected-route
denials passed. A reproduced asynchronous saved-view focus defect was fixed;
closing the restored preview now returns focus to its initiating button in both
paired workrooms. This remains automated technical evidence, not owner feedback.

Separately, 29 reviewed ordinary task updates now record performed subsets as
IN_PROGRESS/LIMITATION across six existing workrooms. Independent verification
checked exact historical transitions, retained originals, roles and all 60 source
stores. The other task instances were not automatically concluded. Additional
report reconciliation, design inspection and exact conditional-duty reasoning
remain substantive work; a generic unperformed label is not an owner blocker.

The selected-source period refresh verified 1,518 artifact references, 1,136
distinct native identity pins and 1,385 retained paths. It preserves documentary
origins, unavailable support and unknown dates. These counts and event extents
do not establish a corporate population or continuous operating coverage.

The frozen `3f4ca8f9` repository suite passed 2,086 tests with three skips. Newer
recorded-inspection and focus changes have separate focused and actual browser
checks; they are not attributed to that earlier full-suite result. Exact private
receipts and preserved failed attempts remain indexed in the execution checkpoint.

### Subsequent report, access and design examinations

Six additional procedures now have attributed workpapers and ordinary task
updates. Four selected-report reconciliation procedures are COMPLETE/LIMITATION:
their exact source, transformation, exclusion and quality checks were performed,
including retained invalid and corrected outputs. Two governance design procedures
remain IN_PROGRESS/LIMITATION after examining the retained charters and committee
records. These dispositions describe procedure performance, not control effectiveness
or acceptance of corporate population completeness.

Two privileged-object observations were corrected after ordinary collection made
the same source bytes readable. The quarantined copies and prior unavailable
observations remain historical. Separately, three already-collected backup tickets
were added to successor workpapers and sample observations; open tickets, failed
attempts and missing occurrences remain unresolved. These corrections required no
new company operations and supplied no automatic review or testing credit.

Sixteen design and implementation examinations of configuration, identity creation,
security logging and training completion now record their performed comparisons
and calculations. Their IN_PROGRESS/LIMITATION conclusions distinguish selected
local operations from enterprise coverage, identity proofing, clock synchronization,
manager notification and other unperformed clauses. A correction and an expiring
exception remain alternative disposition paths; an unexamined alternative is not
automatically a deficiency.

The explicit successor source inventory verifies 1,520 retained references with
the same 1,136 distinct native identity pins and 1,385 physical paths. The two new
references are readable copies of existing bytes, not independent corroboration.
The earlier inventory remains pinned to its historical revisions. Declared-period
reconciliation separately retains 52 ledger slots and eight other native schedule
slots, including missing, late and unallocated observations. None establishes
continuous annual operation. Further conditional-duty examinations and the private
acceptance index remain in progress; unperformed work is not silently waived.
