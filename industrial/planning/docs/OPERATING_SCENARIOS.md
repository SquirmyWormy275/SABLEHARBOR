# Monthly physical operating scenarios, 2027–2031

**Document ID:** SH-PLAN-OPS-001 | **Version:** 1.0.0
**Owner:** Industrial operating model | **Available:** 2026-09-06T00:00:00-07:00
**Origin:** Public synthetic planning model | **State:** Conditional forecast; no authority granted
**Reference corpus:** Accepted v1 case, cutoff September 5, 2026. Its full-year 2026 balances include forecast months, not observed December results.

The model produces 180 monthly records: five years for each of base, downside and expansion. Ore, reagent stocks, saleable uranium, railcar movements, truck hours and customer fulfillment determine the financial drivers. A requested sale is lost when inventory or physical capacity cannot support it. Assumed future service dates remain conditions; they do not commission equipment, qualify crews, grant land rights or permit direct uranium custody.

## Source contract and boundaries

[operating_plan.json](../source/operating_plan.json) contains demand, resource, inventory and disruption assumptions. [capital_options.json](../source/capital_options.json) specifies spending, conditional capacity dates, staff additions and replacement costs. The accepted [operations source](../../source/operations.json) supplies the fictional 40-mile network, commodity payloads, transport costs and drayage cycle times. Its unchanged hash is pinned in the operating source. No new alignment, mine spur or direct uranium service is created here.

The earlier [operating and service plan](../../operations/OPERATING_AND_SERVICE_PLAN.md) retains official-source legal and geographic references. The new numerical scenario inputs are provisional synthetic assumptions, not carrier quotes, engineering acceptance, weather forecasts or mineral reserve estimates. The mine/plant capacity assumptions require independent technical support before use in a real investment decision. No new legal or licensing conclusion is asserted.

External activity starts from the accepted 2025 contract units: 9,000 railway cars; 254,000 terminal short tons; 15,000 truck dispatches; 141,000 reserved pallet-months. These are calibration anchors, not a declaration that 2027 reproduces 2025. Monthly demand weights are 7/7/8/8/9/9/9/9/9/9/8/8 percent. Largest-remainder allocation preserves whole annual car and dispatch quantities exactly. External prices increase 2% annually and cash costs 3%; their indices are relative to 2025. Mine production and inbound service costs are relative to accepted 2026 and therefore divide out the 2026 index.

| Scenario | External annual volume growth: rail / terminal / trucking / warehouse | Annual ore targets, 2027–2031 | Conditional growth projects |
|---|---|---|---|
| Base | 2% / 1.5% / 1.5% / 1.5% | 180 / 182 / 184 / 186 / 188 thousand tons | None |
| Downside | 0% / 0% / 0% / 0%, then specified customer loss | Same requested ore as base | None |
| Expansion | 10% / 7% / 6% / 5% | 185 / 190 / 225 / 225 / 225 thousand tons | $9.4M ARU logistics and common $8M mine option |

Base and downside buy outside fulfillment for 50% of otherwise eligible external overflow, subject to the outside capacity limits. Expansion buys up to 100%. Unserved demand is reported, not transformed into revenue. The capital comparison deliberately overrides these policies to compare zero incremental external outsourcing in its current-asset reference against full qualified outsourcing and staged owned capacity under the **same** expansion demand. This difference is explicit; the capital reference is not the low-growth base scenario.

## Constraints and labor

The rail model uses the derived 33.3485-mile mainline within the existing 40-mile network, a 1.8% modeled ruling grade, 143 gross tons per car and the accepted locomotive roster. Traction-limited cars per train equal the floor of `(tractive effort / (20 × grade percent + rolling resistance) − locomotive tons) / car tons`. Normal effort of 109,400 lb supports the capped 16-car train; a 10% winter effort reduction lowers this to 14. This is a planning resistance calculation, not a braking, adhesion, bridge rating or dispatch certification.

