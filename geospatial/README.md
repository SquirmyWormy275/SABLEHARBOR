# Sable Harbor geospatial framework

[R02 facility drill-down atlas](maps/index.html) · [Campus and floor programme](facilities/README.md) · [Individual plans](maps/facilities/ARTIFACT_INDEX.md)

Facility successor v0.2.0 preserves the approved R01 Sacramento four-building/ten-floor baseline and adds 58 facility sheets across 16 site packages; final R02 QA and release gates remain pending. The geographic rc4 source bytes and status boundaries remain intact.

**v0.1.0-rc4 — reconciled to accepted September 7 canon.** The integration closes the superseded Geo draft work; the full geographic engineering program remains incomplete.

Open the [eleven-sheet atlas](maps/SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc4.pdf), [GeoPackage](master/sable_harbor_master_v0.1.gpkg), [portable QGIS project](qgis/sable_harbor_master.qgz), or [closeout matrix](docs/PROGRAM_CLOSEOUT_MATRIX.md).

## Current source authority

The enterprise Geo package is a combined view. `sources/catalog.json` governs its enterprise object/provenance register. The accepted `industrial/source/operations.json`, `industrial/source/entities.json` and `industrial/source/geography/network.geojson` govern industrial identities and geometry. `scripts/sync_industrial.py` consumes those sources and rejects unreviewed source-hash drift. It does not edit industrial or finance inputs.

- Bedford: Fairmont-area Cradle center, 15–20 acres; exact parcel unfinished. Belle/Kanawha is historical editorial siting, not an operating site or relocation.
- The Fort: Willow's Pittsburgh-area 10–20 acre compound, with Big Shed research, Small Shed administration/temporary lodging, White Shed controlled intake/storage and the Museum working yard. Klein is the historical precursor. Exact shop/Fort occupancy linkage remains open.
- Kelly Gang Mining: external Tasmanian Stream 17 host. Demotte Reclamation Services: separate north-central WV AMD host. Host geography and equipment/recovery rights do not create Sable Harbor ownership of the host.
- Red Wash: 42.22 N, 108.18 W, Sweetwater County. Taylor: accepted candidate A at 42.12 N, 108.10 W. BS&T: 33.3485 mainline + 4.0000 East Materials + 2.6515 Mineral Transfer = 40.0000 route-miles. Truck-only mine access: nine modeled miles; no mine spur.
- The industrial case supplies 12 facilities, 31 track-register segments, 26 structures and ten history events. The 1898/1954 physical alignments remain unlocated; current geometry is not backdated into those epochs. All 2025 Red Wash transport remains external-carrier. Uranium custody remains OPEN_GATED.
- Legal mapping follows SHI → SHIH → Pale Sun → Red Wash and SHIH → ARU → BS&T. Northstar Minerals, Inc. remains external.

## Rebuild and check

```sh
python -m pip install -r geospatial/requirements.txt
python geospatial/scripts/sync_industrial.py
python geospatial/scripts/build_geopackage.py
python geospatial/scripts/render_maps.py
python geospatial/scripts/validate_geospatial.py
python -m pytest geospatial/tests -q
```

Native QGIS, when installed, uses `QT_QPA_PLATFORM=offscreen /usr/bin/python3 geospatial/scripts/validate_qgis.py`. Its evidence is separate from GDAL/Fiona readback. The original and relocated project are both checked.

The census command is `python geospatial/scripts/census.py --ref <accepted-canon-commit> --no-ocr`. Extraction is not semantic acceptance or visual inspection. Every tracked source is accounted for, and per-file extraction limitations are explicit.

## Preservation and delivery

[PR source inventory](history/PR_SOURCE_INVENTORY.json) records every Geo path/blob in PRs #94 and #96 at immutable commits. Earlier source quotations, snapshots and superseded geometry remain traceable. Old rc1/rc2/rc3 ZIPs remain at their original immutable branch paths; no old package bytes are replaced. New distributable bundles belong in GitHub Releases under the repository packaging policy; `scripts/package_release.py` writes only to ignored `dist/`.

[Validation report](reports/GEOSPATIAL_VALIDATION_REPORT.md), [industrial reconciliation](reports/INDUSTRIAL_RECONCILIATION.json), and [open questions](registers/OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md) state the actual limits. A valid framework is not a surveyed estate, a completed 50-section program, or a claim of actual land/rail rights.
