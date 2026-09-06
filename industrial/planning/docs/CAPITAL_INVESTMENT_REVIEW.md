# Prospective logistics investment review

**Document ID:** SH-PLAN-CAP-001 | **Version:** 1.0.0
**Owner:** Industrial capital planning | **Available:** 2026-09-06T00:00:00-07:00
**Origin:** Public synthetic planning model | **State:** Options review; no capital approval
**Reference corpus:** Accepted v1 case, cutoff September 5, 2026; future reference months remain forecasts.

At the stated conditional demand, contracted incremental logistics capacity has a $821,813 incremental NPV at 10%. Staged owned logistics has a negative $449,985 NPV, trailing outsourcing by $1,271,798. This supports testing provider quotes and customer commitments before selecting owned expansion. It does not authorize spending or establish the value of a separate mine project.

## What is compared

All three options face the same expansion customer demand, prices, seasonal distribution and constrained mine production described in [Operating Scenarios](OPERATING_SCENARIOS.md). They share the conditional $8M mine upgrade in 2028 with assumed January 2029 availability. Its spending, mine production benefit and common sustaining costs cancel between logistics alternatives. The result is a **logistics selection screen**, not a standalone NPV of the mine upgrade or the combined $17.4M investment. The mine project still requires its own technical and commercial investment case before approval.

| Option | Additional logistics capital | Service policy | Conditional owned capacity |
|---|---:|---|---|
| Current capacity | $0 | Serve external demand with existing logistics assets; report overflow as lost. Ordinary mine inbound may use outside carriers. | Existing three rail paths, 300k annual terminal tons, 20 drivers/18 tractors, 15k warehouse slots |
| Outsource incremental demand | $0; $150k initial provider setup expense | Buy qualified incremental external fulfillment up to source limits; ARU remains modeled principal | No invented owned assets; rail provider uses at most the fourth path on the existing network |
| Staged owned expansion | $9.4M | Add owned resources after conditional service dates; use outside providers for remaining overflow | Four rail paths, 380k annual terminal tons, 24 drivers/21 tractors, 17k warehouse slots |

Outsourcing limits are 4,160 car-equivalents, 80,000 terminal tons, 5,000 truck dispatches and 36,000 pallet-months annually, divided monthly. Rail additionally respects the network path limit. Assumed 2026 unit costs are $1,450/car, $44/terminal ton, $475/dispatch and $36/pallet-month, inflated with the operating cost index. These are provisional provider cost assumptions, not received quotations or evidence of reserved capacity. Rail and hazardous-material providers must be qualified for their specific work; the scenario grants no custody permission.

## Proposed staged costs and dependencies

| Conditional project | Spend schedule | Cost | First modeled capacity | Incremental annual fixed expense / staff |
|---|---|---:|---|---|
| Rail resilience | Sep–Dec 2027 | $4.2M | July 2028 | $190k / existing qualified roster assumed sufficient |
| Terminal expansion | Jan–Jun 2028 | $3.3M | July 2028 | $90k / four staff |
| Truck capacity | Apr–Jun 2028 | $1.1M | July 2028 | $35k / four drivers |
| Warehouse capacity | Jan–Jun 2029 | $0.8M | July 2029 | $30k / two staff |
| Common mine option, outside differential NPV | Jan–Oct 2028 | $8M | January 2029 | $250k / existing 128 site staff assumed sufficient |

Spending is even across each listed interval. Costs are nominal provisional project budgets; fixed expenses escalate from their 2026 basis. Rail spending comprises an assumed $3M road locomotive and $1.2M yard/control/customer-work readiness. Exact pricing, rights, engineering, path agreements, staff qualification and acceptance remain unproved. Proposed mine capacity is an assumed productivity/reliability gain, requiring independent geotechnical, metallurgical, ventilation, environmental, closure and financing support. Spending dates do not certify completion.