Three normal daily round trips use 20 mph average line movement, 1.2 hours switching per round trip and 1.5 hours branch work. The service day is bounded by 16 combined train-crew duty hours. Conditional expansion or outside rail capacity uses at most four round trips and 24 combined crew hours. These are combined roster planning hours, not permission for one employee to work a 16- or 24-hour shift. Existing 22 train/engine employees within BS&T's 58-person census are retained. The source does not waive individual hours-of-service, rest, qualification, operating-rule or collective bargaining requirements. Normal weekday service loses one day in January, February and December; the severe winter case substitutes six lost days.

External customer freight receives owned capacity first. Mine ordinary inbound then uses the residual rail, terminal and truck capacity. Overflow mine inbound goes to an assumed qualified third-party service paid by Red Wash; ARU earns no revenue on it. The outside rail option is a contracted locomotive/crew using a fourth path on the same network, not an invented parallel route. Its capacity is constrained by the four-path ceiling and the annual outside provider limit.

Truck capacity is the lesser of driver and tractor productive hours: 20 drivers × 1,800 hours/year and 18 tractors × 2,125 hours/year. External dispatches consume two hours each, multiplied by 1.15 in ordinary winter or 1.4 in the severe winter event. Reagent drayage uses the accepted commodity-specific cycle hours and payload-derived trips. Terminals start at 300,000 tons/year; warehouse space starts at 15,000 slots. Monthly constraints expose seasonality even where annual capacity appears sufficient.

The accepted ARU census remains 58 railway, 27 terminal, 24 trucking, 12 warehouse and 10 corporate employees. The truck unit includes 20 drivers plus a manager, dispatcher and two mechanics. Conditional July 2028 capacity adds four terminal staff and four drivers; July 2029 adds two warehouse staff. Existing mine 128 site and 12 platform staff remain fixed under the explicitly provisional productivity assumption. Finance applies these FTE counts to the accepted loaded payroll calibration. Growth fixed costs, outside providers and disruption repairs are separate, added once.

## Mine and material inventory

The existing 600-ton/day plant operates on 330 processing days at 94% availability: 186,120 tons/year. The conditional January 2029 project increases nameplate to 750 tons/day without asserting technical acceptance. Ore grade 0.17% and recovery 92% yield 3.128 lb U3O8 per short ton. Actual feed is the lesser of requested feed, available processing capacity, reagent-supported feed and the product inventory ceiling.

Opening saleable product is the accepted reference 172,400 lb, with a 60,000 lb operating floor and 250,000 lb ceiling. Requested sales start at 570,000 lb in 2027 and grow 3.5% in base/downside or 8% in expansion. Sales consume opening stock plus current production; they cannot cross the inventory floor. The downside price assumption is 20% below the same indexed reference price. It is a stress assumption, not a uranium price forecast.

Acid starts at 290 short tons, minimum 210 and maximum 340. Binder starts at 340 tons, minimum 245 and maximum 450. Intensities are 6,800/225,000 and 8,000/225,000 tons per ore ton. Orders are whole 100-ton rail batches. Receipts replenish the rolling minimum and consumption tracks actual feed; an acid shortfall curtails feed before inventory becomes negative. Binder is then ordered against the curtailed feed. Lime, steel and MRO movements scale from the accepted 225,000-ton planning demand, while ten project cars are allocated February–November. These are new physical forecasts; they do not relabel the accepted 215 billable/225 total planning interface as an observed annual total.

## Explicit stress events

