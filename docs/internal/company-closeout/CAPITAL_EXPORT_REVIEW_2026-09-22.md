# Independent capital export and selected-review route

**Reviewed source:** `f5e919e7c39c9df7300be0ec7408cfba414c6725`.
**Review date:** September 22, 2026 UTC. This is source review while the final
financial build is running, not a receipt for completed final derivatives.

## Capital bridge

The integrated bridge counts the historical industrial contribution once:

- $183,000,000 historical subscription receipts less $174,200,000 authored Core
  losses equals $8,800,000 corrected Core initialization equity.
- $44,312,500 industrial capital is separately represented by the original
  noncash `OPEN-MEMBER-BASIS` entry. It is not added to the $183 million before
  deriving Core equity and then added again as industrial equity.
- Historical holder paid-in capital totals $227,312,500. Subsequent retained
  results and dated opening corrections bridge paid-in capital to book equity;
  they do not change units or create another cash receipt.
- The five-holder contribution, separate $28 million purchase consideration and
  $16,312,500 post-control operating funding agree. Parent holding/company
  formation predates transfers, and the RWH funding date respects July 18 control.

The new record is explicitly authored September 22 under delegated completion of
an existing model amount. The accepted predecessor's provisional/noncash/recovered
bank limitations remain discoverable. No additional owner choice, acquired value,
new investor right or real bank/board execution is inferred by this review.

One export-format correction was reported to the integration owner:
`capital_historical_contribution_holders.csv` contains nested rights dictionaries.
Its initial exporter passes dictionaries directly to CSV, unlike the existing
holder allocation export's JSON serialization. Consistent JSON encoding is needed
for those nested columns; Python dictionary repr is not a portable JSON contract.
This review does not claim that reported correction has already been applied.

## Reusable exact edition paths

Use explicit `--review-member` paths from the **final frozen CONTRACT**, checking
that every selected member exists there and matches its listed hash. These are
repository-relative names produced by the existing composer/generators:

| Member path | Selected inspection purpose |
|---|---|
| `enterprise/closeout/source/capital_register.json` | Newly authored holder authority, dates and distinct historical rounds/contribution |
| `enterprise/generated/company-closeout-v1/capital_opening_equity_bridge.csv` | Paid-in capital, losses and noncash opening reconstruction counted once |
| `enterprise/generated/company-closeout-v1/statutory_current_federal.csv` | Entity/scenario/year tax workpaper identity and separate taxpayers |
| `enterprise/generated/company-closeout-v1/enterprise/enterprise_annual_statements.csv` | Source-composed financial results; preserve forecast versus calibration roles |
| `enterprise/generated/completed-period-2026-08/payroll_source_bridges.csv` | Current employer-cost to source-book reconciliation |
| `enterprise/generated/completed-period-2026-08/current_customer_invoice_ledger.csv` | Individual invoice principal, sale period, payment and dispute states |
| `enterprise/generated/completed-period-2026-08/operating_events.csv` | Declared normal/exception operating chains, chronology and retained failure |

These selections cover all three edition components. They are a bounded software
workflow demonstration, not a statistically representative audit sample, complete
population review, professional tax conclusion or control-effectiveness opinion.
The engagement must retain exact originals, the declared surrounding populations,
independent-role review, and the incomplete hold/disposal/indirect-disclosure scope.
Current scratch/generated directories can be stale during a build; their existence
does not substitute for the final CONTRACT membership and source-hash check.

## Dependency pin

`current_inventory_bridge → rwh_history` now consumes
`enterprise/closeout/source/capital_register.json`. The completed-period generator
therefore includes that source in its input hash population. This is a causal
provenance fix, with no new quantity, carrying amount, cash or equity posting.
