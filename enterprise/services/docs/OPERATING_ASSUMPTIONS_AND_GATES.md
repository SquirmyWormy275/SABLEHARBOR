# Operating assumptions and acceptance gates

**State:** Numerical design proposals and implementation requirements; not vendor selections, SLAs, occupied capacity or operating evidence.

## Proposed workload envelope

| Class | Initial comparison envelope | Proposed recovery objective | Boundary |
|---|---|---|---|
| Primary production | 512 vCPU; 2,048 GiB RAM; 50 TiB usable durable storage | Restore prioritized service within 4 hours; at most 15 minutes of data loss | Product owners must accept degraded service and transaction reconciliation. |
| Restricted / Alexandria | 128 vCPU; 1,024 GiB RAM; 100 TiB storage; eight 80-GiB planning-class GPU units | 8 hours / 1 hour | Same source, disclosure and administration boundaries at recovery; no default public-cloud dependency. |
| Development / evaluation | 128 vCPU; 512 GiB RAM; 20 TiB storage; four GPU units | 24 hours / 24 hours for rebuildable environments | Source and non-rebuildable release evidence use the separate proposed 8-hour / 1-hour overlay. |
| Industrial / site | Aggregate 80 vCPU; 320 GiB RAM; 20 TiB storage | 8 hours / 1 hour for ordinary business compute | This is not a safety-system downtime allowance, a per-site inventory or permission to depend on WAN for safe operation. |
| Corporate / teaching | Aggregate local 16 vCPU; 64 GiB RAM; 5 TiB storage, plus bought enterprise services | 24 hours / 24 hours for ordinary local services | Teaching/instruction remains internal. Provider export and service-continuity capabilities must be verified separately. |
| Independent recovery | Derived from 40% primary and 50% restricted CPU/RAM/GPU demand; 100% of their durable storage | Inherits protected-service objectives | Does not add another full production estate. Backups are separately counted. |

These are starting envelopes for sensitivity analysis, not extrapolations presented as measured demand. vCPU/GPU labels are not demonstrated cross-platform throughput equivalence. Benchmark representative Foundry/Atlas requests, database transactions, J2 ingestion/retrieval and model workloads before ordering equipment.

The proposed key-service overlay is one-hour restoration with no loss of an acknowledged key change. That requires a tested key-change and isolated recovery-copy protocol; ordinary backup frequency alone does not satisfy it. Root recovery must not depend exclusively on the primary identity, DNS, KMS or artifact services it is meant to restore.

## Capacity calculations and missing proof

The CPU calculation reserves one spare node per modeled administrative domain and caps normal utilization at 70%. Sizing takes the larger of CPU and memory demand. Storage uses usable-capacity units, not raw disk capacity. Those calculations **do not prove** storage fault tolerance, database failover, GPU spare capacity, power-path redundancy, packet throughput, carrier-route independence or restore throughput.

Primary and recovery rack/power requirements are derived separately. Restricted infrastructure is an independently controlled domain; sharing a physical facility with other infrastructure does not merge access or authority. Dedicated racks/cage/suite selection remains open. The owned-facility comparator buys sufficient declared 100-kW capacity blocks but does not establish engineering feasibility, permitting, utility delivery or construction schedule.

The industrial/local pool is deliberately an aggregate comparison envelope. Per-site CPU/network inventories, field equipment, spares, local qualification and safety dependencies must be reconciled with each existing site. No new OT process, uranium custody, host-treatment authority or mine/rail qualification follows from an IT register.

## Staffing calculation

Monthly workload hours and role costs are explicit hypothetical inputs. Productive capacity is 40 hours × 52 weeks × 75%, accounting for leave, training and non-delivery time. A continuous staffed seat therefore requires 5.6 FTE before rounding; an on-call rota is not a continuously occupied seat.

The comparison scales variable engineering effort with demand while retaining a fixed governance/service floor. This is a sensitivity assumption, not an empirically verified staffing law. Role pools remain distinct; rounded dedicated positions can exceed the ceiling of pooled fractional FTE. Reuse of existing staff must identify real people/roles, qualifications, remaining capacity and pay attribution. Existing aggregate ESS occupancy is not a free reserve, and dedicated Atlas/J2 roles are not reassigned by this model.

Physical security for Sable Harbor sites remains internally operated. A colocation provider's building services are separately scoped infrastructure inputs, not evidence that Sable Harbor has outsourced all physical security. The owned-building comparator additionally includes its proposed physical-coverage and facilities-engineering burden.

## Financial bridge and comparability

All alternatives include the same enterprise tools and retained technical capabilities. The five-year totals include declared labor, cloud, hardware, backup, support, facilities, selected enterprise-tool costs, transition, refresh and exit. General Finance/Legal/People staffing, industrial operations, insurance premiums, general external counsel/audit/tax fees, site circuits, actual commercial data contracts and other listed exclusions are not silently zero-cost; they are outside this technology-scope comparison.

The 606 full-service and 271 frontline license assumptions combine the conditional Core workforce with an explicit hold-flat industrial scenario. They are not an observed device/user inventory. A license bundle must replace duplicate component charges through an explicit credit, not through an unrecorded discount.

The bridge preserves three separate questions: gross requirement, supported displacement of an old allowance, and genuinely incremental funding. No final net business forecast is calculated while reuse/overlap authority is missing. The original forecast and immutable releases are not modified to make a proposal appear previously funded.

## Bounded execution sequence

| Gate | Accountable existing function | Required output before the next commitment |
|---|---|---|
| Workload/BIA acceptance | Product owners, J2 domain owners, site operators and Technology | Benchmarked envelope, critical service order, tolerable interruption/data loss and qualified coverage. |
| Staffing/financial attribution | Technology, Finance, People & Culture and affected businesses | Skill-pool assignments; verified reusable capacity; conditional incremental positions; unit/period expense bridge. |
| Provider/site comparison | Technology / Facilities / Procurement, with Security and Legal review | Quotes with operating-layer scope, power/carrier dependencies, rights, failure domains and exit; no supplier name becomes selected merely by appearing in a comparison. |
| Pilot and recovery proof | Platform/Security and receiving service owners | Isolated administration, recoverable keys, timed restoration, data integrity, failback and provider-exit test. |
| First production migration | Product and platform owners | Approved release, rollback, service acceptance and actual cost/capacity evidence. |
| Ownership expansion | Existing capital authority and Finance | Utilization and five-year cost case; no automatic owned-building commitment. |

The illustrative month 1–6 / 7–18 / 19–60 transition is a model schedule only. It does not override these gates or make cloud-heavy operation a permanent recommendation.

## Only material owner choices remain

Accept or adjust the proposed recovery/service-priority targets; approve a funding envelope after genuine payroll/allowance overlap is resolved; choose restricted physical-isolation and recovery capacity requirements; and approve actual provider/site offers after diligence. The established sourcing decisions, J2 Education, internal analytics, key custody and progressive ownership direction are not reopened.
