# Adopted parent corporate-tax history and provision

**Document ID:** SH-COMPANY-PARENT-TAX-2026-09-15
**Version:** 1.0.0
**Prepared:** September 15, 2026 UTC
**Status:** Reviewable implementation; repository acceptance follows the company release process.

## Adopted history and legal identity

The owner adopted corporate-from-formation history for **Sable Harbor, LLC**, retaining its Delaware LLC identity. The source supplies formation at year precision in 2016. The successor expressly authors April 12, 2016 formation/election effectiveness, April 14 preparation, April 18 modeled Form 8832 submission and May 20 modeled acknowledgement. These are synthetic history, not recovered documents or real IRS actions. No federal consolidated-return election or legal conversion is inferred.

The election and period distinctions are recorded in `enterprise/closeout/source/parent_tax.json` and the central company-closeout decision. The generated filing register distinguishes preparation, submission, acknowledgement and future duties. Subsidiaries retain their own legal identities and conditional acquisition-election states.

## Historical reconstruction and opening bridge

`HISTORICAL_TAX_RECONSTRUCTION.md`, `historical_tax.py` and the generated annual/event schedules reconstruct 2016–2022 revenue, specified cost components, the existing 2021/2022 financing, the existing debt draw and equipment purchase. Solved cash constraints are labeled separately from recovered facts and newly authored events. A cash-use residual is not automatically a tax loss.

The reconstructed 2016–2025 federal/state tax cash is **$1,037,879.0800**. One opening 2026 journal corrects historical cash and retained earnings by that amount. The reconstructed federal NOL entering 2026 is **$200,846,857.1429**, including the separately supported 2023–2025 cash-cost losses, tax depreciation, 2022 research-pool amortization and $2,400 paid California minimum-tax deduction. Historical returns/payment events are synthetic, with their evidence states retained.

The 2022 domestic research pool is $40 million: $4 million amortization in 2022, $8 million annually in 2023–2026, and $4 million in 2027. The model continues the existing amortization schedule; it does not claim an acceleration election. Current domestic research follows section 174A; no foreign research expenditure is authored. The remaining opening research basis is $12 million.

## Assets, goodwill and deferred tax

`parent_tax_assets.csv` contains source-derived equipment cohorts, separate federal/California deductions and closing bases. The original $9 million equipment cohort is newly assigned a January 2023 service date and seven-year life. Its omitted book depreciation is corrected separately: opening accumulated depreciation **$3,857,142.8571**, followed by monthly depreciation through 2029. This correction is noncash and does not duplicate payroll or production cash costs.

The **$30 million unsupported Core goodwill correction** is a separate source-initialization equity correction with no inferred tax basis, deduction or deferred tax. ARU's distinct initial $14,762,500 book goodwill, $13 million conditional tax goodwill and acquisition reserve DTA remain protected; subsidiary statutory remeasurement requires its own bridge.

Gross deferred assets, liabilities and valuation allowances remain visible. The parent recognizes NOL realization only to the extent supported by same-jurisdiction asset-liability reversals and applicable utilization limits. Unsupported future profitability does not justify recognizing a benefit. The historical research pool, disallowed interest and unremitted transaction taxes have separately tracked temporary differences.

## Current implemented computation and remaining state perimeter

`parent_tax.py` computes separate-parent federal tax at 21%, post-2017 NOL utilization at 80%, and section 163(j) interest limitation using depreciation **and research amortization** addbacks to adjusted taxable income. It reverses book-only shared-service allocations and separately bridges allowances, inventory impairment, depreciation and research deductions.

Unpaid FF003 and software transaction-tax liabilities are added back until payment, consistent with the modeled economic-performance method. No recurring-item exception is asserted. Payment reverses the temporary difference; customer principal and seller tax remain separate. The FF003 payable remains $152,250 with no inferred remittance.

The current California calculation is explicitly a **separate-parent reserve workpaper**, not an adopted all-company combined return. It models the parent $800 minimum and separately identifies exposure above that amount. It does not establish that SHI historical NOLs can offset another member's income. CA/IL/WV unitary perimeter, member-specific NOLs, relevant PA sourcing and subsidiary statutory provisions require the separately researched company-state successor. Until that composition is implemented and reconciled, the edition cannot claim a complete company-wide statutory provision.

The generated `parent_tax_provision.csv` is the numerical authority for the selected source revision. At the clean September successor revision `93a8e6b9`, base federal current tax is zero for 2026–2029, $143,319.3120 for 2030 and $74,862.1860 for 2031; later accepted state/entity changes may alter these figures. Scheduled cash is an authored conditional plan, not evidence of real payment. No fixed member-funding total or sovereignty attainment date is enforced.

## Reproduction and authority

Run the supported company-closeout finance builder from a clean Git checkout. It rebuilds source adjustments, legal books, statements, provision/history/asset schedules and existing-schema exports. `tests/closeout` covers the adopted history, duplicate provisions, equipment basis, unpaid-tax timing, goodwill, FF003 and transaction-tax composition. The release manifest records the exact commit, source hashes and acceptance boundary.

Primary provisions and dated references are retained in the source tax files and historical workpaper, including IRS Form 8832/1120/8990/4562 guidance, section 174/174A transition guidance and period-specific FTB instructions. The controls `SUBSIDIARY_TAX_PERIMETER_RESEARCH.md` supplies the additional state/entity authority contract. Earlier memorandum versions are preserved in Git history; their former $7,200 estimate and missing-history descriptions are superseded by the reconstruction above.
