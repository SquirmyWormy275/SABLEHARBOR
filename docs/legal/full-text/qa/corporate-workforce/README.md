# Corporate and workforce edition review

All 26 selected sources and all 76 final PDF pages passed manual publication review. This is readiness for exact-file design review, not user acceptance. The 52 desktop/mobile HTML viewport captures also passed. Six wide mobile tables were checked at both horizontal endpoints; all columns remain accessible through horizontal scrolling.

The hash-bound page and viewport record, method, corrections and limitations are in [report.json](report.json). Individual PDF pages were inspected at 120 dpi, not judged from small contact sheets. Every changed page was reinspected after renderer corrections. Full-height HTML captures supplement viewport inspection; they are not an assertion that every scroll position was manually inspected.

Corrections addressed one-word paragraph orphans, narrow ID/date columns, fragmented ordinary words and an unnecessary printed provenance tail. Source text was not rewritten. Short final pages carrying complete source sections remain valid.

Run `render_review.py` with PyMuPDF and Playwright to recreate page and HTML captures. It deliberately resets manual judgments to PENDING; capture generation is not a visual pass. Run `check_mobile_tables.py` to capture mobile table endpoints. Source and edition status limitations are recorded in [SOURCE_AUDIT.md](../../SOURCE_AUDIT.md).
