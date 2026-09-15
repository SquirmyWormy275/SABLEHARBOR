# Proposed billing details — Foundry Field invoice FF-003

**Proposal:** SH-FIN-BILL-PROP-001 v0.1.0 · **State:** draft for owner review. Every proposed field has state `PROPOSED_SCENARIO_DETAIL`. These details are not accepted company or released accounting facts.

This is a concrete dataset for one separately labelled reconstructed invoice: `INV-base-FF-003-TERM-0`, base scenario, customer `SYN-CUSTOMER-003`. It does not change the existing accounting evidence memo or authorize new visual design. Review the [machine-readable proposal](proposal.json); the source-value snapshot and proposed fields occupy separate objects so an overlay cannot silently overwrite the release.

## Preserved accounting evidence

The [pinned packet source](https://github.com/SquirmyWormy275/SABLEHARBOR/blob/59201ccfa6a302e19c766694b3160fe8e9b942a4/docs/finance/evidence/SH-FIN-HUMAN-001/source.json) has SHA-256 `c4833cfc6f28db6cd3edcae761b0e2d8f463a20de79f1d6fd5b0c517f8f829b7` at commit `59201ccfa6a302e19c766694b3160fe8e9b942a4`. Its native origin is business-operations-v1.0.0, source `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`; the proposal records release and member hashes. The packet commit is provenance for these extracted rows, not an assertion about its approval state.

- Original invoice amount: **USD 1,740,000.0000**; source issue month **1**; source due date **February 28, 2027**.
- Contract FF-003: 140 seats, 12-month initial term, monthly subscription USD 145,000. Source invoice amount remains unchanged.
- Source January posting period: **January 31, 2027**; legal-book entity code **SHI**. A month-end accounting period is not proof of an exact document issue date.
- Proposed document issue date: **January 31, 2027**, explicitly new scenario detail. The release itself supplies `issue_month`, not an exact invoice issue-date field. The proposed date does not change posting dates, due date, service timing, collections, credits, write-offs or later balances.

The released invoice row summarizes later movements as well as its original amount. Those eventual collections and losses must not appear as facts known on the proposed issue date. The original invoice amount is not automatically its later outstanding balance.

## Proposed display details versus source

The source supplies customer/contract IDs, accounting code and monetary/period fields. It does not supply the following independent billing-master fields. Foundry Field is an accepted business identity, but its placement as the issuer brand on this reconstruction is still a proposed presentation choice.

| Proposed field | Released billing-master value | Proposed value or treatment | Basis and limits |
|---|---|---|---|
| `customer.display_name` | No separate source field | Copperreach Fabrication | New fictional display name for existing SYN-CUSTOMER-003; no new customer ledger row. |
| `customer.billing_address` | No separate source field | 1840 Quarry Exchange; Suite 210; Sacramento, CA 95814; United States | Invented correspondence address for this scenario only; no geocoding, site, property, occupancy or postal-delivery claim. |
| `customer.billing_attention` | No separate source field | Accounts Payable | Functional addressee; no named employee or authorization grant. |
| `customer.display_contact` | No separate source field | accounts-payable@copperreach.invalid | Display-only fictional contact; not an endpoint to deploy or contact. |
| `customer.purchase_order` | No separate source field | CRF-2027-FF003-001 | Invented display reference; no existing approval document or new procurement authorization. |
| `customer.legal_name` | No separate source field | Not established — retain null | Retain customer ID and display name only; no incorporation suffix, jurisdiction or executed party identity inferred. |
| `issuer.brand` | No separate source field | Foundry Field | Use existing business identity; this field proposes invoice presentation, not a new logo or legal entity. |
| `issuer.billing_address` | No separate source field | 240 Harbor Works Avenue; Billing desk — Foundry Field; Sacramento, CA 95814; United States | Invented display-only correspondence address; not the campus location, a registered office, a service site or a proposed geography-register addition. |
| `issuer.display_contact` | No separate source field | billing@foundry-field.invalid | Display-only fictional contact; no live service or remittance endpoint. |
| `issuer.legal_name` | No separate source field | Not established — retain null | Present source legal-book code SHI with legal issuer name unestablished for this reconstructed instrument; do not make Foundry Field a subsidiary. |
| `invoice.display_issue_date` | No separate source field | 2027-01-31 | Proposed documentary date aligned to first posting period; source issue_month is 1 and source has no exact issue-date field. |
| `invoice.service_description` | No separate source field | Foundry Field subscription — initial 12-month term, 140 seats | Plain-language rendering of contract FF-003; does not add SLA terms, acceptance or implementation deliverables. |
| `invoice.tax_presentation` | No separate source field | Tax treatment not established in the source; no separate tax amount represented. | Do not show zero tax, exemption, tax ID, inclusive/exclusive election or recompute the released amount. |
| `invoice.payment_instructions` | No separate source field | Not supplied in this reconstruction. | No bank, routing, account, payment link, remittance address or payee instruction. |

The two street addresses are invented correspondence strings, not sites. They must not enter the geography register or imply campus occupancy, postal delivery, legal domicile or nexus. Display contacts are inert `.invalid` strings. No bank details, telephone contacts, hosted payment pages, signatures or remittance instructions are proposed.

## Decisions for this batch

- **BILL-DEC-001 — customer legal party:** recommend keeping Copperreach Fabrication as a display name, with no legal suffix or registration assertion. Choosing an incorporated counterparty requires a separate explicit fictional party decision.
- **BILL-DEC-002 — seller legal identity:** use Foundry Field branding and preserve SHI accounting linkage, but leave the legal issuer name unresolved. The existing business dossier and organization source do not establish Foundry Field as a separate legal entity. A formally executed seller name needs the controlling legal-party record.
- **BILL-DEC-003 — tax:** recommend an explicit missing-tax-treatment note, no zero/exempt claim, and no separate tax calculation. A tax-bearing scenario would require a separately reviewed financial assumption and cannot be hidden in document styling.

## Acceptance and next use

Review the names, invented addresses, contact strings, PO and documentary date as one field-labelled proposal. Acceptance must identify this version and the exact proposal JSON hash, list any rejected or revised field IDs, and be preserved in a dated repository acceptance record. A changed proposal receives a successor version/hash. Approval of ordinary display details does not resolve the three legal/tax treatments or approve a PDF/workbook design.

Only after that review may a separate reconstruction consume the accepted fields, with its synthetic status visible and source/proposed lineage retained. Keep this PR draft; no shared catalog or financial-source mutation is part of this proposal. The small [manifest](manifest.json) identifies this dataset and its Markdown review surface. Future integration can add discovery metadata without turning proposed fields into booked evidence.

Controlling boundaries: [maintainer authority](../../../../MAINTAINERS.md), [finance handoff](../../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md), [Foundry Field dossier](../../../business-lines/FOUNDRY_FIELD.md), [identity inventory](../../../../assets/brand/README.md), and [Foundry/Foundry Field legal-form boundary](../../../organization/FOUNDRY_AND_FOUNDRY_FIELD.md). Existing logos and financial release bytes remain unchanged.
