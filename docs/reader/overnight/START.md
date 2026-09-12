# Overnight reader and evidence work

**Workline:** SH-READER-OVERNIGHT-001 · **State:** prepared; not a scheduled/background job.

Continue the existing reader/evidence work from a refreshed main. Read [the structured queue](QUEUE.json), [maintainer rules](../../../MAINTAINERS.md), [format boundaries](../SOURCES_AND_FORMATS.md) and [finance handoff](../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md) before assigning work. Earlier finance overnight logs describe historical runs; this queue does not resume their stale commands.

## Scope and decisions

The owner authorized README/wiki usability, existing finance evidence completion, and preparation for a substantial overnight run on September 11 (Pacific). Existing authorization allows isolated branches, commits, pushes, PRs and merges after required gates. New PDF/workbook designs still require exact-file visual review. Pending questions do not become approvals through elapsed time.

Default order is accounting evidence, then transaction access and subject completeness. A priority answer changes the order, not the source/visual gates. If the owner instead requests all work remain in PRs, record that in the queue before continuing. No spending, new hosting, new financial engine or background scheduler is included.

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

- **Finance:** recover the existing draft first; inspect source populations and prepare accounting evidence in the reserved evidence directories. No new monetary assumptions or signed/bank-document imitation.
- **Reader reconciliation:** match the full counterpart-review population to explicit current or immutable-release manifests. A similarly named PDF or a catalog row is not proof of equivalence.
- **Wiki/transactions:** close source-backed subject access gaps and index actual transaction/operating records. Do not invent missing institutions, logos or corporate history.
- **Main agent:** owns README integration, shared schemas/catalog/generators, cross-lane reconciliation, source/visual review, PR descriptions and merges.

Serialise jobs within each lane. The queue includes source-only tasks that can proceed while visual acceptance is pending. FIN-03 cannot start from an unaccepted FIN-01 design. New visual outputs from any lane remain review artifacts regardless of a ready source task.

## Completion discipline

Each job needs: source revision and release identity; concrete output paths; applicable test command/results; missing/unsupported record dispositions; PR and commit; and visual review where applicable. Mark a task complete only when its stated acceptance holds. Keep design review and owner-dependent facts separate from engineering failures.

Use the accepted publication tools and workbook contracts. Do not mass-produce prose or decorative diagrams to increase file count. For absent evidence, record exactly what is absent and which exercise that prevents. Keep historical releases and approved images unchanged. A finance schedule derived from a model is not independent corroboration of that model.

After each coherent batch: stage new indexed sources, regenerate the institutional catalog, validate reader links and logical regeneration, run applicable maintainer/domain tests, inspect every changed visual, then commit and push. Reconcile current main before final checks. Preserve the independent CCF workline; consume only accepted main records.

The morning report should separate **merged**, **ready for exact-file review**, and **blocked on a specific external fact**. Link actual documents and workbooks rather than presenting another planning memo as the deliverable.
