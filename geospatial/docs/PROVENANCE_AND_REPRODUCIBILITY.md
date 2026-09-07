# Provenance and reproducibility

Normal builds are offline and source-pinned. The adapter uses accepted industrial sources; the GeoPackage uses `sources/catalog.json`, committed GeoJSON, the SQL schema and exact reference snapshots. GeoPackage rebuilds are tested for byte identity in the pinned environment. Maps consume the built GeoPackage, with source hash, version, projection, effective date and render hashes in the map manifest.

Every old-PR geographic path is recorded with immutable commit, Git blob ID, size and URL in `history/PR_SOURCE_INVENTORY.json`. Source quotations are retained verbatim even when a current name or region changes. `history/PRESERVATION_MANIFEST.json` binds archived local bytes and source snapshots. Original packages remain at their immutable old branch paths; a successor receives a new release version.

`registers/SOURCE_COVERAGE.csv` accounts for the pinned main tree. The occurrence index and distinct wording register are extraction aids, not canonical objects. Extraction limitations and OCR state are explicit in `CENSUS_MANIFEST.json`. No assertion that every map, PDF page or occurrence has been semantically adjudicated follows from a full-tree scan.

The `.qgz` project references `../master/sable_harbor_master_v0.1.gpkg`. Independent GDAL/Fiona checks and native QGIS checks are different evidence. Prior rc2/rc3 QGIS status is historical; only a report matching current package/project hashes can validate the successor.
