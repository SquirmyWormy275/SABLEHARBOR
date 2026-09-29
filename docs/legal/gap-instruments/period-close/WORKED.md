# Public worked close — ARU Group, January 2027

No new economic facts or correcting entries are introduced. All amounts are USD; liabilities and equity are credit-negative in the trial balance.

| Account | Opening | Activity | Adjustment | Closing |
|---|---:|---:|---:|---:|
| 1000 Cash | 4,198,440.00 | -703,912.00 | 0.00 | 3,494,528.00 |
| 1100 External receivables, net of allowance | 6,120,000.00 | -1,451,868.00 | 0.00 | 4,668,132.00 |
| 1150 Intercompany receivable | 49,240.00 | -14,723.00 | 0.00 | 34,517.00 |
| 1200 Inventory cash cost | 1,854,000.00 | 13,905.00 | 0.00 | 1,867,905.00 |
| 1300 Prepaids | 721,000.00 | 0.00 | 0.00 | 721,000.00 |
| 1400 PPE gross | 61,550,000.00 | 283,250.00 | 0.00 | 61,833,250.00 |
| 1490 Accumulated PPE depreciation | -2,684,091.00 | -285,488.00 | 0.00 | -2,969,579.00 |
| 1500 Finance lease ROU gross | 2,500,000.00 | 0.00 | 0.00 | 2,500,000.00 |
| 1590 Accumulated finance lease ROU depreciation | -491,783.00 | -41,667.00 | 0.00 | -533,450.00 |
| 1600 Goodwill | 14,762,500.00 | 0.00 | 0.00 | 14,762,500.00 |
| 1700 Debt issuance cost, contra term debt | 240,968.00 | -5,000.00 | 0.00 | 235,968.00 |
| 1800 Deferred tax asset on reserved liabilities | 587,500.00 | 0.00 | 0.00 | 587,500.00 |
| 2000 Trade payables | -3,090,000.00 | 1,482,416.00 | 0.00 | -1,607,584.00 |
| 2100 Operating accruals | -1,030,000.00 | 0.00 | 0.00 | -1,030,000.00 |
| 2110 Retention compensation payable | -241,781.00 | 241,781.00 | 0.00 | 0.00 |
| 2200 Environmental reserve / ARO | -1,750,000.00 | 0.00 | 0.00 | -1,750,000.00 |
| 2250 Deferred tax liability on tax goodwill amortization | -216,667.00 | -18,055.00 | 0.00 | -234,722.00 |
| 2300 Claim reserve / other liabilities | -600,000.00 | 0.00 | 0.00 | -600,000.00 |
| 2400 Term debt face value | -21,375,000.00 | 375,000.00 | 0.00 | -21,000,000.00 |
| 2410 Conditional replacement term debt | 0.00 | 0.00 | 0.00 | 0.00 |
| 2600 Finance lease obligation | -2,008,219.00 | 41,667.00 | 0.00 | -1,966,552.00 |
| 2700 Current income tax payable / prepaid | 0.00 | 0.00 | 0.00 | 0.00 |
| 2720 Accrued interest and financing services payable | 0.00 | 0.00 | 0.00 | 0.00 |
| 3000 Contributed equity | -56,004,880.00 | 0.00 | 0.00 | -56,004,880.00 |
| 3100 Prior retained earnings | -3,091,227.00 | 0.00 | 0.00 | -3,091,227.00 |
| 4000 External revenue | 0.00 | -3,138,132.00 | 0.00 | -3,138,132.00 |
| 4100 Intercompany service revenue | 0.00 | -34,517.00 | 0.00 | -34,517.00 |
| 5000 Payroll and employer burden | 0.00 | 1,147,239.00 | 0.00 | 1,147,239.00 |
| 5100 External operating cost | 0.00 | 1,593,679.00 | 0.00 | 1,593,679.00 |
| 5200 Incremental interface external operating cost | 0.00 | 23,866.00 | 0.00 | 23,866.00 |
| 5300 Depreciation in earnings | 0.00 | 327,155.00 | 0.00 | 327,155.00 |
| 5400 Interest and financing fees | 0.00 | 137,130.00 | 0.00 | 137,130.00 |
| 5501 Deferred income tax expense | 0.00 | 18,055.00 | 0.00 | 18,055.00 |
| 5700 Retention and seller consulting | 0.00 | 8,219.00 | 0.00 | 8,219.00 |

## Reconciliation results

- Bank adjusted cash to ledger: 3,494,528.00 versus 3,494,528.00; difference 0.00. Modeled clearing schedule; not independent bank evidence.
- Bank clearing timing: 3,494,528.00 versus 3,494,528.00; difference 0.00. Opening bank cash + cleared receipts - cleared payments + deposits - outstanding payments.
- Complete bank transaction population: -703,912.00 versus -703,912.00; difference 0.00. All 33 selected modeled cash events; journal_id joins activity.
- Receivables opening plus activity: 4,668,132.00 versus 4,668,132.00; difference 0.00. Complete account journal rollforward; independent January open-item schedule unavailable in this case.
- Payables opening plus activity: -1,607,584.00 versus -1,607,584.00; difference 0.00. Complete account journal rollforward; independent January open-item schedule unavailable in this case.
- Debt legacy_term: 21,000,000.00 versus 21,000,000.00; difference 0.00. Native debt row; no contractual compliance conclusion.
- Debt replacement_term: 0.00 versus 0.00; difference 0.00. Native debt row; no contractual compliance conclusion.
- Debt lease: 1,966,552.00 versus 1,966,552.00; difference 0.00. Native debt row; no contractual compliance conclusion.
- PPE gross to ledger: 61,833,250.00 versus 61,833,250.00; difference 0.00. All eight native PPE rows; finance-lease ROU is separate.
- PPE accumulated depreciation: 2,969,579.00 versus 2,969,579.00; difference 0.00. All eight native PPE rows.
- PPE net rollforward: 58,863,671.00 versus 58,863,671.00; difference 0.00. Opening NBV plus additions less depreciation.
- assets_usd: 86,966,303.00 versus 86,966,303.00; difference 0.00. Complete closing account classification.
- liabilities_usd: 27,952,890.00 versus 27,952,890.00; difference 0.00. Complete closing account classification.
- Net income: -82,694.00 versus -82,694.00; difference 0.00. January has no prior-year-to-date forecast income.
- Equity including current income: 59,013,413.00 versus 59,013,413.00; difference 0.00. Opening equity and January income.
- operating_cash_flow_usd: -3,995.00 versus -3,995.00; difference 0.00. Complete cash-account journal classification.
- investing_cash_flow_usd: -283,250.00 versus -283,250.00; difference 0.00. Complete cash-account journal classification.
- financing_cash_flow_usd: -416,667.00 versus -416,667.00; difference 0.00. Complete cash-account journal classification.

## Adjustment and conclusion

No unexplained numerical difference in the selected records. Zero new entries; missing independent evidence does not justify a plug. Closing cash is $3,494,528; assets $86,966,303; liabilities $27,952,890; equity including current income $59,013,413; January net loss $82,694. Independent cash, AR/AP completeness, asset existence and executed debt support remain unproven.
