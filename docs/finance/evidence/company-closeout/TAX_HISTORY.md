# Parent tax history and filing boundaries

Prepared September 15, 2026 UTC. SH-VOICE-TAX-01 selects corporate taxation of
Sable Harbor, LLC. Implementation workpaper, pending acceptance; no real filing.

## Tested source facts

`industrial/source/entities.json`: Delaware LLC formed 2016, year precision;
Sacramento headquarters and synthetic California foreign qualification; parent
federal tax status explicitly unresolved. SHIH and PS are corporations. RWH
remains PS's separate Wyoming legal operator with derived disregarded treatment.
ARU acquisition January 7, 2026 retains assumed S eligibility and pre-close BST
QSub treatment, followed by post-close C treatment; intended 338(h)(10) election
is conditional and filing-ready, not submitted. Financial consolidation does
not authorize a consolidated federal return or California combined report.

The 2021/2022 board records supply approximate financing and governance, not
tax elections, historical returns, member outside bases or a tax closing ledger.
The 2023 opening calibration is not a reconstruction of the 2016 contributions.
The $38.8M opening book equity, corrected to $8.8M for the unsupported goodwill,
is not tax basis and cannot substitute for contributed property tax basis.

## Primary authority reviewed

All links accessed September 15, 2026. These establish rules; none acknowledges
an SH filing. Applicable filing-year instructions remain necessary before actual
filing-year calculations; future instructions are not represented as published.

