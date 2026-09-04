# Sable Harbor financial reconstruction — Phase 0/1

**As of:** September 3, 2026

**Source baseline:** `origin/main` at `904365b27c9b7ebbc89a26c8f500430e032510c1`

**Status:** diagnostic financial archaeology; **NOT CANON**

**Scope boundary:** Sable Harbor company economics, not the Alexandria examination engine

## Executive conclusion

Current canon does **not** support a 47,000-person Sable Harbor. It explicitly leaves exact 2026
enterprise headcount, revenue, office populations, P&Ls, acquisition capital, and most operating
populations open. The only complete quantified establishment is J2 at 237 billets. Named teams and
roles establish a larger minimum visible population, but not a census and not anything close to
47,000.

A 47,000-person Sable Harbor can be made economically plausible only by changing its implied scale.
It would be a roughly **$15–17B minimum-survival enterprise, $20–25B healthy enterprise, or
$27–34B high-performing enterprise**. Its cash compensation and benefits alone would likely be
**$6.5–7.5B**; people plus ordinary work enablement would likely cost **$7.5–9.0B** annually. It
would require a large multi-asset mining portfolio and a major regional or national logistics estate,
not the single Red Wash mine and acquired operator currently described. In short, the present story
reads like a complex, well-funded, middle-market group. A separately modeled canon-congruent
reference has **5,000 employees and $2.3B revenue**; 47,000 employees reads like a different
industrial company.

PR #9 does not solve this conflict. Its 708 employees and $178.6M revenue are `MODEL_PROPOSED`; the
older 426-person/$124.5M model is `LEGACY_CALIBRATION`. Both predate the September 3 corporate
apparatus, and PR #9 assigns only about 70 people to shared corporate services—less than one-third of
the now-locked 237-billet J2 before Finance, Legal, P&C, Technology, Security, facilities, Internal
Audit, and other ESS functions are counted. Its headline EBITDA loss therefore materially
understates the cost of current canon.

## Evidence rules used here

| Class | Treatment |
|---|---|
| `LOCKED` | Explicit current controlling canon. |
| `DERIVED` | Mechanical or economic result from identified inputs. |
| `SUPPORTED ESTIMATE` | External benchmark plus canon-consistent role or asset logic. |
| `PROVISIONAL ASSUMPTION` | Reversible input needed to model an unresolved fact. |
| `SCENARIO` | Deliberate case, never asserted as actual. |
| `OPEN` | A decision or unavailable fact. |
| `CONFLICT` | Authoritative-looking sources disagree. |
| `SUPERSEDED` | Displaced historical assumption. |

PR #9's `MODEL_PROPOSED`, `SCENARIO_INPUT`, and `LEGACY_CALIBRATION` values are mapped here to
`PROVISIONAL ASSUMPTION`, `SCENARIO`, and `SUPERSEDED`/historical calibration as appropriate. None
becomes locked merely because it is implemented in code.

## 1. Authority and archaeology findings

### Controlling quantitative facts

| Fact | Class | Consequence |
|---|---|---|
| Founded in Sacramento in 2016 as services-first mining data and operational consulting. | `LOCKED` | History begins with asset-light service economics. |
| Foundry substrate emerged in 2018; Foundry Field commercialized during 2020–2021. | `LOCKED` | Software revenue cannot be projected backward unchanged. |
| The Crossing involved about twelve weeks of runway. | `LOCKED` | 2020 liquidity was genuinely constrained; no amount is established. |
| Harrison Vale led about $48M of growth financing in 2021. | `LOCKED` direction | Equity inflow is an anchor, not a complete cash-flow statement. |
| Wolf Ridge led about $135M in 2022 at about $900M post-money, no founder secondary, approximately 66.5% insiders / 33.5% outside capital. | `LOCKED` | Capital and ownership anchor; security mechanics remain open. |
| Red Wash is an underground Wyoming uranium mine acquired around July 2025. | `LOCKED` | Acquisition exists; price, financing, reserves, production and liabilities do not. |
| ARU was acquired and includes BS&T as a railway/short-line operating component. | `LOCKED` | A physical logistics business exists; date, price, routes, workforce and assets remain open. |
| J2 establishment is 237 billets: Contact 78, Judgment 42, Orientation 24, JAG 30, Education 35, HQ 28. | `LOCKED` design point | Minimum quantified corporate institution; billets need not all be filled. |
| Sacramento HQ is a long-duration research/industrial campus; financing, size and cost are not set. | `LOCKED` direction / `OPEN` economics | Model owned and leased equivalents; do not choose one. |
| Broad employee ownership/profit participation and strong cash pay are intended; prefer conservative ESOP-like structure. | `LOCKED` direction | Compensation must include profit/ownership economics, but plan mechanics remain open. |

