# J2 leadership integration validation

**Decision:** `SH-J2-PPL-20260910`

**Implementation PR:** #118

**Reviewed baseline main:** `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`

**Build input commit:** `6fc0ad89a89ecc972e9fd054231efb450b8f0aec`

**Generated publication commit:** `f87ab1c55b27de783730242a6485383f943c4323`

## Authorized scope

Six approved people occupy existing roles: Jonathan Goldstryker, Amanda Chenahot, Mara Hammer, Anika Trish, Grant Kohrs and Brett Calder. Exact office and company joining-year assertions are controlled by the canonical decision and structured roster. Appointment dates, commission dates, biographies, incremental billets, payroll and new authority are not inferred. The Chief of Staff and remaining unnamed deputies remain open in issue #19. The independent PR #116 implementation is preserved.

## Publication and source integrity

The prior 56-page master and 202-record display source are byte-preserved in `docs/organization/history/v1.0.0/`. The successor contains 40 chart families, 57 pages, 208 display records and 51 unique current named people. All original content was raster-compared outside the authorized new enterprise card and publication footers. The six-person page includes six complete card borders and no residual seventh template card. All names, offices and joining years match the structured display source.

- Current visual-master SHA-256: `352dfa4f1247f6089d340b19940f75758a666dce14f239fb38b1c2a300aaa38b`.
- Appointment Markdown SHA-256: `05ee1d4bbcad3ff2de9f623de0b57373acaaf611c0b161664a9f3e36b1066509`.
- Two-page appointment PDF SHA-256: `2c99221acdcdc5c0cca4a428eda4fe6d7ed8e9e0e80550e58ac49521e1b02a2d`.

The controlled-publication build rendered one new document and retained all 117 prior hash-verified publications. JSON and SQLite institutional catalogs were regenerated. The existing supported pinned `pypdf` normalizer was used for the new PDF; the earlier qpdf option-compatibility failure was not bypassed by weakening validation or rebuilding prior releases.

## Executed build validation

[Build run 34565946941](https://github.com/SquirmyWormy275/SABLEHARBOR/actions/runs/34565946941) completed successfully and committed its generated representations to the isolated leadership branch.

Passed: governance/J2 validation, institutional catalog validation, organization coverage and source matching, repository hygiene, business records, Ruff formatting and linting, whitespace checks, exact approved roster, correction handling, residual role preservation, prior artwork preservation, footers, and migration/export idempotence.

The focused organization and leadership tests completed with **17 passed**. The full root pytest suite completed with **162 passed and three skipped**, as counted from its emitted outcomes. The skips were not relabeled as passes. One SQLite datetime-adapter deprecation warning was disclosed. The original complete test outputs are retained in the build artifact; final clean-source CI results are recorded on PR #118.

## Downloaded-artifact and visual review

Artifact `10186185055`, `j2-leadership-completed-review`, was downloaded from that run. Its ZIP CRC check passed and its SHA-256 matched the GitHub artifact digest:

`c1c1c0b195408e5fc3b532099d0ba12d04e8cd143ca29cc9f68b93173cf0d7f1`

The artifact identifies generated branch head `f87ab1c55b27de783730242a6485383f943c4323`; its only untracked worktree entry was the temporary review-output directory created after commit. Source, visual-master and controlled-PDF digests were independently recalculated and matched their committed records.

The exact generated J2 and enterprise-leadership PNGs were visually inspected. Both pages of the appointment PDF were rendered and inspected with PyMuPDF; the first page was additionally rendered and inspected with Poppler. Names, years, table rows, six card outlines, title, logo, footers, spacing and page boundaries were checked; no clipping, leftover template text or broken glyphs was observed.

## Persistent regression and archival boundaries

The archived original display register contains explicitly rejected historical-name review rows. `scripts/organization_history.py` recognizes only that exact SHA-256-verified archived source and excludes only the four pre-existing rejected review rows from current-name scanning. All remaining text is still scanned. No wildcard history or stale-name exemption is introduced. Two additional tests verify the narrow handling and rejection of a changed archive; both were executed against the preserved source during final review.

The persistent organization workflow runs the existing six tests, eleven leadership tests and these two archive-boundary tests. It also regenerates the charts and requires a clean generated tree. Temporary source-review and write-enabled build workflows are removed from the final proposed tree.

## Acceptance boundary

The owner approved the personnel decisions. This record documents their implementation and executed build/visual checks, not an invented in-universe appointment date. Final clean-source check status, main-branch merge and the issue #19 delivery-state update are recorded in PR #118. The issue remains open for its residual personnel scope.
