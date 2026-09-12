# Geospatial validation report

Framework validation: **PASS**. Initial program: **INCOMPLETE**.

178 named-object records; 69 source records; 12402 features in 60 spatial layers; 167 map sheets.

Checks: SQLite integrity and foreign keys; GeoPackage header, rowid keys and CRS; independent GDAL/Fiona geometry readback; all feature sources; source and map checksums; object/entity/decision links; dates; forbidden precision and ownership promotion; portable QGIS source paths.

## Explicitly unevaluated

The accepted industrial case supplies the 40-mile BS&T network, nine-mile truck road, 12 facilities, 31 track-register segments and 26 structures. Detailed engineering remains a synthetic screening model. Early 1898/1954 alignments, survey-grade transitions, earthwork quantities and real land rights are not certified. Native QGIS evidence is recorded separately in QGIS_VALIDATION.json.

## Reference repairs

2 invalid federal source geometries repaired with Shapely make_valid in the derived package. Original response snapshots remain byte-for-byte unchanged; feature-level construction records preserve each repair.

## Errors

None in the validated framework scope.