### Noncontrolling quantitative material

| Source | Value | Classification and disposition |
|---|---:|---|
| PR #9 working model | 708 employees; $178.6M revenue; $(4.8)M EBITDA | `PROVISIONAL ASSUMPTION`; useful as evidence of an earlier attempt, rejected as a current complete model. |
| PR #9 CoreCo | 431 people, including about 70 shared corporate | `CONFLICT` with later apparatus if read as current; too small even for J2. |
| PR #9 acquired operations | Red Wash 126; ARU 132 | `SCENARIO`; plausible small-operator test cases, not facts. |
| Older operating model | 426 FTE; $124.5M revenue; ~65% gross margin; $(13.3)M operating loss | `SUPERSEDED` as current model; preserve only as historical calibration. |
| Older funding model | $172.5M cumulative equity; $25M facility/$10M drawn | `SUPERSEDED`/unsupported where it conflicts with current locked financing anchors; do not post to statements. |
| Blackridge dataset | 500 employees plus 75 contractors; 2015 financial records | Separate synthetic case implementation, not consolidated Sable Harbor financial canon. |

## 2. Reconciled workforce census

### What can actually be reconciled

| Population | Count | Class | Double-count treatment |
|---|---:|---|---|
| Contact | 78 | `LOCKED` | Included once in J2. |
| Judgment | 42 | `LOCKED` design point | Includes six Judgment Watch officers. |
| Orientation | 24 | `LOCKED` | Includes Head, Deputy, four Senior and eighteen Officers. |
| JAG | 30 | `LOCKED` | Six five-person teams; rotating practitioners are billets in J2, not added to host headcount. |
| Education | 35 | `LOCKED` approximate | Rotating faculty are not added; they remain employees of their home populations. |
| J2 Headquarters | 28 | `LOCKED` design point | Support positions included here, not duplicated in ESS. |
| **Total quantified establishment** | **237** | `DERIVED` from locked rows | Exact occupancy remains open. |
| Original Eight still employed in 2026 | 6 | `LOCKED` working lore | These six sit in operating/corporate units and are not additive to a future enterprise total. |
| Willow early/core named members | At least 10 named/role-visible people | `DERIVED minimum`, not census | Cross-functional participants and Rachel Sloane must not be double-counted. |
| Board | 9 directors | `LOCKED` | Directors are governance roles, not assumed employees. Daniel and Priya are already employees. |

**Reconciled enterprise headcount: `OPEN`.** The repository supplies no business-line or ESS
establishment from which 47,000 can be summed. Therefore “47,000” is a user-directed `SCENARIO`,
not a supported census.

### Illustrative 47,000-person allocation

This allocation is used only to cost the requested reality test. It demonstrates what would have to
exist; it is not a recommended organization.

| Population | Employees | Economic implication |
|---|---:|---|
| Foundry / Foundry Field | 5,800 | Global industrial-software platform, deployment and support business. |
| Willow | 500 | Very large industrial R&D institution, far beyond the currently described shop. |
| Atlas Meridian | 1,200 | Scaled product/professional investigation business. |
| Pale Sun / Red Wash | 6,500 | Impossible for one ordinary mine; implies multiple mines, processing and development assets. |
| Project Cradle | 800 | Portfolio of projects, not one pilot. |
| ARU / BS&T | 25,000 | Major railroad/logistics network, not a small short line. |
| Advisory | 4,000 | Large professional-services practice. |
| Corporate/ESS excluding J2 | 2,963 | Finance, Legal, P&C, Technology, Security, facilities, assurance and executive offices. |
| J2 | 237 | Locked design point. |
| **Total** | **47,000** | `SCENARIO` |

Corporate/ESS plus J2 is 3,200 people, or 6.8% of the workforce. That ratio is not facially absurd
for a diversified enterprise. The implausibility is the absent operating estate and revenue needed
to employ the other 43,800 people.

## 3. Fully loaded labor economics

The model separates wage/cash incentive, statutory and benefit load, and work enablement. BLS March
2026 data show private-industry benefits at about 30% of total compensation; transportation and
warehousing benefits are about 42% of total compensation, supporting a materially higher load for
rail populations. BLS May 2025 mean wages include software developers at $148.1K, information
security analysts at $132.5K, data scientists at $126.8K, lawyers at $185.8K, management analysts at
$113.8K, and rail transportation workers at $79.3K. Sable Harbor's stated high-quality employment
proposition justifies using market means or premiums rather than low percentiles.

