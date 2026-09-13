# Reconcile the ARU acquisition to its opening books

**Route:** `SH-EX-ACQ-001`. **Question:** can you explain the cash funding, opening trial balance and goodwill without counting financing or escrow twice?

Use the January 7, 2026 ARU stock acquisition and the selected current industrial reconstruction. Its schedules are pinned to source revision `8898d2d0310a60bdf0e4753036790c6eda1388cd` in the [current-source bridge](../../finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json). This is not a `base-2027` operations-release exercise. Currency is USD. The opening trial balance uses `entity=ARU_GROUP`, `year=2026`; subsequent monthly schedules cover the model's 2026 period.

## Open these records

| Record | Read this part |
|---|---|
| `SH-IND-ARU-CLOSE-001`: [closing statement](../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md) · [PDF](../../../industrial/publications/SH-IND-ARU-CLOSE-001_v1.0.0.pdf) | “January 7, 2026 closing” and “Delivery register” |
| `SH-IND-FIN-TXN-001`: [accounting model](../../../industrial/finance/TRANSACTION_ACCOUNTING.md) · [PDF](../../../industrial/publications/SH-IND-FIN-TXN-001_v1.0.0.pdf) | “Sources and uses,” “Purchase price allocation,” and “Postclose schedules and legal books” |
| [Transaction support guide](../../finance/evidence/tax-transaction/TRANSACTION_SUPPORT.md) | Source identity, schedule scope and documentary limits |
| [PPA CSV](../../finance/evidence/tax-transaction/acquisition_ppa.csv) | All 18 `measure` rows and `amount_usd` |
| [Opening trial balance CSV](../../finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv) | All 16 accounts; preserve account identifiers as text |
| [Tax rollforward CSV](../../finance/evidence/tax-transaction/aru_2026_tax_rollforward.csv) | Twelve months, retaining separate book basis, tax basis, tax expense and cash |

Download the CSVs and open them in Excel or another spreadsheet application. They are complete scoped schedules, not formatted workbook designs; there is no required acquisition XLSX. The [SQLite mirror](../../finance/evidence/tax-transaction/transaction-support.sqlite3) is optional and contains these same populations.

## Work through it

1. Make a sources-and-uses working paper from the closing statement. Show enterprise value to seller equity, then buyer-funded share consideration. Identify the excess-cash distribution, direct seller payment and escrow separately. Show old debt payoff, new term debt and parent equity below that bridge; show transaction fees and debt issuance costs separately. Do not add the retained finance leases as a second payoff.
2. Compare the result to PPA measures `close_sources_before_fees_usd`, `close_uses_before_fees_usd`, `stock_consideration_usd`, `parent_cash_before_fees_usd` and `parent_cash_including_fees_usd`. Explain `new_debt_upstream_acquisition_distribution_usd` using “Sources and uses.” A transfer financing the purchase is not revenue or an additional purchase price.
3. Sum `debit_balance_usd` and `credit_balance_usd` across all 16 opening accounts. Record the difference. Explain the account basis using the accounting model; do not compare only selected asset accounts to the entire purchase price or relabel the `ARU_GROUP` view as separate statutory books for ARU and BS&T.
4. Reperform the book goodwill residual from `stock_consideration_usd` and `identifiable_net_assets_before_refinancing_usd`. Separately follow `ppa.tax_allocation` in the current-source bridge: modeled adjusted grossed-up basis, recognized assumed liabilities and other asset tax bases. Explain why `tax_goodwill_basis_usd` differs from `goodwill_usd`. Cite the conditional reserve-DTA and initial-goodwill treatment instead of replacing them with an unsupported balancing entry.
5. Use months 1–12 in the tax rollforward to distinguish cumulative deductions and balances from monthly expenses and cash payments. Do not sum cumulative columns. Compare month 12 book/tax goodwill bases, the reserve DTA, goodwill DTL and current-tax settlement balance to the accounting narrative. Identify any rounding difference explicitly rather than overwriting supplied values.
6. Read delivery ID `ARU-CL-07`. State what the March 2 filing-ready record supports and what evidence would be needed to establish external filing or acceptance. Keep that finding separate from whether your arithmetic reconciles.

## Hand in and review

Produce a funding bridge with source references, a trial-balance check, a short book/tax goodwill explanation and an evidence-request list. A colleague should be able to reproduce each subtotal from the named rows. Show any difference and its cause; do not add a balancing plug. The source CSVs retain rounded dollar amounts, so assess rounded monthly totals in that context.

The transaction is synthetic; model valuations and tax classifications remain conditional. These records do not supply authentic bank confirmations, signed transfer originals, an independent valuation or filed tax evidence. This route tests the repository's stated model and evidence trail; it does not certify GAAP compliance or give a tax opinion. Do not import the separate Red Wash or Northern Nevada purchase into the ARU bridge.

[Return to the three exercises](README.md)
