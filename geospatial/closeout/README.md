# Geographic evidence package

This package joins the accepted spatial estate to source-bound review records in a portable GeoPackage and QGIS project. The [release index](../../docs/releases/GEOGRAPHIC_EVIDENCE_RELEASES.md) provides the complete download.

## Approved continuity edition 1.2.0

Open `chronology/history.html` for the [source-bound history edition](../chronology/README.md): 73 dated events and observations, 34 site histories and accepted route evolution. Four additional GeoPackage attribute tables expose events, normalized event/object links, site histories and 295 operations-review dispositions. Native QGIS verifies all four evidence relations after relocation. The original [Klein/Fort proposal](../chronology/CONTINUITY_PROPOSAL.md) is retained as review history. Edition 1.2.0 implements its owner-approved staged 2024 relocation, with 73 events and year-bounded occupancy queries.

## Open the package

Extract the entire ZIP, then open `geospatial/qgis/sable_harbor_master.qgz` in QGIS. The project retains the original spatial styling and adds an **Evidence and source registers** group. Its site-to-object relation connects `review_site_evidence.object_id` to the canonical `object_registry.object_id`.

The database is `geospatial/master/sable_harbor_master_v0.1.gpkg`. Its compatibility filename is preserved so the portable project keeps working; the geographic evidence release has its own version and manifest. The GeoPackage opens directly in other GIS tools, and its attribute tables can be queried through SQLite.

The existing facility atlas opens at `geospatial/maps/index.html`. The preserved evidence review edition opens at `review/review.html`; its source revision remains explicitly pinned to release 1.1.0. No server or account is required to browse the packaged HTML.

| Table | Contents | Boundary |
|---|---|---|
| Existing feature layers | Full accepted spatial rows, including original geometry, precision and temporal metadata | No new parcel, survey geometry or historical alignment is invented. |
| `review_site_evidence` | 30 SH-SITE records and four named Fort components, exact archived source bindings, geometry references and temporal meanings | Programme, incident, provider-selection and acquisition dates do not become occupancy intervals. |
| `review_occurrences` | Exact 8,961 occurrence carriers outside the three accepted review batches | Unresolved discovery population; no automatic geographic claim adjudication. |
| `review_source_coverage` | 919 baseline files verified against archived bytes | Hash verification does not imply semantic review. |
| `review_source_changes` | Added, modified and removed paths since discovery | A source-tree comparison, not approval of every later claim. |
| `review_raster_candidates` | The 97-image OCR population from accepted evidence release 1.1.0 | Unreviewed machine text; raw word positions/confidence and engine provenance remain under `review/`. |

`SITE_EVIDENCE.csv` is a compact worksheet. `SITE_EVIDENCE.json` retains every full record, source excerpt, operational-state record and feature hash. Seventeen distinct archived source files are supplied with SHA-256 identities under `archived-sources/`.

## Rebuild and qualify

Use a clean checkout with full Git history. Install the locked root dependencies with `make bootstrap`. Retrieve the immutable predecessor package from [evidence release 1.1.0](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/closeout-evidence-v1.1.0). The builder requires its exact SHA-256, `70723d888c6e9eccf9cc9fac87da4fd37e241468a2aefdf0fc097d7325c379d5`; a different archive is rejected.

```bash
uv run --with-requirements geospatial/requirements.txt python -m geospatial.closeout.package \
  --output var/geographic-evidence \
  --evidence-archive /path/to/sable-harbor-closeout-evidence-v1.1.0.zip

uv run --with-requirements tools/wiki/visual/requirements.txt playwright install --only-shell chromium
uv run --with-requirements tools/wiki/visual/requirements.txt python -m geospatial.chronology.check_browser --directory var/geographic-evidence/chronology

QT_QPA_PLATFORM=offscreen /usr/bin/python3 geospatial/closeout/native.py \
  --package var/geographic-evidence

uv run --with-requirements geospatial/requirements.txt python -m geospatial.closeout.package \
  --output var/geographic-evidence --seal
```

The native step requires a system Python with QGIS bindings. The dedicated GitHub workflow installs these dependencies, builds the package, reads and renders it in QGIS, and verifies a relocated project. It checks every registered spatial layer and attribute table, including the site-object relation. Sealing rejects a dirty preview, absent/stale native verification or a replaced existing archive.

Fiona independently verifies layer counts and EPSG:4326. SQLite checks integrity and the site-ID crosswalk. The builder compares every accepted spatial row, including its geometry blob and metadata, before and after the rebuild. The original tracked GeoPackage, maps, approved images and previous release bytes are not overwritten. Native QGIS and ZIP metadata can vary by environment; source and dataset comparisons are separate from artifact checksums.

The top-level `PACKAGE_MANIFEST.json`, `VALIDATION.json`, `NATIVE_QGIS.json` and `BUILD.json` describe the new delivery. Historical QA files retained inside the copied geographic tree describe their original releases. Verify downloaded files against the release checksums and the package manifest before relying on them.

## Issue acceptance

The package completes a source-bound representation and review deliverable. It does **not** close #106 or #108 by substituting missing facts with empty fields. The Klein/Fort continuity and year-bounded occupancy are now owner-approved; other exact site occupancy and parcel evidence remain unresolved; detailed railway geometry and engineering remain under #107. The broader semantic/historical programme remains under #108. New source evidence or accepted fictional decisions must resolve those substantive requirements before whole-issue closure.

The workflow can transfer a qualified ZIP directly to an existing draft release when dispatched on accepted `main` with the optional `release_tag` input. It verifies the version, source commit, draft target and every manifest member; it neither replaces existing assets nor publishes the draft. Normal PR/build runs retain read-only permissions.
