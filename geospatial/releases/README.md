# Geo release and supersession record

Current framework version: **0.1.0-rc4**. Canon snapshot: `d91a22c35c91b213204411421de88815f27d8e16`.

The repository contains current source, GeoPackage, QGIS project, controlled atlas/map outputs and validation evidence. `scripts/package_release.py` assembles a self-contained review ZIP plus MANIFEST.json and SHA256SUMS.txt into ignored `geospatial/dist/`. New bundles are published through GitHub Releases; no current ZIP is duplicated in Git.

Target tag: `geospatial-v0.1.0-rc4`. [Release location](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/geospatial-v0.1.0-rc4). The release is delivered only when retrievable assets and checksum verification are recorded in its release metadata. A target URL alone is not publication evidence.

Original rc1/rc2/rc3 archives retain their original bytes at immutable commits indexed by [PR_SOURCE_INVENTORY.json](../history/PR_SOURCE_INVENTORY.json). PR #94 at `7471ba0f405e94e22813b03890d950f5a8aa1582` and #96 at `2849424fd25dd626d1ea2523add65a374f884457` remain provenance. This successor closes integration of the reconciled framework, not the full geographic engineering program.
