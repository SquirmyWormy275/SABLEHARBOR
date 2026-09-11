# Spatial architectural addendum v1.0.0

[Versioned release and checksums](../../../docs/releases/FACILITY_SPATIAL_RELEASES.md).

Open the [offline spatial review](../../maps/spatial.html), [individual architectural sheets](../../maps/spatial/README.md), or [enterprise atlas](../../maps/index.html). Download the repository or release and open HTML locally; GitHub shows HTML source. The existing atlas and workbench remain the navigation entry points.

This owner-authorized extension preserves accepted R01/R02 geometry and adds coordinated architectural studies. It does not establish construction, occupancy, engineering approval or a geographic location for the fictional Sacramento campus. The accepted base is `ff5cd67ff980790413f7bfbf0829b47d20d266a3`; [architectural assumptions](ARCHITECTURAL_ASSUMPTIONS.json) explicitly identify the new slab, parapet, façade and runtime-height proposals.

## Explore and compare

Select a location or building, drag to orbit, pan and zoom, then peel or explode floors. Select a room in the model or keyboard-accessible selector to open its saved plan. Building links open sections, elevations and roofs; floor links open independent plans and room schedules. External providers have context records without invented interiors. Sacramento rooms are architectural partitions; other rectangles remain program zones.

The geographic-context tab uses committed, hashed official references. Sacramento includes 868 street, 53 rail, eight water, 145 transit-stop, 81 terrain-sample and 76 shared-use-path features. Layer dates and limitations remain visible. The USGS samples are elevations, not surveyed contours. SacRT feed stops are not proof of service on a particular day. No real-world transform places the local campus inside this reference map. [Context methods and provenance](CONTEXT.md).

The comparison tab reports changes by stable site, building, floor and room ID, with affected map links and overlaid room geometry. The default accepted-base comparison has no changed floor geometry. New vertical-study assumptions are identified separately. [Comparison commands and limits](COMPARE.md).

[Access review](ACCESS_REVIEW.md) verifies 21 indirect room routes across six floors with explicit suite, J2 and service-user restrictions. It resolves six concept coordination findings without changing the approved rooms. Forty readiness checks pass; 120 engineering checks remain unassessed. These paths are not an egress or accessibility certification.

## Source and output

The existing [facility sources](../source/), [runtime bridge](../RUNTIME_BRIDGE.json), [population bridge](../population/BRIDGE.md) and [space register](../SPACE_REGISTER.json) remain authoritative for their original facts. [MODEL.json](MODEL.json), [room schedule](ROOM_SCHEDULE.csv), [access overlay data](ACCESS.json), [context data](CONTEXT.json) and [comparison result](COMPARISON.json) are generated derivatives. Unknown room seat categories remain blank rather than becoming invented zeros. Company employment, billets, attendance and physical seats remain distinct; this addendum does not change any population totals.

Eighty-six new sheets use the existing [map ID register](../../registers/MAP_ID_REGISTER.json): 54 building sheets, 25 floor schedules, six access overlays and one regional context sheet. Each has SVG, PNG and PDF outputs. Existing published atlas PDFs and R01 originals retain their prior bytes. The global map manifest records all new derivatives; workbench dependency traversal identifies affected spatial artifacts when a source changes.

## Reproduce

Use Python 3.12, the [geography dependencies](../../requirements.txt), CairoSVG and PyMuPDF. The repository's DejaVu fonts are used for rendering. Node runs the dependency-free viewer tests; browser QA uses Chromium with JavaScript enabled. Exact raster/PDF regeneration requires the same Cairo/font environment.

```sh
python geospatial/facilities/runtime_bridge.py
python geospatial/facilities/population/build.py
python geospatial/facilities/program.py
python geospatial/facilities/render.py
python geospatial/facilities/spatial/build.py --render
python geospatial/facilities/integrate_manifest.py
python geospatial/facilities/atlas.py
python geospatial/facilities/workbench/build.py build
python geospatial/facilities/spatial/build.py --check
python geospatial/facilities/validate.py --check --require-atlas
python -m pytest -q geospatial/facilities/spatial geospatial/facilities/workbench
node geospatial/facilities/spatial/test_viewer.cjs
```

The build checks source hashes, stable IDs, room bounds, floor areas, stacks, sheet completeness, saved artifact hashes and floor links. Mutation tests exercise invalid routes, altered geometry, mismatched sources and revision changes. Rendering and browser inspection supplement these checks. See the hash-bound visual review and release records for acceptance evidence.
