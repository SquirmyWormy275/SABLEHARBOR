# Runtime Reconciliation Index — 2026-09-11

**Document ID:** SH-RT-INDEX-001
**Version:** 1.0.0
**Prepared:** 2026-09-11
**Owner:** Enterprise Technology Services with Legal, Finance, Procurement and Facilities
**Authority:** Owner-authorized PR119 runtime mandate, pending repository acceptance
**Structured companion:** `enterprise/services/source/runtime_sites_2026-09-11.json`; `runtime_capital_plan_2026-09-11.json`

This index reconciles older hosting/planning text against the September 11 runtime decisions. Later entries control where an older file merely preserves an open question that is now closed.

## Closed/superseded open items

The following items in `THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md` section 9 are no longer wholly open:

- **Exact colocation regions:** CLOSED — Reno/Tahoe-Reno primary; Boise recovery.
- **Alexandria final physical hosting geography:** CLOSED for transition/end-state geography — Reno primary transition; Northern Nevada owned primary end state; Boise recovery.
- **Threshold for owned physical plant:** CLOSED as planning gate — sustained colo demand ~100–150 kW plus credible three-year demand ~200–250 kW; final capital authorization still requires measured evidence.
- **Primary production planning envelope:** REPLACED for facility planning by the 2027/2031/2036 scenario model in `RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md`; workload benchmarking remains an implementation gate.

The following remain open by design:

- executed provider contracts and exact provider facility pins;
- negotiated rack/kW/cross-connect/carrier pricing;
- exact carrier routes;
- final equipment SKUs;
- measured workload demand;
- final RTO/RPO acceptance where still proposed;
- incremental headcount after actual capacity reuse is measured;
- construction quotes, utility will-serve, permits, and commissioning evidence.

## Finance reconciliation

`docs/finance/RUNTIME_INFRASTRUCTURE_FINANCE_RECONCILIATION_2026-09-11.md` controls the treatment of the $3.0M planning land event, $15.5M Phase-I planning envelope, colo/recovery OPEX separation, construction-in-progress truth state, and headcount non-double-counting.

## Facilities/layout reconciliation

`docs/facilities/NORTHERN_NEVADA_DATA_CENTER_MASTER_PLAN_2026-09-11.md` and `...LAYOUT_PROGRAM...` control the owned-site phase/status. As of 2026-09-11 the site is acquired/preconstruction; all building/layout content is proposed.

## Geospatial reconciliation

`geospatial/sources/RUNTIME_INFRASTRUCTURE_GEO_ADDENDUM_2026-09-11.md` controls runtime map truth state. `geospatial/scripts/sync_runtime.py` now consumes the structured runtime sites into the catalog, parcel GeoJSON and relationships. GeoPackage, registers, QGIS project and maps have been regenerated in the implementation branch; exact provider coordinates remain unverified.

## CCF reconciliation

`docs/controls/RUNTIME_CONTROL_AND_EVIDENCE_MATRIX_2026-09-11.md` and the colocation SLA/security package define design requirements only. They do not assert provider controls, Sable Harbor controls, construction, recovery, or SOC readiness are operating effectively.

## Executable successor and publication navigation

The [runtime implementation](../../enterprise/runtime/README.md) consumes the original
structured pair. Its [calculated register](../../enterprise/runtime/docs/MODEL_RESULTS.md)
controls source-derived quantities, including workload and maximum-power sensitivities.
The older scenario workbooks retain historical assumptions and do not establish
benchmarked demand or the current investment case. The initial owned engineering
module is 250 kW; a second module raises the selected design to 500 kW conditionally.
Higher historical envelopes require a new engineering and funding decision.

The [runtime release record](../releases/RUNTIME_ESTATE_RELEASES.md) identifies the
separately versioned successor, original-to-successor statement bridge and durable
package convention. Earlier business/operations release views remain historical
versions, with their original source locks and financial scope intact.
