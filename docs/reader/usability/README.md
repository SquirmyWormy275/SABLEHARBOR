# Practical reading routes: verification record

The owner authorized this continuation on September 12, 2026: integrate accepted main, create three practical exercise routes, test reading from the README, prioritize legal evidence gaps and preserve exact visual approvals. Nonvisual changes may merge after validation. New accounting/legal designs in PR #145 and fictional billing proposal #138 still require their separate reviews.

The starting accepted main is `f7c9da881176da19901fe5ec6e776f0fd8719a39`. The [exercise register](../exercises/routes.json) identifies three routes, 19 steps and 20 evidence references. The guides use accepted source documents, PDFs, CSVs and the accepted Foundry Field workbook. They introduce no new company instruments, amounts, legal terms or visual designs. Each guide has a discovery entry in the existing institutional catalog; transaction data remains in its native source databases.

## What was tested

[Browser results](JOURNEYS.json) record five tasks at desktop 1280px and mobile 390px: reach the invoice packet, acquisition accounting record, complete logistics summary, authority rules and a separately saved Sacramento floor plan. The browser followed real links from the README. All ten journeys passed. This is an agent-run navigation test in the existing local Markdown preview, not a study with human participants or an exact reproduction of GitHub's interface.

[Visual review](VISUAL_REVIEW.json) retains 37 inspected screenshots and source hashes. Review covered the full four exercise pages and approved-file protection guide at both widths; the longer legal-priority document was sampled at top, middle and end. The main agent also inspected the exercise index and mobile invoice page. Source reconciliation covered all 17 priority entries. No broader visual-approval claim follows from these checks.

Corrections made:

- Added a direct README and wiki route to the three exercises instead of requiring readers to assemble scattered references.
- Fixed long file-path wrapping in the local preview, which had widened the logistics source on mobile. Corporate publications were unchanged.
- Removed QA implementation commentary from the invoice instructions.
- Added narrow-screen table guidance and reduced the legal-priority summary table to three columns; detailed explanations remain below it.
- Verified worksheet names against the workbook and kept acquisition reconstruction separate from the base-2027 invoice population.

The [legal priorities](../transactions/GAP_PRIORITIES.md) cover all 17 existing gaps without changing their dispositions: five direct readers to existing sources, two warrant owner review only if extending billing, and ten do not require new documents for these exercises. The [approval guard](../APPROVED_ASSET_PROTECTION.md) protects 30 explicitly approved artifacts and two controlling acceptance documents without creating a new approval baseline.

## Reproduce

From the repository root, install `tools/reader/requirements.txt`. Browser checks also use `tools/wiki/visual/requirements.txt` and Chromium. Run:

```sh
python tools/reader/validate_routes.py
python tools/reader/validate_gap_priorities.py
python tools/documents/approval_guard.py
python -m pytest -q tests/publications/test_reader_routes.py tests/publications/test_approval_guard.py
python tools/reader/check_journeys.py --executable /usr/bin/chromium
python scripts/validate_reader_navigation.py --check-regeneration
```

The browser command writes fresh captures and results to `var/reader-journeys`; the wiki visual workflow uploads them as CI review evidence. The historical manual screenshots in this directory are deliberately retained verification evidence, not approved production artwork. Governance CI verifies source hashes, route steps, actual workbook tabs, all gap IDs and approved original bytes. Negative tests reject altered evidence, incorrect tabs, missing guides and resealed approval hashes.

Required repository checks and final commit/merge evidence belong to the implementation PR. The draft publication PR remains a separate acceptance boundary.
