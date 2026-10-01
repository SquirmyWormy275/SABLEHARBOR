# Comparing legal draft revisions

The 17-package comparison baseline is Git commit
`076485ccd954d3292fb5ad1940129027b6590284`. It records the reviewed draft
edition. **It is not owner acceptance of the documents, designs or terms.**
A matching hash establishes unchanged bytes; it cannot establish approval.

Run from the repository with the legal publication dependencies installed:

```bash
python tools/legal_gaps/revisions.py --output /tmp/sable-legal-revision-review
```

Use a new or empty output directory outside the repository. The tool writes
`report.json`, `report.md` and changed-page PNGs there; it does not change sources,
publications, manifests or acceptance records. `--current COMMIT` compares a Git
revision instead of working files. `--fail-on-change` returns nonzero when any
covered file differs, for an optional revision gate. Missing baseline objects,
invalid receipts and unreadable PDFs fail rather than being treated as matches.

Coverage comes from the baseline and current publication manifests together:
all 17 baseline Markdown and structured sources, PDF/HTML/XLSX editions and
manifest-listed shared artifacts. Deleting a current manifest entry cannot hide
a baseline file. The tool compares Git bytes, not mutable manifest checksums.
New files must enter the publication manifest before they enter this coverage;
unlisted working files are not inventoried by this command.

Markdown changes are grouped by heading ancestry, retaining literal clause
headings and distinguishing duplicate headings. Inserting a clause does not
shift every later match. A renamed heading appears as deletion plus addition;
this conservative comparison does not infer legal equivalence. Changes within
each clause use a unified line diff.

Each changed PDF is rasterized at 1.5× using PyMuPDF. Pages are compared by page
number and full RGB pixels. Changed pages have before, after and difference
images; added/deleted pages explicitly lack the absent side. Black difference
pixels mean identical pixels. Re-pagination can mark later pages as changed.
A byte change without raster change remains a change in the report; it may
reflect metadata, links, accessibility or other nonvisual PDF content. HTML and
XLSX receive byte comparisons, not semantic spreadsheet or browser diffs.
Manual inspection of exact editions remains required.

## Separate owner acceptance

No receipt is supplied or created by default. Every unreceipted edition remains
`DRAFT_NOT_OWNER_ACCEPTED`, including unchanged baseline documents. The tool
cannot decide whether a human actually approved a document.

If an actual owner decision is subsequently preserved under repository authority
rules, a separately reviewed receipt can be compared with:

```bash
python tools/legal_gaps/revisions.py --output /tmp/sable-legal-receipt-review \
  --receipt-revision FULL_COMMIT --receipt-path REPO_RELATIVE_RECEIPT.json
```

Both receipt arguments are required. The receipt must be stored at that Git
revision, have `status: OWNER_ACCEPTED`, identify an existing `decision_record`
at the same revision, and map exact repository-relative artifact paths to their
SHA256 values in `artifacts`. This describes an input contract, not an existing
acceptance record. The owner decision's authenticity, scope and authority must
be reviewed separately; merely authoring such a JSON file cannot create them.

Only unchanged bytes explicitly covered by that receipt are reported
`OWNER_RECEIPT_BYTES_MATCH`. Changed or deleted covered files report
`OWNER_ACCEPTANCE_INVALIDATED_BY_BYTES`; uncovered files remain unaccepted.
These are conditional byte-comparison results, not canon promotion or a new
approval. Acceptance of one artifact never extends to a different PDF, source,
workbook, design, term or execution event.
