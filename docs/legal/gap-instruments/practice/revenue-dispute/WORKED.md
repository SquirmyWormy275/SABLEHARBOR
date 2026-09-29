# Foundry Field revenue and credit dispute

**SH-LEGAL-PRACTICE-REVENUE-DISPUTE · PUBLIC_WORKED_EXAMPLE · prepared 2026-09-12**

Scope: Base scenario, January–October 2027; FF-003 term 0. Source revision: `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`. These are public learning materials with source-derived worked answers, not private assessment keys. New workbook designs remain draft for exact-file review.

## Worked calculations

| Calculation | USD | Explanation |
|---|---:|---|
| Closing ledger receivable | 0.00 | Receivable is removed by writeoff, not full payment. |
| Cash collections including recovery | 609,000.00 | Recovery is already included in the released collected total. |
| Credits against written-off claim | 159,500.00 | Credits reduce the claim, with no refund in this selected packet. |
| Surviving written-off claim | 971,500.00 | Derived claim measure; not an asset newly recognized here. |
| Event 1 journal difference | 0.00 | base-01-INVOICE-INV-base-FF-003-TERM-0; two selected journal lines balance. |
| Event 2 journal difference | 0.00 | base-02-COLLECTION-INV-base-FF-003-TERM-0; two selected journal lines balance. |
| Event 3 journal difference | 0.00 | base-06-CREDIT_WRITEOFF-INV-base-FF-003-TERM-0; two selected journal lines balance. |
| Event 4 journal difference | 0.00 | base-07-CREDIT_NOTE-SYN-INC-FF-003-INV-base-FF-003-TERM-0; two selected journal lines balance. |
| Event 5 journal difference | 0.00 | base-08-CREDIT_NOTE-SYN-AMEND-003-INV-base-FF-003-TERM-0; two selected journal lines balance. |
| Event 6 journal difference | 0.00 | base-10-CREDIT_RECOVERY-INV-base-FF-003-TERM-0; two selected journal lines balance. |

The [worked workbook](worked.xlsx) contains actual Excel formulas referencing the supplied Source inputs sheet, with cached results for readers that do not recalculate. Source data and derived totals are distinct. Do not sum the rows as one financial total.

## Supported findings and missing evidence

### REV-F01 — SLA_SERVICE_CREDIT: what is supported?

The source credit debits BIZ_REVENUE, applies to a written-off claim and has no refund amount in this selected record.

Source: `base-07-CREDIT_NOTE-SYN-INC-FF-003-INV-base-FF-003-TERM-0`. Further evidence: Underlying signed SLA or amendment and customer acceptance before asserting contractual validity.

### REV-F02 — SYN-AMEND-003: what is supported?

The source credit debits BIZ_DEFERRED, applies to a written-off claim and has no refund amount in this selected record.

Source: `base-08-CREDIT_NOTE-SYN-AMEND-003-INV-base-FF-003-TERM-0`. Further evidence: Underlying signed SLA or amendment and customer acceptance before asserting contractual validity.

### REV-F03 — Was the invoice paid in full?

No such conclusion follows: modeled receipts plus recovery are less than billing, and writeoff explains zero ledger AR.

Source: `INV-base-FF-003-TERM-0`. Further evidence: Independent collection confirmation would still be required to establish actual cash.

## Evidence and limitations

- [docs/finance/evidence/SH-FIN-HUMAN-001/source.json](../../../../finance/evidence/SH-FIN-HUMAN-001/source.json) — SHA-256 `c4833cfc6f28db6cd3edcae761b0e2d8f463a20de79f1d6fd5b0c517f8f829b7`
- [docs/finance/evidence/SH-FIN-HUMAN-001/PACKET.md](../../../../finance/evidence/SH-FIN-HUMAN-001/PACKET.md) — SHA-256 `1b7828cb0a69551ef5ff14fad874bdc6222f697679e4163933d3a6f85f27f60c`
- [docs/finance/evidence/SH-FIN-HUMAN-001/reconciliation.xlsx](../../../../finance/evidence/SH-FIN-HUMAN-001/reconciliation.xlsx) — SHA-256 `7077ec3ae8e796a6f94759fe19624ab51a11ac45b7ce538a0c447b4c9c384214`
- [docs/finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json](../../../../finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json) — SHA-256 `6f521e7deb88875267ca705649e4db2dab8ca3dd5689c3cd22e8472fd5016f72`

- The accepted packet is reconstructed evidence, not an original invoice, signed SLA or bank confirmation.
- No revenue dispute outcome, customer consent or proposed billing identity is invented.
- Contract-wide recognition and pooled allowance entries are excluded; this is not a complete customer P&L.

[Return to the task](TASK.md). Public worked conclusions do not establish execution, payment, audit assurance or legal enforceability.
