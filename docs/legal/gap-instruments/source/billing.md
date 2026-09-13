# Foundry Field proposed billing instrument and reconciliation attachment

**Document ID:** SH-LEGAL-DRAFT-BILLING  
**Gap ID:** LEGAL-GAP-BILLING  
**Status:** DRAFT_FOR_REVIEW — synthetic, unexecuted proposed instrument  
**Version:** 0.1.0  
**Prepared:** 2026-09-12  
**Owner:** Finance / Legal  
**Approval date:** not established  
**Effective date:** not established; source event dates below are not execution of this draft  
**Authority:** Markdown controls this draft; JSON is its structured companion.

## 1. Instrument and sole proposal dependency

This proposed reconstructed billing instrument applies only to invoice **INV-base-FF-003-TERM-0**, contract **FF-003**, customer **SYN-CUSTOMER-003**, base scenario, Foundry Field. Its sole fictional billing-detail source is **SH-FIN-BILL-PROP-001 version 0.1.0**, preserved from the PR #138 proposal at revision `e4995ba`. The local dependency copy is an immutable review reference, not a second customer master or a newly accepted billing dataset. It shall not be edited to reconcile a preferred design.

The invoice amount, due date, contract economics and ledger linkage derive from the accepted source packet and immutable business operations release. The display name, correspondence fields and documentary issue date derive only from the unaccepted billing proposal. This instrument keeps those two origins separate. Approval of a page layout cannot silently approve a missing legal party, tax treatment or payment destination. The original accepted Foundry Field evidence packet and release rows remain unchanged.

## 2. Proposed invoice face and identities

The proposed business heading is **Foundry Field**. The source book code **SHI** identifies the accepted parent **Sable Harbor, LLC**. The sole proposal retains a null invoice-specific legal-issuer presentation field; that unresolved assignment does not reopen the established parent identity. Foundry Field branding is not a new subsidiary. The customer display name is **Copperreach Fabrication**, attached only to existing customer ID SYN-CUSTOMER-003. No incorporation suffix, registered jurisdiction or executed legal party is inferred from that display name.

The proposed customer correspondence block is Accounts Payable, 1840 Quarry Exchange, Suite 210, Sacramento, CA 95814, United States. Its proposed contact is `accounts-payable@copperreach.invalid`. The proposed issuer correspondence block is 240 Harbor Works Avenue, Billing desk — Foundry Field, Sacramento, CA 95814, United States; proposed contact is `billing@foundry-field.invalid`. These are display-only fictional correspondence details. They establish no postal deliverability, registered office, campus, lease, site occupancy or geographic-register update and are not endpoints to contact or deploy.

The proposed purchase-order display reference is **CRF-2027-FF003-001**. It is not an existing purchase-order original, approval signature or procurement authorization. A human reader must be able to distinguish this invented reference from invoice, contract and customer IDs that already exist in the source population. Neither side's legal-name field shall be filled by guessing from brand identity.

## 3. Proposed billing statement

| Field | Display or source value | Status |
|---|---|---|
| Invoice | INV-base-FF-003-TERM-0 | Released native identifier |
| Customer | SYN-CUSTOMER-003 / Copperreach Fabrication | Released ID / proposed display name |
| Contract | FF-003; initial term 0 | Released linkage |
| Proposed issue date | January 31, 2027 | Proposed documentary date aligned to posting period |
| Due date | February 28, 2027 | Released due date |
| Description | Foundry Field subscription — initial 12-month term, 140 seats | Proposed wording of released contract scope |
| Monthly subscription | $145,000 USD | Released contract amount |
| Initial term | 12 months | Released term |
| Invoice amount | $1,740,000 USD | Released amount; not recalculated for invented tax |
| Deployment fee | $0 USD | Released contract field; not a new discount |
| Tax | Treatment not established; no separate tax amount represented | Unresolved source field |
| Payment instructions | Not supplied in this reconstruction | No remittance authorization |

The documentary issue date is a proposed presentation field. Source `issue_month=1` and posting period January 31 do not independently establish an original invoice issue day. No invoice was issued to a real customer by creating this record. The description adds no SLA obligation, implementation deliverable, customer acceptance or new service entitlement beyond the stated source term.

## 4. Amount integrity and no implied tax election

The subscription calculation is twelve monthly amounts of $145,000, with 140 source seats and no deployment fee. The invoice remains $1,740,000. The preparer shall not divide the amount into invented tax and net charges, add tax, describe the transaction as exempt or assert a zero rate. The sole proposal expressly leaves tax unestablished. Any separately approved tax scenario must state its authority and effect and must not rewrite this release's historical values.

