# Geo reconciliation validation checkpoint

Accepted baseline: `d91a22c35c91b213204411421de88815f27d8e16`. Successor: v0.1.0-rc4.

- Geo: 20 tests passed, including stale Taylor/Bedford/legal-parent/name/branch rejection, deterministic rebuild, independent readback and temporal boundaries.
- GIS: 175 object records, 68 registered sources, 59 spatial layers and 12,401 features; no SQLite integrity, foreign-key, coordinate, geometry, provenance, source-hash or map-hash errors.
- Cross-model: 40.000000 rail route-miles, nine-mile truck road, 12 facilities, 31 track-register segments, 26 structures and ten industrial history events reconciled to accepted inputs.
- Discovery: all 919 tracked baseline files accounted for; 78,145 extracted geographic occurrences; no extraction errors. OCR not rerun; semantic census remains incomplete.
- Visual: all eleven atlas pages rendered and inspected; corporate labels and Wamsutter sidebar spacing corrected. No off-page text found.
- Package: independently extracted source package rebuilt and validated without access to the original Git checkout.
- Governance/J2, institutional catalog, organization-map and repository hygiene validators passed locally. Existing industrial, finance, approved source artwork and current canon bytes were not edited.
- Native QGIS: CI PASS for the exact package/project hashes, all 59 layers in both original and relocated projects. Version, feature counts, renderers, test-merge commit and workflow/job evidence are recorded in QGIS_VALIDATION.json. The runtime remains unavailable locally.

Remote materialization matched the complete reviewed tree `34a14f6d65043b91ceb42e4c748c2f5b6ac04ff0` byte for byte. BUILD_OUTPUT_EXPECTATIONS.json binds the generated maps/GeoPackage/QGIS bytes. Final acceptance also requires the applicable PR checks. The full original geographic program is incomplete; PROGRAM_CLOSEOUT_MATRIX.md records all sections 0–49 and the remaining work.

PR #105 is the successor to #94/#96. Remaining Geo follow-ups: #106, #107 and #108. The public-file size guard registers only the exact rc4 GeoPackage and the byte-identical approved Blackridge snapshot, with path, size and SHA-256 bounds; all other scans remain enforced.