| Event | Conditional period | Physical effect | Separate nominal repair/response cash |
|---|---|---|---|
| WINTER-2027 | Jan–Feb 2027 | Six lost service days per month; 1.4× truck cycle; lower traction | $45k railway + $20k terminals + $30k trucking each month |
| LOCO-FAILURE-2027 | Mar 2027 | One failed unit; two initial stopped days; remaining modeled outage up to 23 service days; slower substitute pair | $280k railway |
| CUSTOMER-LOSS-2028 | Jun 2028–Dec 2031 | C-001 canceled; lost physical and revenue shares differ by its actual contract mix | No invented cancellation fee |
| MINE-INTERRUPTION-2027 | Aug 2027 | Twenty calendar days unavailable; product buffer can temporarily support sales | $450k mine |
| ACID-SUPPLY-2028 | Feb 2028 | Only 40% of ordered acid delivered; mine feed curtailed to protect minimum stock | $35k mine |

C-001's physical shares are 2,200/9,000 railcars and 26,900/254,000 terminal tons. Its revenue shares are $3.275M/$15.5M and $1.345M/$13M. `lost_customer_ids` makes its forecast contract revenue zero; remaining customer revenues reconcile to the value-sensitive segment target. Aggregate physical scaling alone would incorrectly retain invoices to the canceled customer.

| Scenario / year | Ore processed, short tons | U3O8 sold, lb | Lost requested sales, lb | Ending product, lb | Total / outside-provider mine inbound cars |
|---|---:|---:|---:|---:|---:|
| Base 2027 | 180,000 | 570,000 | 0 | 165,440 | 176 / 0 |
| Base 2031 | 186,120 | 582,183 | 71,905 | 60,000 | 180 / 80 |
| Downside 2027 | 170,321 | 570,000 | 0 | 135,165 | 166 / 42 |
| Downside 2028 | 173,093 | 589,950 | 0 | 86,649 | 169 / 0 |
| Expansion 2031 | 225,000 | 775,479 | 0 | 100,700 | 206 / 121 |

Amounts shown are rounded; generated rows retain calculation precision. Downside 2027–2028 sales remain deliverable by consuming stock, so an interruption need not immediately lose sales. Base 2031 cannot sustain requested sales once stock reaches its floor. Expansion still requires 121 outside inbound cars in 2031 because seasonal external demand takes owned capacity first; buying the proposed assets does not remove every peak bottleneck.

## Capital, financial interface and reproducibility

All future sustaining and rehabilitation outlays are in the operating rows: ARU $3.3M/year in 2026 dollars, mine $4M/year in 2026 dollars, remaining mine rehabilitation $3M in 2027 and $2M in 2028, plus 3% annual replacement on active incremental ARU assets. Finance adds no duplicate schedule. Approved 2026 $8.5M interface spending and other accepted 2026 capital remain in the reference opening and are not rebooked.

`calculate(source=None, strategy_overrides=None, capital_source=None)` returns the 180-row contract. `build(output=..., source=None)` returns `operating_rows` plus a validation summary. Segment `served_units` includes owned and subcontracted fulfillment; `cost_volume_factor` includes only owned activity. `additional_cash_cost_usd` contains provider, repair and incremental fixed costs. The reciprocal mine/ARU schedule uses only `aru_served_cars_by_commodity`; `outside_cars_by_commodity` is a Red Wash third-party expense. Financial sales use constrained pounds and the separately supplied uranium price. See [transaction evidence](TRANSACTION_EVIDENCE.md) for procurement calibration and invoicing limits.

Run `python -m industrial.planning.operating_model`. Outputs are `operating_rows.json`, `monthly_operating_summary.csv`, `validation.json` and `manifest.json` under `industrial/generated/planning/operations`. The manifest pins all four disk dependencies, effective input hashes and named artifact hashes. Override hashes are separate from on-disk provenance, so a sensitivity cannot masquerade as the default source. Twelve tests exercise quantity conservation, constrained sales, stress effects, cancellation value mix, capital timing, outsourced-cost boundaries, validation rejection and deterministic manifests. Validation remains active under optimized Python.

True open conditions remain direct uranium custody, future mine spur authority and evidence-supported expansion dates, together with the particular technical, commercial and financing conditions attached to each proposed project. Forecast scenario dates do not close them.