Amounts on the invoice face describe initial billing. Later collections, writeoff and credits belong in the separate reconciliation in clause 6. They must not appear as though known at initial issue. The present proposed reconstruction is prepared September 12, 2026 from a conditional 2027 scenario; dates in the model are not observed future events. No “paid” stamp, payment receipt or customer acknowledgment shall be inferred from the existence of a ledger field.

## 5. Payment, dispute and correction provisions

The source due date remains February 28, 2027. This proposed instrument supplies no bank, routing number, account, payment link, payee instruction or remittance address. Display correspondence addresses are not instructions to send funds. A future accepted payment instruction must come from the verified issuer through an approved process; it cannot be inferred from the `.invalid` contact or a designer's footer.

For case-review purposes, a dispute shall identify the invoice ID, disputed source field, reason and supporting record. The preparer shall retain the original statement and issue a separately versioned proposed correction rather than silently alter the evidence. This clause is a proposed administrative correction procedure, not a newly executed customer dispute term, late-charge covenant or waiver of rights. No interest, penalty, collection fee or acceleration is added because the source does not establish one.

If the legal issuer or customer identity is later completed, the accepted decision must identify the affected field IDs and the exact proposal version. A correspondence change must not change customer identity or create another ledger customer. The original native IDs and release lineage shall survive any approved successor presentation. Corrections must also retain the distinction between commercial agreement, invoice, accounting event and payment evidence.

## 6. Separate retrospective reconciliation attachment

The accepted source packet follows five later movements after original billing: a $435,000 February receipt, a $1,305,000 June writeoff, a $14,500 July credit, a $145,000 August credit and a $174,000 October recovery. These are synthetic scenario events, not bank confirmations. This attachment permits a reader to compare the proposed billing face with the accepted accounting packet; it does not rebill the customer or create new postings.

The source collected total is $609,000 and already includes the $174,000 recovery. Total credits are $159,500. Ledger receivable remaining is zero following the writeoff; the derived surviving written-off claim is $971,500 after later credits and recovery. The claim is not an asset newly recognized by this instrument. A zero receivable does not certify that the invoice was paid in full. Adding recovery a second time to the collected total would overstate cash.

The July credit's source reason is SLA_SERVICE_CREDIT; its existence does not provide the complete customer SLA. The August amendment reference SYN-AMEND-003 and version change are synthetic model records, not a signature or an executed amendment supplied by this proposed invoice. Neither credit creates a cash refund in the selected packet. Original source events, including `base-01-INVOICE-INV-base-FF-003-TERM-0`, retain their journal linkage without a second invoice population.

## 7. Delivery, privacy and evidence record

This is a public synthetic review instrument. It shall contain no real customer contact, account credential, employee payment information, signature image or private assessment answer. The `.invalid` addresses remain text-only display references. A reviewer may compare the proposed fields with the pinned dependency and inspect the accepted packet's original source rows. Repetition across PDF, Markdown, JSON or a workbook does not provide independent corroboration.

The case record shall preserve proposal ID/version, dependency hash, original packet path/hash, release source revision and each proposed field's status. Proposed addresses and display names must not propagate into accepted enterprise geography, legal entity registers or customer source tables through catalog generation. A database index may link this draft while retaining its review status; it shall not normalize null legal names into guessed entities.

## 8. Acceptance schedule and unresolved material fields

The exact proposal requires owner review with accepted or rejected field IDs. **BILL-DEC-001** remains the customer legal identity choice, **BILL-DEC-002** the invoice-specific issuer presentation/assignment, and **BILL-DEC-003** the tax-treatment decision. The proposal keeps its customer legal-name and invoice issuer-presentation fields null and supplies no tax scenario; Sable Harbor, LLC remains the established SHI legal identity. This document does not resolve those decisions by rendering a more realistic page.

Execution, signature, delivery to a customer, receipt of payment and current legal enforceability remain unestablished. If the owner accepts selected display fields, the acceptance record shall identify the version and hashes and state that accepted source amounts and the frozen packet cannot be overwritten. Any new design still requires exact-file review. The artifact is useful as a proposed billing document and an invoice-to-ledger reading aid; it is not an instruction to pay or evidence of a real sale.

## Source record and approval boundary

- [Accepted billing decision reconciliation](../../evidence/proposals/decision-register.json)
- [Accepted SHI entity identity](../../../../industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md)
- [docs/legal/gap-instruments/dependencies/billing-proposal-PR138.json](../../../../docs/legal/gap-instruments/dependencies/billing-proposal-PR138.json)
- [docs/finance/evidence/SH-FIN-HUMAN-001/source.json](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json)
- [docs/finance/evidence/SH-FIN-HUMAN-001/PACKET.md](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/PACKET.md)
- [docs/finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json)

No signatures, payments, provider acceptance or external filing are established by this draft. Its proposed clauses become neither accepted canon nor effective obligations through rendering, indexing or validation. Approval must identify the exact instrument and any completed schedules.
