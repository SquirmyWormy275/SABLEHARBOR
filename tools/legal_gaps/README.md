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