| Population | Cash pay incl. incentive | Benefits/statutory | Tools, travel, training, workspace | All-in per employee | Class |
|---|---:|---:|---:|---:|---|
| Foundry product/delivery | $150K | $45K | $32K | $227K | `SUPPORTED ESTIMATE` |
| Willow | 170 | 51 | 70 | 291 | `SUPPORTED ESTIMATE` |
| Atlas Meridian | 165 | 50 | 40 | 255 | `SUPPORTED ESTIMATE` |
| Mine operations | 85 | 38 | 30 | 153 | `SUPPORTED ESTIMATE` |
| Rail/logistics | 78 | 36 | 27 | 141 | `SUPPORTED ESTIMATE` |
| Cradle | 125 | 45 | 45 | 215 | `SUPPORTED ESTIMATE` |
| Advisory | 140 | 42 | 35 | 217 | `SUPPORTED ESTIMATE` |
| Corporate/ESS | 145 | 44 | 35 | 224 | `SUPPORTED ESTIMATE` |
| J2 | 155 | 47 | 70 | 272 | `SUPPORTED ESTIMATE` |

Applied to the illustrative allocation, formulaic cash compensation plus benefits is about **$6.6B**;
a **$6.9B** healthy planning case includes stronger profit participation and vacancy/overtime mix.
All-in people-enabled cost is about **$8.1B**. A defensible sensitivity range is $6.1–7.5B and
$7.5–9.0B respectively. ESOP contributions, exceptional profit sharing, large equity grants,
contractor labor, and unusual overtime could raise this further. Equity dilution is not an income
statement cash cost, but share-based compensation is an economic cost and must be modeled after the
plan is defined.

## 4. Revenue architecture by business

### Foundry / Foundry Field

Customers buy a maintained representation/integration substrate and deployable applications, plus
implementation, configuration, support and specialist field work. The plausible architecture is
annual subscription/platform fees by site or enterprise, usage/data-scale charges, implementation
fees, and premium support. Recurring software can earn 70–85% gross margin; deployment-heavy work
may earn 25–45%. A blended mature margin of 60–75% and $450K–$900K revenue per employee is plausible
only with genuine product repeatability. Sales, customer success and R&D remain substantial.

**Current finding:** likely long-run cash generator, but no customers, contracts, ARR, retention,
pricing, or employee population are canonized. PR #9's $123.3M Foundry subscription/services figure
is unsupported as current truth.

### Willow

Current canon describes an internal bounded industrial research capability, not a mature external
commercial business. Transfers into products or businesses may create future value but should not
create consolidated revenue. Treat Willow primarily as R&D expense with capitalized equipment only
where accounting criteria are met. A meaningful 2026 external revenue assumption would contradict
the present description unless a customer-funded research contract is established.

