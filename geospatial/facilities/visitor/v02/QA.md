# V02 visual and preservation review

Review date: 11 September 2026. Status: draft; user visual acceptance pending.

- Inspected the complete PNG and PDF raster, plus desktop comparison and mobile full-width browser screenshots. Labels, entrances, parking symbols, route and directory render without visible clipping or overlap.
- Exercised comparison, V01-only and V02-only modes at 1600 × 1050 and 390 × 844. All images loaded; no horizontal page overflow. Full-resolution image links support inspection beyond the reduced page preview.
- Validated SVG XML, all PDF text bounds, source and artifact hashes, the four original R01 hashes, and every comparison-page local link.
- Rebuilt SVG, PNG and PDF twice: byte-identical outputs in the same toolchain.
- Re-ran the V01 validator, including its source, artifact and review-page hashes. V01 remains unchanged.
- Highlighted route remains within source walks and outside building interiors; entrances remain tied to the accepted source coordinates.

Corrections from V01: removed pastel building fills and duplicate in-map reception subtitles; restored source parking markings; reduced directory density; changed heading to Campus Visitor Guide. No campus geometry changes. The inner footprint keyline is graphic articulation only.

Run `python geospatial/facilities/visitor/v02/validate.py` from the repository root. The review surface is [review.html](review.html); source and output hashes are in [MANIFEST.json](MANIFEST.json).
