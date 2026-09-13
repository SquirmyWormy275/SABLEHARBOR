# Follow one Foundry Field invoice into the ledger

**Route:** `SH-EX-INV-001`. **Question:** what happened to the invoice, and which journal entries support each movement?

Use `INV-base-FF-003-TERM-0`, customer `SYN-CUSTOMER-003`, contract `FF-003`, term `0`, unit `foundry-field`, legal-book code `SHI`. The scope is the **base scenario, January–October 2027**, from `business-operations-v1.0.0`, release source `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`. These are conditional forecast records, not observed 2027 activity.

## Open the accepted packet

Start at the [accepted packet index](../../finance/evidence/SH-FIN-HUMAN-001/README.md), then download its [PDF](../../finance/evidence/SH-FIN-HUMAN-001/packet.pdf) and [Excel workbook](../../finance/evidence/SH-FIN-HUMAN-001/reconciliation.xlsx). The [Markdown packet](../../finance/evidence/SH-FIN-HUMAN-001/PACKET.md) is readable directly on GitHub. The [acceptance record](../../finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json) applies to these exact files; their frozen draft wording is historical.

| Exact workbook sheet | Use it for |
|---|---|
| Source register | Confirm release and selected population before using the other sheets |
| Terms and credits | Read the two contract versions and two credit notes |
| Movements | Follow the five dated collection, writeoff, credit and recovery movements |
| Journal | Trace the six included events to twelve journal lines |
| Reconciliation | Inspect the supplied formulas after making your own movement schedule |

The [source extract](../../finance/evidence/SH-FIN-HUMAN-001/source.json) preserves all original columns and native IDs. It is optional deeper evidence; the worksheet views are sufficient for the core exercise.

## Work through it

1. Write the invoice, contract, scenario, period and release on a separate working paper. Read “The account” in the packet. Compare the original billing amount with the original contract term; distinguish the stated due date from the later model period-end events.
2. Read **Terms and credits** and **Movements**. Put the five movements in date order after the initial invoice. Give ledger receivable, written-off claim, cash collections and credits separate columns. A credit after writeoff does not recreate a receivable or automatically become a cash refund.
3. Trace initial event `base-01-INVOICE-INV-base-FF-003-TERM-0` to **Journal**, starting with journal ID `BIZ-base-0000014`. Then use each movement's exact source event ID to find its journal lines. Check debits equal credits for each of the six events, retaining account codes and dates in your cross-reference.
4. Compare the July `SLA_SERVICE_CREDIT` and August `SYN-AMEND-003` credits. Identify their different debit accounts and the contract-version change supporting the latter. A synthetic approval ID is not independent customer consent.
5. Reconcile closing ledger receivable and the surviving written-off claim separately. Calculate collections from the dated movements and compare with the invoice's collected total. Explain why adding `recovered_usd` again to a total that already includes recovery would double-count cash. Now compare your working paper to **Reconciliation** and inspect the formulas.
6. List what you could conclude from this packet alone and what additional records would be needed to test actual receipt, customer agreement or the period's pooled allowance. Do not interpret these twelve lines as a complete contract P&L or a period trial balance.

## Hand in and review

Produce a dated movement bridge, six-event journal cross-reference and an evidence-request list. Your reader should be able to follow one source event ID from a movement to balanced journal lines. Explain any difference between your schedule and the supplied formulas without editing the accepted workbook.

The packet supplies no original customer invoice, billing address, tax specification, payment instruction, signed contract, bank statement or independent collection confirmation. Its PDF, workbook and JSON are derivatives of the same population, not three independent confirmations. Broader revenue recognition and allowance entries are outside this selected packet. Proposed fictional billing data and new workbook designs are not prerequisites for this exercise.

[Return to the three exercises](README.md)
