# Legal and billing fields awaiting evidence or review

This reconciliation supplies no new legal-party names, addresses, grant amounts, tax rates or contract clauses. It connects existing source facts and missing fields to the one retained billing proposal and the legal missing-record register.

[PR #138](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/138) remains unaccepted. Its JSON SHA-256 is `23d8d6080ad296468d6b649eda55593d49c33cde0e6b038343ce11e4973e23f8` at commit `e4995ba`. The proposal is referenced, not copied, adopted or rendered into a new invoice.

[Field-level register](decision-register.json) · [Legal missing records](../../../reader/transactions/RECONCILIATION.md)

## Parent identity versus invoice presentation

The accepted legal register already identifies SHI as Sable Harbor, LLC. PR #138 must not be interpreted as reopening that identity. Its invoice-specific legal-issuer presentation remains distinct from the established entity and the source accounting code. No invoice field is adopted here.

## LEGAL-FIELD-001 — invoice.customer.legal_name

**Source value:** Not established at this field level.

No new value proposed; retain native customer ID and the unaccepted BILL-DEC-001 route.

**Next action:** Exact owner adoption of a separately specified fictional legal party, if wanted.

[Source](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json) · Decision route `BILL-DEC-001`

## LEGAL-FIELD-002 — invoice.issuer.legal_name

**Source value:** SHI entity register maps to Sable Harbor, LLC; the invoice source separately carries SHI accounting linkage.

Do not claim a new entity or reopen its established legal name. Keep proposal BILL-DEC-002 about instrument-level issuer presentation/assignment, not parent identity.

**Next action:** Resolve exact invoice issuer-field adoption without changing the legal entity register.

[Source](../../../../industrial/source/entities.json) · Decision route `BILL-DEC-002`

## LEGAL-FIELD-003 — invoice.tax_treatment

**Source value:** Not established at this field level.

Retain explicit absence; no zero/exemption/tax-ID or amount change.

**Next action:** Any tax-bearing scenario needs a separate source-bound assumption and financial impact review.

[Source](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json) · Decision route `BILL-DEC-003`

## LEGAL-FIELD-004 — runtime.provider_legal_name

**Source value:** Not established at this field level.

Keep Switch/IDACORE as selected brands; legal contracting entities remain null.

**Next action:** Procurement/Legal verify exact party before negotiated order execution.

[Source](../../../../enterprise/services/source/runtime_sites_2026-09-11.json) · Decision route `LEGAL-GAP-COLO`

## LEGAL-FIELD-005 — aru.form8023.submission_confirmation

**Source value:** Not established at this field level.

Retain filing-ready status and conditional model; do not fill a filing number or acceptance date.

**Next action:** Source a submission/status record; no invented government artifact.

[Source](../../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md) · Decision route `LEGAL-GAP-TAX-FILING`

## LEGAL-FIELD-006 — cradle.host_participation_percent

**Source value:** Not established at this field level.

No permanent canon percentage proposed. Use chosen quantitative model assumptions in their own scenario only.

**Next action:** Obtain scoped contract terms if an executed host agreement exercise is required.

[Source](../../../../docs/canon/CRADLE_CLOSEOUT_2026-09-06.md) · Decision route `LEGAL-GAP-HOST-RIGHTS`

## LEGAL-FIELD-007 — campus.lease_execution_date

**Source value:** Not established at this field level.

Retain per-site tenure gap, rather than assign the plan-render date as occupancy or lease date.

**Next action:** Accepted site-specific tenure source with effective date and precision.

[Source](../../../../geospatial/facilities/README.md) · Decision route `LEGAL-GAP-TENURE`

## LEGAL-FIELD-008 — advisory.carry.individual_grant

**Source value:** Not established at this field level.

No recipient or grant proposed. Current professional plan direction is not an allocation.

**Next action:** Completed former-J2 eligibility, individual grant authority and counsel instrument; no serving-person preview.

[Source](../../../../docs/advisory/CARRY_PLAN_STANDARD.md) · Decision route `LEGAL-GAP-CARRY`

## LEGAL-FIELD-009 — northern_nevada.land.settlement

**Source value:** Accepted fictional $3M acquisition with unresolved settlement clearing.

Preserve the acquisition. Do not invent cash, lender or payable settlement to fill the posting counterpart.

**Next action:** Source settlement/funding evidence independently of planning ownership.

[Source](../../../../docs/finance/RUNTIME_INFRASTRUCTURE_FINANCE_RECONCILIATION_2026-09-11.md) · Decision route `LEGAL-GAP-LAND`

## Review boundaries

Display-detail approval must identify the exact PR #138 proposal version/hash and accepted/rejected fields. It does not approve PDF/workbook design, a government filing, a new legal entity, tax treatment or altered release amounts. No payment endpoints or signatures are introduced.
