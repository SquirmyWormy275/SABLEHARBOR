# Overnight reader and evidence work

**Execution update:** the owner authorized the audit-company run to proceed autonomously from canon and repository sources, stopping only for real blockers. The structured queue now records `audit_execution` and current job states; earlier “queued, not started” passages below are retained planning history. See the [company-source implementation checkpoint](../../internal/development/audit-suite/COMPANY_SOURCE_IMPLEMENTATION.md) for implemented behavior and precise limits. Historical reader review jobs are not restarted or silently approved.

**Workline:** SH-READER-OVERNIGHT-001 · **State:** prior reader source implementation delivered; designs await exact-file review; company-source audit readiness queued, not started.

## Company-source audit readiness addition — September 13

The owner added the complete [audit-readiness workflow](../../internal/development/audit-suite/AUDIT_READINESS_WORKFLOW_QUEUE.md) to this overnight queue. AQ-01 through AQ-08 cover source inventory, persistent company systems, retroactive migration, full-period operations, actual audit collection, population/evidence sufficiency, a fresh audit rehearsal and reviewed release. All eight are queued; `READY` denotes eligibility only after dependencies complete and an execution instruction is received. Adding these jobs does not start an overnight run or scheduler.

Use the `audit_company` lane sequentially, within the existing three-worker cap; do not add a fourth simultaneous worker. The integrator owns shared schema, dependency and catalog changes. Preserve the current audit-suite worktree and its uncommitted queue additions when reconciling branches; a refreshed main alone may not contain this work. Record the actual execution baseline when this new lane starts; the earlier queue base and execution records describe the historical reader run.

The company must own its operational history independently of engagements. Auditors collect existing source records through authorized people and systems; only collected copies belong in audit evidence storage. Preserve old synthetic history and snapshots with truthful migration provenance. Keep populated company records and hidden scenario/rubric material private and separate. No Atlas writes, remote publication, external deployment or source-license acceptance is authorized by this queue addition; earlier reader publication instructions do not extend to AQ jobs. AQ-08 remains awaiting review until real qualified review and owner acceptance occur. Missing source records and control failures remain visible rather than becoming manufactured passing evidence.

The owner started execution with “ok. let er rip”. The structured queue records the source revision, isolated branches and current job states. The [execution results](RESULTS.md) record delivered sources, validation and held review files. PR #142 supplies source-merge acceptance; no new design acceptance is implied.

Continue the existing reader/evidence work from a refreshed main. Read [the structured queue](QUEUE.json), [maintainer rules](../../../MAINTAINERS.md), [format boundaries](../SOURCES_AND_FORMATS.md) and [finance handoff](../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md) before assigning work. Earlier finance overnight logs describe historical runs; this queue does not resume their stale commands.

## Instructor key addition — September 13

IK-01 through IK-06 add the [instructor investigation and debrief workflow](../../internal/development/audit-suite/INSTRUCTOR_KEY_WORKFLOW_QUEUE.md): structured scenario explanations, protected key access, an interactive explorer, evidence-linked learner comparison, progressive reveals and debriefs, and qualified calibration across Clean/Messy modes. These six jobs are queued, not started, and run in the existing `audit_company` lane after their listed dependencies. They preserve scope/availability-based judgments, acceptable alternative procedures, assessment history and separation of hidden truth from learner/company access. Final acceptance requires real professional review and owner usability feedback. The execution/publication restrictions for AQ additions also apply to IK jobs.

## Scope and decisions

CX-01 through CX-05 lock the [intelligent contextual workspace](../../internal/development/audit-suite/CONTEXTUAL_WORKSPACE_WORKFLOW.md) and all final navigation proposals: stable destinations, unified search, previews, consistent summaries, contextual actions, saved workspaces, shortcuts, progressive forms and navigation/recovery checks. Contextual guidance must explain its relevance using authorized evidence, preserve investigation continuity and never consume hidden instructor answers. These jobs reuse UX/AQ/IK foundations in the same lane; they are queued, not started.

The owner locked the [UX professionalization direction](../../internal/development/audit-suite/UX_PROFESSIONALIZATION_WORKFLOW.md). UX-01 through UX-05 queue navigation/terminology, evidence/workpaper ergonomics, responsiveness/recovery, visual/accessibility/export consistency and full-session usability evaluation, in that priority order with listed dependencies. These jobs share the `audit_company` lane and its restrictions. Locked direction is not implemented work or exact visual acceptance; subsequent recommendations are proposals until adopted.

The owner authorized README/wiki usability, existing finance evidence completion, and preparation for a substantial overnight run on September 11 (Pacific). Existing authorization allows isolated branches, commits, pushes, PRs and merges after required gates. New PDF/workbook designs still require exact-file visual review. Pending questions do not become approvals through elapsed time.

