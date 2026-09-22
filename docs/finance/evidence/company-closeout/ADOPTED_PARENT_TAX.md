# Adopted corporate history and statutory provision successor

**Document ID:** SH-COMPANY-PARENT-TAX-2026-09-15  
**Version:** 2.0.0  
**Current workpaper authored:** September 22, 2026 UTC  
**Acceptance:** Pending repository acceptance of the company edition.

## Controlling direction and scope

The owner adopted corporate taxation of the existing Delaware Sable Harbor, LLC and subsequently adopted a newly authored corporate-from-formation history. Legal identity, headquarters and ownership chain remain intact. The dated decision is `docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md`; formation/election precision is `source/parent_tax.json`. Formation/effective date April12,2016, preparation April14, modeled submission April18 and acknowledgment May20 are expressly authored fictional events, not recovered IRS records or real filings.

The current computation contract is `source/statutory_policy.json`. It supersedes the earlier separate-parent California reserve and aggregate deferred-liability realization simplifications in `source/parent_tax.json`, retaining that source's adopted history. Earlier memoranda remain in Git history; frozen financial releases retain their omission disclosures.

The edition uses the dated management-accrual basis in `ACCOUNTING_BASIS_SUCCESSOR.md`. It does not claim GAAP compliance or an audit opinion. The 2026 monthly income-tax provision uses an estimated annual statutory rate and annual source assumptions; conditional later-month inputs remain conditional. Accounting date is distinct from evidence availability.

## Historical and acquisition bridges

`historical_tax.py`, `tax_assets.py` and `rwh_history.py` reconstruct labeled fictional annual activity, asset cohorts, cash and tax adjustments. Parent historical tax cash is1,037,879.08; supported opening federal NOL is200,846,857.1429 before subsequent current-period changes. The2022 domestic research cohort remains on its adopted amortization schedule. Original initialization is distinguished from historical contributions and accumulated operating results.

Core goodwill is reduced by exactly30,000,000 against initialization equity, with no cash, deduction or replacement asset. The separate9,000,000 equipment cohort's book depreciation correction follows its authored2023 service date. Neither correction changes ARU's original14,762,500 book goodwill or13,000,000 tax-goodwill allocation.

The separate900,000 existing ARU facilitative transaction expense is capitalized for the conditional338 tax architecture. `acquisition_tax_costs.py` preserves original68,000,000 AGUB and55,000,000 non-goodwill allocation, adds900,000 residualClassVII basis and60,000 annual amortization. It does not add book goodwill or cash. The no-election alternative remains stock-basis treatment in the acquisition source memorandum. Original acquired587,500 DTA remains discoverable in the native PPA; subsequent valuation replacement affects expense, not historical opening equity.

## Filing populations and tax calculation

Five federal taxpayers are separate: SHI, SHIH, PS including disregarded RWH, ARU and BST. Financial consolidation does not establish a federal consolidated return. The adopted state unitary matrix supports CA/IL/WV combined reporting with member-specific factors and losses. PA's selected SHI receipt factor is zero; this does not remove Pennsylvania employment obligations.

`statutory_current.py` composes72 industrial/holding federal annual rows and270 member-state rows, alongside18 parent federal rows. `state_apportionment.py` supplies288 factor records. Source-specific cost recovery, research, interest limitation, acquisition timing, inventory absorption, depletion, unpaid transaction tax and conditional retention awards are reconciled before losses are used. CA suspension and Illinois year-specific loss limits are applied to their proper populations.

`statutory_deferred.py` provides360 current annual gross-DTA/DTL/valuation rows and15 historical opening rows. All gross DTAs have a full valuation allowance. Gross DTLs remain recognized; a closing DTL stock is not represented as a demonstrated year-by-year net reversal schedule. ARO, inventory and other competing deductions cannot silently support multiple benefits. Federal benefit of future state-tax differences is not claimed without a supporting realization schedule.

## Payment and publication contract

`statutory_posting.py` reverses native planning tax representations once and posts the statutory successor. Existing2026 industrial cash remains paid cash, with separate taxpayer prepayment assets where appropriate; no refund is invented. Each jurisdiction's credit applies only to that jurisdiction and taxpayer. Actual modeled state-tax cash feeds federal deductions; an unpaid provision is not a payment.

`statutory_build.py` reuses the native forecast's finite payment/funding engine, iterating annual current tax, monthly requests and settled-tax deductions to the whole-dollar cash boundary. Failure to converge blocks publication. Requests, payments, arrears, gross prepayments and liabilities remain separate. The resulting source workpapers, iteration receipt and payment allocations are emitted under `enterprise/generated/company-closeout-v1/statutory_*` by the same build as statements and seven-unit exports.

Final accepted amounts must be read from the clean edition's generated workpapers and identity manifest. This memorandum does not promote an intermediate build, submitted-return state or future cash assumption into accepted history.
