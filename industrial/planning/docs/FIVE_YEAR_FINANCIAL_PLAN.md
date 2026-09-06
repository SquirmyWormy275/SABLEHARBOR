# Five-year industrial financial plan

**Document ID:** SH-PLAN-FIN-001 | **Version:** 2.0.0
**Owner:** Industrial finance and treasury planning
**Effective:** September 6, 2026
**Record origin:** PUBLIC_SYNTHETIC_PLANNING_MODEL
**Evidence state:** CONDITIONAL_FORECAST with separately identified provisional assumptions

This model carries the accepted December 2026 industrial scenario through every month of 2027–2031. It produces base, downside and expansion cases. None of those future periods represents actual company performance, an executed loan, an approved project or an observed receipt. The published 2026 package is preserved unchanged.

## Opening control and reporting perimeter

The opening source records the accepted release, source commit, ZIP hash and individual trial-balance hashes. It carries every asset, liability and equity balance directly. The 2026 income accounts close into retained earnings: ARU opens with a $3,091,227 retained-earnings credit, while the mine/platform opens with a $2,869,375 accumulated-loss debit. This changes neither cash nor net assets.

| Opening January 2027 control | ARU group | Mine and Pale Sun operating perimeter |
|---|---:|---:|
| Cash | $4,198,440 | $2,000,000 |
| Total assets | $89,166,806 | $75,400,866 |
| Total liabilities | $30,070,699 | $22,831,108 |
| Equity including closed 2026 income | $59,096,107 | $52,569,758 |

The two aggregate books retain entity IDs `ARU_GROUP` and `RWH_PS`. The enterprise integration supplies separate ARU/BS&T/Pale Sun/Red Wash ownership allocations and the parent funding chain. It also bridges subsequent book-only shared-service allocations to this forecast's tax perimeter. The forecast does not imply a particular tax classification for SHI or a consolidated federal tax group.

Each year has its own opening journal. Prior-year income closes into retained earnings, while accounts such as receivables, inventory, liabilities, tax prepayments and debt carry forward. Every monthly trial balance, income statement, balance sheet, cash rollforward and equity bridge reconciles independently.

## Inputs and executable interface

The controlling financial source is [`forecast.json`](../source/forecast.json). Physical fulfillment, outages, inventories, staffing and capital options come from `operating_model.py` in the source checkout. Item-level procurement comes from `transactions.py` in the source checkout, using disclosed quantities, calibrated unit rates and fixed service charges. Its calibration is not an independently obtained supplier quote.

```bash
uv run python -m industrial.planning.forecast
uv run python -m unittest industrial.planning.tests.test_forecast -v
```

`build(output=..., operating_rows=None, source=None)` returns the summary, complete journal rows, month-end trial-balance rows, monthly statements, funding rows, opening rows, adjusted operating rows, datasets and emitted file paths. Passing a source dictionary or operating rows permits controlled scenario changes without changing the accepted source package.

All outputs are under `industrial/generated/planning/forecast/` by default. `journal.csv` preserves scenario, entity, year, month, account, debit, credit, signed amount, source ID, source type, segment and counterparty. The other schedules are `trial_balances`, `monthly_statements`, `opening_balances`, `funding`, `payments`, `assets`, `debt`, `tax`, `intercompany`, `inventory`, `contract_revenue` and `eliminations`. `summary.json` identifies scope and results; `manifest.json` authenticates exact emitted CSV bytes and the supplied financial source.

## Revenue, physical constraints and operating costs

The operating model supplies fulfilled customer volume after capacity constraints, outside-provider fulfillment, outages and customer cancellations. Finance applies those results to the accepted monthly contract book and future prices. Canceled ARU-C-001 contracts receive zero revenue from the downside cancellation date. The remaining contracts receive the segment revenue target in proportion to their inherited revenue mix. This preserves the operating model's customer value mix without continuing to invoice the canceled customer.

ARU-C-002 renewal pricing has a separately declared multiplier: unchanged in base, a 12% reduction in downside and a 3% increase in expansion. These are conditional negotiated-price scenarios, not new executed agreements. The source also exposes external revenue, ordinary indexed cash cost and payroll multipliers for meaningful financial stress tests. Those parameters change amounts throughout the journals, cash requirements and taxes.

ARU payroll uses accepted loaded compensation and the operating model's declared segment FTE. Corporate staffing is separately declared. Ordinary nonpayroll purchases are posted item by item with the procurement source ID, vendor and due date. Disruption, outside-capacity and incremental fixed expenses are added once; they are excluded from ordinary procurement calibration. Payments retain the original item IDs so the transaction evidence layer can match the same invoice to both its expense and settlement.

Mine production starts from the accepted $27.95M **2026** cash-cost basis. The forward cost index is therefore divided by its 1.03 reference index; the model does not inadvertently apply the 2026 increase twice. The fixed/variable split and a 50% staffing-cost exposure are explicit calibrations. Mine and platform FTE changes affect costs, but those elasticities are not represented as individual mine timecards or independently observed salaries.

Weighted-average inventory costing uses actual modeled production and shipments. Sales cannot exceed available pounds. Normal production cost and production depreciation enter inventory and are released proportionately to shipments. Abnormal idle fixed overhead and unallocated fixed production depreciation remain current expense; standing idle cannot create finished-product inventory. The accepted opening stock is 172,400 pounds, with separately carried cash and depreciation costs.

## Assets, capital and financing

Opening asset cards reconcile exactly to accepted gross and accumulated depreciation. The individual allocations remain synthetic. Depreciation never exceeds remaining net book value. Legacy mine production assets retain their declared units-of-production method; future production assets use stated lives and normal-capacity allocation. Retained lease ROU depreciation is separate from lease principal and interest.

