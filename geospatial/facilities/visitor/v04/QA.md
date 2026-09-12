# V04 review evidence

Owner direction: V02 preferred over V03; retain content and research comparable real maps before revising aesthetics. Status: draft pending owner acceptance.

Visually inspected the Salk entrance map, Getty Map and Highlights first page, Stanford self-guided map page, and Kati Lacey's Wolfson map. Links and specific design observations are in [README.md](README.md). References are not treated as corporate canon or copied artwork.

Inspected full V04 PNG, PDF raster, desktop comparison and mobile draft page. An initial north-only building projection crowded the Residence identifier and approached the central-quad label; corrected it to a shallower northeast projection and centered the roof labels within each roof. The final rendition retains visible entrances and route, with no observed clipped text or label collisions. Roofs visually occlude small parts of adjacent ground features, as expected in an oblique representation; ground geometry remains unchanged.

Validation passes for source/artifact/reference hashes, preserved V01/V02 hashes, PDF text bounds, XML and all review-page local links. Every mass reconciles to its source footprint, modelled floor count and floor height. V03 remains preserved independently and its validator is still in CI.

Two same-toolchain builds produced byte-identical SVG/PNG/PDF. Browser checks exercised comparison/current/previous modes at 1600 × 1050 and 390 × 844: all images loaded, no horizontal page overflow. Full-resolution images are linked for reading on small screens.

[Comparison](review.html) · [Exact hashes](MANIFEST.json)
