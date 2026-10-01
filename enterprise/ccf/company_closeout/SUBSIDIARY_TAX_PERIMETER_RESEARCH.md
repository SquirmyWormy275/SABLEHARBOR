# Subsidiary and state income-tax implementation contract

Document ID: SH-C05-TAX-PERIMETER-20260915. Version 1.0.0.
State: PENDING_REPOSITORY_ACCEPTANCE. Prepared September 15, 2026 UTC.
Origin: newly authored synthetic company analysis with primary-authority research.
This supplements the closeout's transaction-tax facts; finance owns calculations,
journals and the filing calendar. No federal consolidated-return election, new
entity, government filing, acknowledgement or tax-sharing agreement is created.
The release commit timestamp bounds actual availability; the preparation date is
not proof that this analysis was available earlier that day.

## Federal taxpayers and timing

- The accepted entity register identifies PS as a corporation and RWH as its
  wholly owned disregarded LLC. Include RWH income-tax items on PS's return,
  eliminating PS–RWH internal charges for this purpose. Preserve separate legal
  books, payroll employer and certain excise duties. This treatment follows
  [IRS single-member LLC guidance](https://www.irs.gov/businesses/small-businesses-self-employed/single-member-limited-liability-companies)
  and [Illinois's owner-return rule](https://tax.illinois.gov/questionsandanswers/answer.604.html).
- SHI, SHIH, PS, ARU and BST remain separate federal corporation taxpayers in
  the no-consolidated-election architecture. ARU and BST's post-QSub losses do
  not automatically offset one another. Federal corporate tax is 21% of the
  properly computed taxable base, not the retained 18% RWH or 25% ARU scenario
  provision. [26 USC 11](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section11&num=0&edition=prelim).
- The accepted [ARU memorandum](../../../industrial/transaction/07_ARU_TAX_STRUCTURE_MEMORANDUM.md)
  already separates the January 1–6 economic closing stub from tax reporting.
  For the intended valid section 338 election, the January 7 acquisition-date
  deemed sale belongs to old target; new target begins January 8. Preserve the
  distinct no-election transition rather than labeling both January 7. All four
  S sellers must join the election; its October 15, 2026 deadline remains future
  due at cutoff. Filing-ready is not filed. The QSub assets enter the old-ARU
  model; this is not a separate BST section 338 election.
  [Form 8023 instructions, October 2023](https://www.irs.gov/instructions/i8023),
  [Form 8883 instructions, October 2017](https://www.irs.gov/instructions/i8883).
- Preserve the original $14,762,500 book goodwill, $13,000,000 conditional tax
  goodwill and $587,500 conditional acquisition reserve DTA. Subsequent rate or
  realizability reassessment needs a dated bridge; it does not rewrite opening
  acquisition bytes. Failed election leaves the alternative basis case relevant.
  Allocating deductions between ARU and BST requires the asset's legal/tax owner,
  not the financial ARU_GROUP subtotal.

The current-tax bridge must add back book-only closure/ARO accruals without
performed services. Acquired contingent-liability settlements can increase basis
rather than become immediate expenses, as the accepted ARU memorandum explains.
Likewise seller ROT booked but unpaid is not an automatic federal deduction:
economic performance for taxes generally occurs on payment. Apply any
recurring-item exception only with documented method and subsequent timing facts.
These are separate bridges from the sales-tax principal/payable computation.
[IRS 2007-4, service economic performance](https://www.irs.gov/irb/2007-04_IRB),
[IRS 2018-22, section 1.461-4(g)(6)](https://www.irs.gov/irb/2018-22_IRB).

## Illinois: nexus, receipts and unitary boundary

The accepted annual mine contracts deliver to an Illinois converter, with title
passing after receipt/final assay. The current transaction-tax successor newly
specifies Metropolis for the existing receiver and rejects unsupported utility
resale. That is not an acquisition or a new mine site. The separate September
200 lb shipment remains RWH-owned inventory at the external toll converter; it
is not customer revenue or evidence of the annual 500,000 lb sales population.
See [transaction-tax facts](industrial_transaction_tax.json) and
[shipment qualification](september_shipment_qualification.json).

Treat PS's deliberate title-retained toll-processing inventory as an activity
beyond order solicitation in the selected 2026 model. This is a factual application,
not an Illinois ruling. Do not test de minimis merely as 200/500,000 pounds: the
question is the character and regularity of the in-state business activity.
The directly relevant March 16, 2026
[IDOR IT 26-0001 GIL](https://taxarchive.illinois.gov/content/dam/soi/en/web/taxarchive/research/legal/letter-rulings/income-tax/2026/it26-0001-gil.pdf)
discusses retained inventory at a contract packager and quotes the regulation's
whole-taxable-year consequence for activity exceeding solicitation. It is
nonbinding and does not decide SH's facts. Direct regulation retrieval failed
with gateway/certificate errors; the primary GIL reproduces the relevant
100.9720(c)(2)(A) rule. Do not represent the entire regulation as freshly recovered.

Corporation rates are 7% income plus 2.5% replacement tax, on the respective
Illinois bases after state modifications/apportionment/loss rules, not gross
receipts. [IDOR rates](https://tax.illinois.gov/research/taxrates/income.html).
RWH follows PS for income tax, while RWH remains the sales-tax legal seller.
Illinois-delivered mine sales require an Illinois receipts-factor determination
under [IITA 304](https://www.ilga.gov/legislation/ILCS/details?ActID=577&ActName=Illinois+Income+Tax+Act.&ChapAct=35+ILCS+5%2F&Chapter=&ChapterID=8&MajorTopic=&SeqEnd=7200000&SeqStart=6600000).
A buyer's eventual fuel use elsewhere does not itself move this seller's accepted
converter delivery. Freight has a distinct transportation receipts/mileage rule;
no ARU/BST uranium haul or Illinois railway miles are invented.

A PS-only 9.5% calculation is insufficient without a unitary analysis. The
[2025 Schedule UB instructions, revision March 2026](https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/documents/currentyear/business/miscellaneous/schedule-ub-instr.pdf)
require the Finnigan approach for years ending on/after December 31, 2025,
including Illinois sales of non-taxable unitary members when another member has
nexus. Different apportionment formulas no longer automatically exclude a member
(after 2017); follow the prescribed subgroup computations, including transportation.
Common ownership alone is insufficient: document functional integration,
centralized management and economies of scale. Accepted source facts supporting
review include the PS/RWH vertical operating platform, SHIH's acquisition/capital
oversight, parent treasury and service allocations, and ARU/BST integrated
logistics. Routine common accounting or one board alone does not establish that
all seven disparate capabilities constitute one unitary business. Record the
conclusion and entity/subgroup populations before final state tax measurement.

## California member rules

Preserve each member's California NOL register and origination years; SHI's
historical NOL cannot simply absorb another member's apportioned income. A
combined report is a computation method, distinct from electing a group return.
[FTB 3805Q, 2024 instructions, combined reporting](https://www.ftb.ca.gov/forms/2024/2024-3805q-instructions.html)
and [FTB 1061, 2024](https://www.ftb.ca.gov/forms/2024/2024-1061-publication.pdf).
Apply the period-specific 2024–2026 suspension and relevant income exception
already researched by finance; a current loss does not erase the member register.

Each corporation incorporated, qualified or doing business in California generally
owes at least $800, subject to the first-taxable-year incorporated/qualified
exception. Zero external receipts is not zero nexus: PS's 12 California platform
employees matter. SHIH's actual central management domicile must be explicit;
Delaware incorporation is not California registration evidence. If finance authors
ordinary first-year qualification facts for PS2025/SHIH2024, label them synthetic
and preserve evidence dates. They support only the corresponding first year,
not a recurring minimum exemption. [FTB corporations](https://www.ftb.ca.gov/file/business/types/corporations/index.html).

## Pennsylvania and West Virginia

PA employee presence supports SHI filing review even if selected customer receipts
are zero. Its 2026 corporate rate is 7.49%, 2027 6.99%, then decreases by 0.5
percentage points annually to 4.99% in 2031. Apportionment ordinarily uses sales;
20 employees do not create a 20/431 receipts fraction.
[PA corporate tax](https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/corporation-taxes/corporate-net-income-tax).
Under [Act 56 of 2024](https://www.legis.state.pa.us/WU01/LI/LI/US/HTM/2024/0/0056..HTM),
pre-2025 losses retain the 40% income limitation. The additional capacity for
post-2024 losses rises to total 50% in 2026, 60%2027, 70%2028, 80%2029 onward;
do not apply 50% to the entire historical loss pool. A zero PA numerator requires
complete customer destination evidence, not missing addresses.

WV's corporate rate is 6.5%. Since 2022 ordinary apportionment is single sales;
TPP follows purchaser receipt (including a designated recipient) rather than
manufacturing location. The authored August Cradle refiner receipt is WV, but
one $60,000 invoice does not establish every month's destination.
[WV 11-24-7](https://code.wvlegislature.gov/11-24-7/),
[WV tax-law report 51](https://tax.wv.gov/Documents/Legal/TaxLawReports/TaxLawReport.51.pdf).
WV requires unitary combined reporting from 2009, with default water's-edge scope
absent a worldwide election. Do not infer SHI-only filing from the federal model.
[11-24-13a(j)](https://code.wvlegislature.gov/pdf/11-24-13a/),
[11-24-13f](https://code.wvlegislature.gov/11-24-13f/).

Add back federal NOL and compute the WV-specific apportioned carryforward.
The [2023 CIT-120 instructions](https://tax.wv.gov/Documents/CIT/2023/cit120.instructions.2023.pdf)
limit deduction to eligible WV business/filing-year losses, distinguish member
SRLY restrictions, and describe indefinite carryforward for post-2017 losses
with an 80% deduction limit from 2022. An old federal NOL alone establishes no
WV deduction. The corporate annual return is generally due the fifteenth day of
the fourth month after year-end under
[11-24-13](https://code.wvlegislature.gov/11-24-13/).

## Handoff and validation requirements

Finance must publish legal taxpayer, state group/subgroup, tax period, taxable
base adjustments, member NOL origin/use, receipts numerator/denominator, enacted
rate and current/deferred/cash-tax bridges. Model state payments, federal deduction
timing and reciprocal tax allocations consistently; no financing plug or assumed
payment offsets a new liability. The source 18%/25% scenario tax remains historical
and is reversed/replaced exactly once in the successor. This research does not
claim those calculations are implemented.

Primary URLs above were accessed September 15, 2026 UTC. IRS dated instructions,
WV statutory effective clauses, PA enacted Act56 and Illinois 2025/2026 materials
supply the period boundaries; current landing pages corroborate them. Where a
full normative source was unavailable, that limitation is stated at the dependent
conclusion. No private evaluator material is included.
