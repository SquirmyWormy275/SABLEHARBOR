# Provenance and reproducibility

## Census coverage

The discovery run reads all 673 tracked files in the pinned main tree. It extracts plain text, JSON strings, PDF text, Office XML, SQLite text, ZIP members and raster OCR. File SHA-256, exact locators and extraction methods are retained in `registers/SOURCE_COVERAGE.csv`. It produced 65,932 candidate occurrences and 3,711 distinct exact wordings, with no extraction errors. Generated Blackridge database text supplies most repeated occurrences; those are not 65,932 distinct corporate assets.

`GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz` is a losslessly compressed CSV with exact source wording; `DISCOVERY_STATEMENTS.csv` is a deduplicated discovery index with counts and example locators. The 89-object curated census supplies classification, source, time, conflicts and next action for adjudicated named objects. Keyword matches, OCR and XML extraction do not guarantee exhaustive semantic interpretation of every sentence, embedded image, drawing or note. `semantic_census_complete` deliberately remains false. A follow-on review must trace any newly adjudicated reference into the object register and preserve its source occurrence.

The selected Red Wash image originals received visual inspection and hash verification. Other images are registered and OCR-indexed unless a separate inspection is expressly documented. The HQ reference binary is not declared recovered merely because a hash appears in text.

## Reference snapshots

Each federal extract is fetched with a bounded query and an independent count and object-ID request. IDs are paginated in chunks of 500. Transfer-limit flags, mismatched counts and partial fetches fail the snapshot. Request URLs, response hashes, output hashes, authority and license are recorded in `sources/reference_manifest.json`.

Raw reference GeoJSON is retained unchanged as build input. Generalized Census geometry that is invalid is repaired only in the derived package using Shapely `make_valid`; the original validity explanation, method and area change are saved in feature properties. Generalization and repair make these context layers unsuitable as cadastral boundaries. The Red Wash county check uses a separately archived unsimplified server-side intersection.

The federal snapshot access date is not necessarily its survey, acquisition or update date. Transportation, hydrography and municipal data have different source vintages. Feature accuracy is left unknown when it is not supplied. State context is generalized at 0.02 degrees; counties at 0.001 degrees; places at 0.0001 degrees. Road/rail/hydro coordinates are rounded to six decimals on extraction, without assuming equivalent positional accuracy.

The two NAIP screen images and their source catalog responses are separately hashed. Catalog results include overviews as well as source tiles. The 2022 tile dates support the imagery-vintage note; no claim is made that every displayed pixel was individually attributed to one tile. Image export metadata record the server-adjusted extent. No raster has been used as an undocumented georeferencing shortcut.

## Build chain

1. Governed catalog and GeoJSON plus pinned references → deterministic GeoPackage.
2. GeoPackage → portable QGIS XML project and PDF/SVG/PNG map sheets.
3. Independent GDAL/Fiona readback, SQLite integrity/foreign keys, status/date/provenance checks and map hashes → structural validation report.
4. Targeted tests → false-date, damaged-network and deterministic-rebuild evidence.
5. Native QGIS loads original and relocated projects → separate compatibility report.
6. PDF pages and PNG exports are rendered and visually inspected → visual QA report.
7. Versioned release staging and archive → file manifest and SHA-256 checksums.

Changing a source requires rebuilding dependent maps; validation rejects stale GeoPackage hashes in map metadata. Normal build commands perform no network fetch. Refresh is deliberate and reviewed in Git. The baseline main hash remains fixed even if main later moves; changing it requires a new census and reconciliation.

For portability, the release contains the geospatial inputs, scripts, references, registers, maps, database and relative QGIS layout. Pinned source snapshots are included for standalone hash validation. Full source census re-execution additionally needs the SABLEHARBOR Git history at the pinned commit and Tesseract. The release manifest identifies those requirements instead of pretending an exported zip contains the entire repository history.
