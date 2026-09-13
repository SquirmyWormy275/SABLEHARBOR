# Geographic requirements: source review, site alternatives and history

This work addresses the remaining executable requirements in #106 and #108 from accepted main `a8e6dd99c113e0470bdc4fcc63bab616949186d0`. The [versioned geographic release](../../docs/releases/GEOGRAPHIC_EVIDENCE_RELEASES.md) contains the complete offline readers, maps, source records and validation. Acceptance belongs to the merged PR and its release receipt; these files do not authorize new property rights or fictional occupancy dates.

## Read the completed work

In the extracted release, open:

- `completion/maps/index.html`: searchable historical and site atlas, with standalone PDF/SVG/PNG plates and one bookmarked PDF.
- `completion/site-docket.html`: all 34 site/component records, 17 independently bound controlling excerpts, approved occupancy bounds and concrete remaining evidence or decisions.
- `completion/source-review.html`: 1,770 newly reviewed discovery carriers across 147 archived files, with complete records, pagination and source/disposition filters.
- `completion/ocr/RASTER_INVENTORY.json`: every baseline PDF/office/archive container, page/image coverage and executed sparse-page OCR provenance.

QGIS includes two additional **unselected** GeoJSON layers for nine site alternatives and nine access tests, switched off initially. They are separate from the 60 accepted spatial tables, whose original rows are preserved. Five new review tables retain source, visual, site-docket, observation and option records. Eight QGIS evidence relationships are validated before and after moving the package.

## Source adjudication

[The review](SOURCE_REVIEW.json) preserves each original occurrence ID, source locator, wording and baseline revision. Every source hash is checked against the discovery inventory. Executable/test references retain nearby text and their enclosing Python function/class where applicable. SQL/configuration/checksum/diagram references remain representations rather than independent geographic evidence. Every selected financial record retains its full containing record, including all 90 employee-allocation carriers. Each geographic property retains the complete feature and geometry hash.

Five disjoint batches now classify **71,249 of 78,145** original discovery carriers. [The remaining 6,896](REMAINING_OCCURRENCES.csv.gz) are preserved individually. No narrative, publication or subsequent canon delta is declared semantically reviewed merely because its file type, name or hash is known. The 919-source baseline and complete later tree-change inventory remain in the parent package.

Reproduce with `uv run python -m geospatial.completion.source_review`. Changing a quote, pointer, source byte or population causes validation to fail. Classification of a copied reference does not erase the underlying record or claim that its content is false.

## Visual and OCR evidence

[Visual dispositions](RASTER_REVIEW.json) cover all **97 individually registered baseline PNGs**. Contact sheets were inspected for image role; the two geographic images and enterprise overview were inspected at full image resolution. Small-text transcription is not claimed for contact-sheet review.

The two Red Wash maps visibly print **Carbon County** and **42.3127° N, 106.9213° W**. They are superseded geographic illustrations under GEO-C001 and the [governing addendum](../sources/GOVERNING_CANON_ADDENDUM_2026-09-05.md). Sweetwater and the accepted 42.22, -108.18 anchor continue to control. The old pixels, conceptual component drawings and conflicting coordinate grids remain preserved; none is digitized into new accepted geometry.

The broader audit inspects **109 containers**, **101 distinct PDFs / 353 pages**, and **290 embedded-image appearances / 135 distinct byte identities**. Seventy-four appearances match reviewed baseline PNG bytes exactly. All three unique low-text PDF pages with embedded raster images receive fresh Tesseract OCR at 144 dpi. Raw TSV, logs, source/render hashes, engine/executable/model identities and the exact selection rule are retained. This sparse-page rule is not a universal visual reading of every PDF page; remaining image content and later images retain explicit review limits. The archived numeric GeoTIFF is read as geographic cell data and metadata, not sent to text OCR.

## Dimensioned site alternatives

[Sacramento, Fort and Bedford screens](SITE_SCREEN.json) produce three alternatives each. These implement the mandate to engineer fictional site geometry, while keeping selection and unsupported physical facts explicit.

| Site | Dimensioned design | Controlling scope |
|---|---|---|
| Sacramento | 256.032 × 182.88 m; 11.57 acres | The accepted R01-derived 840 × 600 ft envelope remains unchanged; 8–15 acre geographic design range. |
| Fort / Willow | 300 × 220 m; 16.31 acres | Separate 10–20 acre industrial premises; approved 2024 relocation preserved. |
| Bedford | 330 × 220 m; 17.94 acres | 15–20 acre Fairmont-area brownfield concept, distinct from the Demotte host. |

The deterministic projected grid tests containment within the archived study window and excludes intersections with buffered archived road, railway and hydro linework. Alternatives are ranked by a short straight-line gap to an ordinary road reference; this is **not a suitability ranking**. The nine access lines are geometric tests, not engineered driveways or easements. The full screen records the projection, dimensions, source hashes, candidates considered and criteria.

These alternatives have **no selected parcel, property owner or invented occupancy interval**. Building/tenant occupancy, parcel interests, zoning, floodplain and actual waterbody extent, terrain/geotechnical conditions, contamination, utility capacity and access permission are unestablished. A linework-clear rectangle must not be presented as a construction-ready or approved site.

Kelly Gang and Demotte receive separate host-interface plates showing the process/recovery boundary and bypass. They remain regionally located external hosts. No synthetic layout transfers their plant, water-treatment obligations or land to Cradle.

## Historical map series

Every year represented in the 73-event chronology receives a dated plate, with additional 2015 and 2017 continuity checkpoints. Maps use the five explicitly dated accepted route segments. No modern alignment appears before its effective interval; 1898 and 1954 remain unlocated histories. Event bounds and year-end route views have separate meanings. Current owner fields are not projected backward. `FRAME_EVENTS.csv` retains every event/frame link, including events too numerous for an individual plate's summary.

The series is the complete published view of the recovered dated evidence, not a claim that unsourced early/abandoned routes or every enterprise occupancy history has been recovered.

## Reproduce and validate

```bash
make bootstrap
uv run --with-requirements geospatial/requirements.txt python -m geospatial.completion.build --output var/research
uv run --with-requirements geospatial/requirements.txt python -m pytest geospatial/tests/test_completion.py -q
uv run --with-requirements tools/wiki/visual/requirements.txt python -m geospatial.completion.check_browser --directory var/research
```

Install Tesseract with English data for the build, and Chromium through the documented Playwright setup for browser checks. The full [package build](../closeout/README.md) includes these outputs, native QGIS read/render/relocation checks, source-row preservation and a checksum for every delivered file.

## Remaining issue boundary

The [site docket](SITE_DOCKET.json) distinguishes proposed offices, shared/dedicated accommodation decisions, operating hosts, aggregate collections, Fort components and runtime-controlled evidence. It identifies the exact next action for each of the 34 records. Source prose now positively distinguishes Demotte's operating snapshot from the merely proposed Reno/Elko/Tucson office network.

#106 remains open for supported site selection, occupancy and access evidence. #108 remains open for the 6,896 remaining baseline carriers, full narrative/publication semantics, later-source claims, unmatched embedded image content and unsourced historical geometry. The new maps, OCR and review rows complete specific executable work; they do not close an unresolved institutional decision by relabeling it.
