# Source-change impact report

**REVIEW_REQUIRED**

Baseline: `3004549cfe2018698b0a5085abd90d1d85ad2f68`. Current: `381e4ae3fc7505405b74a1dc7fa8eb6d3ba1dc06`.

This report requests rechecking; it does not regenerate, approve or overwrite anything.

Changed/missing mapped files: 2. Impacted nodes: 17.

## Changed inputs

- `docs/legal/gap-instruments/case-briefs/manifest.json` — MODIFIED
- `tools/legal_gaps/case_briefs.py` — MODIFIED

## Recheck queue

- `docs/legal/gap-instruments/case-briefs/README.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-ARU-01.html` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-ARU-01.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-ARU-01.pdf` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-CLOSE-01.html` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-CLOSE-01.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-CLOSE-01.pdf` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-FF-01.html` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-FF-01.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-FF-01.pdf` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RECON-01.html` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RECON-01.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RECON-01.pdf` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RW-01.html` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RW-01.md` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RW-01.pdf` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.
- `docs/legal/gap-instruments/case-briefs/case-briefs.sqlite3` — file; caused by `docs/legal/gap-instruments/case-briefs/manifest.json`, `tools/legal_gaps/case_briefs.py`.

Exact selectors, calculation IDs and traversed edges are in report.json and the SQLite impact table.

## Unclassified changes

- `.github/workflows/legal-gap-instruments.yml`
- `docs/internal/institutional_catalog.sqlite3`
- `docs/legal/gap-instruments/case-briefs/ACCEPTANCE.json`
- `docs/legal/gap-instruments/case-briefs/ACCEPTANCE.md`
- `docs/legal/gap-instruments/case-briefs/qa/COLD_START.md`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/PROPOSAL.md`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/PROPOSAL.original.txt`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/import-receipt.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/tracker.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/tracker.sqlite3`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/tracker.xlsx`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-update-corrected.xlsx`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/PROPOSAL.md`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/PROPOSAL.original.txt`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/import-receipt.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/tracker.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/tracker.sqlite3`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/tracker.xlsx`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-update-corrected.xlsx`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/import.stderr.txt`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/import.stdout.txt`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/manifest.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/manifest.original.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/import.stdout.txt`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/manifest.json`
- `docs/legal/gap-instruments/case-briefs/qa/cold-start/manifest.original.json`
- `docs/legal/gap-instruments/review-support/qa/v4/01-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/05-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/06-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/07-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/08-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/09-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/10-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/11-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/13-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/14-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/15-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/46-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/47-contact-000.png`
- `docs/legal/gap-instruments/review-support/qa/v4/47-contact-004.png`
- `docs/legal/gap-instruments/review-support/qa/v4/HTML.json`
- `docs/legal/gap-instruments/review-support/qa/v4/PRESERVATION.md`
- `docs/legal/gap-instruments/review-support/qa/v4/REVIEW.json`
- `docs/legal/gap-instruments/review-support/qa/v4/full-pytest.log`
- `docs/legal/gap-instruments/source-impact/README.md`
- `docs/legal/gap-instruments/source-impact/graph.json`
- `docs/legal/gap-instruments/source-impact/sample-audit/REPORT.md`
- `docs/legal/gap-instruments/source-impact/sample-audit/report.json`
- `docs/legal/gap-instruments/source-impact/sample-audit/report.sqlite3`
- `docs/wiki/Library.md`
- `docs/wiki/library/finance.md`
- `docs/wiki/library/format-review.md`
- `scripts/check_public_safety.py`
- `tests/publications/test_legal_case_briefs.py`
- `tests/publications/test_legal_package_v4.py`
- `tools/legal_gaps/package_v4.py`
- `tools/legal_gaps/validate_close_review.py`
- `tools/legal_gaps/validate_close_review_v42.py`

## Baseline problems

None.

## Coverage limits

- Other enterprise generators and source chains are not mapped.
- Walkthrough dependencies are package-level, not individual worksheet cells.
- Release targets cover graph members only, not all files in each bundle.
- Changes outside these registers require classification; no universal clean claim.
