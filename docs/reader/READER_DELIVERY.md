# Reader experience implementation record

**Decision reference:** owner instructions, September 11, 2026.
**Base:** `5baa59d6bc6ef21441ff1d787395d06ae2bc9738`.
**Branch:** `build/universe-reader-experience`.
**State:** review branch; not accepted main or live GitHub Wiki publication.

## Authorized direction

Make the README a guide to using the fictional enterprise for accounting, audit, financial analysis, management studies and other supported exercises. Make the wiki a thorough subject-based navigation layer to actual records. Preserve Markdown sources, provide human-facing corporate documents or Excel where applicable, and record database lineage. Do not include unrelated-project promotion in reader navigation.

## Review boundary

Existing approved artwork and publications are reused. No new maps, logos, diagrams, layouts, or bulk restyling are authorized for publication by this navigation work. Newly designed visual materials remain subject to exact-file review. Draft work stays on this branch pending owner review; a code or content check is not visual acceptance.

## Parallel work

Business and department navigation pages are partitioned from root integration. Finance/accounting readiness is assessed against actual release files; a bounded parallel-chat handoff identifies remaining human-document and subledger work. A separate owner-directed Codex chat owns SOC/CCF implementation. This branch links accepted controls records and does not absorb that workline or assert its future completion.

## Implementation scope

The README and use-case guide offer reading routes and honest exercise limits. Business and department pages reuse approved identities and current organization charts. The generated document library adds file-level discovery in Markdown and in the existing institutional database without claiming financial transaction completeness.

The new three-form delivery requirement is recorded in [Sources and formats](SOURCES_AND_FORMATS.md). It is not retroactively declared complete. Explicitly manifested controlled source/PDF pairs are verified; other entries are inventoried without speculative pairing. The finance handoff covers the remaining accounting-specific work.

## Publication boundary

The GitHub repository reports Wiki enabled, but its separate wiki Git endpoint was unavailable during this build. Repository Markdown remains immediately reviewable. No wiki contents were overwritten and no live wiki deployment is claimed.

Validation and exact coverage totals are recorded after integration below.

## Local validation and review

- Root `python -m pytest -q`: passed, three skips.
- `python -m unittest discover -s tests/publications`: 10 passed.
- Governance/J2, institutional catalog, organization, repository hygiene and business-record validators: passed.
- Reader validator: all local document/image targets and linked Markdown anchors resolved; indexed source hashes reconciled.
- Controlled-publication build: zero rendered, 131 existing publications retained with verified hashes.
- Configured `ruff check .` and `ruff format --check .`: passed.
- Browser checks: 98 desktop/mobile views of 49 reader pages, zero broken images, page-width overflows or missing same-page anchors. Preview screenshots are temporary local QA files, not new production artwork.
- Parent visual inspection sampled the README, Advisory business page and Finance department page at readable desktop/mobile sizes. Other pages received browser/render checks and source/link review, not a claimed exhaustive human visual acceptance. The owner has not yet accepted these drafts.

Corrections made: reduced oversized corporate/J2 logo display widths without changing source images; linked chart previews to full-size originals; excluded untracked scratch files from discovery; used descriptive source titles for manifested PDFs; added a complete counterpart-review queue; corrected the stale operations release status from a verified download.

The library contains 970 files: 639 Markdown, 328 PDF and 3 XLSX. Of the Markdown records, 131 have verified controlled PDF pairs, 82 are reader/maintenance pages, and 426 need counterpart reconciliation against domain manifests/releases. The last count is not a missing-publication count. Every inventoried file has a database discovery row; native financial completeness remains separate.

No main merge, live Wiki publication, new financial engine, source-art revision or bulk corporate-document conversion is claimed. The next owner review concerns the reading structure and wording. Finance continuation is provided as the explicitly authorized parallel-chat handoff.