**Current finding:** cash consumer; plausible annual cost from roughly $8–15M for a two-dozen-person
shop (PR #9 scale) to $120–180M for a 500-person global lab. The latter is required by the 47K case
but unsupported by canon.

### Atlas Meridian

Atlas is in a controlled-commercialization bridge. Customers plausibly buy annual platform access,
bounded investigations/design-partner programs, and specialist services. Revenue recognition should
separate licenses from time-and-materials or milestone work. Early economics resemble an R&D-heavy
professional service: low utilization and 20–45% gross margin. At maturity, software repeatability
could produce 55–75% blended margin and $300K–$700K revenue per employee.

**Current finding:** near-term cash consumer or breakeven experiment; potential later cash generator.
No price, customer count, launch volume, or staffing is established.

### Pale Sun / Red Wash

The product is uranium concentrate (`U3O8`) if Red Wash includes or contracts appropriate processing.
Revenue is pounds sold times realized price, recognized on transfer of control. The required model is:

`ore tonnes × grade × recovery = contained/recovered pounds → inventory → shipped pounds × realized price`.

Costs must include underground development and stoping, processing/toll milling, royalties, energy,
reagents, labor, maintenance, transport, site G&A, sustaining capital, depreciation/depletion, and
reclamation/asset-retirement obligations. Receivables, ore/WIP/finished inventory, supplies, payables
and accrued reclamation create working capital.

**Current finding:** economics are blocked. Reserves, grade, recovery, mine plan, mill arrangement,
permits, workforce, production, contracts and closure estimate are explicitly `OPEN`. Do not inherit
PR #9's $24.7M revenue, 126 employees or $18.5M ARO. A 6,500-person Pale Sun requires a multi-asset
producer; one Red Wash mine cannot economically explain it.

### Project Cradle

Canon permits a recovery system, stream right, equipment position or participation without mine
ownership. Economics therefore vary by contract: engineering/service fees over performance, equipment
sale/lease, royalty per recovered unit, or share of project cash flow. Development costs precede
episodic milestones; host-dependent WIP and contract assets/liabilities are likely. Capital at risk
can range from modest equipment to a large participation investment.

**Current finding:** pre-scale investment/project business. No host contract, recovery rate, volume,
ownership, capex or pricing is established. It should not receive a smooth recurring revenue curve.

### American Resource Utility / BS&T

Customers buy freight movement, switching, terminal/handling, storage and related resource logistics.
Revenue is carloads/tons × distance or tariff/contract rate plus accessorials. Economics require route,
interchange, carload, commodity, customer and terminal detail. Major costs are crews, fuel, locomotive
and car lease/ownership, track and signal maintenance, terminals, insurance, casualty, property,
dispatch, regulation and depreciation. Operating ratio (operating expense / revenue) is the core
diagnostic; a healthy established railway may operate around 65–80%, while a small or troubled line
may be worse.

**Current finding:** potentially steady cash generator but capital intensive. PR #9's 132 people and
$23.6M revenue describe a plausible small regional operator, not the 25,000-person network required
by the 47K case. The latter likely needs $7–10B revenue, thousands of route-miles, hundreds of
locomotives and billions of PP&E—none of which appears in canon.

### Advisory

Revenue equals billable professionals × available hours × utilization × realized rate, plus
subcontracted/project revenue. A practical mature range is 60–75% utilization, $225–$500 realized
hourly rates depending on level/mix, and $250K–$500K revenue per professional. Direct labor, travel
and subcontractors drive 30–50% gross margin before practice selling and corporate overhead.

**Current finding:** plausible capital-light cash generator, but canon only establishes an emerging
method-transfer line. A 4,000-person practice would be a large consultancy and is not narratively
present.

## 5. Corporate cost architecture

### 47,000-person diagnostic envelope

| Function | People | Recurring annual cost | Class / note |
|---|---:|---:|---|
| CEO, executive office, board, communications | 90–140 | $45–80M | `SUPPORTED ESTIMATE`; includes board/travel/advisers. |
| Finance, Treasury, Accounting, Tax | 350–500 | 95–150 | Transaction and capital complexity, not just size. |
| Legal/OGC, Corporate Secretary, Compliance/Risk | 220–350 | 75–130 | Excludes major litigation/deal spikes. |
| Internal Audit | 70–120 | 18–35 | Independent; not merged into ESS or J2. |
| People & Culture | 450–650 | 105–165 | High-touch recruiting, mobility and continuity doctrine. |
| Technology Services and cybersecurity labor | 1,050–1,500 | 230–370 | Product engineers remain in businesses. |
| Procurement, safety/quality governance, other ESS | 250–400 | 55–100 | Enterprise layer only; operating safety remains local. |
| Facilities/workplace and HQ operations | 250–400 | 55–100 | Excludes rent/depreciation and utilities. |
| J2 | 237 | 90–145 | About $48M cash comp/benefits plus tools, travel, research, education and facilities. |
| **Corporate recurring envelope** | **~3,000–3,600** | **$0.8–1.2B before enterprise technology/occupancy overlap** | Avoid double counting labor embedded in technology and facilities totals. |

J2's 237 billets are expensive but not the decisive problem at 47,000 people: approximately
0.5% of workforce and 0.4–0.7% of required healthy revenue. At PR #9's $178.6M revenue, however,
$90–145M of J2 cost alone would consume 50–81% of revenue. The September 3 institution cannot fit
inside the old model.

## 6. Technology cost model

For 47,000 people, the canon implies a genuine enterprise platform organization: endpoints and
identity; collaboration/productivity; network/telecom; ERP/HRIS/finance; developer platform; cloud,
storage and observability; data platforms; backup/recovery; cyber tooling and red teams; AI gateways,
hosted/private compute and frontier usage; architecture/supply-chain; service and reliability.

| Cost family | Annual range | Capital / depreciation implication |
|---|---:|---|
| Technology and cyber labor | $230–370M | Mostly expense; internal-use software subject to policy. |
| Endpoint fleet and lifecycle | 80–140 | 3–4 year refresh; some capitalized hardware. |
| Productivity, ERP, HRIS and enterprise SaaS | 120–220 | Mostly recurring expense. |
| Cloud, storage, network, telecom, observability | 180–350 | Consumption expense plus network assets. |
| Security/identity tooling and managed services | 80–160 | Recurring; incident surge separate. |
| Developer tooling and software supply chain | 45–90 | Recurring; business product tooling partly in business P&Ls. |
| Data and AI/model infrastructure/usage | 120–350 | Wide range; private compute may add capex and depreciation. |
| Backup, recovery, support and other | 45–120 | Must include restore testing and vendor support. |
| **Total** | **$0.9–1.8B** | `SUPPORTED ESTIMATE`; 4–8% of healthy-case revenue. |

The upper range is justified only if the enterprise truly operates the data/AI fabric described at
global scale. The 5,000-person canon-congruent reference carries approximately $115M annually, with
many platforms purchased rather than built.

## 7. Facilities and headquarters

Sacramento location and campus character are locked; size, tenure and financing are open. A
47,000-person enterprise does not require all employees at HQ. A 3,000–4,000-person corporate/J2
population plus education/conference/research space implies roughly 1.2–2.5M gross square feet,
depending on hybrid attendance, residential capacity and laboratories.

An owned-campus scenario is **$1.0–2.3B** of development and fit-out, with **$100–220M** annual
utilities, maintenance, security, tax/insurance, hospitality and lifecycle reserve. A lease case
should translate the same space to rent and tenant improvements; no financing choice is made here.
J2 must remain physically separate from ESS and Internal Audit requires a distinct secured suite.

Business-line facilities remain unquantifiable: Red Wash mine/processing infrastructure, ARU routes,
terminals and rolling stock, and Cradle host/owned equipment are all open. Those assets—not the
campus—would dominate consolidated PP&E at 47,000-person scale.

## 8. Capital and working-capital map

| Business | Maintenance capex | Growth capex | Working capital | Cash posture |
|---|---|---|---|---|
| Foundry Field | Low–moderate; endpoints/platform | Product/data/AI development | Receivables offset by deferred revenue | Likely generator when mature. |
| Willow | Lab equipment | Experiments and new facilities | Low inventory/WIP; no normal revenue offset | Consumer. |
| Atlas | Platform/compute | Commercialization and model capability | Contract assets/deferred revenue | Consumer until repeatable; later generator. |
| Pale Sun/Red Wash | High sustaining mine development/plant | Resource development, shafts, mill | Ore, WIP, concentrate, supplies and receivables | Cyclical generator/consumer. |
| Cradle | Equipment-dependent | Project participation | Project WIP, deposits, milestones | Episodic consumer then generator. |
| ARU/BS&T | High track, locomotive, car and terminal renewal | Routes/terminals/fleet | Receivables, fuel/materials, payables | Generator if operating ratio and capex are disciplined. |
| Advisory | Minimal | Hiring/practice build | Receivables and accrued bonus | Generator at utilization. |
| Corporate/J2 | Technology and campus lifecycle | Campus, data/AI and new capability | Compensation/vendor accruals | Consumes business surplus. |

At the healthy 47K scale, maintenance and technology/facilities capex likely total **$1.3–1.8B**
annually (6–8% of revenue), excluding major mine or railway expansions and acquisitions. Net working
capital likely absorbs **6–10% of revenue** because industrial inventory and receivables outweigh
software deferred revenue. This is a provisional range pending business mix.

## 9. Reverse-solved required revenue

The central equation is:

`required gross profit = corporate/J2 + product R&D + selling/delivery opex + other overhead + target EBITDA`

`required revenue = required gross profit / blended gross margin`.

For the illustrative 47K mix, all-in people-enabled cost is about $8.1B. Adding nonlabor mine/rail
operations, energy/fuel/materials, enterprise technology not already in role loads, insurance,
facilities, professional fees and target EBITDA yields $5.27B–$15.83B of gross profit depending on
case. At blended gross margins of 34–53%, required revenue is $15.5B–$30.0B.

## 10. Three diagnostic scale cases

USD billions except headcount and per-employee amounts.

| Measure | Case A — minimum survival | Case B — healthy | Case C — high performance |
|---|---:|---:|---:|
| Revenue | $15.50 | $22.00 | $30.00 |
| Gross profit | 5.27 (34.0%) | 9.71 (44.1%) | 15.83 (52.8%) |
| EBITDA | 0.45 (2.9%) | 2.20 (10.0%) | 4.80 (16.0%) |
| EBIT | (0.25) | 1.25 | 3.65 |
| Net income | (0.35) | 0.68 | 2.35 |
| Operating cash flow | 0.75 | 2.00 | 4.40 |
| Capex | (1.20) | (1.55) | (2.05) |
| Free cash flow | **(0.45)** | **0.45** | **2.35** |
| Headcount | 47,000 | 47,000 | 47,000 |
| Revenue / employee | $330K | $468K | $638K |
| Gross profit / employee | $112K | $207K | $337K |
| EBITDA / employee | $10K | $47K | $102K |
| Cash compensation + benefits | $6.65 | $6.90 | $7.30 |
| Corporate recurring cost | $0.80 | $0.95 | $1.10 |
| Technology cost | $0.95 | $1.20 | $1.55 |
| J2 cost | $0.095 | $0.110 | $0.130 |
| Capex / revenue | 7.7% | 7.0% | 6.8% |
| FCF / EBITDA | (100.0%) | 20.5% | 49.0% |

Major business-line revenue contributions:

| Business | Case A | Case B | Case C |
|---|---:|---:|---:|
| Foundry Field | $3.8B | $6.0B | $9.0B |
| Atlas Meridian | 0.5 | 1.2 | 2.0 |
| Pale Sun / Red Wash portfolio | 2.4 | 3.5 | 4.5 |
| Project Cradle portfolio | 0.5 | 0.8 | 1.2 |
| ARU / BS&T network | 7.1 | 8.5 | 10.3 |
| Advisory | 1.2 | 2.0 | 3.0 |
| **Total** | **15.5** | **22.0** | **30.0** |

Case A survives operationally but does not sustain its capital estate: low EBITDA, an EBIT loss and
negative FCF make it dependent on financing. Case B is the minimum credible long-duration expression
of the stated culture and reinvestment philosophy. Case C requires excellent software/product mix,
rail efficiency, commodity execution, professional-services utilization and capital discipline
simultaneously.

### Canon-congruent reference—not a fourth 47K case

To avoid leaving only the giant-company answer, the executable model also provides a separate
`PROVISIONAL ASSUMPTION` reference for the organization the narrative currently appears to describe:
5,000 employees, $2.3B revenue, $1.094B gross profit, $250M EBITDA, $115M EBIT, $50M net income,
$225M operating cash flow, $190M capex and $35M free cash flow. It assigns 1,350 people to Foundry
Field, 75 Willow, 225 Atlas, 550 Pale Sun/Red Wash, 75 Cradle, 1,750 ARU/BS&T, 375 Advisory, 363
other corporate/ESS and 237 J2.

This reference is economically possible but still tight: J2 costs about $82M, technology about
$115M, and total people-enabled cost about $960M. It is much more consistent with one mine, a
regional logistics operator, a scaled industrial-software business, and an emerging advisory line
than 47,000 employees. It should replace the earlier 1,000–3,000 shorthand as the preferred modeling
envelope unless management chooses to expand the asset narrative.

Illustrative healthy-case debt of $4–7B would imply 1.8–3.2× debt/EBITDA. At a 6.5–8.0% cash rate,
interest would be about $260–560M and EBIT interest coverage about 2.2–4.8×. These are `SCENARIO`
sensitivities only: current debt principal, rates and covenants are `OPEN`.

## 11. Required reality tests

| Test | Case B result | Interpretation |
|---|---:|---|
| Revenue / employee | $468K | Plausible only with major rail/mining assets plus strong software mix. |
| Gross profit / employee | $191K | Supports the high-cost intellectual apparatus if direct operations remain efficient. |
| EBITDA / employee | $47K | Healthy, not exceptional, for the mixed portfolio. |
| Corporate employees / workforce | 6.8% | Plausible; exact allocation remains scenario. |
| Corporate recurring cost / revenue | 4.3% | Defensible for complexity; overlaps must be eliminated. |
| Technology expense / revenue | 5.5% | High for industrials, justified only by real software/data/AI economics. |
| J2 cost / revenue | 0.5% | Affordable at $22B; unaffordable at PR #9 scale. |
| P&C cost / revenue | ~0.6% | Consistent with high-touch doctrine at scale. |
| Cash compensation + benefits / revenue | 31.4% | Plausible for mixed industrial/software/services. |
| Capex / revenue | 7.0% | Requires substantial asset base and disciplined maintenance. |
| FCF conversion | 20.5% of EBITDA | Thin but positive after reinvestment. |
| Net working capital / revenue | 6–10% range | $1.3–2.2B capital tied up; business data needed. |
| Debt / EBITDA | 1.8–3.2× scenario | Depends entirely on unestablished capital structure. |
| Interest coverage | 2.2–4.8× scenario | Lower end leaves limited cycle resilience. |
| Consolidated ROIC | Not measurable | Invested capital/acquisition prices and asset values are open. |
| Revenue concentration | Not measurable | Customer/offtake/freight populations are open. |
| Overhead absorption | $0.95B corporate / $9.71B GP = 9.8% | Manageable in Case B; catastrophic in PR #9 model. |

## 12. Organizational overbuild findings

1. **J2 is overbuilt for the PR #9 company.** A 237-billet institution cannot fit within a 708-person
   enterprise without becoming 33.5% of the workforce; its plausible cost consumes most of old-model
   revenue.
2. **The combined corporate apparatus is overbuilt below roughly $3–5B revenue**, even with modest
   non-J2 staffing. The company can preserve the doctrine at smaller scale only by leaving billets
   unfilled, buying shared platforms, and staging campus investment.
3. **47,000 employees are overbuilt for the described assets.** One underground mine and one acquired
   railway operator do not absorb 31,500 industrial employees without thousands of unsupported assets,
   routes and customers.
4. **Technology is either strategically justified or an expensive mismatch.** At $20B+ with several
   billion dollars of software/AI revenue, a $0.9–1.8B technology fabric is defensible. At $178.6M,
   it is not.
5. **HQ should follow economic scale.** Building a $1B+ campus before recurring cash generation and
   industrial asset funding exist would invert the capital-allocation doctrine.
6. **Under-resourcing also exists.** PR #9's approximately 70 shared-service staff cannot cover J2,
   regulated mining/rail operations, a nine-member board/five committees, Internal Audit independence,
   sophisticated P&C, cybersecurity, tax, treasury and facilities.

## 13. Historical reconstruction

| Period | Known financial development | Readiness |
|---|---|---|
| 2016–2017 | Formation; services-first work; Original Eight assembled over time. No revenue, payroll, founder capital or balance-sheet amounts. | Unresolved interval. |
| 2018–2019 | Foundry substrate emerges; Evalon begins late 2018. No revenue/cost/assets/funding amounts. | Unresolved interval. |
| 2020 | Crossing; roughly twelve weeks runway; productization pressure. No dollar revenue, burn or cash anchor. | Unresolved interval. |
| 2021 | Repeatability threshold; approximately $48M Harrison Vale financing. | One financing anchor only. |
| 2022 | Willow recharter; Atlas thesis; approximately $135M Wolf Ridge financing at ~$900M post-money. | Financing/ownership anchor only. |
| 2023–2024 | Willow work, Foundry improvement, Atlas reboot; Pale Sun thesis; Australia/Deloraine; board maturation. No statements. | Narrative milestones only. |
| 2025 | Hound/gauntlet; Red Wash acquisition around July after walk-away/restructure; Cradle opportunity; ARU acquisition exists but exact date/terms open. | Transactions known, accounting blocked. |
| 2026 | Atlas controlled commercialization; current portfolio and September 3 corporate architecture. | Economic architecture known; quantities mostly open. |

Do not interpolate these anchors into smooth revenue or headcount curves. The two locked financings
total approximately $183M, but uses, prior cash, security terms and subsequent capital are missing.
That capital is insufficient by itself to create the 47K estate implied above.

## 14. Capital structure inventory

| Item | State |
|---|---|
| Founders/insiders and outside capital approximately 66.5%/33.5% after 2022 round | `LOCKED` working posture. |
| 2021 approximately $48M Harrison Vale financing; director seat | `LOCKED` direction. |
| 2022 approximately $135M Wolf Ridge financing; no founder secondary; director seat | `LOCKED`. |
| Broad long-duration employee ownership / profit participation | `LOCKED` direction; implementation `OPEN`. |
| Common/preferred terms, option pool, ESOP trust, vesting, distributions and fully diluted cap table | `OPEN`. |
| Red Wash and ARU purchase prices, consideration, debt, rollover and contingent liabilities | `OPEN`. |
| Corporate debt, subsidiary/project debt, leases, cash and covenants | `OPEN`. |
| Legal entity and tax implementation | `OPEN`, controlled by issue #18. |

## 15. Financial-statement readiness

| Deliverable | Status | Why |
|---|---|---|
| 2016–2020 historical statements | `BLOCKED BY MISSING CANON` | No transactions, revenue, payroll, cash or capitalization. |
| 2021–2024 historical statements | `BLOCKED BY MISSING CANON` | Financing anchors exist; operating and balance-sheet records do not. |
| 2025 statements / acquisition accounting | `BLOCKED BY USER DECISION` | Red Wash/ARU terms, dates, assets, liabilities and financing absent. |
| 2026 current-year estimate | `READY WITH PROVISIONAL ASSUMPTIONS` | Diagnostic build possible, but it would not be actual company truth. |
| 2026 balance sheet/liquidity/debt | `BLOCKED BY USER DECISION` | Opening balances, acquisitions and capital structure absent. |
| Business-line P&Ls | `READY WITH PROVISIONAL ASSUMPTIONS` for Foundry/Atlas/Willow/Advisory; `BLOCKED BY MISSING CANON` for mine/rail | Physical drivers are indispensable. |
| Forward operating budget | `READY WITH PROVISIONAL ASSUMPTIONS` after scale selection | Bottom-up driver model can be built. |
| Capital budget/cash forecast | `BLOCKED BY USER DECISION` | Asset estate, acquisition financing, HQ tenure and liquidity policy absent. |
| Changes in equity | `BLOCKED BY USER DECISION` | Security and employee-ownership mechanics absent. |
| Capital rollforwards | `BLOCKED BY MISSING CANON` | Opening asset registers and transaction PPAs absent. |

## 16. Short decision queue

### A. Must decide before the financial build

1. **What is the intended 2026 scale: hundreds, low thousands, or approximately 47,000 employees?**
   Evidence: canon leaves total open; prior noncanon work says 708. Recommendation: select a
   canon-congruent **approximately 5,000-employee / $2–3B planning envelope** unless the user intends to add a major
   mining/logistics portfolio. Sensitivity: every 1,000 employees adds roughly $140–230M of all-in
   people cost; 47K requires roughly $15–30B revenue.
2. **What are Red Wash's physical model and acquisition terms?** At minimum: reserve/resource basis,
   mine/mill configuration, 2025–2027 production, realized-price mechanism, workforce, sustaining and
   development capital, purchase consideration and ARO. Recommendation: approve ranges and keep
   reserves formally open until a technical report exists. Sensitivity: can swing revenue and cash
   flow by hundreds of millions and determines whether Pale Sun is a business or development asset.
3. **What exactly was acquired with ARU and when?** Routes, route-miles, terminals, customers,
   carloads/tons, rolling stock, workforce, labor terms, purchase price, debt and maintenance backlog.
   Recommendation: define one coherent regional-operator package before statements. Sensitivity:
   determines billions of possible PP&E/debt and whether ARU is cash generative.
4. **What is the opening capitalization and cash position after the 2022 financing?** Securities,
   subsequent issuances, debt/leases, acquisitions and cash. Recommendation: preserve legal entity
   issue #18 while deciding economic ownership and financing first. Sensitivity: blocks every balance
   sheet, interest, tax, liquidity and ROIC result.

### B. Can estimate and later ratify

- Function-by-function ESS staffing and compensation bands.
- Foundry pricing, services mix, retention and gross-margin ranges.
- Atlas design-partner pricing and commercialization ramp.
- Willow annual R&D envelope and lab equipment lifecycle.
- Advisory utilization, rates, leverage and travel.
- Enterprise technology, cybersecurity and insurance envelopes.
- HQ size, owned/leased equivalents and operating costs, provided both tenure cases remain visible.

### C. Should remain open

- Proven reserves, exact mine life and production until technical evidence exists.
- Exact legal entities, tax elections and SPVs until issue #18 is resolved.
- Exact individual compensation, named J2 leaders and employee-level data.
- Smooth historical P&Ls between isolated canon anchors.
- ROIC and valuation until acquisition prices and invested-capital bases exist.

## External benchmark sources

- U.S. Bureau of Labor Statistics, [Employer Costs for Employee Compensation, March 2026](https://www.bls.gov/news.release/ecec.htm).
- U.S. Bureau of Labor Statistics, [May 2025 national occupational employment and wage estimates](https://www.bls.gov/news.release/ocwage.t01.htm).
- Berkshire Hathaway 2025 Form 10-K, [BNSF operating economics](https://www.sec.gov/Archives/edgar/data/1067983/000119312526083899/brka-20251231.htm) (large-rail directional analog, not a direct peer).
- Ur-Energy 2025 Form 10-K, [Wyoming uranium workforce and revenue-recognition context](https://www.sec.gov/Archives/edgar/data/1375205/000110465926025923/urg-20251231x10k.htm) (ISR operator; underground Red Wash requires different cost structure).
- Palantir 2025 Form 10-K, [industrial/data software gross-margin reference](https://investors.palantir.com/files/2025%20FY%20PLTR%2010-K.pdf) (upper-bound software analog, not a direct peer).

These external sources support ranges only. They do not establish Sable Harbor facts.
