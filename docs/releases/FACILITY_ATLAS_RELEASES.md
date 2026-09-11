# Facility atlas controlled releases

## v0.1.0 — September 11, 2026

Acceptance: [PR #121](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/121). Release publication follows successful final-head CI and PR merge. The GitHub release's published state and tag identify actual delivery; this pre-merge index alone is not a publication claim.

- [Release `facility-atlas-v0.1.0`](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-atlas-v0.1.0).
- [Package](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.zip): **148,862,665 bytes**, SHA-256 `8fb51b8b42eb09b3446977d1c6dc1c4f8faf13dc5887b49bb4a2dc1b26110168`.
- [File manifest](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.manifest.json) and [checksum](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/facility-atlas-v0.1.0/SABLE_HARBOR_Facility_Atlas_v0.1.0.sha256).
- Exact packaged source commit: `dcb827cf296ee5a2e1eb31874d7997c320b1aa6b`; authoritative canon base `786fc9a5311a04dde92ee6dbb08ac3b77a380200`. Later release-index or closeout-evidence commits do not change packaged source identity.
- Contents: 1,842 files plus an embedded package manifest. One file is generated offline release navigation, replacing the source release index to avoid a circular archive checksum; the other 1,841 files retain exact committed bytes. The complete public source context is included deliberately so atlas provenance links work offline. Historical source statuses remain unchanged. Two preserved historical ZIP packages are excluded from redistribution; their original Git bytes remain intact.
- Start at `geospatial/maps/index.html`, or use the portable 146-page PDF and individual map index. Contains 63 facility sheets in three independent formats, 16 site packages, 19 building plans and 27 floors, alongside preserved rc4 context.
- Boundaries: concept layouts and assumed capacity, not established property, hiring, construction, actual occupancy or operating effectiveness. The [dated closeout](../../geospatial/facilities/CLOSEOUT_2026-09-11.md) and per-record coverage dispositions preserve unknown facts.

Build from the exact committed snapshot using:

```sh
python geospatial/facilities/package_release.py \
  --revision dcb827cf296ee5a2e1eb31874d7997c320b1aa6b \
  --output /tmp/SABLE_HARBOR_Facility_Atlas_v0.1.0.zip
```

The builder validates ZIP integrity and every embedded file checksum. Archive member timestamps, ordering and permissions are fixed. Release download bytes must match the recorded checksum before delivery is asserted. Corrections require a successor version; no published asset is silently replaced.
