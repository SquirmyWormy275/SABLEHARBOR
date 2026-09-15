# Commercial and accounting-tax visual review

Fifteen complete source editions passed manual review: 69 PDF pages and 30 HTML initial viewports. This is implementation QA, not owner design acceptance.

[Page-by-page evidence and exact artifact hashes](PAGE_REVIEW.json) identify every inspected surface. PDF pages were viewed individually at 765 × 990 pixels; all body text, table content, pagination, margins and draft identity were inspected. HTML initial viewports were viewed at 1280 × 1000 and 390 × 1000. Whole-document DOM checks additionally covered overflow, concealed source text and broken images at both widths across all 56 editions.

The first build stranded “created.” at the top of the logistics agreement continuation and “transferred capability.” in the Advisory term sheet. Both were corrected by keeping paragraphs together. Final corrected pages were reinspected. Sparse final pages containing substantive source paragraphs remain complete rather than shortened to meet a page limit.

The validator independently compares complete source text, including every heading, paragraph and table cell. It caught a PyMuPDF extraction preclipping defect affecting leading dots in wrapped code paths; independent extraction confirmed the rendered punctuation. Extraction now includes all spans and then checks page bounds explicitly.

Commands: `python docs/legal/full-text/validate.py --browser` passed for 56 sources, 200 pages, 3,277 source blocks and 112 viewport checks. `python -m unittest discover -s docs/legal/full-text -p 'test_*.py'` passed all 13 tests, including clause and table-cell removal, changed amounts, reordered sections, cropped PDF text, and real artifact deletion with resealed manifests.

The PNGs are deliberately retained exact-review evidence. [Render script](render_review.py) regenerates the views but resets review state; rerendering is not a claim that a person or agent inspected changed bytes.
