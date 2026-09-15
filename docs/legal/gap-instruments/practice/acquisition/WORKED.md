# ARU acquisition accounting

**SH-LEGAL-PRACTICE-ACQUISITION · PUBLIC_WORKED_EXAMPLE · prepared 2026-09-12**

Scope: January 7, 2026 acquisition opening. Source revision: `8898d2d0310a60bdf0e4753036790c6eda1388cd`. These are public learning materials with source-derived worked answers, not private assessment keys. New workbook designs remain draft for exact-file review.

## Worked calculations

| Calculation | USD | Explanation |
|---|---:|---|
| Closing uses before fees | 61,500,000.00 | Stock consideration includes escrow; retained leases are not paid off again. |
| Closing sources before fees | 61,500,000.00 | New term debt and parent equity finance the same uses. |
| Funding reconciliation difference | 0.00 | Zero means this selected funding bridge reconciles, not that cash settled. |
| Parent cash including fees | 40,200,000.00 | Fees are separate from stock consideration. |
| Book goodwill residual | 14,762,500.00 | Source-model residual; no invented operating-income plug. |
| Tax goodwill residual | 13,000,000.00 | Independent conditional tax allocation, not book goodwill copied into tax. |
| Opening trial-balance debit total | 70,650,000.00 | All 16 source accounts included. |
| Opening trial-balance credit total | 70,650,000.00 | All 16 source accounts included. |
| Opening trial-balance difference | 0.00 | Balanced group opening books do not certify external evidence. |

The [worked workbook](worked.xlsx) contains actual Excel formulas referencing the supplied Source inputs sheet, with cached results for readers that do not recalculate. Source data and derived totals are distinct. Do not sum the rows as one financial total.

## Supported findings and missing evidence

### ACQ-F01 — What does ARU-CL-07 establish?

The March 2 source records filing-ready review, not IRS submission or acceptance.

Source: `industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md#delivery-register`. Further evidence: Actual submission/status evidence and qualified eligibility review.

### ACQ-F02 — Why do the goodwill amounts differ?

Book goodwill uses fair identifiable net assets including the conditional reserve DTA; tax goodwill uses separately modeled recognized liabilities and other tax bases.

Source: `industrial/finance/TRANSACTION_ACCOUNTING.md#purchase-price-allocation`. Further evidence: Independent valuation and support for conditional tax classifications before external reliance.

## Evidence and limitations

- [industrial/source/finance.json](../../../../../industrial/source/finance.json) — SHA-256 `0d4461abfcdb138da36db503ff0cfea7c47ea7fd7109494126514225fd43e38c`
- [industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md](../../../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md) — SHA-256 `a6dd448ed3a4a3ad6f0f3748e79dd918ea43c75685de762fe00843477a5d22c9`
- [industrial/finance/TRANSACTION_ACCOUNTING.md](../../../../../industrial/finance/TRANSACTION_ACCOUNTING.md) — SHA-256 `d13f142968958585cfc56a7b06d54b5e95bccef6d434d11bb6bba93933a0aa58`
- [docs/finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json](../../../../finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json) — SHA-256 `4e4c35d03d5613e0ef037d7dd14d27c250fa547fc29d2f93ddd1a1b25274e17c`
- [docs/finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv](../../../../finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv) — SHA-256 `33a28e198a5ce5a5d35f751ca8a3fac6aefc04faba4329b6297c7cd560ca02d5`
- [industrial/publications/SH-IND-ARU-CLOSE-001_v1.0.0.pdf](../../../../../industrial/publications/SH-IND-ARU-CLOSE-001_v1.0.0.pdf) — SHA-256 `2db8049ce4ee571d4a681505321b73af49739adb2cbd86d1fae78e92082d7883`

- Selected industrial reconstruction; do not add it to the separate operations release.
- PPA and tax basis retain conditional model assumptions; no valuation or tax opinion is supplied.
- An opening group trial balance is not independently reconstructed statutory books for each subsidiary.

[Return to the task](TASK.md). Public worked conclusions do not establish execution, payment, audit assurance or legal enforceability.
