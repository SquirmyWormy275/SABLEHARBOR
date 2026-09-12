# Legal reader draft visual review

Status: **QA complete; exact-file owner design approval pending.** These files are reader editions of sourced terms, not signed originals or newly adopted legal terms.

The legal lane inspected every final PDF page individually at readable 1.5× resolution (13 pages), every desktop dossier HTML surface (13), and all three plain review indexes. Browser checks covered 1360px and 390px widths for every dossier: no horizontal overflow or broken images. Advisory engagement, carry and Northern Nevada mobile views were also inspected manually. The other ten mobile views received programmatic checks only.

An initial Advisory render left its controlling source paths alone on a second page. The source renderer now uses 1.36 line spacing and a 10px heading top margin, retaining 10.5pt body text. The final set has 13 one-page PDFs; no clipped source blocks, overlaps or broken approved logos were observed. Existing controlled PDFs and artwork were reused unchanged.

[Exact page, file and review evidence](PAGE_REVIEW.json) binds final PDF hashes and all 42 retained PNG captures. Source regeneration produced no tracked drift, and repeat PDF rendering produced identical bytes for all 13 files. Re-rendering requires reinspection; [the capture script](render_review.py) deliberately resets the review status.

Open each package's review index: [commercial](../../../commercial/drafts/index.html), [corporate](../../../corporate/drafts/index.html), [assets and rights](../index.html). Each index links the independent PDF and editable HTML. The package visual manifests record exact source, logo, HTML and PDF hashes. Neither this record nor a successful validator approves the design for main.

Reproduce from repository root using an environment with Playwright, PyMuPDF and Chromium:

```bash
python docs/reader/transactions/build.py
python docs/reader/transactions/build_readers.py --render
python docs/legal/evidence/assets-rights/drafts/qa/render_review.py
python docs/reader/transactions/validate.py --drafts
```
