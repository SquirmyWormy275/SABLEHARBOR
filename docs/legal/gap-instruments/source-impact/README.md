# What needs rechecking when a source changes?

This technical review tool traces explicitly registered source dependencies into
legal documents, accounting selections, workbook calculations, practice cases and
retained review releases. It does not update source records, regenerate a workbook,
adopt a proposed term or replace a delivered release.

[The simulated invoice-source audit](sample-audit/REPORT.md) demonstrates the
recheck queue without changing the real invoice. Its [JSON](sample-audit/report.json)
preserves every traversed edge; its [SQLite database](sample-audit/report.sqlite3)
has one row per impacted node. These are technical audit records, not new corporate
financial statements or approved document designs.

## Run a comparison

From the repository root, use a new output directory:

```sh
python tools/legal_gaps/source_impact.py report --output /tmp/sh-impact-review
python tools/legal_gaps/source_impact.py report --current HEAD --output /tmp/sh-impact-commit
python -m pytest -q tests/publications/test_legal_source_impact.py --confcutdir=tests/publications
```

The default compares the pinned Git baseline in [graph.json](graph.json) with
working files, including staged changes and untracked paths. `--current COMMIT`
compares that Git revision instead. This analysis is intentionally read-only; it
never calls financial or publication generators. Reports use a new output directory
and refuse to replace an earlier report.

Read `REPORT.md` for the queue, then `report.json` or `report.sqlite3` for the
source path, clause/selection locator, calculation or case identifier and edge
basis. File-level changes conservatively invalidate dependent selections; the tool
does not claim to know whether an edit changed a monetary conclusion.

## Scope and completeness

The graph is assembled from publication manifests, accounting source selectors,
practice input/calculation records, reconciliation evidence and check formulas,
and the walkthrough source register. Adapters also support the period-close,
evidence tracker and case briefs when they exist at the selected Git baseline.
It uses explicit structured relationships, not text similarity or keyword matches.

The original 17 instruments and their recorded dependencies are covered. Worksheet
calculation IDs and source locators are preserved where the registers supply them.
Walkthroughs and the period close have conservative package/case-level edges;
this is not a universal cell-level lineage engine. Unmapped enterprise packages,
indirect upstream dependencies absent from these registers and private evidence
are outside this graph.

A changed register itself triggers its downstream queue, even if an entry was
removed. Missing baseline files and pin mismatches remain explicit problems.
Unknown edge endpoints, duplicate IDs and cycles fail graph validation. Added
files outside the graph appear under **unclassified changes**; they never silently
produce a clean result. `NO_CHANGE_IN_BOUNDED_GRAPH` means exactly that, not that
the enterprise archive has no stale material. `REVIEW_REQUIRED` is a report result,
not an instruction to regenerate or reseal prior artifacts automatically.

The two [retained membership manifests](release-manifests/) are exact copies from
the previously verified v0.2 and v0.3 legal-review bundles, indexed in
[the release record](../REVIEW_RELEASES.md). Their source revisions, original-file
lists and manifest hashes define release membership for graph members. A source
change reaching a release means **review a successor; retain the previous bytes**.
This does not mean the historical snapshot has become invalid for its original
purpose. No new release membership is inferred before that release exists.

## Baseline maintenance

The integrated baseline is commit
`381e4ae3fc7505405b74a1dc7fa8eb6d3ba1dc06`: 473 nodes and 2,452 explicit edges.
The [CI portability reconciliation](baseline-reconciliation-381e4ae/DISPOSITION.md)
records the two changed mapped inputs, 17 flagged downstream nodes and verification
that all 13 reviewed PDF/HTML/workbook files remain byte-identical. The prior
3004549 baseline remains in Git history.
The preliminary d1c5945 baseline remains preserved in Git at commit
`831e5cec3616779f59ce1f9f2b963bf256cf8416`; it was extended to include the new
period close, 14-request tracker and five case briefs. The simulated invoice
change now reaches 132 nodes. All 15 focused mutation/rebuild tests pass.

The graph records exact Git input hashes, logical calculation/selection nodes and
structured dependency edges. Rebuild a proposed successor baseline with:

```sh
python tools/legal_gaps/source_impact.py baseline \
  --baseline FULL_COMMIT \
  --output /tmp/proposed-graph.json
```

Review the comparison against the old baseline before adopting the new graph.
Do not use a baseline refresh to erase an unresolved change queue. The focused
mutation tests demonstrate modification, deletion, additions, transitive release
impact, unknown paths, cycles and manifest-entry removal. The retained sample uses
an in-memory hash overlay and records that no source bytes were modified.
