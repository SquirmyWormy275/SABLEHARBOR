# September 6 canon closeout - validation and delivery evidence

**State:** Documentation and publication acceptance passed; repository acceptance is evidenced by the linked PR merge and checks

**Scope:** PR #97, CLOSE-001 through CLOSE-004

**Base:** `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`

The initial source-only draft was saved in commit `26644c3bb51625fde8e5f866cb561cf729f3357e`.
The owner subsequently authorized the compatible PDF normalization path and completion of
source reconciliation, validation, and merge. This record documents executed checks, not
approval inferred from a generated artifact. The accepted commit and integration time are
recorded by [PR #97](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/97); a branch copy
does not assert that the merge has already happened.

## Executed documentation and publication checks

| Check | Result |
|---|---|
| Controlled-publication build, explicitly using pypdf | PASS: seven revised/new PDFs; 40 existing current PDFs retained after source/PDF hash verification |
| Fresh-build repeatability | PASS: two explicit rebuilds of all seven changed publications; all 47 current PDF hashes, publication manifest, JSON catalog, and SQLite catalog identical (50 artifacts, zero drift) |
| Final board-source whitespace cleanup | PASS: rebuilt the board again twice; same 50 artifact hashes across the repeat; PDF content/layout unchanged |
| PDF visual and geometry review | PASS: all 15 pages inspected; approved logos, readable tables, no footer-only pages, no clipped or out-of-page text; all pages US Letter |
| PDF link review | PASS: source-relative links resolve to their canonical repository URLs; all emitted links in the seven PDFs are HTTPS |
| Publication regressions | PASS: seven unittest cases covering metadata/ID repeatability, geometry preservation, encrypted-input rejection, paragraph/list/hard-break handling, short table labels, and repository link resolution |
| `python scripts/validate_governance_j2.py` | PASS: governance records, authority, nine directors, five committees, nine Pinakes portals, charts, source/PDF hashes, page size, links, supersession |
| `python scripts/validate_institutional_catalog.py` | PASS: 47 objects, nine portals, all source/publication hashes, JSON/SQLite reconciliation, employee search queries including these decisions |
| `python scripts/validate_organization_maps.py` | PASS: nine charts and 162 baseline decision IDs |
| `python scripts/validate_repository_hygiene.py` | PASS: 690 staged/tracked paths, JSON, Markdown links, stale-name and public/private checks |
| `uv run ruff format --check .` and `uv run ruff check .` | PASS |
| `uv run mypy src` | PASS: 37 source files |
| Governed finance snapshot resolution | PASS: all 18 pinned Git snapshot entries resolve |

The complete finance/SQLite test suite and PostgreSQL 16 matrix are acceptance gates on the
committed PR head. Their executed logs, exact totals, package-generation results, and check
conclusions are retained in the [PR checks](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/97/checks).
Local structural or PDF checks are not a substitute for those gates. Merge requires their
successful completion; this pre-merge record does not predeclare a future CI result.

## Reproduction environment and limits

Publication build: Python 3.12.13, LibreOfficeDev 26.8.0.0.alpha0
(`2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`), Ghostscript 10.02.1, and pypdf 6.10.0.
Visual/text inspection used PyMuPDF 1.26.6. Builds set `LC_ALL=C.UTF-8` and `TZ=UTC`.
The separate pinned publication requirement leaves the finance dependency lock unchanged.
The missing qpdf/package-installation restriction was not bypassed. Explicit `--normalizer
pypdf` selects the owner-authorized compatibility path; qpdf remains available as a backend
where installed. Reproducibility here means identical inputs and toolchain, not byte parity
between different office versions, fonts, or qpdf and pypdf.

The HTML adapter now joins wrapped Markdown paragraphs, preserves list and explicit break
boundaries, repeats table headings, reserves width for short labels/counts, uses compact
footers, and resolves links relative to the source record. Those layout corrections removed
footer-only pages found during review. Approved logo source bytes are unchanged.

Reproduction commands and selective rebuild options are documented in the
[publication builder guide](../../../tools/documents/README.md). The current
[manifest](../../governance/publication_manifest.json) records each source/PDF SHA-256 and
the normalizer used for newly built outputs. The derived catalog is version 1.0.2.

## Preserved historical boundaries

All 45 PDFs indexed by the reviewed main branch retain their exact original bytes. Five
receive new current versions, and two new controlled publications are added, giving 47
current catalog entries. Older versioned PDF files remain available as historical artifacts.

Initial testing correctly rejected edits to finance-pinned source bytes. The resolution
preserves the exact original corporate lore v0.3, decision register, and board doctrine
v1.0.0, and publishes the current board as `BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md`.
The September 6 addendum supplies explicit supersession for the earlier conflicting name
statements. Finance's snapshot enforcement, runtime, source locks, and dependency lock are
unchanged; the enforcement check passes without weakening it.

Both tracked historical ZIPs, their existing manifests, and the September 3 size audit are
byte-identical to the reviewed main branch. The new delivery policy inventories exact ZIP
hashes and flags and indexes the existing finance release. Release-asset metadata was read
from GitHub; this closeout does not claim a new package download or internal package audit.
No historical release, Board record, or September 2–3 conversation ledger was rewritten.

## Closure scope and accepted delivery

The controlling sources and current PDFs are linked from the
[controlled-document index](../../CONTROLLED_DOCUMENT_INDEX.md). GitHub issue state supplies
the actual closure event after accepted integration:

- [#23](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/23): Routine / Priority / Immediate / Flash, handling urgency only.
- [#25](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/25): ordinary desktop usability and planned future AR and VR integration; interface implementation, vendor, hardware, and date remain OPEN.
- [#35](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/35): repository delivery/packaging policy and documented historical package exceptions.
- Daniel Mercer/COL-013: name resolved, stable identities preserved, no family relationship with Evan Mercer inferred.

[#37](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/37) remains OPEN for the specific
catalog/SQLite lifecycle. Other open canon questions and separate geospatial/ARU draft PRs
are outside this acceptance. The PR merge, controlling repository records, checks, and
retrievable publication bytes are the delivery evidence; this conversation alone is not.
