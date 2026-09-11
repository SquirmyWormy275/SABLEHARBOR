# Runtime estate calculated design register

**Document ID:** SH-RT-RESULTS-001
**Version:** 1.0.0
**State:** GENERATED SYNTHETIC DESIGN; no operating acceptance
**Owner:** Enterprise Technology Services / Finance
**Prepared:** 2026-09-11
**Authority:** September 11 runtime decisions; generated output does not create canon
**Structured companion:** enterprise/services/source/runtime_sites_2026-09-11.json; enterprise/services/source/runtime_capital_plan_2026-09-11.json

Source content SHA-256: `6f359aa710dd0ece6c253cea1c3312f81831b0be63782a6315269478e69c4771`. Regenerate with `python -m enterprise.runtime.report`. Do not edit calculated values in this derivative.

## Current design boundary

Selected providers remain uncontracted, unreserved and uninstalled. The synthetic owned parcel is acquired/preconstruction, with 0% vertical construction and 0 kW commissioned. September 2026 actual service-operation history is not established.

| Site | Planned facility / geography | State |
|---|---|---|
| Reno primary colocation | Tahoe-Reno, Nevada | PROVIDER_SELECTED_PROCUREMENT_PENDING |
| Boise independent recovery colocation | Boise, Idaho | PROVIDER_SELECTED_PROCUREMENT_PENDING |
| SABLE HARBOR Northern Nevada Data Center | Tahoe-Reno Industrial Center / USA Parkway industrial district, Storey County, Nevada | LAND_ACQUIRED_PRECONSTRUCTION |

## Causal configuration classes

All quantities are unmeasured planning assumptions. Accelerator throughput, power limits and thermal configuration need qualified acceptance. Each rack observes space, peak power, weight and separation constraints; A/B feeds are not additive load.

| Case / year | Site | CPU / GPU systems | Shelves / racks | Peak / typical kW | Durable TiB |
|---|---|---|---|---|---|
| base / 2027 | RENO | 3 / 11 | 5 / 11 | 96.4 / 60.05 | 150.0 |
| base / 2027 | BOISE | 2 / 2 | 5 / 3 | 23.6 / 14.6 | 150.0 |
| base / 2031 | RENO | 4 / 15 | 9 / 15 | 132.4 / 82.5 | 311.04 |
| base / 2031 | BOISE | 2 / 3 | 9 / 4 | 34.8 / 21.6 | 311.04 |
| base / 2036 | RENO | 5 / 22 | 21 / 22 | 198.8 / 123.95 | 773.97 |
| base / 2036 | BOISE | 3 / 4 | 21 / 7 | 53.2 / 33.05 | 773.97 |
| slower_adoption / 2027 | RENO | 3 / 7 | 5 / 7 | 64.4 / 40.05 | 90.0 |
| slower_adoption / 2027 | BOISE | 2 / 2 | 5 / 3 | 23.6 / 14.6 | 90.0 |
| slower_adoption / 2031 | RENO | 3 / 7 | 7 / 7 | 66.0 / 41.05 | 186.62 |
| slower_adoption / 2031 | BOISE | 2 / 2 | 7 / 4 | 25.2 / 15.6 | 186.62 |
| slower_adoption / 2036 | RENO | 3 / 6 | 13 / 6 | 62.8 / 39.05 | 464.38 |
| slower_adoption / 2036 | BOISE | 2 / 2 | 13 / 4 | 30.0 / 18.6 | 464.38 |
| high_demand / 2027 | RENO | 3 / 15 | 7 / 15 | 130.0 / 81.05 | 225.0 |
| high_demand / 2027 | BOISE | 2 / 3 | 7 / 4 | 33.2 / 20.6 | 225.0 |
| high_demand / 2031 | RENO | 4 / 36 | 13 / 36 | 303.6 / 189.5 | 466.56 |
| high_demand / 2031 | BOISE | 3 / 5 | 13 / 6 | 54.8 / 34.05 | 466.56 |
| high_demand / 2036 | RENO | 9 / 105 | 29 / 105 | 872.4 / 544.75 | 1160.95 |
| high_demand / 2036 | BOISE | 4 / 12 | 29 / 12 | 124.4 / 77.5 | 1160.95 |
| delayed_build / 2027 | RENO | 3 / 11 | 5 / 11 | 96.4 / 60.05 | 150.0 |
| delayed_build / 2027 | BOISE | 2 / 2 | 5 / 3 | 23.6 / 14.6 | 150.0 |
| delayed_build / 2031 | RENO | 4 / 15 | 9 / 15 | 132.4 / 82.5 | 311.04 |
| delayed_build / 2031 | BOISE | 2 / 3 | 9 / 4 | 34.8 / 21.6 | 311.04 |
| delayed_build / 2036 | RENO | 5 / 22 | 21 / 22 | 198.8 / 123.95 | 773.97 |
| delayed_build / 2036 | BOISE | 3 / 4 | 21 / 7 | 53.2 / 33.05 | 773.97 |

## Reference hardware and uncertainty

The sourced DGX H100 10.2 kW maximum is a separate sensitivity from the unqualified 8 kW capped design class. It is not an adopted supplier BOM or proof that the proposed throughput is attainable at a cap.

