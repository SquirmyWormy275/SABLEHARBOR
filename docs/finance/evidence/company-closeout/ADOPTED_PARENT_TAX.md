# Adopted corporate history and statutory provision successor

**Document ID:** SH-COMPANY-PARENT-TAX-2026-09-15
**Version:** 2.0.0
**Current workpaper authored:** September 22, 2026 UTC
**Acceptance:** Pending repository acceptance of the company edition.

## Controlling direction and scope

The owner adopted corporate taxation of the existing Delaware Sable Harbor, LLC and subsequently adopted a newly authored corporate-from-formation history. Legal identity, headquarters and ownership chain remain intact. The dated decision is [docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md](../../../../docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md); formation/election precision is [source/parent_tax.json](../../../../enterprise/closeout/source/parent_tax.json). Formation/effective date April 12, 2016, preparation April 14, modeled submission April 18 and acknowledgment May 20 are expressly authored fictional events, not recovered IRS records or real filings.

The current computation contract is [source/statutory_policy.json](../../../../enterprise/closeout/source/statutory_policy.json). It supersedes the earlier separate-parent California reserve and aggregate deferred-liability realization simplifications in [source/parent_tax.json](../../../../enterprise/closeout/source/parent_tax.json), retaining that source's adopted history. Earlier memoranda remain in Git history; frozen financial releases retain their omission disclosures.

The edition uses the dated management-accrual basis in [ACCOUNTING_BASIS_SUCCESSOR.md](ACCOUNTING_BASIS_SUCCESSOR.md). It does not claim GAAP compliance or an audit opinion. The 2026 monthly income-tax provision uses an estimated annual statutory rate and annual source assumptions; conditional later-month inputs remain conditional. Accounting date is distinct from evidence availability.

## Historical and acquisition bridges

[historical_tax.py](../../../../enterprise/closeout/historical_tax.py), [tax_assets.py](../../../../enterprise/closeout/tax_assets.py) and [rwh_history.py](../../../../enterprise/closeout/rwh_history.py) reconstruct labeled fictional annual activity, asset cohorts, cash and tax adjustments. Parent historical tax cash is 1,037,879.08; supported opening federal NOL is 200,846,857.1429 before subsequent current-period changes. The 2022 domestic research cohort remains on its adopted amortization schedule. Original initialization is distinguished from historical contributions and accumulated operating results.

Core goodwill is reduced by exactly 30,000,000 against initialization equity, with no cash, deduction or replacement asset. The separate 9,000,000 equipment cohort's book depreciation correction follows its authored 2023 service date. Neither correction changes ARU's original 14,762,500 book goodwill or 13,000,000 tax-goodwill allocation.

The separate 900,000 existing ARU facilitative transaction expense is capitalized for the conditional section 338 tax architecture. `acquisition_tax_costs.py` preserves original 68,000,000 AGUB and 55,000,000 non-goodwill allocation, adds 900,000 residual Class VII basis and 60,000 annual amortization. It does not add book goodwill or cash. The no-election alternative remains stock-basis treatment in the acquisition source memorandum. Original acquired 587,500 DTA remains discoverable in the native PPA; subsequent valuation replacement affects expense, not historical opening equity.

## Filing populations and tax calculation

Five federal taxpayers are separate: SHI, SHIH, PS including disregarded RWH, ARU and BST. Financial consolidation does not establish a federal consolidated return. The adopted state unitary matrix supports CA/IL/WV combined reporting with member-specific factors and losses. PA's selected SHI receipt factor is zero; this does not remove Pennsylvania employment obligations.

`statutory_current.py` composes 72 industrial/holding federal annual rows and 270 member-state rows, alongside 18 parent federal rows. `state_apportionment.py` supplies 288 factor records. Source-specific cost recovery, research, interest limitation, acquisition timing, inventory absorption, depletion, unpaid transaction tax and conditional retention awards are reconciled before losses are used. CA suspension and Illinois year-specific loss limits are applied to their proper populations.

`statutory_deferred.py` provides 360 current annual gross-DTA/DTL/valuation rows and 15 historical opening rows. All gross DTAs have a full valuation allowance. Gross DTLs remain recognized; a closing DTL stock is not represented as a demonstrated year-by-year net reversal schedule. ARO, inventory and other competing deductions cannot silently support multiple benefits. Federal benefit of future state-tax differences is not claimed without a supporting realization schedule.

## Payment and publication contract

`statutory_posting.py` reverses native planning tax representations once and posts the statutory successor. Existing 2026 industrial cash remains paid cash, with separate taxpayer prepayment assets where appropriate; no refund is invented. Each jurisdiction's credit applies only to that jurisdiction and taxpayer. Actual modeled state-tax cash feeds federal deductions; an unpaid provision is not a payment.

`statutory_build.py` reuses the native forecast's finite payment/funding engine, iterating annual current tax, monthly requests and settled-tax deductions to the whole-dollar cash boundary. Failure to converge blocks publication. Requests, payments, arrears, gross prepayments and liabilities remain separate. The resulting source workpapers, iteration receipt and payment allocations are emitted under `enterprise/generated/company-closeout-v1/statutory_*` by the same build as statements and seven-unit exports.

Final accepted amounts must be read from the clean edition's generated workpapers and identity manifest. This memorandum does not promote an intermediate build, submitted-return state or future cash assumption into accepted history.

## Historical ROT performance failure

The H2 2025 utility receipt-tax population remains unpaid. Its $646,624.38 book accrual includes amounts not yet collected; the $441,346.80 collected-tax population supports the separate penalty workpaper. The new penalty/interest liabilities total $69,137.56 at August 31, 2026 and $70,322.54 at the September 14 event cutoff. Opening December 31, 2025 accrual is separately bridged to current expense. Neither tax principal nor cash is posted twice.

Penalties are added back for income tax. Corporate interest accrues economically and enters the section 163(j) business-interest calculation; it is not automatically deferred until cash payment under the underlying tax's payment rule. Historical negative adjusted taxable income leaves an interest carryforward. California's separate treatment and the Illinois/West Virginia federal-conforming interest carry are tracked explicitly. Gross deferred benefits remain fully reserved.

For 2027–2031 the unpaid historical principal continues to generate interest under an expressly conditional held 7% planning rate. This is not a claim about future published statutory rates. The H2 workpaper covers only its own receipts; the separate 2026 due/receipt reconciliation below prevents extrapolation or double counting.

The separate completed January–August 2026 receipt workpaper resolves the accelerated-installment population. It preserves $23,950,000 customer cash and the August June/July FIFO collected-tax result of $167,698.94. The 2026 receipt-tax principal is $1,243,161.07, including collection of previously accrued opening receivables; none is posted again as tax expense. At September 14, $1,147,309.29 is due and unpaid, while the $95,851.78 August return remainder is due September 21.

The separate 2026 duty population adds $136,207.67 penalties/interest at August 31 and $141,084.28 at September 14. Combined with H2 2025 duties, total penalties/interest are therefore $205,345.23 and $211,406.82 respectively. Accelerated installments and monthly remainders are disjoint, preventing duplicate late-payment penalties. Later conditional months are not promoted into this completed receipt population. Future interest on these already established unpaid duties uses the disclosed held-rate assumption.

January–July 2026 uses the expressly selected permitted current-month method: four 22.5% installments and a 10% return remainder. August uses the supported same-prior-month alternative. Red Wash’s continuing legal operator predates the acquisition; missing pre-acquisition returns are not treated as zero tax. These are modeled amounts under the selected lawful administrative method, not an assertion of the smallest possible penalty under an unknown alternative.
