# Overnight reader and evidence work

**Workline:** SH-READER-OVERNIGHT-001 · **State:** executing in the active session from September 12, 2026; not a scheduled/background job.

The owner started execution with “ok. let er rip”. The structured queue records the source revision, isolated branches and current job states. A running state is not completion evidence.

Continue the existing reader/evidence work from a refreshed main. Read [the structured queue](QUEUE.json), [maintainer rules](../../../MAINTAINERS.md), [format boundaries](../SOURCES_AND_FORMATS.md) and [finance handoff](../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md) before assigning work. Earlier finance overnight logs describe historical runs; this queue does not resume their stale commands.

## Scope and decisions

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
