# Facility atlas controlled releases

## v0.1.0 — September 11, 2026

Acceptance: [PR #121](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/121). Release publication follows successful final-head CI and PR merge. The GitHub release's published state and tag identify actual delivery; this pre-merge index alone is not a publication claim.

- [Release `facility-atlas-v0.1.0`](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-atlas-v0.1.0).
- [Package](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.zip): **148,857,623 bytes**, SHA-256 `6176c016f302d1689d43822b9f7c1a83a59943ed387f57c8247f9b31e53ed2cf`.
- [File manifest](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.manifest.json) and [checksum](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.sha256).
- Exact packaged source commit: `2b6384bafcab553ea126f010c7c1eec68a85faca`; authoritative canon base `786fc9a5311a04dde92ee6dbb08ac3b77a380200`. Later release-index or closeout-evidence commits do not change packaged source identity.
- Contents: 1,841 committed files plus an embedded package manifest. The complete public source context is included deliberately so atlas provenance links work offline. Historical source statuses remain unchanged. Two preserved historical ZIP packages are excluded from redistribution; their original Git bytes remain intact.
- Start at `geospatial/maps/index.html`, or use the portable 146-page PDF and individual map index. Contains 63 facility sheets in three independent formats, 16 site packages, 19 building plans and 27 floors, alongside preserved rc4 context.
- Boundaries: concept layouts and assumed capacity, not established property, hiring, construction, actual occupancy or operating effectiveness. The [dated closeout](../../geospatial/facilities/CLOSEOUT_2026-09-11.md) and per-record coverage dispositions preserve unknown facts.

Build from the exact committed snapshot using:

```sh
python geospatial/facilities/package_release.py \
  --revision 2b6384bafcab553ea126f010c7c1eec68a85faca \
  --output /tmp/SABLE_HARBOR_Facility_Atlas_v0.1.0.zip
```

The builder validates ZIP integrity and every embedded file checksum. Archive member timestamps, ordering and permissions are fixed. Release download bytes must match the recorded checksum before delivery is asserted. Corrections require a successor version; no published asset is silently replaced.
