# Geospatial validation report

Framework validation: **PASS**. Initial program: **INCOMPLETE**.

89 named-object records; 52 source records; 11456 features in 50 spatial layers; 11 map sheets.

Checks: SQLite integrity and foreign keys; GeoPackage header, rowid keys and CRS; independent GDAL/Fiona geometry readback; all feature sources; source and map checksums; object/entity/decision links; dates; forbidden precision and ownership promotion; portable QGIS source paths.

## Explicitly unevaluated

A connected Wamsutter-Taylor preliminary BS&T proposal is present, with separately computed ground and formation profiles. It is not an approved historical or construction alignment. Detailed crossings, track transitions, yard capacity, mileposts, earthwork volumes, historical operating dates and real land rights remain open. Native QGIS evidence is recorded separately in QGIS_VALIDATION.json.

## Reference repairs

2 invalid federal source geometries repaired with Shapely make_valid in the derived package. Original response snapshots remain byte-for-byte unchanged; feature-level construction records preserve each repair.

## Errors

None in the validated framework scope.