- [IRS Form 8832, December 2013 revision](https://www.irs.gov/pub/irs-pdf/f8832.pdf):
  corporate classification election; ordinary effective window 75 days before
  through 12 months after submission. Preparation, requested effective date,
  modeled submission and acknowledgement are separate states.
- [IRS LLC repercussions](https://www.irs.gov/businesses/small-businesses-self-employed/limited-liability-company-possible-repercussions):
  partnership-to-corporation election deems assets/liabilities contributed for
  stock, followed by partnership liquidation. Initial formation-effective
  election is distinguished from later classification changes.
- [2025 Form 1120 instructions](https://www.irs.gov/instructions/i1120):
  corporation return/provision starting point and generally fourth/sixth/ninth/
  twelfth-month estimated payments. A generic quarter-end book payment model is
  not this statutory calendar.
- [2025 California Form 100 instructions](https://www.ftb.ca.gov/forms/2025/2025-100-booklet.html):
  8.84% ordinary C-corporation rate, $800 minimum with stated exceptions;
  qualification/doing business and state adjustments govern applicability.
  Headquarters supports evaluating California; Delaware formation does not
  establish Delaware taxable operating income or eliminate other state nexus.
- [IRS Form 8023 instructions](https://www.irs.gov/instructions/i8023):
  joint election and S-shareholder participation requirements; ordinary deadline
  fifteenth day of ninth month after acquisition. January 7 gives October 15,
  2026. Preserve eligibility/signature conditions and no submission inference.

## Researched implementation alternatives, not owner preference questions

1. **Newly authored initial-election history in 2016.** Retains LLC legal identity
   and implements the selected direction throughout modeled history, avoiding a
   2026 classification transition. Exact formation/election/submission dates
   would be fictional completion, not recovered facts. It also assigns historical
   income/loss taxation to the company instead of members for all pre-2026 years;
   that is a substantive historical consequence. Supporting initial contribution
   tax basis, prior returns, earnings/profits, losses and state history would need
   a coherent newly authored schedule. Existing financing cash may not be treated
   as income simply because it is received after an election.
2. **Prospective election with existing pre-election history.** Retains LLC and
   avoids claiming recovered 2016 corporate taxation, but requires determining
   prior default/elected classification and the tax bases/liabilities entering
   the deemed transaction. A convenient January 1 or voice date is not selected.
   Nominal book net assets cannot measure transition gain, member consequences or
   carryover bases. Missing outside basis and property basis are material here.

Neither route is blocked by a missing account number. The unresolved consequence
is assignment of historical taxable results and transition/basis effects, for
which the accepted source supplies no amounts. Choosing initial history solely
to make those liabilities disappear would be unsupported. A reviewer can accept
a fully authored initial corporate history only with reconciled underlying
historical tax books; this lane has not completed that evidence. No broad owner
approval is required for ordinary fictional drafting; no question reopens C tax.

## Period/entity filing register at this boundary

| Entity/period | Classification and filing unit | Current evidence state / next calculation |
|---|---|---|
| SHI 2016–2026 | Corporate direction selected; effective history unresolved | No return/submission asserted; reconstruct tax basis and election chronology before provision |
| SHI successor 2027–2031 | C treatment intended; no consolidated group inferred | Compute separate federal/state taxable income, NOL limits, valuation allowance, taxes and funding after history bridge |
| SHIH from formation | C corporation; separate legal taxpayer | Shared services and acquisition-cost deductions require tax characterization; book elimination is not tax elimination |
| PS / RWH | PS C corporation; RWH disregarded for income-tax source treatment | Keep RWH legal/payroll/regulatory obligations distinct; jurisdiction activity census remains required |
| ARU through acquisition | Conditional S status / joint 338 election | Track short-period and deemed-sale mechanics separately from economic January 1–6 stub |
| BST pre-close | Conditional QSub | Separate legal identity retained; QSub termination review remains |
| ARU/BST post-close | C treatment in accepted acquisition model | Preserve modeled $13M tax goodwill / $14.7625M book goodwill and quarterly cash convention; filing-ready is not filed |

No current-tax zero, tax saving or automatically realizable deferred-tax asset
is concluded. Removal of unsupported Core goodwill creates no tax basis or
amortization. ARU remains governed by its independent conditional allocation.
Historical tax omissions remain discoverable in preserved sources and are not
silently reclassified as tax-free operations.

## Authored executable alternatives and quantified consequence

`enterprise/closeout/source/tax_options.json` now prepares both histories with
explicit dates and provenance. Initial option: newly authored formation April
12, 2016; preparation April 14; modeled submission April 18; requested effective
formation date. Source only establishes year 2016. This ordinary precision is
expressly an authored option, not a recovered certificate or owner selection.
Prospective option: prepare September 15, planned submission September 16,
requested effective October 1, 2026, using the next monthly accounting boundary.
Both are within the ordinary Form 8832 window. Neither has an acknowledgement.
No alteration to the underlying year-precision legal entity source occurs.

`python -m enterprise.closeout.tax_sensitivity enterprise/generated/company-closeout-v1`
produces 216 explicit workpaper rows: two histories, three operating cases,
California apportionment 0/100% cases, initial-history opening federal post-2017
NOL $0/$10M cases, and deductible/addback FF-003 alternatives. No row is posted.
Each uses emitted parent book P&L, federal 21%, the 80% post-2017 loss limitation,
California 8.84% and the $800 minimum as a conservative annual sensitivity. The
prospective initial short period may have a first-year exception; $800 is not a
resolved first-year legal assessment. Pre-election income is excluded from that
option's corporate workpaper, not erased from company books or member duties.
Amounts are rounded to cents with Decimal half-even for reports; calculations
retain Decimal precision.

The calculation makes current state tax deductible federally, carries federal/
state losses separately, and computes gross NOL DTA with a matching full valuation
allowance. No benefit is recognized from unsupported future profit projections.
Gross deferred expense and the allowance change offset explicitly. The report
holds other book-tax differences at zero only for sensitivity; no conclusion on
research capitalization, depreciation, interest, fees or member basis follows.
No unsupported transition gain is inserted as zero into the accounting ledger.

Base case, zero opening NOL, 100% California apportionment, FF-003 deductible:

| Year | Initial-history parent book income | Prospective corporate-period income | Current tax sensitivity, either option |
|---|---:|---:|---:|
| 2026 | -$10,502,666.6668 | -$2,805,500.0001 | $800.00 |
| 2027 | -$14,812,689.6979 | same | $800.00 |
| 2028 | -$9,194,675.2226 | same | $800.00 |
| 2029 | $20,130.9438 | same | $1,611.90 |
| 2030 | $9,890,024.4206 | same | $416,147.43 |
| 2031 | $15,499,703.8188 | same | $651,753.96 |

The 2026 corporate-loss population differs by $7,697,166.6667, attributable to
January–September classification, before unknown book-tax differences. Closing
2031 federal loss carryforward is $14,186,464.24074 under initial history versus
$6,489,297.57404 under prospective history in this sensitivity. Current tax is
equal in these selected base rows because both retain enough losses for the 80%
limit; equality does not establish equivalent member consequences or tax basis.
Neither creates a goodwill deduction. The initial option still needs 2016–2025
reconstruction; the prospective option needs September 30 tax contribution bases
and prior member treatment. Those are the precise remaining affected claims.

Additional primary support, accessed September 15, 2026:
[2025 Form 1120 NOL instructions](https://www.irs.gov/instructions/i1120)
and [California 2024 FTB 3805Q instructions](https://www.ftb.ca.gov/forms/2024/2024-3805q-instructions.html)
(the latter describes 2024–2026 suspension at income of $1M or more).
[FTB combined-report guidance](https://www.ftb.ca.gov/forms/2024/2024-1061-publication.pdf)
shows that unitary-business combined reporting needs analysis; the 0/100%
separate-parent cases are therefore sensitivity bounds, not an elected separate
California filing architecture. Source versions are retained in links; future
years use a constant-law scenario, not unpublished future filing instructions.
