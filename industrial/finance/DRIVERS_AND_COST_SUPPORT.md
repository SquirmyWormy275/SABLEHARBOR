# Physical drivers, contracts and operating cost support

**Document ID:** SH-IND-FIN-DRV-001
**Version:** 1.0.0
**Owner:** Industrial finance / operating controllers
**Effective:** 2026-09-05
**Record origin:** PUBLIC_SYNTHETIC_DIEGETIC
**Evidence state:** LOCKED_DERIVED_IMPLEMENTATION with explicitly labeled PROVISIONAL_ASSUMPTION inputs

The 2025 customer register is derived fictional case data. Each contract identifies a stable customer, segment, unit, annual volume, price, fixed capacity/accessorial charge, term and renewal. Annual revenue is calculated from those rows. The monthly calendar allocates annual physical units with an integer largest-remainder method, preserving every car, dispatch and billable storage unit. Fixed annual reservations/accessorial schedules are divided across twelve months separately.

## External revenue and concentration

The 12 rail contracts generate 9,000 loaded cars and $13,949,250 freight revenue across the six selected traffic classes. Explicit fixed accessorial/reserved-capacity fees add $1,550,750. Total railway revenue is $15.5M. These charges are internal synthetic contracts, not a purported published carrier tariff.

The other 17 contracts generate $13M terminals, $7.5M trucking and $6M warehousing. Four rail customers also buy nonrail services. They are aggregated by stable customer ID before concentration is calculated. The largest is Red Desert Alkali Products LLC at $4.62M; the top five total $16.8M. Basin Well Services Inc.'s November 30, 2026 renewal is the one material diligence renewal risk. A sensitivity shows December exposure without changing the selected contract case.

The warehouse book sells 141,000 reserved pallet-months, averaging 11,750 occupied/reserved slots. Operations provides 15,000 physical slots across Taylor and the truck-served Rawlins satellite. Reserved-space commitments and integrated handling explain the revenue model; twelve FTE operate the warehousing segment. The 45% selected warehouse EBITDA margin remains a constrained case assumption, not independently demonstrated market performance.

The terminal contract units are short tons, with capacity/reservation commitments embedded in the integrated handling price. The 300,000-ton physical terminal capacity must cover the complete external terminal contract schedule plus Red Wash inputs; the builder's linked physical checks compare those totals. Rawlins is off the BS&T network and truck-served through external connections. No Rawlins railroad branch is inferred from a customer destination label.

## Payroll and headcount

The source census contains 58 BS&T employees, 27 terminal staff, 24 trucking staff, 12 warehouse staff and 10 ARU corporate staff. There are 14 named leaders and explicitly synthetic anonymized staff IDs. A 30% loaded employer burden is applied to individual salary assumptions. This is a combined model of benefits, employer payroll costs and related labor expense, not a real wage survey or national bargaining settlement.

BS&T functions are 22 train-and-engine, 10 maintenance-of-way, 8 mechanical, 6 operations/dispatch, 3 safety and 9 management/administration. Train-and-engine employees are represented under the property SMART-TD agreement; MOW employees under BMWED. The other functions are modeled as nonunion. Existing employees remain after the stock acquisition; the seller transition does not count Fred Tolman as an additional operating FTE.

Corporate gross expenses are $2.18M. Explicit shared-service allocations are $0.83M rail, $0.55M terminals, $0.32M trucking and $0.28M warehouses, totaling $1.98M. The net corporate/unallocated charge is therefore $0.2M. This shows how ten corporate employees can coexist with the small reported unallocated charge. Allocations are expense transfers, not external revenue, and eliminate within the group.

The trucking census identifies twenty qualified drivers, one manager, one dispatcher and two mechanics. Existing salaries and the 24-person total are preserved. Operations reconciles the 15,000 external dispatches and mine dray work to available productive driver and tractor hours; no unnamed additional driver payroll is assumed.

## Working capital and earnings support

