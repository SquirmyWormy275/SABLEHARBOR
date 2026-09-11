# Spatial viewer browser and visual review

Result: **PASS** for the offline viewer at `geospatial/maps/spatial.html`.
Reviewed HTML SHA-256: `bebbeb59dda70dc558a9281dd55d5106874b45086cbd42f3ec9240ded5844176`.
Viewer source freeze: `1e16da6`. Exact source and screenshot hashes are in [RESULTS.json](RESULTS.json).

System Chromium was driven with Playwright over `file://`, without a server or CDN. Desktop viewport was 1500 × 1100; mobile viewport was 390 × 844. All 19 site selections and 18 building selections passed. Every building exposes its section, elevation and roof links. Floor hash navigation, room dropdown selection, direct canvas picking, orbit, wheel zoom, right-drag pan, plan view, floor peeling and exploded floors were exercised. Three tabs rendered at both viewport sizes with no horizontal page overflow or browser exceptions.

All 19 site and 18 building screenshots were inspected through ten readable contact sheets. Separate desktop and mobile captures were inspected for room details, legends, links, controls, comparison and context. Corrected defects were site envelopes cropped by building-only framing, oversized framing after a mobile resize, and filled context boundary polygons obscuring line layers. Final site envelopes and building volumes fit the reset view. Nonarchitectural program zones remain flat with dashed height envelopes; external locations retain explicit context-only dispositions.

The Sacramento context inset uses supplied projected layers and explicitly leaves the campus unsited. Other locations retain their accepted map links; this review does not claim newly rendered Hazelwood, Fairmont or Wamsutter SVG insets. The actual embedded comparison records zero source changes. The separately labelled `comparison-overlay-fixture.png` tests a one-metre room shift imported through the file control, followed by reset to the embedded comparison and rejection of an invalid site ID. This fixture does not alter committed geometry or canon.

Reproduction commands, from the repository root:

```sh
node geospatial/facilities/spatial/test_viewer.cjs
.venv/bin/python geospatial/facilities/qa/spatial-viewer/browser_review.py
.venv/bin/python geospatial/facilities/qa/spatial-viewer/import_review.py
.venv/bin/python geospatial/facilities/qa/spatial-viewer/contact_sheets.py
.venv/bin/ruff check geospatial/facilities/qa/spatial-viewer
```

Node checks cover local coordinate projection, depth, polygon picking and comparison import identity/geometry validation. Browser scripts capture fresh evidence; rerunning the browser script replaces the automated results and requires renewed manual review before a final QA claim. This report covers the interactive viewer, not the separate 86-sheet publication, engineering certification, repository CI or merge gates.

[Recheck after the CI reproducibility correction](RECHECK.json) binds the current HTML. Scene data and viewer source are unchanged; source-hash ordering and the builder hash changed. All browser interactions and comparison import were rerun successfully.
