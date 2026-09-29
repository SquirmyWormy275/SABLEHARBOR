# Foundry Field tax determination and invoice-change workpaper draft

**Document ID:** SH-LEGAL-DRAFT-TAX-BILLING  
**Gap:** LEGAL-GAP-TAX-BILLING  
**Version:** 0.1.0  
**Prepared:** 2026-09-12  
**Status:** DRAFT_FOR_REVIEW — internal tax workpaper and proposed review procedure  
**Owner:** Finance / Tax Review / Legal  
**Effective date and approval:** not established for proposed procedure or tax treatment; no tax determination is adopted.

## 1. Transaction selected for review

The selected record is invoice `INV-base-FF-003-TERM-0`, customer `SYN-CUSTOMER-003`, contract `FF-003`, term `0`, business unit `foundry-field`, accounting entity `SHI`, in the base 2027 scenario. The [accepted packet source](../../../finance/evidence/SH-FIN-HUMAN-001/source.json) preserves the released fields. The [acceptance record](../../../canon/FINANCE_HUMAN_EVIDENCE_001_ACCEPTANCE_2026-09-11.md) applies to the exact existing human-readable packet; its acceptance does not supply absent tax facts.

The released invoice amount is $1,740,000. The source does not provide an independent tax-master determination, exact customer billing address, complete legal billing identity, tax registration or an adopted rate. The [existing billing proposal](../../evidence/proposals/decision-register.json) routes field decisions separately. A proposed fictional address, if later accepted, would not alone establish taxable situs, taxability, nexus, exemption or amount due.

The issuer's accounting key maps to Sable Harbor, LLC in the [entity register](../../../../industrial/source/entities.json). That accepted identity is not a resolution of every parent tax election or an instruction that the invoice should display a particular issuer field. The workpaper must keep entity identity, invoice presentation, sales/use-tax treatment and parent federal tax classification separate.

## 2. Intended workpaper conclusion

The current conclusion is **UNDETERMINED — required transaction facts and treatment evidence unavailable**. It is not zero-rated, exempt, tax-inclusive or taxable at a guessed rate. The released amount remains unchanged. A participant may complete the evidence inventory and proposed review procedure without fabricating a numerical tax result.