The owner confirmed all three content lanes: accounting evidence, transaction/legal access, and business/department completeness. Nonvisual work may merge after required gates; future designs remain in exact-file review. The owner also authorized a separate proposed fictional billing dataset for review only; it must not change booked amounts or established legal canon. [The dated authorization](../../canon/READER_OVERNIGHT_SCOPE_2026-09-11.md) records these decisions. No spending, new hosting, new financial engine or background scheduler is included.

## Accounting and legal rollup — September 12

The owner added accounting and legal completion to this same run. The queue now has 17 jobs, including completed work and pending reviews. This is an expanded execution scope, not a claim that those jobs have run.

- **Accounting:** customer billing/collections/revenue; procurement/payables/Treasury; close/allowances/statements/consolidation; workforce costs; inventory/assets/debt; tax-support and transaction-accounting bridges.
- **Legal:** corporate/capital/workforce records; customer/vendor/service contracts and SLAs; acquisitions/bills of sale; asset, lease, host and custody rights; missing legal/billing terms as clearly separated review proposals.
- **Reader/business:** department and business coverage, format reconciliation, navigation and practical exercise access.

Work through the actual applicable populations identified in the pinned sources, using coherent batches across all seven business lines and their legal entities. This is document and evidence completion over existing models, not authorization for a replacement accounting engine or invented legal execution. A topic is not complete merely because an index or sample exists.

Every scoped record needs readable Markdown, the applicable letterhead PDF or Excel representation, and a stable native database/discovery link, or an explicit justified absent/exempt/proposed disposition. Source-backed nonvisual work may merge after checks; new visual files and changes to proposed legal/financial facts remain held for review. A missing signature, bank record, tax election or exact legal-party fact must not be disguised by a professional-looking document.

The Foundry Field packet is already accepted and merged in PR #134. Preserve it. The billing dataset already exists in draft PR #138; recover it and continue its review rather than generating another competing proposal. Independent legal-gap proposals can proceed while that review is pending.

## Start or resume

Tell the active coding session:

> Execute docs/reader/overnight/START.md and QUEUE.json. Work through every ready item, preserve the frozen assets, use the three bounded lanes, and continue independent work when an item needs review. Leave new visual artifacts in review PRs unless their exact files have been accepted. Commit durable state and report accepted changes, draft review links, validation, and external blockers.

This is a resumable execution instruction, not a claim that closing the CLI launches a service. Keep the active session and machine running for an unattended run. Do not add desktop settings or scheduled jobs as a side effect.

Before work, run:

```bash
python scripts/validate_reader_workqueue.py
```

The validator checks the job graph, existing inputs, permitted relative paths and frozen source hashes. It does not execute tasks, confer approval, or validate future artifacts.

## Partition work

Use up to three worker lanes and one main integrator. Give each lane an isolated worktree if it needs to commit or rebase. Never let separate workers stage the same index or regenerate the shared catalog concurrently.

- **Accounting worker (`finance`):** FIN-02 through FIN-08, using only the reserved accounting evidence directories and preserving FIN-01. Draft billing details remain separated from booked amounts.
- **Legal worker (`legal`):** LEGAL-01 through LEGAL-05, including instrument recovery, document packages and proposed missing terms. No changes to accepted legal identity, ownership or execution state.
- **Reader/business worker (`reader`):** READ-02 and WIKI-01, including counterpart reconciliation and business/department coverage. A similarly named PDF is not proof of a source/publication pairing.
- **Main agent (`integrator`):** shared schemas/catalog/generators, cross-lane accounting/legal/source reconciliation, source/visual review, PR descriptions and merges.

Serialise jobs within each lane. The queue includes source-only tasks that can proceed while visual acceptance is pending. FIN-01 is exact-file accepted; FIN-03 source work may proceed when FIN-02 is complete. FIN-01 acceptance does not approve FIN-03 or FIN-06 designs. New visual outputs from any lane remain review artifacts regardless of a ready source task.

## Completion discipline

Each job needs: source revision and release identity; concrete output paths; applicable test command/results; missing/unsupported record dispositions; PR and commit; and visual review where applicable. Mark a task complete only when its stated acceptance holds. Keep design review and owner-dependent facts separate from engineering failures.

Use the accepted publication tools and workbook contracts. Do not mass-produce prose or decorative diagrams to increase file count. For absent evidence, record exactly what is absent and which exercise that prevents. Keep historical releases and approved images unchanged. A finance schedule derived from a model is not independent corroboration of that model.

After each coherent batch: stage new indexed sources, regenerate the institutional catalog, validate reader links and logical regeneration, run applicable maintainer/domain tests, inspect every changed visual, then commit and push. Reconcile current main before final checks. Preserve the independent CCF workline; consume only accepted main records.

The morning report should separate **merged**, **ready for exact-file review**, and **blocked on a specific external fact**. Link actual documents and workbooks rather than presenting another planning memo as the deliverable.
