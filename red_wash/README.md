# Red Wash transaction and operating evidence

**Record:** `SH-PS-RW-TOR-001` · **Version:** 1.1.0
**Case cutoff:** September 5, 2026 · **Synthetic calibration:** through August 31, 2026
**Classification:** `PUBLIC_SYNTHETIC_DIEGETIC`

Red Wash Mining, LLC is the Wyoming mine operator, wholly owned by Pale Sun Inc.
The controlling industrial structure, acquisitions, integrated financing and Taylor
service case are in the [industrial package](../industrial/README.md). This directory
supplies its detailed mine, diligence, operating and commercial evidence.

The preserved standalone 2026 numerical baseline remains reproducible here. The
industrial successor separately identifies additional interface costs, capital,
financing and the acquisition-to-opening ARO rollforward. The two model versions
must not be presented as the same projection. Neither contains observed or audited
company results: January–August is synthetic calibration and September–December is
management forecast available at the publication cutoff.

## Current records

| Record | Source |
|---|---|
| Selected transaction and standalone baseline | [Canon 1.1](../docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md) |
| Reconciled decisions | [Decision addendum 1.1](../docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md) |
| Full mine evidence narrative | [Casebook](RED_WASH_CASEBOOK.md) |
| Operating archaeology and diligence | [Operating record](TRANSACTION_OPERATING_RECORD.md) |
| Commercial instruments | [Transaction and contracts](agreements/TRANSACTION_AND_COMMERCIAL_INSTRUMENTS.md) |
| Permits and closure | [Regulatory record](regulatory/REGULATORY_PERMIT_AND_ENVIRONMENTAL_FILE.md) |
| Taylor relationship | [Interface record](logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md) |
| Controlled mine inputs | [Core source](source/core_operating_data.json) |
| Controlled interface inputs | [Bridge source](source/aru_bst_bridge.json) |
| External references | [Source register](source/external_source_register.csv) |
| Historical source bytes | [Version 1.0 preservation manifest](history/v1.0.0/manifest.json) |

## Geographic and visual control

The selected fictional mine is in Sweetwater County's Great Divide Basin, north of
Wamsutter, at 42.2200 N, 108.1800 W. Approximately 6,885 feet is a DEM screening
value, not a survey. Current synthetic drill collars use NAD83 / UTM zone 12N
(EPSG:26912). Resource, mine and facility geometry remain synthetic engineering data.

[Current site schematic](../industrial/visuals/red_wash_site.svg) ·
[Current underground schematic](../industrial/visuals/red_wash_underground.svg)

The approved [Pale Sun logo](../assets/brand/logos/pale_sun__canonical.png) and
[Red Wash logo](../assets/brand/logos/red_wash__canonical.png) remain byte-identical.
The old Carbon County map PNGs retain their original bytes as superseded historical
illustrations. Their approval manifest preserves provenance; their old location,
elevation, operator and rail-loadout labels do not describe the current case.

## Build and validation

```bash
python red_wash/tools/validate_red_wash_record.py --generate
python -m unittest discover -s red_wash/tests -q
```

The builder emits 27 typed CSV datasets, a constrained SQLite database and source
hash manifests into ignored `generated/` and `dist/` directories. Independent
validation recomputes production, inventory, statements, capital and source bindings.
The industrial builder assembles a versioned participant corpus from explicitly
selected evidence. Source lineage remains distinct from participant availability.

## Custody and chronology

Qualified external carriers handled every 2025 Red Wash movement. Operating analysis
surfaced ARU in Q4 2025; its acquisition closed January 7, 2026. Selected Taylor
ordinary industrial-input service starts July 7, 2026. That service does not confer
uranium custody. Qualified external carriers remain available permanently; there is
no minimum-volume promise or mine rail spur. Nonpublic evaluation material remains
in the separate private control repository and is excluded from these public sources.
