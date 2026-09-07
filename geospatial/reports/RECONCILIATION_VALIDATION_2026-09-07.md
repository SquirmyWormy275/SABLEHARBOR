# Geo reconciliation validation checkpoint

Accepted baseline: `d91a22c35c91b213204411421de88815f27d8e16`. Successor: v0.1.0-rc4.

- Geo: 20 tests passed, including stale Taylor/Bedford/legal-parent/name/branch rejection, deterministic rebuild, independent readback and temporal boundaries.
- GIS: 175 object records, 68 registered sources, 59 spatial layers and 12,401 features; no SQLite integrity, foreign-key, coordinate, geometry, provenance, source-hash or map-hash errors.
- Cross-model: 40.000000 rail route-miles, nine-mile truck road, 12 facilities, 31 track-register segments, 26 structures and ten industrial history events reconciled to accepted inputs.
- Discovery: all 919 tracked baseline files accounted for; 78,145 extracted geographic occurrences; no extraction errors. OCR not rerun; semantic census remains incomplete.
- Visual: all eleven atlas pages rendered and inspected; corporate labels and Wamsutter sidebar spacing corrected. No off-page text found.
- Package: independently extracted source package rebuilt and validated without access to the original Git checkout.
- Governance/J2, institutional catalog, organization-map and repository hygiene validators passed locally. Existing industrial, finance, approved source artwork and current canon bytes were not edited.
- Native QGIS: unavailable locally; exact current source/project hashes recorded. A dedicated native CI job checks opening, feature counts, renderers and relocation; its result is separate evidence.

Remote materialization must match BUILD_OUTPUT_EXPECTATIONS.json before committing generated maps/GeoPackage/QGIS bytes. Final acceptance also requires the applicable PR checks. The full original geographic program is incomplete; PROGRAM_CLOSEOUT_MATRIX.md records all sections 0–49 and the remaining work.
