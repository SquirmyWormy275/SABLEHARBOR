# Runtime Infrastructure Geospatial Addendum — 2026-09-11

This addendum supplies map-safe geography and temporal status for the runtime program. It does not assert real-world property ownership or executed colocation contracts.

## GEO-RUNTIME-001 — Reno primary colocation

- Canon geography: Reno/Tahoe-Reno, Nevada.
- Object type: `COLOCATION_PRIMARY_PLANNED` until contract execution; after execution `COLOCATION_PRIMARY_CONTRACTED`; only after service acceptance `COLOCATION_PRIMARY_OPERATING`.
- Exact provider/facility pin: intentionally not canon until supplier contract is executed. Lead diligence candidate is Switch Tahoe-Reno.
- 2026-09-11 map state: `PLANNED_PROCUREMENT`.

## GEO-RUNTIME-002 — Boise independent recovery

- Canon geography: Boise, Idaho.
- Object type: `COLOCATION_RECOVERY_PLANNED` until contract execution; only after recovery acceptance `COLOCATION_RECOVERY_OPERATING`.
- Exact provider/facility pin: intentionally not canon until supplier contract is executed. Lead diligence candidate is IDACORE Boise.
- 2026-09-11 map state: `PLANNED_PROCUREMENT`.

## GEO-RUNTIME-003 — SABLE HARBOR Northern Nevada Data Center

- Canon name: SABLE HARBOR Northern Nevada Data Center.
- Object type: `OWNED_DATA_CENTER`.
- Entity: Sable Harbor Industries, Inc. (`SH-ENT-001`).
- Place: Tahoe-Reno Industrial Center / USA Parkway industrial district, Storey County, Nevada.
- Planning coordinate: **39.5450, -119.4550**.
- Geometry precision: `PLANNING_PIN_WITH_SYNTHETIC_ENVELOPE`.
- Planning parcel: 7.5 acres.
- Fictionality: `FICTIONAL_IN_REAL_GEOGRAPHY`.
- Planning-universe purchase date: **2026-09-04**.
- 2026-09-11 construction state: `LAND_ACQUIRED_PRECONSTRUCTION`.
- Vertical construction percent: **0**.
- Commissioned owned IT capacity: **0 kW**.
- Commissioned owned critical plant: **0 kW**.
- Planned initial shell: 10,000–15,000 sq ft.
- Planned initial critical plant: 250–500 kW.
- Planned site pathway: 1 MW; preserve 2 MW expansion path if feasible.

### Synthetic envelope rule

Any polygon shown around the planning pin is a nonsurveyed planning envelope derived from 7.5 acres. It must not coincide intentionally with a real cadastral boundary and must not be assigned a real APN. The mock deed is a fictional planning instrument.

## Temporal rendering

- 2026-09-04 through preconstruction: show acquired parcel/planning envelope only.
- Site work start through shell completion: show construction symbology and actual accepted construction footprint only.
- Shell completion: label `SHELL_COMPLETE`; do not label operating.
- Commissioning: label `COMMISSIONING`.
- Production acceptance: only then label `OPERATING_DATA_CENTER`.

Future dates in the master plan are schedule targets, not historical facts. Geo exports must use the latest status event whose effective date is on or before the map's as-of date.
