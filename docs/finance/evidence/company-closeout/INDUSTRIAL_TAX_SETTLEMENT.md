# Industrial native income-tax settlement adapter

Implemented/reviewed September 21, 2026 UTC. Historical source accounting periods
and the declared company cutoff are unchanged. New adapter output is available no
earlier than September 21 and the clean source commit timestamp, with dirty previews
labeled nonpublishable by the existing availability contract.

`enterprise.closeout.industrial_tax_settlement.build(journal_rows, forecast)` consumes
the successor legal journal and native forecast journal, and independently regenerates
the locked 2026 anchor. It emits 432 monthly source-group rows: three scenarios,
two industrial source groups, six years, twelve months. It requires the complete
successor legal populations for ARU, BST, RWH and PS. Explicit zero-payment months
are retained. Actual payment occurrences carry their source and journal identifiers.

## Source treatment

- ARU's 2026 TAX26-PAYMENT entries debit 2700 and credit cash. Base/source payments
  are June $247,283, September $380,658 and December $185,802: total $813,743.
- RWH's 2026 RW-TAX entries debit native 5500 and credit cash directly. There is no
  2700 entry to invent. RWH is the legal cash book owner; PS is the modeled taxpayer
  for its disregarded operator. These historical estimates remain distinct from
  the successor actual tax calculation.
- Forecast TAX-CASH entries count only their cash/2700 payment pairs, not an unpaid
  tax obligation or scheduled due date. Native 5500/5501 and 2700 changes reconcile
  against the original LEGAL-* entries retained within the successor journal.
- Native ARU_GROUP provision ownership on ARU does not establish BST's separate
  tax obligation or prove that all group cash belongs on ARU's return. The adapter
  reports that cash pool without inventing taxpayer or jurisdiction allocation.
  Finance's new separate-return provision supplies a disclosed allocation.
- Positive native 2700 is shown as prepayment; negative 2700 as payable. The new
  provision may allocate gross source payments to receivables/payables but cannot
  manufacture cash, a refund, or an extra payment by netting different taxpayers.
- SHI CO_TAX payments are a separate parent population and are excluded here.

This is source reperformance, not an IRS/state acknowledgement or independent bank
confirmation. The original planning rates are identified as native provisions to
replace; they are not adopted as new tax rates. Input canonical hashes and source
hashes accompany output. Final finance composition and accepted-version validation
remain separate.

Tests reject omitted scenarios/entities/months, duplicate source or legal legs,
reversed balanced payments and stale legal amounts. A separate overpayment test
checks that a positive balance creates no refund or negative liability.
