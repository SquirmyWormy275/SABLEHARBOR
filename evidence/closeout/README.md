# Closeout evidence

This dossier records actual executions of the accepted public synthetic runtime reference and reconciles the accepted geographic review batches. It gives reviewers observed results, complete inputs, retained command logs and the remaining geographic population. It does not create institutional decisions or certify a deployed estate.

## Download and inspect

The [versioned release index](../../docs/releases/CLOSEOUT_EVIDENCE_RELEASES.md) identifies the complete downloadable package. In version 1.1.0, open `review.html` for the offline review interface: search and filter all cases, source records, later changes, site records, OCR candidates and the geographic backlog; inspect full records; export filtered CSV; and save portable draft review notes. Open `report.html` for the overview and `closeout-evidence.xlsx` for the filterable reviewer workbook. `case-events.json` preserves each input, expected result and observation. CSV files support independent analysis; the geographic CSV retains original source wording and locators.

| Requirement | Generated evidence | Boundary |
|---|---|---|
| #21 runtime | Runtime model validation and the existing runtime/security test suite, with actual exit codes and logs | Reference implementation only; no deployment qualification |
| #22 source rights | 63 disclosure/identity combinations, two existence cases and three delegation rejection cases | No third-party license or operating entitlement assertion |
| #24 retention | A five-node revocation, legal-hold and restoration exercise | No invented retention periods or approved class schedule |
| #34 disclosure | Nine disclosure channels, five forbidden authority operations, delegation and derived-copy suppression | No claim of model-wide inference safety |
| #106–108 geography | Reconciliation of 78,145 occurrence carriers, 69,184 previously classified carriers and the exact 8,961 remaining rows | No new adjudication, geometry or historical occupancy assertions |
| #11, #18, #19, #88 | Source-linked requirements in the workbook | Administrative actions, legal execution, appointments and the exact original artwork still require their respective evidence |

The 74 runtime cases are overlapping evidence for several issues, not 74 independent control certifications. The five validation commands include the existing public test suite and all three geographic batch checks. No issue closes automatically.

## Reproduce and verify

Use the release manifest's source revision in a clean checkout, then:

```bash
make bootstrap
uv run python -m tools.evidence.closeout --output /tmp/closeout-evidence-new-run --with-ocr
uv run python -m tools.evidence.closeout --verify /tmp/closeout-evidence-new-run
```

Each run requires a new output directory and produces a sibling ZIP. Timestamps and elapsed times reflect actual execution and vary between runs. Source revision, selected source fingerprints, dependency lock, Python version, expectations, observations and artifact hashes are recorded. Reproduction requires the Git history used by the accepted geographic review scripts; do not use a shallow clone.

`--allow-dirty-review` permits a development preview, explicitly marked as unsuitable for delivery. Failed commands or cases retain their diagnostics and prevent ZIP publication. Verification rejects changed, missing or additional files and review-only manifests. A checksum confirms bytes against a trusted manifest; it does not establish independent approval or authenticity by itself.

The issue register reproduces the [dated review snapshot](../../docs/audit/PROFESSIONAL_PRESENTATION_ISSUE_REVIEW.json). Its original source hashes describe that review, while `source-inputs.json` fingerprints the sources used by each new execution. Follow the GitHub issues for later decisions. Private CCF packages and pending legal publications are outside this generator's inputs and output.

## Complete source coverage and raster extraction

The source inventory verifies every one of the 919 baseline Git blobs against the recorded byte length and SHA-256, covering 72,828,248 bytes. It rejects omitted sources, duplicates and changed hashes. It also compares the complete baseline and package source trees, exposing additions, modifications and removals without classifying later canon by filename. The 60 site records retain their accepted wording, precision, dates and unresolved actions.

The OCR-enabled release executes Tesseract against all 97 individually registered baseline PNGs. It preserves raw TSV word positions/confidence, stderr logs, source hashes, actual execution times, engine version, executable hash and English model hash. These are **unreviewed OCR candidates**, not a completed visual review or geographic adjudication. PDF pages, images embedded in archives and images added after the baseline remain outside this OCR pass. The inventory separately identifies 199 source files whose extraction methods require visual/OCR attention, including PDFs and archives; the 97-image extraction does not close that wider requirement.

Install Tesseract with its English language model before using `--with-ocr`; omit that flag for the Python-only reference/source review build. CI installs the engine and records its identity. Engine/model/platform differences can change OCR output, so only compare OCR runs with matching recorded dependencies; no cross-version byte-equivalence is asserted.

## Review notes and offline behavior

The interface embeds all browsing data and uses no CDN, external fonts, analytics or server. External source links are pinned to the recorded Git revision. Links to workbook, logs and companion files need the complete extracted ZIP; the standalone HTML remains usable for browsing and draft notes.

Open a backlog row to save a draft disposition and rationale. Browser storage is a convenience; export the JSON draft to retain a portable copy. Imports must match the exact evidence edition and known occurrence IDs, and conflicting drafts are rejected without changing existing notes. Nothing uploads notes or changes accepted source files. Draft statuses never establish canon or close an issue. Review an exported proposal through the repository's normal accepted-source process before using it as a disposition.

Filtered CSV exports escape spreadsheet-formula prefixes; the package's original backlog CSV and JSON retain exact wording. Empty filtered exports retain their headers. Source text is rendered as text, and hostile markup cannot execute in the interface. The browser checks exercise offline use, keyboard dismissal, pagination, draft persistence and import/export, conflict handling, formula escaping, and all collections at mobile/desktop widths in light/dark themes.
