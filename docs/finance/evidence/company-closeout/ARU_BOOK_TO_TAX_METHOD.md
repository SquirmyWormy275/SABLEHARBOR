# ARU/BST annual tax-base bridge

Authored September 15, 2026 UTC. Synthetic workpaper; no tax journal, payment or
filed election. `enterprise.closeout.aru_tax_workpapers.build(journal_rows, forecast)`
consumes complete legal monthly journals plus native forecast datasets assets,
debt and journal. Finance separately applies interest limits, NOLs, state factors
and current/deferred provisions.

The intended 338(h)(10) new-target period begins January 8, 2026. January books
include January 7–31; evenly earned ordinary revenue and service-day costs remove
one of those 25 days. Discrete acquisition accounts are excluded from that
ordinary-cost rule. D&A is reversed fully and replaced by the separate tax asset
schedule. Financing removes the identified January 7 source-day accrual separately.
It changes neither principal nor repayment dates. Native planning taxes 5500/5501
and book-only 5900/SHARED_EXP allocations are reversed.

Debt components reconcile to combined legal account 5400. BST receives 8% and ARU
92% financing allocation, independent of PPE's 55/45 shares. Loan/lease interest
and issuance amortization enter the eligible interest population. Unused revolver
commitment service fees are separately deductible outside that population under
the reviewed fee characterization. Legal cumulative allocation rounding is explicit.

ARU retains $14,762,500 book goodwill and $13,000,000 original tax goodwill. The
latter amortizes over 180 months, including the full acquisition month, on ARU
alone. No second Core-goodwill correction is posted.

## Retention

Source employee retention accrual is $491,781 in 2026; July payment is $250,000.
The future installment requires continued service; no fixed reallocated bonus
pool is authored. Reverse the book accrual after excluding the old-target day,
then deduct source-posted fixed payment. For 2027 reverse the final service
accrual and deduct only the source conditional payment. A planned January date
alone does not establish an earlier deduction.

The all-events distinction appears in [Rev. Rul. 2011-29](https://www.irs.gov/irb/2011-49_IRB):
its fixed aggregate pool with reallocation differs from this individual service
contingency. [CCA 201246029](https://www.irs.gov/pub/irs-wd/1246029.pdf) illustrates
continued-employment contingencies but is nonprecedential. Both sources were
accessed September 15, 2026. The company facts remain expressly synthetic.

Unpaid July employer levies ARU $16,065/BST $8,201.75 are separately added back;
bonus settlement is not employer-tax remittance. Later payment requires a sourced
successor deduction. No reserve settlement or election acknowledgement is inferred.

Tests reject duplicate journal legs, omitted months, changed financing totals and
recursive tax inputs, and reperform retention timing. Final same-source finance
composition remains required; this module does not issue an audit conclusion.


The default source scope is exactly three scenarios, two legal taxpayers and
2026–2031: 36 entity-year groups, each with twelve monthly book populations.
Omitting an entire group fails before tax calculations. Explicit smaller review
scopes require the `expected_groups` keyword and are labeled partial; they cannot
silently become full-release evidence. Both CO_TAX and CO_SUB_TAX income-tax
expense namespaces are rejected as recursive provider inputs.
