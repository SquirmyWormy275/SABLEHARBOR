# ARU debt reconciliation

**SH-LEGAL-PRACTICE-DEBT · PUBLIC_WORKED_EXAMPLE · prepared 2026-09-12**

Scope: January–December 2026 selected industrial debt model. Source revision: `8898d2d0310a60bdf0e4753036790c6eda1388cd`. These are public learning materials with source-derived worked answers, not private assessment keys. New workbook designs remain draft for exact-file review.

## Worked calculations

| Calculation | USD | Explanation |
|---|---:|---|
| Advance allocation difference | 0.00 | New borrowing is used once; upstream funds are financing, not revenue. |
| Month 1 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 2 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 3 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 4 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 5 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 6 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 7 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 8 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 9 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 10 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 11 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Month 12 principal difference | 0.00 | Opening less principal reduction equals closing; interest is not principal. |
| Full-year term principal reductions | 1,125,000.00 | Three modeled quarterly reductions, not twelve installments. |
| December funded principal including leases | 23,383,219.00 | Principal amount; do not net unamortized issuance costs here. |
| December term debt carrying amount | 21,134,032.00 | Term principal less unamortized term-debt issuance cost; excludes leases. |

The [worked workbook](worked.xlsx) contains actual Excel formulas referencing the supplied Source inputs sheet, with cached results for readers that do not recalculate. Source data and derived totals are distinct. Do not sum the rows as one financial total.

## Supported findings and missing evidence

### DEBT-F01 — Does a zero model payoff balance prove liens were released?

No. The source records internal payoff instructions and modeled refinancing; it supplies no independent executed release.

Source: `industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md#delivery-register`. Further evidence: Lender payoff statement, verified settlement and item-specific release evidence.

## Evidence and limitations

- [industrial/source/finance.json](../../../../../industrial/source/finance.json) — SHA-256 `0d4461abfcdb138da36db503ff0cfea7c47ea7fd7109494126514225fd43e38c`
- [industrial/finance/TRANSACTION_ACCOUNTING.md](../../../../../industrial/finance/TRANSACTION_ACCOUNTING.md) — SHA-256 `d13f142968958585cfc56a7b06d54b5e95bccef6d434d11bb6bba93933a0aa58`
- [industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md](../../../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md) — SHA-256 `a6dd448ed3a4a3ad6f0f3748e79dd918ea43c75685de762fe00843477a5d22c9`
- [docs/finance/evidence/tax-transaction/aru_2026_debt.csv](../../../../finance/evidence/tax-transaction/aru_2026_debt.csv) — SHA-256 `f4fe40dcd3672ed876be4b539428c92fbeb8ed441f7f4fd1f610529c4ebb2d53`
- [docs/finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json](../../../../finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json) — SHA-256 `4e4c35d03d5613e0ef037d7dd14d27c250fa547fc29d2f93ddd1a1b25274e17c`

- ACT/365 and the 6.75% rate are source model conventions, not a verified lender agreement.
- The twelve monthly rows are conditional modeled schedules; no bank settlement is proved.
- Do not add a revolver limit to drawn principal or expense debt issuance costs twice.

[Return to the task](TASK.md). Public worked conclusions do not establish execution, payment, audit assurance or legal enforceability.