| Site | Reference maximum kW | Racks | Initial envelope sufficient |
|---|---|---|---|
| RENO | 120.6 | 11 | False |
| BOISE | 28.0 | 4 | False |

| Throughput sensitivity | Site | GPU systems | Peak kW |
|---|---|---|---|
| low / 800 tokens/sec | RENO | 20 | 168.4 |
| low / 800 tokens/sec | BOISE | 3 | 31.6 |
| high / 2400 tokens/sec | RENO | 8 | 72.4 |
| high / 2400 tokens/sec | BOISE | 2 | 23.6 |

## Owned engineering arithmetic

These are component ratings for a concept, not a licensed protection, structural, fire or hydraulic design. Annual PUE does not replace coincident peak-load calculations.

| Stage | Usable IT kW | Peak facility input kW | Surviving UPS path kW | N+1 generation / thermal cooling kW |
|---|---|---|---|---|
| initial | 250 | 396.67 | 350 | 600 / 300 |
| expanded | 500 | 793.33 | 700 | 1200 / 600 |

## Finance and workforce reconciliation

Phase I includes the $3M land overlay. No land payment is evidenced. The $15,500,000 envelope reconciles to $3,000,000 land, $780,000 unaccepted/unrecognized 2026 requests, $11,220,000 conditional post-2026 CIP requests and $500,000 unspent reserve. Earlier calibrated journals remain unchanged outside the separate land overlay. The enterprise successor applies existing finite Treasury limits to conditional requests.

| Workforce phase | Technical FTE | Facilities / guards | Annual gross payroll | New authorized / occupied |
|---|---|---|---|---|
| COLO | 20 | 0 / 0 | $3,590,000 | 0 / 0 |
| OWNED_CONDITIONAL | 20 | 2 / 6 | $4,530,000 | 0 / 0 |

Construction lead allocation is within the vendor-coordination pool; purchased specialist capacity is within design/commissioning costs. Neither is added again as permanent payroll. Workstations and roving assignments remain requirements, not occupancy records.

| Base case year | Facility request | IT request | Operating request | Gross requirement |
|---|---|---|---|---|
| 2026 | 3780000.00 | 0 | 0.00 | 3780000.00 |
| 2027 | 4795000.00 | 4360000 | 4401710.00 | 13556710.00 |
| 2028 | 6425000.00 | 720000 | 4672224.20 | 11817224.20 |
| 2029 | 0 | 280000 | 4822359.14 | 5102359.14 |
| 2030 | 0 | 464000 | 4983284.45 | 5447284.45 |
| 2031 | 0 | 6104000 | 5266189.81 | 11370189.81 |
| 2032 | 0 | 440000 | 5447171.81 | 5887171.81 |
| 2033 | 0 | 440000 | 5763525.54 | 6203525.54 |
| 2034 | 0 | 744000 | 5971606.16 | 6715606.16 |
| 2035 | 0 | 8168000 | 6323864.67 | 14491864.67 |
| 2036 | 0 | 1184000 | 6590391.31 | 7774391.31 |

Owned investment sensitivities separately include a demand-triggered second module, refurbishment, escalation, migration overlap and decommissioning. Cases above the 500 kW owned envelope remain infeasible; an attractive arithmetic NPV cannot approve an undersized facility. Terminal proceeds occur only in the terminal period. Tax benefits and verified displaced-cost credits are zero.

## Recovery and execution gates

| Native service | Tier | Minimum service |
|---|---|---|
| SVC-keys | BOOTSTRAP | Independent HSM pair, sealed recovery material and off-primary custodians; acknowledge key changes only after recovery durability |
| SVC-connectivity | BOOTSTRAP | Offline signed DNS/time/routing bootstrap; independent transport credentials |
| SVC-identity | BOOTSTRAP | Independent recovery realm and break-glass roots; no primary-only identity dependency |
| SVC-observability | BOOTSTRAP | Local protected incident log buffer before central collectors |
| SVC-compute | PRODUCTION | Prioritized transaction/database workloads |
| SVC-finance-systems | PRODUCTION | Minimum finance transaction/reporting dependencies; ICFR relevance requires customer scope |
| SVC-atlas-product | PRODUCTION | Prioritized centrally hosted client/professional planes; optional accelerators degraded |
| SVC-foundry-product | PRODUCTION | Central control/support only; customer operating authority retained |
| SVC-institutional | ALEXANDRIA | Canon authoritative records, minimum Pinakes/Semaphore discovery and source-rights enforcement; indexes rebuildable |
| SVC-private-ai | ALEXANDRIA | 10% planning accelerator throughput; core institutional records do not wait for full AI restoration |
| SVC-developer | DEVELOPMENT | Rebuildable development; signed release artifacts protected with production prerequisites |

Recovery is unverified for every tier. Prepositioned copies, independent keys/identities/DNS, complete logs and restore tombstones are required; a full network seed is not the timed minimum-service restore. The source register and accountable external evidence gates are in `enterprise/runtime/readiness.json`. Management owns implementation; Internal Audit retains independent evaluation.
