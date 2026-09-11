# Source-backed geographic context

`build_context(root)` supplies separate real-world context and an explicitly unsited campus diagram. Sacramento’s approved 840 × 600 ft frame has **no geographic transform or parcel placement**. The display window is an analyst regional extent, not acquired land. Existing master GeoPackage layers are inspected read-only; accepted reference snapshots remain unchanged.

Sacramento context uses EPSG:26910 (NAD83 / UTM zone 10N), metre coordinates relative to `origin_projected_m`. `extent_local_m` gives drawing bounds; x points east and y north. Renderer screen coordinates must invert y. Every feature retains source ID/path/properties and a null campus connection. Geometry is clipped to the regional window, not simplified into invented roads or access links.

Supported categories now include committed federal streets, rail and hydrography, plus three newly archived official snapshots:

- **Transit:** 145 stop points inside the window from [SacRT’s official GTFS portal](https://www.sacrt.com/transit-data-portal/). Downloaded September 11; feed metadata says August 9, 2026–January 2, 2027 (`SEP26 GTFS`). Original selected CSV members and archive/member hashes are retained. Stop presence is not a service-frequency, accessible approach, campus stop or operating-occupancy claim. SacRT’s limited, revocable reproduction/redistribution terms apply; no SacRT logo or endorsement is used. Portal text was verified in the browser; direct archival HTML download returned HTTP403, recorded in DOWNLOAD_LOG.json.
- **Terrain:** 81 discrete points from the official [USGS 3DEP getSamples service](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer). The archived service metadata describes DEM publication through August 24, 2026. Values are metres; original source raster IDs and resolution are retained. The 9 × 9 sampling lattice is roughly 500 m apart: it is not a continuous survey, derived contours, flood surface or excavation model. Vertical datum is not independently established by the response; consult raster metadata before engineering. No interpolation or elevation fabrication occurs.
- **Paths:** 76 clipped class 1 shared-use path features from [SACOG’s Existing Bikeway service](https://services.sacog.org/hosting/rest/services/Transportation/Existing_Bikeway/FeatureServer). The original response includes other bicycle classes; the generator selects only class 1 for pedestrian/shared use. SACOG and regional-jurisdiction copyright/attribution remain explicit; no public-domain grant is asserted. This does not establish complete sidewalks, crossings, ADA condition, legal access or an entrance to the hypothetical campus. Per-feature effective dates remain unknown.

Existing road source descriptions include 2016 TIGER data; rail metadata includes 2025 FRA records. The 2026 retrieval date is not the date a road, building or company occupancy began. The preserved NAIP image has its returned extent and catalog attached; it is optional historical imagery, not a DEM or current vacancy/title evidence.

All 19 facility/runtime locations remain represented. Fort uses Hazelwood context, Bedford uses Fairmont context, and applicable industrial records retain Wamsutter/Wyoming context links. Regional layers are not exact site positions. Runtime provider/owned-site records retain their accepted source boundaries and links; this module adds no speculative street connections. Kanawha imagery is not reused as Bedford evidence. Existing map IDs and their manifest-backed files remain the navigation authority.

`CONTEXT_SOURCES.json` records sources, requests, licenses/attribution, projection, vintage/precision and hashes. `context_sources/` contains raw downloaded responses and original CSV members. The downloaded transit ZIP is not duplicated in Git; its hash and exact preserved-member hashes are retained. No shared source catalog, GeoPackage, geographic layer or map manifest is changed by this module.

```sh
.venv/bin/python geospatial/facilities/spatial/context.py > /tmp/sable-context.json
.venv/bin/python -m pytest geospatial/facilities/spatial/test_context.py -q
```

Rendering and allocated map IDs belong to the integrating generator. Rebuilds consume pinned local bytes without network access and fail on stale source hashes, incomplete path responses, invalid geometry or nonfinite elevation samples.
