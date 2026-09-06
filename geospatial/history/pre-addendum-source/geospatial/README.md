# Master geospatial program — foundation / conflict review

Canon baseline: `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd` (5 September 2026 Pacific). Branch: `feature/master-geospatial-package`; PR #94.

The pinned repository census has inventoried 673 tracked files, scanned 506 text files and returned 2,603 candidate occurrences. A separate reviewed foundation contains 41 geographic objects, 19 sources, six approximate study polygons and two location/reference points. Keyword hits are NOT canonical objects or proof of semantic completeness.

The companion downloadable `sable-harbor-geospatial-0.1.0-foundation.zip` contains the working 12-layer GeoPackage, controlled inputs, Python builders, validator, tests, GeoJSON, QGIS project, registers, two vector map plates and exact source-map evidence. It passed 345 automated foundation checks and 11 tests locally. A repeated same-environment GeoPackage build produced the same SHA-256. Four PDF pages were rendered and visually inspected. QGIS runtime opening was NOT tested; Fiona/GDAL layer reading and QGIS project XML/path checks passed.

## Repository integration boundary

This initial repository commit preserves the source hierarchy, discovered conflicts, schema, study-area inputs, generated study-area GeoJSON, and an execution record. The full downloadable release and every builder/source file have NOT yet been uploaded to this branch. Do not claim a clean repository checkout can rebuild the complete release at this commit. The earlier read-only census workflow can reproduce the pinned whole-tree candidate inventory as an Actions artifact.

No exact mine, campus, yard, interchange or railway is approved here. No source image is modified. No controlling canon is changed. No main merge is requested while the location conflict remains open.

## Blocking Red Wash decision

The two approved maps in `assets/brand/maps/` print 42.3127 N, 106.9213 W, Carbon County. Their bytes match the approved manifest. The current handover instead selects Sweetwater County, north of Wamsutter. Both claims are preserved; neither is silently superseded. See `reports/OPEN_CONFLICTS.md`.

RW-017 through RW-025 also prohibit importing a historical BS&T relationship into Red Wash: no pre-existing carrier arrangement, all 2025 movements by external carriers, no existing direct mine connection on discovery, and the full ARU/BS&T transaction and route case remains open.