The receivables ledger carries net amounts. Its supporting schedule starts with gross receivables and a separate $80,000 specific allowance for an older disputed balance attributed to fictional ARU-C-025. The allowance remains unchanged across modeled opening and closing dates: no new provision, writeoff or recovery is assumed. At December 2025, $6.08M gross less $0.08M allowance equals the $6M recorded net receivable. The aging buckets are $5M current, $0.7M at 31–60 days, $0.3M at 61–90 days and the fully reserved $0.08M beyond 90 days. Other balances are assumed collectible. These are explicit synthetic aging and credit assumptions, not recovered invoices or an independently validated expected-credit-loss estimate.

Inventory is allocated 50% to rail/mobile parts, 20% to diesel/lubricants and 30% to maintenance materials. The $1.8M December 2025 total therefore comprises $900,000, $360,000 and $540,000. Declared blended unit costs of $900 per equivalent component lot, $2 per equivalent gallon and $300 per equivalent short ton produce transparent equivalent quantities. These cost/quantity conventions support the balance; they are not a claim of physical stock counts or current supplier quotes. The serviceable-stock assumption produces zero obsolescence reserve. Any later write-down must reduce both assets and earnings explicitly.

The reported-to-normalized EBITDA schedule begins with synthetic net income and adds only recorded interest, tax and depreciation. Unsupported seller discretionary, consulting, retention and commissioning addbacks are zero. The 2025 result remains $9.8M. Calling the schedule reported does not assert possession of audited company statements. The 2026 normalization likewise retains actual modeled expenses rather than increasing acquisition earnings by an assumed addback.

## Expense evidence boundary

The selected segment envelopes and detailed BS&T expense classes are controlling handoff inputs. Payroll is calculated from the employee census. Nonpayroll budgets are then explicitly allocated by service/material/occupancy/insurance categories. `external_cost_budget_support.csv` labels those allocations provisional. Its monthly service-budget units are budgeting support, not fabricated invoices or independently observed supplier prices. Analytical customer margin allocations use the selected segment expense ratio and are clearly distinguished from incremental customer cost-to-serve.

The physical Red Wash interface has stronger unit support: rail moves, terminal handling, truck legs and per-unit labor/equipment/risk cost assumptions are explicit in `operations.json`. Origin-carrier line-haul is outside ARU revenue and separately charged to the mine scenario. No carrier quotation has been invented. Annual market review and the external-carrier right remain substantive contract conditions.

## Interface scenarios and return

The normalized basis is **205 base physical cars + 10 project cars = 215 billable cars**, plus **10 contingent, unbilled buffer cars**. The 225 figure is a planning allowance. The 300-car figure is capacity. Neither unused buffer nor unused capacity creates an invoice or a minimum-volume guarantee.

The derived normalized ARU revenue is $583,480, variable cost $332,190 and fixed incremental operating cost $48,000, producing $203,290 incremental EBITDA. This is $291,520 below the old $875,000 revenue target and $161,710 below the old $365,000 EBITDA target. The differences are preserved rather than forced away. The new EBITDA is only about 2.39% of the entire $8.5M interface capital, or about 3.87% of the $5.25M ARU-owned portion; those ratios do not establish an acceptable investment return. Shared Taylor capital needs additional customer use, documented benefits and disciplined follow-up.

The 2026 ramp is 3, 6, 9, 12, 15 and 18 cars from July through December: 63 physical cars. July service starts July 7. The specific mix produces $171,380 of ARU/BS&T invoices and $87,400 of separately modeled external origin line-haul. It does not produce a full normalized annual revenue contribution. ARU incurs $24,000 half-year fixed interface cost plus a separate $20,000 June commissioning expense. The commissioning expense is not hidden in capital or capitalized solely to preserve margin.

Invoices carry exact IDs and counterparties. Mine payments occur in the following month. December's receivable/payable remains reciprocal at year-end and settles in January 2027. Income-statement elimination removes the same service amount from ARU revenue and Red Wash expense; balance-sheet elimination removes only the remaining reciprocal receivable/payable. Third-party line-haul, wages, fuel and terminal costs remain external consolidated expenses.
