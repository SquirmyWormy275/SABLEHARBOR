# Exact-artifact visual QA

This folder retains review evidence for all 17 draft instruments. The
[surface manifest](surfaces.json) binds each original artifact to its contact
images by SHA-256. The [manual receipt](REVIEW.json) binds the completed agent
inspection to that manifest. Owner acceptance is separate and remains pending.

## Coverage

- PDF: all 98 pages at 1.3× raster scale, in full-resolution four-page contacts.
- Excel: all 39 worksheets from all 17 workbooks, rendered natively by
  LibreOffice. Every populated cell is also checked against the exported text.
- HTML: all 17 complete documents and the review index in Chromium at 1280-pixel
  desktop width. Full-scroll captures are retained; main and facilities reviewers
  also used overlapping readable viewport captures. No horizontal overflow or
  broken logos was observed. Mobile usability was not certified.

The main agent inspected Advisory, billing, carry, colocation and workforce:
27 PDF pages and five HTML documents, plus the review index. Two independent
agents inspected the other 71 PDF pages and 12 HTML documents. A third agent
inspected every workbook sheet. Detailed findings and reinspection notes:

- [Finance and formation review](REVIEW_FINANCE.txt)
- [Facilities, title and clearance review](REVIEW_FACILITIES.txt)
- [All workbook sheets](REVIEW_WORKBOOKS.txt)
- [Automated validation log](CHECKS.txt)

## Corrections verified

Completion forms now remain together; source lists no longer split into stranded
bullets; the tax-filing conclusion stays with its heading. Metadata spacing was
tightened. Workbook headers use human wording, money columns have separation,
percentage formats preserve the actual underlying values, and the financing
schedule is readable at its native print size.

A blank uranium workbook export during development was caught and regenerated.
The renderer now rejects any export that omits a populated cell. All final sheets
passed. Minor line wrapping in two workbook labels and whitespace on complete
source-appendix pages remain readable and were recorded as nonblocking.

This is visual inspection by Codex agents, not a claim of human design approval,
legal sufficiency, responsive/mobile testing or external factual verification.
The raw surface generator intentionally records an awaiting-review state; the
separate hash-bound manual receipt is the completion record.