The operating model's replacement fields contain the complete future sustaining/rehabilitation program. Finance does not add a second sustaining budget. Growth capital is separate. Replacement assets enter the balance sheet when paid and depreciate from the following month. Growth tranches enter account 1410 construction in progress when paid. A project transfers to owned PPE without cash only after every planned tranche has been funded and its conditional in-service date has arrived; depreciation begins the following month. Asset cards retain the project ID, paid cost, planned gate and actual conditional service month. A missed funding gate leaves paid construction visible without invented commissioning. Monthly asset cards reconcile both owned PPE and construction, including additions in their purchase month. Unfunded capital remains a disclosed deferred plan rather than being silently presented as a completed, financed asset. Operating capacity increases continue to depend on the operating model's completion and qualification assumptions.

The legacy loan carries its accepted $21,375,000 opening balance. Quarterly principal, lease service, interest, issuance-cost amortization, January 2031 maturity and conditional replacement debt are explicit. Refinancing limits are $18M base, $12M downside and $20M expansion. They are hypothetical financing capacities, not executed lender commitments. New principal and issuance fees are separate from the retirement of the old loan. An unpaid maturity remains old debt and is reported overdue.

The debt model uses opening monthly principal with ACT/365 interest and month-end payment/refinancing buckets. A replacement draw begins accruing interest in the following month, avoiding simultaneous full-month interest on both sides of a refinance. This is a disclosed monthly approximation to seventh-of-month contractual timing. It is not represented as an exact daily lender calculation. The $5M revolver remains undrawn and incurs its disclosed commitment fee.

## Working capital and finite liquidity

New external invoices are collected 50% in the next month and 50% in the second month. Accepted opening receivables receive a separately disclosed January/February aging reconstruction. Procurement follows its 30-day due dates, payroll is due in the current month, inherited payables settle from January and inherited operating accruals become due in February. Rolling deposits remain on the balance sheet. Indexed safety-stock additions are explicit purchases; the model does not create a fictional refund by writing inventory down.

Mine intercompany invoices use only ARU-served physical cars and the declared rail, terminal and truck-leg rates. Outside-provider charges stay external. Mine payment and ARU receipt are simultaneous reciprocal entries with matching IDs. Seller segment ownership survives settlement, including the accepted $49,240 opening balance: BS&T $16,550, terminals $10,650 and trucking $22,040.

| Conditional annual equity envelope, each forecast year | ARU group | Mine through Pale Sun |
|---|---:|---:|
| Base | $6M | $12M |
| Downside | $4M | $12M |
| Expansion | $10M | $15M |

Required equity covers due payments, planned capital and the declared $2M cash reserve. Received modeled equity is capped by the unused annual envelope. Payroll, financing, tax/closure, intercompany and other supplier obligations follow the disclosed payment priority. Unpaid costs stay in their liabilities; deferred capital remains unpurchased. These capital receipts are financing, never income.

The positive cash reserve does **not** establish solvency if bills are unpaid. A period with arrears or deferred capital is explicitly financially infeasible as scheduled. Physical output in such a stress case remains a conditional operating plan, not a promise that suppliers, workers or regulators would permit indefinite continuation. A funding gap repeats while unmet obligations persist, so monthly gap balances must not be summed as independent new capital requirements.

## Taxes and closure

ARU tax goodwill begins with the separate $13M original basis and twelve months of accepted amortization already completed. The next sixty months continue the 180-month schedule. At December 2031 its remaining tax basis is $7.8M, with $1.3M subsequent-amortization DTL at the selected 25% rate. Book goodwill and the initial $1,762,500 book excess remain separately identified under the accepted conditional accounting treatment.

Current tax uses cumulative annual taxable income, an explicit 80% NOL utilization ceiling and modeled carryforward of unused losses. New loss DTAs have a full valuation allowance; losses do not create speculative tax-benefit income. The accepted reserve DTA remains conditional in base/expansion, while downside records a full prospective valuation allowance in January 2027. No 2026 balance is restated. Quarterly payments and any unpaid/prepaid settlements reconcile to current tax expense.

The mine retains the accepted simplified 18% book-based tax convention, including book ARO accretion. This is not a statutory federal/state return computation. Future reserve settlements would require a new tax allocation/deduction assessment; no automatic immediate deduction is inferred. The forecast adds no tax-group election or classification beyond the expressly conditional source assumptions.

The accepted $17,281,868 opening ARO accrues at an effective 6.5% rate compounded monthly. Its 2027–2031 cash schedule comes from the published liability-calibrated closure timing, including the larger 2030 reclamation payment. Settlement reduces the liability and operating cash; it is neither capital spending nor a second expense. The underlying calibration is still not an independently measured engineering estimate.

## Validation and interpretation

Tests independently recompute journal equality, all 360 monthly trial balances and cash rollforwards, exact opening/year-end carry, finite funding, debt movements, tax and NOL chains, intercompany eliminations, canceled-customer invoices and inventory/asset carrying values. Price, cost, payroll and debt changes must propagate. A zero-equity test must produce visible unmet obligations and deferred capital without negative cash or invented financing. Missing months and unbalanced anchors are rejected. Repeated unchanged builds produce identical CSV manifests, and accepted sources remain byte-identical.

Passing these controls means the selected conditional model is computationally consistent. It does not establish that downside financing is obtainable, that an unfunded operating plan can continue, that a project is qualified, or that provisional tax and valuation judgments are audited conclusions.
