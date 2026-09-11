# Runtime Infrastructure Geospatial Addendum — 2026-09-11

**State:** owner-approved runtime selections pending PR #119 acceptance and generated-output reconciliation.

This addendum supplies map-safe geography and temporal status for the runtime program. It does not assert real-world property ownership, executed colocation contracts, or operating services. The controlling selection record is `docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md`.

## GEO-RUNTIME-001 — Reno primary colocation

- Selected geography: Reno/Tahoe-Reno, Nevada.
- Selected provider/site: **Switch TAHOE RENO — The Citadel Campus**. This is no longer a candidate-selection question.
- Runtime identifier: `RUNTIME-RENO-COLO`.
- Facility object type: `COLOCATION_PRIMARY`; relationship/service state is stored separately.
- 2026-09-11 relationship state: `PROVIDER_SELECTED_PROCUREMENT_PENDING`.
- Contract executed: **false**. Capacity reserved: **false**. Sable Harbor service operating: **false**.
- Publicly sourced provider-campus geometry may be represented as a real external reference. Its existence/location does not depend on Sable Harbor executing a contract.
- Exact building allocation, customer cage, rack positions and contracted capacity remain separate implementation records. A campus pin must not imply these have been assigned.
- Coordinates require an identified source and precision classification; until verified, preserve the selected campus/geographic constraint rather than inventing a precise operational footprint.

## GEO-RUNTIME-002 — Boise independent recovery

- Selected geography: Boise, Idaho.
- Selected provider/site: **IDACORE Boise, 2653 S Victory View Way, Boise, Idaho 83709**. This is no longer a candidate-selection question.
- Runtime identifier: `RUNTIME-BOISE-DR`.
- Facility object type: `COLOCATION_RECOVERY`; relationship/service state is stored separately.
- 2026-09-11 relationship state: `PROVIDER_SELECTED_PROCUREMENT_PENDING`.
- Contract executed: **false**. Capacity reserved: **false**. Sable Harbor recovery operating: **false**.
- Source-supported provider-location geometry and the proposed Sable Harbor tenancy are distinct records. Neither geocoding the address nor selecting the provider establishes a lease, capacity reservation or recovery test.
- Provider independence is a selected architectural requirement. Carrier, administration, key-recovery and shared-infrastructure independence must be verified; do not infer all of them from different provider names.

## GEO-RUNTIME-003 — SABLE HARBOR Northern Nevada Data Center

- Name: SABLE HARBOR Northern Nevada Data Center.
- Runtime identifier: `RUNTIME-NN-OWNED-DC`.
- Object type: `OWNED_DATA_CENTER` with a separately recorded construction/service state.
- Entity: **Sable Harbor, LLC** (finance/entity key `SHI`; geospatial parent reference `SH-ENT-001`). Parent identity follows `industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md` and `industrial/source/entities.json`; no new corporation is created.
- Place: Tahoe-Reno Industrial Center / USA Parkway industrial district, Storey County, Nevada.
- Planning coordinate: **39.5450, -119.4550** (latitude, longitude). GeoJSON coordinates are **[-119.4550, 39.5450]** (longitude, latitude).
- Geometry precision: `PLANNING_PIN_WITH_SYNTHETIC_ENVELOPE`.
- Planning parcel: 7.5 acres.
- Fictionality: `FICTIONAL_IN_REAL_GEOGRAPHY`.
- Planning-universe purchase effective date: **2026-09-04**. Record preparation/approval provenance: **2026-09-11**; do not imply the new record was available earlier.
- 2026-09-11 construction state: `LAND_ACQUIRED_PRECONSTRUCTION`.
- Vertical construction percent: **0**. Completed shell: **false**.
- Commissioned owned IT capacity: **0 kW**.
- Commissioned owned critical plant: **0 kW**.
- Planned initial shell: 10,000–15,000 sq ft.
- Planned initial critical plant: 250–500 kW.
- Planned site pathway: 1 MW; preserve 2 MW expansion path if feasible.

### Synthetic envelope rule

Any polygon shown around the planning pin is a nonsurveyed planning envelope derived from 7.5 acres. Record the construction method, coordinate system, area calculation, and precision. It must not intentionally appropriate a real cadastral boundary and must not be assigned a real APN. The mock deed is a fictional planning instrument. A precise coordinate format does not confer survey accuracy.

## Temporal rendering

- Before 2026-09-04: do not show acquired Sable Harbor land in the reconstructed world-state view.
- 2026-09-04 through preconstruction: show the acquired planning envelope, explicitly classified as synthetic; show proposed buildings only on a separately labeled design layer.
- Site work start through shell completion: show construction symbology only when an accepted construction-status event supports it.
- Shell completion: label `SHELL_COMPLETE`; do not label operating.
- Commissioning: label `COMMISSIONING` only after an accepted commencement event.
- Production acceptance: only then label `OPERATING_DATA_CENTER` with the accepted commissioned capacity.

Future dates in the master plan are schedule targets, not historical facts. An as-of filter alone is insufficient: current-state exports must select only accepted historical/status events, not forecast milestones whose target date has passed. Preserve effective date, recorded/available date, evidence classification, acceptance state and scenario separately. Historical-knowledge views must also respect the recorded/available cutoff. Future-design and forecast layers must remain visibly distinct from accepted current-state layers.

## Integration acceptance

This source correction does not claim that the GeoPackage, QGIS project, site registers, maps or institutional catalog have been regenerated. Complete the source-to-generator integration and temporal regression tests within PR #119 before claiming those outputs are reconciled. Preserve existing `SH-SITE-*` identities and use explicit mappings/placement history for the three runtime identifiers rather than silently renaming or duplicating Alexandria's existing hosting record.
