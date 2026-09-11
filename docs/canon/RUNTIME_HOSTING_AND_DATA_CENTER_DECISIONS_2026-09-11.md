# Runtime Hosting and Data Center Decisions — 2026-09-11

**State:** CANON DECISION / implementation evidence remains separate

## Locked geography and operating model

1. **Primary transitional runtime geography:** Reno/Tahoe-Reno, Nevada. Sable Harbor-owned compute, storage, network, and key-management equipment operates in a dedicated controlled colocation environment. Provider contract remains a procurement selection until executed; Switch Tahoe-Reno is the lead diligence candidate, not canon merely by being named.
2. **Independent recovery geography:** Boise, Idaho. Recovery must use an administratively and operationally independent facility/provider, independent carrier paths, independent recovery credentials, and recovery keys that do not depend exclusively on Reno. IDACORE is the lead diligence candidate, not an executed supplier.
3. **Owned primary end state:** SABLE HARBOR Northern Nevada Data Center, Tahoe-Reno Industrial Center planning district, Storey County, Nevada, planning pin **39.5450, -119.4550**. This is a fictional Sable Harbor facility in real geography; it is not a claim concerning a real parcel or real-world ownership.
4. **Owned-site acquisition date in the Sable Harbor planning universe:** **2026-09-04**. The acquired planning parcel is **7.5 acres** with planning consideration **$3.0 million**. No real APN is assigned.
5. **Status as of 2026-09-11:** LAND ACQUIRED / PRECONSTRUCTION. Survey/geotechnical/utility/fiber/design/permitting work is authorized and in progress. **No vertical construction, completed shell, commissioned electrical plant, occupied data hall, or operating owned data center may be depicted.**
6. **Initial colocation design:** 75–100 kW usable IT capacity, expansion rights to at least 200–250 kW, liquid-cooling/high-density capable, dual A/B power, two physically diverse carrier paths.
7. **Owned-site design:** 10,000–15,000 sq ft initial hardened shell; 250–500 kW initial modular critical plant; practical 1 MW utility/service pathway; preserve a 2 MW expansion pathway where engineering supports it. Installed capacity must not be confused with ultimate site capability.
8. **Migration trigger:** owned critical-plant commitment is gated by measured demand and committed pipeline. Planning trigger is sustained colocated demand approaching 100–150 kW plus credible three-year demand of 200–250 kW. Migration requires completed commissioning, recovery proof, security acceptance, and Finance authorization.
9. **Long-run topology:** owned Northern Nevada primary + independent Boise recovery + separately protected immutable/offline copies. Colocation remains available for recovery, burst, transition, and capacity shocks after primary migration.

## Capacity planning baseline

The current engineering planning cases are design capacities, not observed consumption:

| Horizon | Efficiency/edge-heavy | Base | High-growth/centralized |
|---|---:|---:|---:|
| 2027 central IT | 75 kW | 85 kW | 120 kW |
| 2031 central IT | 115 kW | 175 kW | 355 kW |
| 2036 central IT | 175 kW | 370 kW | 1.20 MW |

Foundry Field customer/OT execution is not presumed to run centrally. Atlas Meridian central demand depends on hosted client-plane adoption and agent intensity. Alexandria/Daedalus is a protected internal workload. Quarterly reforecasting must use measured GPU utilization, agent-hours/tokens, data ingest, storage growth, concurrency, and customer deployment mix.

## Truth-state rule

Maps, finance, facilities, headcount, and service registers must distinguish **planned**, **contracted**, **under construction**, **commissioning**, and **operating**. A future milestone or approved budget is not operating evidence. Synthetic deeds, planning pins, cost models, and schedules are planning/canon artifacts and must not be represented as real-world property records, vendor contracts, utility commitments, or completed construction.
