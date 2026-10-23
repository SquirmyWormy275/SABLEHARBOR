# Service operating-model comparison

**State: synthetic planning assumptions; not approved budgets, vendor quotes or proven recovery.**

57 services; 49 support components; 49 dependency requirements; 4 source-named external parties; six workload classes.

| Alternative | Five-year cash | Capital | Cash operating cost | Closing net book | Year-one required FTE |
|---|---:|---:|---:|---:|---:|
| Cloud-heavy transition with owned restricted estate | $54,214,489 | $3,217,433 | $50,997,056 | $1,353,168 | 32.31 |
| Hybrid transition: 60% owned production, 50% owned dev | $53,847,479 | $4,584,535 | $49,262,944 | $1,932,511 | 34.15 |
| Owned baseline in professional colocation; cloud burst | $51,796,143 | $5,432,054 | $46,364,089 | $2,288,490 | 34.15 |
| Future owned primary plant; independent recovery still colo | $64,079,561 | $11,432,054 | $52,647,508 | $6,813,490 | 41.75 |
| Illustrative staged ownership: cloud to hybrid to owned colo | $52,391,118 | $5,208,570 | $47,182,549 | $2,213,011 | 34.15 |

All alternatives preserve owned restricted infrastructure and local hardware. Cloud-only is not offered as a compliant restricted-estate option. These are gross technology-scope comparisons, not total enterprise expenditure or approved net additions to the existing forecast.

## Capacity and recovery limitations

CPU sizing includes one spare node per domain and 30% normal utilization headroom. GPU failover, storage performance, per-site industrial redundancy, actual rack density, carrier diversity and restore throughput are NOT established by those calculations. A sizing row does not certify RTO/RPO.

## Source and accounting boundaries

Policy extract: 2027 conditional workforce; vendor allowance $216,000/year; corporate facilities $1,140,000/year; ESS payroll $6,720,000/year. These amounts are not automatically deducted. Existing staff allocations and overlap amounts remain null until evidenced.

Depreciation starts the month after purchase. Hardware refresh is modeled at 48 months. Capex is not also counted as an operating expense. Closing book value is shown without treating it as cash resale proceeds. Owned-plant capacity expands in declared 100-kW blocks; no construction feasibility or delivery date is asserted.

Read `financial_bridge.json`, `capacity.json`, `staffing.csv`, `monthly_costs.csv` and `sensitivity.csv` with the source assumptions and exclusions.
