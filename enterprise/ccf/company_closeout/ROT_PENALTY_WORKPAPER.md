# Unpaid historical receipt-tax consequences

Authored September 22, 2026 UTC; event measurement September 14, 2026. Pending repository acceptance. This is a synthetic company estimate, not an IDOR assessment or a filed return.

`rot_penalty_workpaper.build()` consumes the six H2 2025 monthly receipt populations from `tax_calendar_supplement.history()`. It aggregates three utility contracts per return. The $441,346.80 receipt-tax principal is already included in the $646,624.38 historical accrual; do not post it again. Additional unpaid modeled consequences are $1,250 filing penalty, $44,134.68 payment penalty and $24,937.86 interest, totaling $70,322.54. No cash settlement is authored. Interest is measured through the cutoff, not through this workpaper's later authorship.

Primary authority checked September 22, 2026:

- [IDOR Publication 103](https://tax.illinois.gov/research/publications/pubs/penalties-and-interest-for-illinois-taxes.html), uniform penalties for returns due after January 1, 1994: first-tier nonfiling is lesser $250 or 2% of tax less timely payments; ordinary payment penalty is 2% through day 30 and 10% thereafter. Simple daily interest starts after payment due date, principal × annual rate / 365 (366 for leap year) × days. Calendar source provides the monthly ST-1 deadlines.
- [Official Illinois interest table](https://tax.illinois.gov/individuals/interestrate.html): 7% January 1, 2025–December 31, 2026. Both measured years have 365 days. Round each return/component to cents after calculation; do not round daily interest.

All five positive H2 monthly receipt taxes are more than 30 days overdue. July has no receipt tax: ordinary first-tier monetary penalty computes zero while the missing return remains visible. No second-tier notice, audit initiation, collection demand, bad check or relief is authored; associated contingent enhancements are excluded. This does not assert those events are legally impossible. H2 2025 periods are outside the 2025 amnesty's pre-July-2024 period boundary.

No accelerated schedule applied to these H2 2025 returns. For 2026, the source's accelerated account exists, but the installment amounts/safe-harbor and earlier actual receipt population require separate reperformance. Do not duplicate an accelerated penalty and ordinary payment penalty on the same principal (Publication 103's explicit subtraction rule). August 2026 monthly ST-1 is not due by September 14; this says nothing about its earlier accelerated installments. Uncollected invoice tax, trader purchase/resale review, acquired receivable successor exposure and unsupported 2026 receipt populations are excluded, not treated as exempt or paid. This bounded total is not the company's complete tax-penalty exposure.

For an August 31 statement use `build('2026-08-31')`; the September movement is the difference from the September 14 workpaper. Finance owns journals and income-tax characterization. The function permits only the researched 2025–2026 interest window and rejects changed settled/filed source populations.

## Explicit conditional continuation

`build(cutoff, planning_interest_rate=Decimal('.07'))` permits 2027–2031 projections only when the caller expressly supplies a finite rate between zero and one. This holds a planning assumption, not verified future law. Verified 2025–2026 interest remains7% regardless of the supplied future rate. Annual day-count segments use365/366, with rounding only after each return's accumulated interest. Unpaid principal and one-time penalties persist without fabricated settlement; no additional future receipt population or recurring penalty is invented.
