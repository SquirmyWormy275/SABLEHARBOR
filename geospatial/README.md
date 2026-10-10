# Sable Harbor geospatial framework

[Current locations](../docs/wiki/Locations.md) describes the offices and operating sites. For the decisions behind the maps, use [Records and decisions](../docs/wiki/Records-and-Decisions.md#locations). The package editions below retain their own dates and scope.

## Explore the places

Start with the [Sacramento visitor map](facilities/visitor/v08/artifacts/visitor-map-v08.png), browse the [individual maps and floor plans](maps/facilities/ARTIFACT_INDEX.md), or download the [facility atlas PDF](maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf). The [interactive atlas](maps/index.html) runs locally from a downloaded checkout, not inside GitHub.

| Edition | What it contains |
|---|---|
| [Facility atlas v0.2.0 / R02](../docs/releases/FACILITY_ATLAS_RELEASES.md) | Published September 11, 2026. It preserves the approved four-building, ten-floor Sacramento baseline and connects site, building and floor plans with the runtime locations. |
| [Geographic evidence v1.5.0](../docs/releases/GEOGRAPHIC_EVIDENCE_1_5_0_RECEIPT.md) | Published September 29, 2026. The complete declared synthetic geographic edition, including its preserved earlier package and supplement. |
| [Geographic framework v0.1.0-rc4](maps/SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc4.pdf) | The earlier eleven-sheet context atlas. Its [GeoPackage](master/sable_harbor_master_v0.1.gpkg), [QGIS project](qgis/sable_harbor_master.qgz) and [closeout matrix](docs/PROGRAM_CLOSEOUT_MATRIX.md) retain that edition's dates and limitations. |

A published plan is not a completed building, a survey or a property conveyance. Use the [locations guide](../docs/wiki/Locations.md) to distinguish offices, operating sites, shared accommodation and proposed facilities. The 1898/1954 rail alignments remain unlocated; later illustrative history does not establish their real positions.

<details>
<summary>Atlas inventory and earlier editions</summary>

The original facility subpackage contains 58 sheets across 16 sites. The [runtime bridge](facilities/RUNTIME_BRIDGE.json) reuses twelve existing plates and adds three location packages, one proposed building and one floor. The combined inventory is 19 locations, 18 buildings, 25 floors and 70 facility/runtime plates in 210 SVG/PNG/PDF assets, plus eleven preserved rc4 context records: 81 maps. The [facility release record](../docs/releases/FACILITY_ATLAS_RELEASES.md) provides the checks and publication history.

The rc4 framework was reconciled to September 7 company decisions. Its original open-work statements describe that edition, not the later v1.5.0 delivery. Engineering, survey and real-world rights limitations remain in force.

</details>

## Current source authority

The geographic package brings several source sets together. `sources/catalog.json` governs its enterprise object/provenance register. The accepted `industrial/source/operations.json`, `industrial/source/entities.json` and `industrial/source/geography/network.geojson` govern industrial identities and geometry. `scripts/sync_industrial.py` consumes those sources and rejects unreviewed source-hash drift. It does not edit industrial or finance inputs.

- Bedford: Cradle’s Fairmont / White Hall-area center. The September 13 decision selects a 15.27-acre fictional redevelopment footprint. Belle/Kanawha is historical siting, not a current operation; the selected footprint is not a real property conveyance.
- The Fort: Willow’s Hazelwood, Pittsburgh compound, with Big Shed research, Small Shed administration/temporary lodging, White Shed intake/storage and the Museum working yard. The September 13 decision selects a 10.65-acre fictional footprint and preserves the staged 2024 move. The earlier Klein shop remains a distinct historical premise.
- Kelly Gang Mining: external Tasmanian Stream 17 host. Demotte Reclamation Services: separate north-central WV AMD host. Host geography and equipment/recovery rights do not create Sable Harbor ownership of the host.
- Red Wash: 42.22 N, 108.18 W, Sweetwater County. Taylor: accepted candidate A at 42.12 N, 108.10 W. BS&T: 33.3485 mainline + 4.0000 East Materials + 2.6515 Mineral Transfer = 40.0000 route-miles. Truck-only mine access: nine modeled miles; no mine spur.
- The industrial case supplies 12 facilities, 31 track-register segments, 26 structures and ten history events. The 1898/1954 physical alignments remain unlocated; current geometry is not backdated into those epochs. All 2025 Red Wash transport remains external-carrier. Uranium custody remains OPEN_GATED.
- Legal mapping follows SHI → SHIH → Pale Sun → Red Wash and SHIH → ARU → BS&T. Northstar Minerals, Inc. remains external.

The [accepted runtime decisions](../docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md) select Switch Reno primary and IDACORE Boise recovery. Those selections alone do not establish signed contracts or operating services. Northern Nevada is an acquired fictional planning parcel in preconstruction; proposed building drawings do not depict a completed shell.

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

[Validation report](reports/GEOSPATIAL_VALIDATION_REPORT.md), [industrial reconciliation](reports/INDUSTRIAL_RECONCILIATION.json), and [open questions](registers/OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md) describe the earlier framework’s limits. For the later delivered scope, use the [v1.5.0 receipt](../docs/releases/GEOGRAPHIC_EVIDENCE_1_5_0_RECEIPT.md). Neither edition establishes surveyed boundaries or real land and rail rights.

## Facility planning workbench

[Open the offline workbench](maps/workbench.html) for capacity scenarios, source-change impacts, architectural readiness and controlled evidence intake. [Methods and commands](facilities/workbench/README.md).

[Spatial review and architectural addendum](facilities/spatial/README.md) adds coordinated building views and official Sacramento reference layers to the existing atlas.

## Geographic evidence delivery

The [portable geographic evidence package](closeout/README.md) joins the accepted spatial layers with site-source bindings, explicit occupancy limits, the residual occurrence population and source/OCR review tables. Its native QGIS project is relocation-tested. [Versioned downloads](../docs/releases/GEOGRAPHIC_EVIDENCE_RELEASES.md) preserve the distinction between a complete package and unresolved geographic facts.
