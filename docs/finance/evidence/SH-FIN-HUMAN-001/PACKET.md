# Foundry Field: invoice evidence

**SH-FIN-HUMAN-001 · Draft 01 · September 11, 2026**

**Synthetic exercise record — base scenario, 2027.** This is a reconstruction of released accounting rows for review. It is not an original invoice, an executed contract or a request for payment.

## The account

| Field | Released record |
|---|---|
| Invoice | INV-base-FF-003-TERM-0 |
| Customer | SYN-CUSTOMER-003 |
| Contract / term | FF-003 / term 0 |
| Business / legal-book code | Foundry Field / SHI |
| Billing period / due date | January 2027 / February 28, 2027 |
| Original subscription | 140 seats; $145,000 per month; 12 months |
| Original invoice | **$1,740,000.00 USD** |

The selected contract has no deployment fee. January billing debits receivables and credits deferred revenue. This packet follows that invoice's collection and credit-loss history; it does not reconstruct all contract revenue recognition or the pooled allowance close.

## What happened

| Period end | Released event | Amount USD | Ledger AR remaining USD |
|---|---|---:|---:|
| January 31, 2027 | Invoice recorded | 1,740,000.00 | 1,740,000.00 |
| February 28, 2027 | Partial receipt | 435,000.00 | 1,305,000.00 |
| June 30, 2027 | Remaining AR written off | 1,305,000.00 | 0.00 |
| July 31, 2027 | Service credit against written-off claim | 14,500.00 | 0.00 |
| August 31, 2027 | Contraction credit against written-off claim | 145,000.00 | 0.00 |
| October 31, 2027 | Recovery after writeoff | 174,000.00 | 0.00 |

The July credit carries reason `SLA_SERVICE_CREDIT` and debits revenue. The August credit carries reason `SYN-AMEND-003` and debits deferred revenue. Both reduce the written-off claim; neither creates a cash refund. The August contract version records 112 seats at $116,000 per month. Its approval identifier is a synthetic model record, not a signature or evidence of real customer consent.

## Reconciliation

| Measure | Calculation | USD |
|---|---|---:|
| Closing ledger receivable | 1,740,000 − 435,000 − 1,305,000 | 0.00 |
| Total modeled collections | 435,000 receipt + 174,000 recovery | 609,000.00 |
| Total credits | 14,500 + 145,000 | 159,500.00 |
| Surviving written-off claim | 1,305,000 − 159,500 − 174,000 | 971,500.00 |

**A zero receivable does not mean the invoice was paid.** The $971,500 remainder is a derived written-off claim measure, not an asset recognized by this packet. The source invoice's $609,000 collected total already includes the $174,000 recovery; adding it again would double-count cash.

## Inspect the supporting evidence

Open `reconciliation.xlsx`: Reconciliation contains the formulas; Movements shows all five released history rows; Journal shows all twelve lines for the six invoice-linked events; Terms and credits shows two contract versions and two credit notes; Source register identifies the immutable release and scope. `source.json` retains all original columns of the selected rows, including native IDs. These worksheets and the PDF derive from the same evidence; they are not independent corroboration.

For journal tracing, match the movement's source event ID to the Journal worksheet. January invoice posting uses event `base-01-INVOICE-INV-base-FF-003-TERM-0`. Later events use the exact released IDs shown in the workbook. Each included event's debits equal credits. Contract-wide revenue and allowance entries are excluded, so these twelve lines are not a complete customer P&L or period trial balance.

## What is not supplied

No customer address, tax specification, payment instructions, signed contract, bank statement, approval signature or independent collection confirmation is supplied. Do not infer those fields from presentation. Dates are model period ends and the stated contractual due date, not proof of real-world activity. The separate SOC/CCF workline is outside this packet.

## Provenance and review boundary

Source: `business-operations-v1.0.0`, published September 11, 2026. Source revision: `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`. Invoice-specific extracts come from `units/foundry-field/` in that release. The package manifest records the verified archive SHA-256, source-member hashes and derivative hashes. The native reporting database is the release's `units/foundry-field/evidence.sqlite3`.

This draft requires review of these exact files before adoption. It changes no financial source, journal, approved artwork or prior release. Its package-local catalog record awaits integration with the repository catalog.
