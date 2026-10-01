# Baseline reconciliation: CI import portability

Compared `3004549cfe2018698b0a5085abd90d1d85ad2f68` with `381e4ae3fc7505405b74a1dc7fa8eb6d3ba1dc06` before refreshing the baseline.

Only two mapped inputs changed: `tools/legal_gaps/case_briefs.py` and the case-brief manifest. The generator moves the Playwright import inside its build function so finance-only test environments can import the module. The manifest updates that generator pin. The prior graph correctly flagged 17 downstream nodes for review.

All 13 owner-reviewed PDF, HTML and workbook artifacts listed below are byte-identical between the two Git revisions. No source terms or financial amounts changed in these artifacts. Approval is not inferred from this check; the check establishes preservation of the exact reviewed bytes.

- `docs/legal/gap-instruments/case-briefs/SH-CASE-ARU-01.html`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-ARU-01.pdf`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-CLOSE-01.html`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-CLOSE-01.pdf`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-FF-01.html`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-FF-01.pdf`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RECON-01.html`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RECON-01.pdf`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RW-01.html`
- `docs/legal/gap-instruments/case-briefs/SH-CASE-RW-01.pdf`
- `docs/legal/gap-instruments/evidence-tracking/tracker.xlsx`
- `docs/legal/gap-instruments/period-close/blank.xlsx`
- `docs/legal/gap-instruments/period-close/worked.xlsx`

The unmapped changes are retained in report.json for separate classification. The main integration owns the portable proposal-reading companions, retained raw text, release and QA records. This graph successor addresses only the two mapped input changes; the prior graph remains in Git history.
