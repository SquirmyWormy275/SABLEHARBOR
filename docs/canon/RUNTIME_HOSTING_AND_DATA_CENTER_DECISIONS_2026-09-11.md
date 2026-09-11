# Runtime Hosting and Data Center Decisions — 2026-09-11

**State:** CANON DECISION / implementation evidence remains separate

## Locked geography, provider selections, and operating model

1. **Primary transitional runtime:** **Switch TAHOE RENO — The Citadel Campus, Nevada** is the selected colocation provider/site for Sable Harbor's Reno primary transitional estate. Sable Harbor-owned compute, storage, network, and key-management equipment will operate in a dedicated controlled Switch environment. This is an owner-approved provider selection and procurement target; it does **not** assert that a contract has been executed, capacity has been reserved, equipment has been installed, or provider controls have been accepted as operating evidence.
2. **Independent recovery runtime:** **IDACORE Boise, 2653 S Victory View Way, Boise, Idaho 83709** is the selected colocation provider/site for the independent recovery estate. Recovery must preserve administrative independence from Reno, independent carrier paths, independent recovery credentials, and recovery keys that do not depend exclusively on Reno. Provider selection does **not** assert executed contract, installed equipment, completed replication, or tested recovery.
3. **Provider-independence rule:** Boise recovery is intentionally operated by a provider other than Switch. No Switch inter-campus service may become the sole recovery path. Carrier and last-mile diversity must be evidenced before recovery acceptance.
4. **Commercial diligence remains an implementation gate, not a provider-selection question.** Procurement must negotiate and document capacity, price, term, expansion rights, audit reports, complementary user-entity controls, subservice organizations, incident obligations, insurance, remote hands, access, cross-connects, exit rights, and the SLA/control requirements in this PR. A material failure to meet mandatory requirements returns the exception to the owner rather than silently substituting another provider.
5. **Owned primary end state:** SABLE HARBOR Northern Nevada Data Center, Tahoe-Reno Industrial Center planning district, Storey County, Nevada, planning pin **39.5450, -119.4550**. This is a fictional Sable Harbor facility in real geography; it is not a claim concerning a real parcel or real-world ownership.
6. **Owned-site acquisition date in the Sable Harbor planning universe:** **2026-09-04**. The acquired planning parcel is **7.5 acres** with planning consideration **$3.0 million**. No real APN is assigned.
7. **Status as of 2026-09-11:** LAND ACQUIRED / PRECONSTRUCTION. Survey/geotechnical/utility/fiber/design/permitting work is authorized and in progress. **No vertical construction, completed shell, commissioned electrical plant, occupied data hall, or operating owned data center may be depicted.**
8. **Initial Switch Reno design:** 75–100 kW usable IT capacity, contractual/physical expansion rights to at least 200–250 kW, liquid-cooling/high-density capability, dual A/B power, and two physically diverse carrier paths. Exact contracted capacity and commercial terms remain implementation evidence until executed.
9. **Initial IDACORE Boise recovery design:** recovery capacity is sized from accepted RTO/RPO and protected-service priorities rather than assumed to be a full production mirror. Current procurement must preserve at least the repository's independent-recovery planning envelope and require dual power-path design, independent connectivity, customer-controlled equipment/keys, and documented recovery expansion rights. Exact contracted kW/racks remain implementation evidence.
10. **Owned-site design:** 10,000–15,000 sq ft initial hardened shell; 250–500 kW initial modular critical plant; practical 1 MW utility/service pathway; preserve a 2 MW expansion pathway where engineering supports it. Installed capacity must not be confused with ultimate site capability.
11. **Migration trigger:** owned critical-plant commitment is gated by measured demand and committed pipeline. Planning trigger is sustained colocated demand approaching 100–150 kW plus credible three-year demand of 200–250 kW. Migration requires completed commissioning, recovery proof, security acceptance, and Finance authorization.
12. **Long-run topology:** owned Northern Nevada primary + IDACORE Boise recovery + separately protected immutable/offline copies. Switch Reno remains available for transition, burst, recovery support, and capacity shocks after primary migration subject to later economics and control acceptance.

## Provider basis recorded at selection

The provider decision is based on current public provider information plus the comparative diligence already performed. Public claims are selection inputs, not Sable Harbor operating evidence.

### Switch TAHOE RENO

At selection, Switch publicly represented The Citadel Campus as a Tahoe-Reno colocation campus with a 100% power-uptime guarantee, high-density capability, 24x7x365 security, Nevada tax advantages, and low-latency connectivity. Sable Harbor must obtain the applicable contract, technical schedule, audit reports and evidence package before relying on any such representation for control operation or audit assertion.

### IDACORE Boise

At selection, IDACORE publicly represented its Boise facility at 2653 S Victory View Way as a 34,000-sq-ft purpose-built facility with 1.4 MW facility power, dual Idaho Power feeds, N+1 UPS and cooling, seven on-net carriers, no minimum power commitment, 12-month standard terms, and SOC 2 Type II plus other stated compliance certifications. Published pricing was $300/kW/month with power included. These are procurement baselines only; Sable Harbor must verify the contract, audit period/scope, bridge coverage where applicable, exceptions, CUECs, subservice organizations and actual technical configuration before reliance.

## Capacity planning baseline

The current engineering planning cases are design capacities, not observed consumption:

| Horizon | Efficiency/edge-heavy | Base | High-growth/centralized |
|---|---:|---:|---:|
| 2027 central IT | 75 kW | 85 kW | 120 kW |
| 2031 central IT | 115 kW | 175 kW | 355 kW |
| 2036 central IT | 175 kW | 370 kW | 1.20 MW |

Foundry Field customer/OT execution is not presumed to run centrally. Atlas Meridian central demand depends on hosted client-plane adoption and agent intensity. Alexandria/Daedalus is a protected internal workload. Quarterly reforecasting must use measured GPU utilization, agent-hours/tokens, data ingest, storage growth, concurrency, and customer deployment mix.

## Truth-state rule

Maps, finance, facilities, headcount, and service registers must distinguish **selected**, **planned procurement**, **contracted**, **under construction**, **commissioning**, and **operating**. Provider selection is not a contract. A future milestone or approved budget is not operating evidence. Synthetic deeds, planning pins, cost models, and schedules are planning/canon artifacts and must not be represented as real-world property records, vendor contracts, utility commitments, or completed construction.