This workpaper uses the California tax authority only as a possible research starting point, because Sacramento headquarters does not determine every customer transaction's jurisdiction. CDTFA's sales/use-tax program distinguishes California sales tax and use tax and provides official guidance routes. The applicable jurisdiction, transaction classification and facts must be established before choosing relevant guidance or a rate. [CDTFA Sales and Use Tax in California](https://cdtfa.ca.gov/taxes-and-fees/sutprograms.htm), reviewed September 12, 2026. No conclusion about this invoice's taxability follows from that general reference.

## 3. Required fact schedule

| Field | Present source support | Required next evidence |
|---|---|---|
| Invoice and scenario identity | Exact IDs above | Confirm selected released version before review |
| Accounting entity | SHI linkage; accepted parent legal identity | Resolve instrument-level issuer presentation separately if needed |
| Customer legal party | Native synthetic customer ID only | Accepted legal-party record; no inferred company from a site label |
| Delivery/use location | Not established by this selected packet | Contract-specific delivery and use facts appropriate to the selected transaction |
| Supply components | Source contract/version records | Identify each actual promised item and allocation basis |
| Tax jurisdiction and obligation | Unestablished | Qualified review against complete transaction facts |
| Rate and effective period | Unestablished | Applicable dated authority after jurisdiction and treatment are determined |
| Exemption or resale basis | No independent support supplied | Applicable certificate or other accepted basis, if claimed |
| Tax inclusion in price | Not established | Controlling contract term or separately accepted scenario decision |
| Parent federal tax classification | Not fully resolved here | Separate governing tax records; do not borrow ARU assumptions |

A field marked unavailable would remain a null value in a financial derivative, with a readable explanation. It would not be stored as numeric zero merely because a spreadsheet requires a cell. A document that supports a customer's identity may not support its tax treatment; the reviewer would record the claim and evidence relationship explicitly.

## 4. Proposed determination procedure

The preparer would first freeze the selected transaction identity and list all relevant contract versions, credits and invoice movements. The preparer would separate source facts from proposed scenario additions and identify whether the requested review concerns original billing, a later credit, a writeoff or a recovery. These events can have different factual questions; a single undifferentiated “tax adjustment” would not be sufficient.

A qualified reviewer would identify the relevant jurisdictional framework only after delivery, use, parties and supply are established. The workpaper would record the official authority, applicable period, factual assumptions and conclusion for each component. It would not classify all Foundry Field activity from the business name or reuse another customer's determination without testing the factual match. This is a proposed internal process, not a legal or tax opinion.

If a supply contains multiple components, the reviewer would identify the accepted contract allocation or mark it unresolved. No percentage allocation is proposed simply to obtain a desirable tax amount. The reviewer would distinguish a stated contract price from a tax base and document whether an adopted treatment changes customer consideration, company expense or neither. An unresolved price-inclusion term would block a final calculation.

The determination would state its scope, effective period, supporting facts and conditions for reuse. It would also state what change requires review, such as an accepted contract amendment or a changed delivery fact. A commercial manager's approval of a credit would not replace the tax determination, and a tax reviewer would not silently amend the customer's commercial bargain.

## 5. Calculation schedule with no assumed rate

| Calculation field | Value for this draft | Treatment |
|---|---|---|
| Released invoice amount | $1,740,000 | Existing source amount, unchanged |
| Taxable component allocation | Unavailable | Requires supported classification and allocation |
| Applicable tax rate | Unavailable | No default rate or zero |
| Tax-exclusive versus tax-inclusive basis | Unavailable | Requires controlling price term |
| Calculated tax | Not calculated | Missing inputs prevent a supported result |
| Revised customer amount | Not calculated | No adopted change to released amount |
| Proposed posting | None | No new journal authorized |

For a future approved scenario, the workpaper would show each component's accepted base, dated rate, rounding convention and resulting amount. A tax-exclusive and a tax-inclusive calculation would not be mixed. Any formula would be applied only after the relevant inputs are accepted and would preserve the original invoice as a historical record. This draft deliberately supplies no illustrative tax percentage that might later be mistaken for a default.

The calculation reviewer would recompute totals independently and reconcile them to the proposed invoice and ledger effect. Differences would be explained by component and cause. A tax amount would not be inserted into the existing $1,740,000 total merely to make a rendered invoice look complete. Publication polish does not settle whether the original price included tax.

## 6. Credits, writeoff and recovery review

The selected packet contains a July service credit and an August amendment credit, with later movements in a written-off claim. The proposed tax review would trace each event by its source ID and contract version before concluding whether a tax adjustment is relevant. A credit affecting a written-off claim does not automatically create a cash refund, and a recovery already included in collected amounts must not be added again.

The reviewer would request any underlying customer agreement and applicable treatment evidence needed for the particular event. The released movement classification would remain unchanged until an accepted successor explicitly corrects it. This workpaper does not create customer consent, a tax refund claim or a right to recover tax from another party.

A proposed adjustment record would identify original invoice, affected event, reason, tax determination reference, commercial authority and accounting effect. Where tax facts remain unavailable, the event would be flagged for unresolved treatment rather than assigned an arbitrary tax code. Missing tax information does not authorize reversing a valid source credit or rewriting the release.

## 7. Proposed approval and implementation clauses

Before a new tax-bearing fictional scenario is adopted, the owner would accept its specifically identified new facts and financial effects. Finance would review the calculation and ledger bridge; Legal or the qualified tax reviewer would identify the source and limitations of the treatment. Billing presentation would be reviewed separately. Acceptance of a proposed customer name or address would not constitute acceptance of a tax rate, exemption or amount change.

The proposed implementation record would show the original released amount, each accepted adjustment, revised scenario amount and affected accounting entries. It would use a successor version and preserve the frozen packet's hashes. New customer-facing PDFs or workbooks would remain held for exact-file visual review. No approved packet is regenerated by this workpaper.

A reviewer would document acceptance, rejection or required changes at field level. If evidence remains insufficient, the correct disposition is to preserve the unresolved fields and stop numerical implementation. A deadline or a completed spreadsheet cannot substitute for missing facts. This proposed process creates no tax registration, filing or payment instruction.

## 8. Parent tax classification boundary

The industrial model's ARU S-corporation history, BS&T QSub assumption and intended acquisition election are transaction-specific. They do not establish SHI's federal classification or authorize copying ARU's modeled 25% rate into a Foundry Field invoice. The parent's LLC form and its Sacramento working base are separate from any tax election or customer transaction determination.

If parent classification becomes necessary for an exercise, the requester would identify the specific question and seek the governing source or a separately accepted fictional assumption. It would be recorded outside this invoice's tax calculation with its own scope and consequences. No tax identifier, government acceptance letter or election certificate would be invented to fill that need.

## 9. Review record and usable deliverables

The completed draft packet supplies a transaction-specific fact request, determination procedure, nonnumeric calculation schedule, change-control clauses and release-preservation instructions. It enables a reviewer to state precisely why a tax conclusion cannot yet be reached and what would permit one. It does not leave that problem hidden behind a generic “consult tax” label.

The review record would identify the preparer, technical reviewer, version, source inventory, unresolved fields and owner decisions. Proposed administrative timing is a five-business-day initial completeness review after receipt of a full fact packet; it is not a filing deadline or a promise that a tax opinion will be delivered in that period. No reviewer name, signature or completed approval is represented here.
