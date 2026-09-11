# Spatial integration review

The [hash-bound record](REVIEW.json) confirms 258 new SVG/PNG/PDF assets regenerated identically, while all 210 existing facility/runtime assets and the old 150-page atlas remain byte-identical. The new portable addendum has 86 pages and 86 bookmarks. Every new PDF page passes text-bound inspection.

The Sacramento context sheet was visually inspected after centering the map and adding source-derived road/river labels and selected elevation sample annotations. No site polygon is placed in this real reference frame. The other 85 sheets have their own [complete visual review](../spatial-architecture/REVIEW.md). [Browser review](../spatial-viewer/REVIEW.md) covers the interactive surfaces.

The integrated package passes 154 focused facility, population, coverage, workbench and spatial tests. Source freshness, area/stack reconciliation and atlas links pass. A clean detached baseline run passed 166 root tests (three skips), 23 geography tests and the maintainer validators. Publication/catalog rebuilds retained 131 publications without tracked drift. Native QGIS is unavailable locally; final CI must supply its required pass. Final-head checks, merge and retrieved release hashes are recorded in the release acceptance evidence.
