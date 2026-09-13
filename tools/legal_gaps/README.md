# Gap instrument publications

Build with `python tools/legal_gaps/build.py`; validate with
`python tools/legal_gaps/validate.py`. Use the pinned publication environment in
`requirements.txt` and Chromium at `/usr/bin/chromium`.

Markdown in `docs/legal/gap-instruments/source/` controls the draft language.
Companion JSON records proposed terms, unresolved fields and workbook schedules.
The builder publishes the entire Markdown, a searchable SQLite slot per package,
HTML/PDF editions, and Excel schedules without adopting any proposed term.

The typography and full-source rendering approach derive from the review-only
PR #145 legal publication pipeline, commit
`69a562cae5673301303293198d3a2135b3f494ff`. This is a new draft publication, not
acceptance of that design. The approved corporate identity and document standard
remain controlling. No existing approved asset is rewritten.

## Review and reproducibility

Run these from the repository root after installing the pinned Python requirements:

```sh
python tools/legal_gaps/build.py
python tools/legal_gaps/validate.py
python tools/legal_gaps/check_terms.py
python tools/legal_gaps/review_surfaces.py
python tools/legal_gaps/validate_qa.py
python -m pytest -q tests/publications/test_legal_gap_instruments.py --confcutdir=tests/publications
```

The review renderer also needs LibreOffice on PATH. It exports every worksheet
through LibreOffice and checks every populated cell against the rendered text.
It captures all PDF pages and desktop HTML surfaces. The QA validator requires a
separate manual inspection receipt bound to the exact surface manifest hash;
generating screenshots alone does not pass that gate.

Two consecutive builds in the recorded environment produced identical manifests
and artifact hashes, including PDFs, XLSX and SQLite. Chromium and LibreOffice
versions are recorded in the QA receipt. Different browser/font/office versions
can change pagination and raster output; rerender and inspect before accepting
new bytes. PDF and XLSX metadata timestamps are normalized in the builder.

To browse locally, run `python -m http.server 8000` from the repository root and
open `http://localhost:8000/docs/legal/gap-instruments/review.html`.
GitHub readers can use `docs/legal/gap-instruments/PACKAGE_INDEX.md` directly.
