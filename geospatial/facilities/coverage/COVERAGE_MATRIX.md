# Facility coverage matrix

Coverage records are not distinct site counts. Aliases map repeated census appearances to the same record. Concept design does not establish occupied floors, tenure or dates.

Source: current main 786fc9a5311a04dde92ee6dbb08ac3b77a380200. Build command: `python geospatial/facilities/coverage/build_coverage.py`.

The 175 geographic catalog objects remain authoritative geographic IDs. `ORG:`, `SERVICE:` and `GEOMETRY:` keys are census-disposition keys, not newly allocated site IDs. All newly designed building IDs must be allocated by the facility program.
# Counts

{"catalog_objects": 175, "census_appearances": 889, "classes": {"1": 2, "2": 15, "3": 6, "4": 62, "5": 17, "6": 437, "7": 5, "8": 42}, "coverage_records": 586}

# Required design queue

| ID | Name | Required output | Boundary |
|---|---|---|---|
| SH-SITE-0001 | Sacramento headquarters campus | context, site, program | Integrated campus concept required; study envelope is not a property claim. |
| SH-SITE-0002 | Klein historical Pittsburgh-area shop | context, disposition | Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry. |
| SH-SITE-0003 | The Fort — Willow industrial compound | context, site, program | Integrated campus concept required; study envelope is not a property claim. |
| SH-SITE-0004 | Emberline Charleston program geography | context, disposition | Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry. |
| SH-SITE-0005 | Bedford — Cradle recovery-development center | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0006 | Red Wash Mine | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0007 | Taylor — BS&T industrial town and operating hub | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0008 | Wamsutter fictional interchange | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0009 | Blackridge Mine | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0010 | Forty-Seven Names customer operation | context, disposition | Host/customer retains property and operating authority; only permitted context and bounded intervention are represented. |
| SH-SITE-0011 | Reno provisional office | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0012 | Elko provisional field office | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0013 | Tucson provisional engineering office | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0014 | J2 Education residential campus and conference center | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0015 | J2 headquarters physical accommodation | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0016 | Alexandria physical hosting | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0017 | Foundry/Foundry Field dedicated footprint | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0018 | Atlas Meridian dedicated footprint | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0019 | Advisory project hubs/offices | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0020 | ARU terminal, warehouse and trucking estate | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-SITE-0021 | ARU external customer delivery interfaces | context, disposition | Host/customer retains property and operating authority; only permitted context and bounded intervention are represented. |
| SH-SITE-0022 | Wallaby residue/tailings opportunity | context, disposition | Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry. |
| SH-SITE-0023 | Kelly Gang Mining / Stream 17 host operation | context, disposition | Host/customer retains property and operating authority; only permitted context and bounded intervention are represented. |
| SH-SITE-0024 | Glasshouse underground trial site | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0025 | Licensed conversion-facility delivery point | context, disposition | Host/customer retains property and operating authority; only permitted context and bounded intervention are represented. |
| SH-SITE-0026 | Former headquarters / early offices | context, disposition | Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry. |
| SH-RAIL-0003 | BS&T historical/abandoned branches | context, disposition | Historical/former/killed asset; retain history without asserting present occupancy or inventing historic geometry. |
| SH-FAC-RW-001 | Red Wash Mine Portal (Decline) | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-002 | Red Wash Surface Operations | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-003 | Red Wash Ventilation Raise (Exhaust) | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-004 | Red Wash Fresh Air Intake | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-005 | Red Wash Processing Plant | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-006 | Red Wash Loadout (Rail/Truck) | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-007 | Red Wash Tailings Management Facility | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-008 | Red Wash Administration / Dry | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-009 | Red Wash Power Substation | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-010 | Red Wash Maintenance | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-011 | Red Wash Mine Rescue / Emergency | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-012 | Red Wash Fuel & Explosives Storage | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-013 | Red Wash Water Management | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-L1 | Red Wash underground level 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-L2 | Red Wash underground level 2 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-L3 | Red Wash underground level 3 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-L4 | Red Wash underground level 4 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-FAC-RW-L5 | Red Wash underground level 5 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-FACILITY-001 | Facility 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-FACILITY-002 | Facility 2 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-WAREHOUSE-001 | Warehouse 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-PIT-001 | Pit 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-BENCH-001 | Bench 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-STOCKPILE-001 | Stockpile 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-BUILDING-001 | Building 1 | context, disposition | Illustration/source-derived detail has no accepted engineering layout; preserve labeled detail placeholder, not installed plant or surveyed underground floor geometry. |
| SH-BR-AREA-001 | West Wall Phase 4 | context, disposition | Location, dedicated footprint or implementation remains proposed/unresolved; labeled planning disposition preserves the record without claiming occupancy. |
| SH-SITE-0027 | Demotte AMD host treatment and Gen 1 recovery deployment | context, disposition | Host/customer retains property and operating authority; only permitted context and bounded intervention are represented. |
| SH-FAC-FORT-BIG | The Big Shed | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-FAC-FORT-SMALL | The Small Shed | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-FAC-FORT-WHITE | The White Shed | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-IND-FAC-WAM-INT | Wamsutter interchange | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-TAY-YARD | Taylor Yard and Shops | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-TAY-TERMINAL | Taylor Industrial Transload Complex | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-TAY-WAREHOUSE | Taylor warehouse | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-IND-FAC-TAY-TRUCK | Taylor trucking depot | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-EAST-MATERIALS | East Materials team track | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-MINERAL-TEAM | Mineral Transfer team track | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-RAW-TERMINAL | Rawlins satellite terminal | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-RAW-WAREHOUSE | Rawlins warehouse | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-IND-FAC-RAW-TRUCK | Rawlins trucking satellite | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| SH-IND-FAC-ARU-OFFICE | Taylor ARU office | context, site, building_program, floor_plans | Established building function; prepare intentionally modelled concept floor plan. Actual floor count, measured area and occupancy remain unknown. |
| SH-IND-FAC-RW-RECEIVING | Red Wash receiving and reagent storage | context, site, program | Operating site/envelope requires context and site program; buildings must be separately modelled where program supports them. |
| ORG:kgm | Kelly Gang Mining | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:demotte | Demotte Reclamation Services | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:harrison-vale | Harrison Vale Partners | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:wolf-ridge | Wolf Ridge Holdings | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:cedar | Cedar Junction Conversion Services, LLC | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:juniper | Juniper Mesa | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:mesa-lantern | Mesa Lantern Minerals, LLC | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:salt-rim | Salt Rim Recovery Venture | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:NMI | Northstar Minerals, Inc. | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:qfc | Quality Forest Communications | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:argent-ridge | Argent Ridge Mining | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:balloon | Gid Voss’s balloon business | context, disposition | External organization or personal business; no enterprise-controlled building authorized. Context-only organization record does not assert a physical address. |
| ORG:FORT-TEST-RIG | FORT-TEST-RIG | context, disposition | Forecast equipment asset is not evidence of September 2026 installation; no occupied architectural floor is established. |
| ORG:FORT-ANALYTICAL | FORT-ANALYTICAL | context, disposition | Forecast equipment asset is not evidence of September 2026 installation; no occupied architectural floor is established. |
| ORG:BEDFORD-MODULE | BEDFORD-MODULE | context, disposition | Forecast equipment asset is not evidence of September 2026 installation; no occupied architectural floor is established. |
| SERVICE:FAC-PRIMARY | Primary colocation requirement | context, disposition | Facility requirement only; provider/address/readiness unresolved. PR #119 remains pending and is not imported. |
| SERVICE:FAC-RECOVERY | Independent recovery facility requirement | context, disposition | Facility requirement only; provider/address/readiness unresolved. PR #119 remains pending and is not imported. |
| SERVICE:FAC-OWNED | Future owned-facility alternative | context, disposition | Facility requirement only; provider/address/readiness unresolved. PR #119 remains pending and is not imported. |

# Complete census

Machine-readable appearances, source hashes, aliases, statuses, tenure and unknown temporal/occupancy fields are in [COVERAGE_MATRIX.json](COVERAGE_MATRIX.json). A class 8 disposition is a placeholder requirement, not permission to drop its atlas record. Class 3 requires concept floors even when measured floor counts remain unknown. Class 4 exempts outdoor, rail and civil assets from architectural floors; the existing network and structure representations remain authoritative.

Foundry, Atlas Meridian and Advisory lack dedicated accepted physical footprints (SH-SITE-0017–0019). Their organizational cards are class 6 and their physical-footprint question remains class 8; this avoids multiplying business functions into sites. J2 Education (SH-SITE-0014) remains a separate unresolved residential-campus record even where the Sacramento model includes day education. Alexandria and provider requirements remain unlocated pending accepted implementation. Wallaby is historical/killed under the September 6 Cradle closeout despite the earlier catalog OPEN label. Bedford is Fairmont, not the superseded Belle study area.
