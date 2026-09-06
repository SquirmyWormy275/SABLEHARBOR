# Foundation execution record — 5 September 2026

Pinned main: 8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd.

## Executed

The read-only Geospatial census workflow ran on PR #94. Run ID 34003784536; artifact ID 9980282072, `sable-harbor-geospatial-census`. The artifact contained an exact pinned source archive, source coverage, raw candidate occurrences and coverage manifest. The archive was downloaded and safely extracted for local analysis.

Counts: 673 tracked files; 506 text files scanned; 2,603 raw keyword occurrences. These are not 2,603 distinct sites. The reviewed geographic register contains 41 objects. A separate binary/map inventory covers 232 PNG/SVG/PDF/Office/archive assets; only the two recovered Red Wash source maps are certified here as visually inspected location evidence.

The local working foundation has 19 source records, six study polygons, a conflicting Red Wash coordinate-label point and an approximate Wamsutter reference point. Twelve typed GeoPackage layers exist, including intentionally empty facility, site, rail and territory layers. There are zero engineered railway segments and zero approved exact site geometries.

Local validation: 345/345 automated foundation checks, 11 tests passed, source quotes and available hashes verified, foreign keys/integrity/CRS/GeoJSON parity checked. The same-environment repeat build of the GeoPackage had SHA-256 `ab9984a6733dd507788bb6a3340ef1ccb5b9c00a89934fab7cf44cefba82525e`. Cross-version binary determinism is not claimed. QGIS project XML and relative paths were checked; actual QGIS runtime opening remains NOT_TESTED.

Two 17 x 11 vector map plates were built: geographic framework and Red Wash location conflict. A two-page source-evidence PDF preserves the approved maps. Four PDF pages were rendered with pdftoppm and visually reviewed. Source PNGs are unchanged.

## Not completed / not claimed

Full semantic census, full binary/archive review, exact mine/campus/yard/interchange polygons, elevation or land-tenure analysis, host railway geometry, historical route dates, connected BS&T engineering and the full map series remain incomplete. The full local release and every builder/source file have not yet been uploaded to the repository. The companion ZIP contains that work; this initial commit preserves core controls and a working study-area export entry point. No main merge or geographic canon supersession has occurred.