The operating source supplies all future sustaining, rehabilitation and incremental replacement cash. Baseline sustaining cancels between matched alternatives. Owned logistics adds $1,076,201 of modeled replacement outlays over the five-year screen, in addition to its $9.4M growth capital. Neither the forecast nor this review adds a duplicate baseline capital schedule.

## Cash-flow construction

Each option is compared month by month with current logistics assets serving the identical requested demand. External revenue uses constrained served units and the accepted contract economics, with explicit reservation-fee volume dependence. The calculation uses the same whole-dollar segment targets, largest-remainder customer allocations and per-contract rounding as the financial forecast. The expansion C-002 renewal multiplier of 1.03 is included; canceled customers receive zero revenue. Ordinary nonpayroll cost comes from the same `transactions.procurement_costs` hook as the financial forecast. It uses owned physical activity and calibrated variable/fixed cost categories. Accepted census payroll scales by staff count and the cash cost index. Outside provider charges, disruption costs, setup expense and incremental fixed expenses are then added once.

Intercompany ARU-to-Red Wash invoices are excluded from consolidated project revenue. Actual owned transport/handling cash costs, third-party mine inbound service and external linehaul remain expenses. A markup change in the internal rate card cannot improve project cash margin. The outside inbound cost source is independent of that markup. This distinguishes a legal-entity profit allocation from a consolidated economic saving.

Cash flows are monthly and unlevered, valued at December 31, 2026 through December 31, 2031 using the effective monthly equivalent of the annual discount rate. Funding proceeds, interest and dividends do not enter project NPV. The forecast separately tests financing availability; a positive project NPV would not prove available cash or borrowing authority.

The tax screen uses a provisional 25% cash rate, straight-line 15-year growth-asset depreciation beginning the month following conditional service, and 15-year replacement depreciation beginning the month following payment. Incremental project tax losses carry within the option with an 80% positive-income utilization ceiling, matching the financial forecast assumption; no immediate refund or use against unrelated group income is assumed. Annual positive taxable income net of available losses settles in December. These are planning conventions, not asserted statutory depreciation, tax elections or a tax opinion.

Incremental working capital is 12% of annualized monthly incremental external revenue. Its monthly increase consumes cash and its decrease releases cash. The default terminal scenario assumes disposal on December 31, 2031 for 45% of the original growth cost and recovers remaining incremental working capital. Gross proceeds enter cash, while disposal gain/loss against remaining project growth basis affects modeled tax and carried losses. Replacement assets have zero assumed terminal proceeds, a conservative simplification. No perpetuity or unverified appraisal is implied.

The project cash identity is operating cash margin minus cash tax, growth capital, replacement capital and working-capital increase, plus terminal disposal proceeds and working-capital recovery. Generated monthly rows expose every term. A separate continuing-operation sensitivity assumes neither terminal disposal nor working-capital recovery and recalculates tax; it does not merely subtract gross salvage from the default result.

## Results and decision thresholds

| Five-year incremental measure | Current | Outsource | Staged owned |
|---|---:|---:|---:|
| External revenue | $0 | $17,685,389 | $17,822,751 |
| Growth logistics capital | $0 | $0 | $9,400,000 |
| Incremental replacement capital | $0 | $0 | $1,076,201 |
| NPV at 10%, default disposal assumption | $0 | $821,813 | −$449,985 |
| NPV without terminal disposal or WC recovery | $0 | $75,938 | −$4,300,811 |

Both alternatives have nonconventional monthly cash-flow sign patterns: 25 sign changes for outsourcing and 15 for owned. The solver reports `AMBIGUOUS_NONCONVENTIONAL_CASH_FLOW` and no single IRR. Sign changes alone do not prove multiple real roots; they prevent claiming a unique conventional IRR without further analysis. NPV is the comparison statistic. A separate test uses the known two-root cash flow −100/+230/−132 to verify that the software does not arbitrarily choose 10% or 20%.

