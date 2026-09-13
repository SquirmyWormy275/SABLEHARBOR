# Taylor–Red Wash legal due diligence

**SH-LEGAL-PRACTICE-LEGAL-DUE-DILIGENCE · PUBLIC_WORKED_EXAMPLE · prepared 2026-09-12**

Scope: Agreement source effective July 7, 2026; publication cutoff September 5, 2026. Source revision: `659a56747fe76522d18645ff115888c13fa8d2b0`. These are public learning materials with source-derived worked answers, not private assessment keys. New workbook designs remain draft for exact-file review.

## Worked calculations

| Calculation | USD | Explanation |
|---|---:|---|
| Combined rate per car (not an invoice) | 3,010.00 | Four road trips are priced, not one; no physical quantity ordered. |
| Difference from source combined rate | 0.00 | Arithmetic agreement does not establish delivered service. |

The [worked workbook](worked.xlsx) contains actual Excel formulas referencing the supplied Source inputs sheet, with cached results for readers that do not recalculate. Source data and derived totals are distinct. Do not sum the rows as one financial total.

## Supported findings and missing evidence

### LEGAL-F01 — Who performs and bills?

ARU supplies terminal/trucking; BS&T supplies rail; RWH is customer. Billing agency does not merge the sellers.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Parties, authority and term`. Further evidence: Verified signatures and invoice naming the actual performing seller.

### LEGAL-F02 — Does planned capacity guarantee revenue?

No minimum-volume guarantee or take-or-pay covenant is stated; unused slots produce no invoice.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule A — service and rates`. Further evidence: Actual quantities, source events and accepted rate version for a selected invoice.

### LEGAL-F03 — Can you test a late-service breach?

The source states 72 elapsed hours, 96 for steel, with a separate 36–48-hour operating goal. No selected shipment timestamps are supplied here.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule B — clock, free time and service remedies`. Further evidence: Interchange/empty-release timestamps, exclusions and responsibility evidence.

### LEGAL-F04 — Is storage automatically chargeable?

Only supported customer-caused occupancy after free time may receive the stated prorated charge; baseline has no chargeable dwell.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule B — clock, free time and service remedies`. Further evidence: Car, custody, start/end time, expiry, cause and charging entity; any third-party invoice.

### LEGAL-F05 — Is uranium custody authorized?

Finished uranium concentrate is excluded and direct product custody remains OPEN_GATED.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule C — custody, insurance and qualification`. Further evidence: Separate agreement and provider-specific qualification before any future activation.

### LEGAL-F06 — Are insurance policies evidenced?

The source states synthetic coverage assumptions, not insurer names, policies or certificates.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule C — custody, insurance and qualification`. Further evidence: Applicable policy/certificate and exclusions; no inference from a budget.

### LEGAL-F07 — Who owns the Phase 1 assets?

RWH owns the mine programme; ARU owns reusable Taylor infrastructure. Ownership and depreciation remain separate.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule D — assets, billing and termination`. Further evidence: Asset register and funding/acceptance evidence for any installed asset assertion.

### LEGAL-F08 — Does next-month settlement prove timely payment?

No. The source due period is 30 calendar days, while the model uses following-month settlement; exact invoice and payment dates are needed.

Source: `industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md — Schedule D — assets, billing and termination`. Further evidence: Dated invoice and independent settlement reference for the selected obligation.

## Evidence and limitations

- [industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md](../../../../../industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md) — SHA-256 `23153dc86a3e9ea9fd501bce6bdf3c8478dbdf3ab79fa5e8abc84ca8bbb771fc`
- [industrial/publications/SH-IND-IC-001_v1.0.0.pdf](../../../../../industrial/publications/SH-IND-IC-001_v1.0.0.pdf) — SHA-256 `6edd5e8f041b09b9447f51dee8f0dcc1179b1a58083396230642e31f383134f1`
- [industrial/source/entities.json](../../../../../industrial/source/entities.json) — SHA-256 `799a24baf3240d50c5d6a80ac0f9ddb9d023b7a36de058ec12546aac60caee29`

- The accepted source is a reconstructed internal agreement summary, not an authentic executed agreement.
- An absent document in this selected packet does not prove it is absent everywhere or that a party breached.
- No legal enforceability opinion, shipment, payment deadline breach or uranium qualification is asserted.

[Return to the task](TASK.md). Public worked conclusions do not establish execution, payment, audit assurance or legal enforceability.
