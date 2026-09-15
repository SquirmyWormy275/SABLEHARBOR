# Adopted parent corporate history and provision successor

Prepared September 15, 2026 UTC. Authority: SH-VOICE-TAX-01 and the subsequent
owner statement, **“Adopt corporate-from-formation history.”** This supersedes
the open initial-versus-prospective history selection in TAX_HISTORY.md. It does
not select a tax-consolidated group, a tax rate or a benefit. Repository state
remains pending acceptance until integration; the direction is owner-approved.

## Authored history and source precision

`enterprise/closeout/source/parent_tax.json` adopts the previously prepared
initial option: formation/effective date April 12, 2016; preparation April 14;
modeled Form 8832 submission April 18; modeled acknowledgement May 20. April 12
is newly authored precision within accepted year 2016. The acknowledgement is
also explicitly authored fiction, not recovered IRS evidence. California
qualification is modeled April 20, 2016. Legal name remains Sable Harbor, LLC;
subsidiary identities, ownership chains and governance remain intact. Preparation,
effective/submission/acknowledgement dates and September 15 authorship are distinct.

[IRS Form 8832, December 2013 revision](https://www.irs.gov/pub/irs-pdf/f8832.pdf),
accessed September 15, 2026, supports the initial election window. Six days from
formation to submission fits the ordinary window. No real filing or government
form replica is created. The preserved `industrial/source/entities.json` year
precision is superseded only for this dated authored implementation; frozen
releases retain their bytes and prior unresolved-parent-tax disclosures.

## Historical income and opening bridge

**Current historical successor:** [HISTORICAL_TAX_RECONSTRUCTION.md](HISTORICAL_TAX_RECONSTRUCTION.md)
completes the authored 2016–2022 event budgets and section 174 pool. It supersedes
the earlier pre-2023 exclusion and $7,200-only correction described below; current
generator output uses the reconstructed history and $1,037,879.0800 correction.
The following earlier workpaper paragraphs remain provenance, not current totals.

The actual isolated legacy PRIMARY_USD SHI population gives:

| Period | Revenue | Production cost | Book loss |
|---|---:|---:|---:|
| 2023 | $67,200,000 | $75,000,000 | $7,800,000 |
| 2024 | $85,700,000 | $95,000,000 | $9,300,000 |
| 2025 | $104,900,000 | $115,000,000 | $10,100,000 |

The adapter independently selects those historical source entries and derives
$27,200,000 book loss before the separately reconstructed tax depreciation below. These legacy
entries identify production/service costs, not a separately capitalized foreign
research pool. No extra 2022–2024 research asset is manufactured. Source cost
classification is a synthetic accounting premise, not external verification
that all historical software development costs were classified correctly.
Pre-2023 taxable-income/property-basis records remain incomplete: the model
claims no additional pre-2023 NOL deduction, not zero historical losses or zero
tax basis. The unknown older history does not reopen the approved election.

The source authors the $800 California minimum for 2017–2025 as previously paid
synthetic tax omitted from the calibration: $7,200 debit opening accumulated
deficit (3100), credit cash, dated as a successor opening correction. The first
qualification year is excluded. This is separate from the $30M noncash goodwill
correction and changes funding only through the real modeled cash reduction.
Additional historical federal/state tax, interest or penalties above this
supported minimum are not certified absent. Supporting 2016–2022 returns/basis
remain an explicit historical completeness residual, not silently forged returns.

Opening gross modeled NOL DTA, depreciable-asset DTL and valuation allowance are separately
posted. Only same-jurisdiction DTL reversal supports partial NOL realization. Historical cash-tax expense is not
converted into an unsupported additional loss carryforward. Individual member
capital accounts and contributed property bases are never inferred from the
$38.8M initialization equity or corrected $8.8M net initialization equity.

## Current provision method and tax differences

The build first composes runtime, operating, goodwill and FF-003 books, computes
the parent tax workpaper from that full pre-tax population, then rebuilds with
its tax journal/cash provider before Treasury funding. It retains pre-parent-tax
statements and monthly data, `parent_tax_provision.csv`, `parent_tax_history.json`
and a source-identified exact bridge. All legal, unit, consolidated statements,
CSV/SQLite exports and sovereignty metrics use the rebuilt books. Legacy tax
alternatives remain unposted comparisons based on the retained pre-tax input.

- **Federal:** 21% statutory rate; apply the post-2017 80% NOL limit. Current
  interest is limited by 30% of ATI with post-2024 depreciation addback, and
  disallowed interest carries forward. No small-business exception or invented
  inherited interest balance is used. [2025 Form 1120 instructions](https://www.irs.gov/instructions/i1120)
  and [2025 Form 8990 instructions](https://www.irs.gov/instructions/i8990),
  accessed September 15, 2026. Future scenario years hold reviewed law constant.
- **Research:** represented parent projects operate at US sites; the authored
  edition contains no foreign-performed research. Current BIZ_RESEARCH and
  LEG_6000 expenses remain domestic current deductions under section 174A.
  Foreign work, if introduced, requires the separate 15-year pool and must not
  inherit this zero foreign population. The model does not claim research
  credits. [IRS Revenue Procedure 2025-28](https://www.irs.gov/irb/2025-38_IRB)
  and [2025 FTB research-credit instructions](https://www.ftb.ca.gov/forms/2025/2025-3523-instructions.html),
  accessed September 15, 2026; California does not adopt the federal 2022
  mandatory research amortization change described in those instructions.
- **Depreciation:** `parent_tax_assets.csv` reconstructs existing owned-asset cost
  and source purchase events. The $9M legacy equipment cost has newly authored
  purchase December 31, 2022 and first service January 1, 2023; seven-year
  equipment class and a straight-line election for the residual after 80%
  bonus are expressly authored characterization. This yields $7,842,857.1429
  pre-2026 federal deductions and $3,857,142.8571 California deductions. No
  purchase price, new business acquisition or cash transaction is added.
  Subsequent existing new-equipment purchases receive federal 100% bonus under
  the post-January-19-2025 acquisition rule; source acquisition/service months
  are retained. California corporations use straight-line estimated useful
  lives: source asset life where available, 48 months runtime equipment,
  60 months later legacy purchases and 84 months opening equipment. This is
  California corporate straight-line, not federal MACRS. Land, construction in
  progress and internal same-entity transfers receive no extra deduction.
  [IRS Publication 946](https://www.irs.gov/publications/p946),
  [2026 bonus depreciation guidance](https://www.irs.gov/irb/2026-06_IRB), and
  [2025 California corporate Form 3885 instructions](https://www.ftb.ca.gov/forms/2025/2025-3885-instructions.html),
  accessed September 15, 2026. Book DDA is added back and these separate tax
  deductions are applied once. Closing book carrying amounts, original costs,
  deductions and tax bases are exported by cohort and annual jurisdiction.
- **Credit/inventory:** allowance movement is added back separately from modeled
  specific write-offs/recoveries; inventory impairment is added back pending
  supported tax disposition. Their temporary-difference exposures carry full
  allowances. The source does not infer bad-debt relief merely from zero AR.
- **Intercompany:** remove source book-only service allocation charges/revenue
  from parent taxable income pending tax characterization. Financial
  eliminations do not establish a tax group. Other supported parent operating
  income/costs are included in its own federal workpaper. ARU's $14.7625M book/
  $13M tax goodwill and its independent tax model remain untouched.
- **Valuation allowance:** gross loss, interest and allowance/impairment
  deferred balances are reserved except NOL realization supported by the same
  jurisdiction's asset DTL reversal. Federal support is capped at 80% of that
  DTL because of the NOL limitation; California support is capped at the full
  corresponding DTL. This does not rely on conditional forecast profitability.
  DTA, DTL and valuation allowance changes reconcile through separate journals;
  no automatic goodwill DTA arises. The California balances remain within the
  expressly provisional parent state perimeter described below.

## California combined-report and geographic conclusion

California analysis cannot stop at a separate-parent 100% scenario. The current
facts support substantial unitary indicators: SHI owns SHIH wholly, which owns
PS and ARU wholly; PS owns RWH and ARU owns BST; centralized executive management,
ESS/accounting, financing, parent support and intercompany logistics connect
operations. Distinct software/mining/rail activity does not itself negate the
contribution/dependency test. SHIH's intermediate holding function is not a
sufficient reason to exclude it.

Primary authorities, accessed September 15, 2026:
[FTB 2024 Publication 1061](https://www.ftb.ca.gov/forms/2024/2024-1061-publication.pdf),
[Legal Ruling 1995-7](https://www.ftb.ca.gov/tax-pros/law/legal-rulings/1995-7.html),
[Legal Ruling 1995-8](https://www.ftb.ca.gov/tax-pros/law/legal-rulings/1995-8.html),
and [2025 Schedule R instructions](https://www.ftb.ca.gov/forms/2025/2025-100r-instructions.html).
These require examining actual unitary facts and apportionment; a federal
consolidation election is not necessary for California combined reporting.

The working applicability conclusion is that SHI/SHIH/PS-RWH/ARU/BST require a
combined-report analysis from their respective acquisition/ownership periods.
Sacramento headquarters and California qualification establish parent California
review. Wyoming mine/rail/logistics operations and Pennsylvania research sites
preclude treating all represented operations as physically Californian. FF-003
is a specific California customer, not the whole company's sales factor.
Customer market sourcing, group state modifications and appropriate factors
are not supplied by headquarters location or unit names.

Accordingly the posted California **cash** plan uses only the supported parent
$800 minimum. Any positive excess in the unallocated 100%-parent case is placed
in a distinct `CO_TAX_STATE_RESERVE`, not certified current state assessment,
not remitted and not deducted federally. This explicit conservative reserve is
not proof of full group liability coverage. Parent state NOLs remain workpaper
amounts subject to combined-report and allocation reconciliation. California
2024–2026 suspension above the $1M threshold is applied to the separate-parent
case; no federal 80% limit is imported into the California case.
[FTB 2024 Form 3805Q instructions](https://www.ftb.ca.gov/forms/2024/2024-3805q-instructions.html).

This is a material state-provision limitation for a full enterprise tax opinion;
it is not an owner preference or authorization request. Finance/legal must join
actual market/geography populations and other entities' state adjustments,
reconcile the combined report and replace the unallocated reserve with a scoped
successor. No separate-parent CA filing election has been invented.

## Payment and filing states

The annual modeled federal provision is allocated over four equal April/June/
September/December installments; California minimum follows 30/40/0/30. The
modeled planning date is the 15th, subject to actual year-specific due-day and
safe-harbor review. These are explicitly authored conditional cash plans, not
real remittances or assertions that interim over/underpayments meet law. Cash
settlement reduces provision payables once; no automatic refund or disposal of
the unallocated state reserve occurs. Actual filing preparation/submission/
acknowledgement evidence remains separate from cash plan entries.

The adopted corporate history is implemented; a complete federal tax-basis and
multi-jurisdiction filing/provision conclusion remains bounded by the identified
historical/state population residuals. These are accurately disclosed limits,
not an unchanged “C-corporation undecided” status.