At 10%, owned NPV is −$2.652M with zero gross disposal proceeds, −$0.450M with 45% and +$0.426M with 65%, all retaining the default terminal disposal/WC recovery policy and related tax treatment. At 45% proceeds, owned NPV ranges from +$0.073M at an 8% discount rate to −$1.504M at 15%. Outsourcing remains positive across that discount range, but its $0.076M no-terminal result shows that release of working capital matters materially even without owned asset salvage.

Break-even scales the **incremental growth above the 2025 annual units**, holding customer mix and annual growth shape together. Scale 0 is flat starting activity; scale 1 is the stated expansion growth; 1.10 is 10% more incremental growth, not 10% more total volume. Integer allocation and capacity thresholds make NPV stepped. The algorithm reports the first positive crossing bracket found on the 0–3 test range; it does not claim a globally monotonic demand curve or a market demand forecast.

| First bracketed threshold | Incremental growth scale | Requested 2031 railcars | Terminal tons | Truck dispatches | Pallet-months |
|---|---:|---:|---:|---:|---:|
| Outsource versus current | 0.5190 | 11,851 | 307,063 | 17,633 | 161,216 |
| Owned versus current | 1.0302 | 14,661 | 359,338 | 20,227 | 181,133 |
| Owned versus outsource | 1.0992 | 15,040 | 366,391 | 20,577 | 183,820 |

Crossing zero against current assets does not make owned expansion preferable to outsourcing. At the last threshold only 15,020 of 15,040 requested railcars can be served by the owned-plus-overflow strategy; the lost volume remains visible. The stated scale-1 2031 comparison serves 14,495 cars under both added-capacity options; owned terminals serve 356,248 tons versus 353,872 with outsourcing. Other constraints explain why extra capital buys only a small revenue difference at this mix.

## Retrospective $8.5M interface review

The completed/accepted 2026 interface budget is $3.25M Red Wash-owned plus $5.25M ARU-owned, totaling $8.5M. It is sunk in every prospective option and contributes zero new project outflow here. Accepted normalized internal revenue of $583,480 and incremental ARU EBITDA of $203,290 describe legal-entity service economics before depreciation, tax, working capital and replacement. Annual EBITDA divided by sunk construction cost is not a defensible project IRR.

Internal billing disappears on consolidation. A standalone retrospective return would require dated incremental project cash flows and a supported counterfactual for the actual third-party cost avoided, reliability effects or incremental external mine sales enabled. No proved prior outside-cost saving is supplied; the model therefore credits zero unproved saving and reports no retrospective IRR. This is an evidence limitation, not a claim that the completed assets have no operational value.

## Evidence and reproducibility

The authoritative assumptions are [capital_options.json](../source/capital_options.json), [operating_plan.json](../source/operating_plan.json), the accepted [finance source](../../source/finance.json) and [transaction policy](../source/transaction_policy.json). Unit-cost calibration, accounting timing and synthetic procurement limits are documented in [Transaction Evidence](TRANSACTION_EVIDENCE.md). All new assumptions were authored as September 6 conditional planning inputs; none is backdated into the September 5 participant corpus.

Run `python -m industrial.planning.capital`. Outputs under `industrial/generated/planning/capital` are `capital_review.json`, `incremental_project_cashflows.csv`, `discount_residual_sensitivity.csv`, `validation.json` and `manifest.json`. The manifest hashes ten code/source dependencies, effective inputs and named artifacts. `--skip-break-even` supports quicker checks while retaining the main comparison and sensitivities. Nine tests independently check DCF arithmetic, tax/cash identity, ambiguity, residual sensitivity, matched physical demand, sunk/common cost exclusion intercompany markup neutrality, the tax-loss ceiling, following-month depreciation and contract renewal/cancellation pricing.

Selection requires actual customer commitments at adequate contribution margin, verified outside provider quotes and capacity, property and operating rights, engineering acceptance, financing capacity and the applicable qualified personnel. No proposed project closes the direct uranium custody gate or authorizes a future mine spur.
