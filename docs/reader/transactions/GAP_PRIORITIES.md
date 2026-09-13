# Legal evidence priorities for the reader exercises

This is a reader implementation queue, not a new legal gap register. The [existing 17-gap register](RECONCILIATION.md) retains every disposition. Recommendations below refer to the same stable IDs; no gap is closed, missing instrument supplied, or fictional outcome adopted.

The immediate work is to make existing debt, retention, ordinary-inbound contract, conditional tax and proposed colocation records easier to use. The acquisition-accounting, invoice-to-ledger and contract-obligations routes do not need invented agreements. Five items support use of existing sources now, two justify owner review only if the invoice scenario expands, and ten do not warrant new documents for these routes.

The [structured companion](gap-priorities.json) records ranks, source hashes and the audited accepted main revision `f7c9da881176da19901fe5ec6e776f0fd8719a39` (September 12, 2026). It is a dated prioritization overlay. If accepted sources change, re-audit affected entries; do not treat this snapshot as a live approval register. All linked source paths below are repository-relative.

PR #138 was OPEN and unmerged at `e4995ba59d5eeab46fc6e6dd09bcf4b43efa2df4` when checked. Its existing billing proposal remains the only proposal to review. The accepted Foundry Field packet’s later acceptance record controls its release status despite historical draft wording in its pinned source JSON. New field adoption and new visual approval remain separate.

## Order of work

| Rank | Gap | Action |
|---:|---|---|
| 1 | [LEGAL-GAP-DEBT-LIENS](#legal-gap-debt-liens) | Use existing sources |
| 2 | [LEGAL-GAP-WORKFORCE](#legal-gap-workforce) | Use existing sources |
| 3 | [LEGAL-GAP-URANIUM-CUSTODY](#legal-gap-uranium-custody) | Use existing sources |
| 4 | [LEGAL-GAP-TAX-FILING](#legal-gap-tax-filing) | Use existing sources |
| 5 | [LEGAL-GAP-COLO](#legal-gap-colo) | Use existing sources |
| 6 | [LEGAL-GAP-BILLING](#legal-gap-billing) | Review only if expanding |
| 7 | [LEGAL-GAP-TAX-BILLING](#legal-gap-tax-billing) | Review only if expanding |
| 8 | [LEGAL-GAP-RW-CHRONOLOGY](#legal-gap-rw-chronology) | Defer new documents |
| 9 | [LEGAL-GAP-LAND](#legal-gap-land) | Defer new documents |
| 10 | [LEGAL-GAP-RW-TITLE](#legal-gap-rw-title) | Defer new documents |
| 11 | [LEGAL-GAP-FORMATIONS](#legal-gap-formations) | Defer new documents |
| 12 | [LEGAL-GAP-ADVISORY-CONTRACTS](#legal-gap-advisory-contracts) | Defer new documents |
| 13 | [LEGAL-GAP-HOST-RIGHTS](#legal-gap-host-rights) | Defer new documents |
| 14 | [LEGAL-GAP-FINANCING-DOCUMENTS](#legal-gap-financing-documents) | Defer new documents |
| 15 | [LEGAL-GAP-TENURE](#legal-gap-tenure) | Defer new documents |
| 16 | [LEGAL-GAP-CARRY](#legal-gap-carry) | Defer new documents |
| 17 | [LEGAL-GAP-MARK-CLEARANCE](#legal-gap-mark-clearance) | Defer new documents |

## LEGAL-GAP-DEBT-LIENS

ARU closing delivery ARU-CL-03 and transaction accounting identify debt payoff, retained leases and funding separately.

**Task unlocked:** A closing sources-and-uses reconciliation with a separate column for independently unsupported balances.

**Usable now:** Use the native finance schedule and closing statement; label modeled balances and retain the retained-lease distinction.

**Next action:** Link the debt/payoff and lease rows into the acquisition route. Seek a specific lender confirmation or release only if the exercise later tests discharge of security.

**Acceptance boundary:** No new instrument is needed for the current route. A fictional confirmation would require separate owner acceptance.

**Sources:** [05_ARU_CLOSING_AND_TAX_DELIVERY.md](../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md), [TRANSACTION_ACCOUNTING.md](../../../industrial/finance/TRANSACTION_ACCOUNTING.md), [finance.json](../../../industrial/source/finance.json).

## LEGAL-GAP-WORKFORCE

The transition instrument names eight retention allocations and Fred Tolman’s separate nine-month consultancy; it does not confirm cash payment.

**Task unlocked:** A service-compensation versus acquisition-consideration comparison and a schedule of future service conditions.

**Usable now:** Use the retention table, consultancy scope and native finance schedules without adding employees or treating modeled payment timing as bank evidence.

**Next action:** Point readers to the retention and consultancy sections; request only the individual service/payment evidence needed for a subsequently selected payment test.

**Acceptance boundary:** New employment originals, signatures or payment facts require separate source and owner acceptance.

**Sources:** [06_ARU_TRANSITION_AND_RETENTION.md](../../../industrial/transaction/06_ARU_TRANSITION_AND_RETENTION.md), [PEOPLE_AND_CULTURE_DOCTRINE.md](../../../docs/governance/PEOPLE_AND_CULTURE_DOCTRINE.md), [LABOR_SAFETY_AND_CONTROLS.md](../../../industrial/operations/LABOR_SAFETY_AND_CONTROLS.md), [finance.json](../../../industrial/source/finance.json).

## LEGAL-GAP-URANIUM-CUSTODY

The July 7 logistics summary contains rates, clocks, invoice requirements and exclusions; direct uranium-product custody remains OPEN_GATED.

**Task unlocked:** A duty-to-evidence review and, separately from the Foundry Field invoice route, a possible future intercompany billing comparison.

**Usable now:** Use ordinary-inbound service terms only; a planned slot is not a shipment, and a future service period is not performed service.

**Next action:** Extract the existing ordinary-inbound obligations for the contract route. Leave uranium transport adoption outside this queue.

**Acceptance boundary:** Any new product-custody service requires separate operating, legal, safety, insurance and owner authorization.

**Sources:** [08_INTERCOMPANY_LOGISTICS_AGREEMENT.md](../../../industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md), [operations.json](../../../industrial/source/operations.json).

## LEGAL-GAP-TAX-FILING

ARU-CL-07 establishes an internal filing-ready review, not external submission or acceptance.

**Task unlocked:** Identify which acquisition-model conclusions depend on an unproved election and what evidence would change that assessment.

**Usable now:** Use the existing tax memorandum and conditional allocation. Retain the no-election alternative as an analysis boundary; do not describe it as a separately delivered workbook.

**Next action:** Include the filing-ready distinction in the acquisition route. If a later case needs a resolved outcome, obtain an accepted dated filing-status record through LEGAL-FIELD-005.

**Acceptance boundary:** A newly authored fictional filing outcome needs owner acceptance; never manufacture a government confirmation.

**Sources:** [05_ARU_CLOSING_AND_TAX_DELIVERY.md](../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md), [07_ARU_TAX_STRUCTURE_MEMORANDUM.md](../../../industrial/transaction/07_ARU_TAX_STRUCTURE_MEMORANDUM.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-COLO

The dossier supplies a proposed master, site orders and schedules; selected provider brands are not verified contracting parties.

**Task unlocked:** A draft-contract readiness review, including who must approve price, scope, technical delivery and evidence rights.

**Usable now:** Use the unsigned dossier beside accepted runtime decisions; calculate illustrative examples only in their stated draft/assumption status.

**Next action:** Link the proposed schedules as an optional contract comparison; route legal-party/order evidence to existing LEGAL-FIELD-004 before any executed-order scenario.

**Acceptance boundary:** Provider confirmation is missing. New fictional executed terms or acceptance events require owner acceptance.

**Sources:** [CONTRACT_DOSSIER.md](../../../enterprise/runtime/docs/CONTRACT_DOSSIER.md), [RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md](../../../docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-BILLING

PR138 holds the existing field-level proposal; its customer identity and presentation fields are not adopted on the audited main.

**Task unlocked:** A future fully addressed invoice example after field adoption and separate visual acceptance.

**Usable now:** Use the exact accepted Foundry Field packet, source invoice ID and customer ID with unavailable fields left explicit.

**Next action:** Review the existing proposal version 0.1.0 and SHA-256 23d8d6080ad296468d6b649eda55593d49c33cde0e6b038343ce11e4973e23f8; record accepted/rejected field IDs. Do not create another billing proposal.

**Acceptance boundary:** Owner acceptance of fields is distinct from acceptance of any changed PDF or workbook.

**Sources:** [READER_OVERNIGHT_SCOPE_2026-09-11.md](../../../docs/canon/READER_OVERNIGHT_SCOPE_2026-09-11.md), [source.json](../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json), [FINANCE_HUMAN_EVIDENCE_001_ACCEPTANCE_2026-09-11.md](../../../docs/canon/FINANCE_HUMAN_EVIDENCE_001_ACCEPTANCE_2026-09-11.md).

## LEGAL-GAP-TAX-BILLING

The packet has no independent tax-master determination; the entity register does not resolve all parent tax treatment.

**Task unlocked:** A future tax-bearing invoice scenario with an explicit basis and reconciled financial effect.

**Usable now:** Trace existing booked amounts unchanged and record tax treatment as unavailable, not zero or exempt.

**Next action:** Keep tax out of the current route. If tax testing is requested, scope one separate proposed scenario through BILL-DEC-003 / LEGAL-FIELD-003 with affected amounts identified.

**Acceptance boundary:** Owner acceptance and an adequate source basis are required before adopting new treatment or amounts.

**Sources:** [entities.json](../../../industrial/source/entities.json), [source.json](../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-RW-CHRONOLOGY

Industrial and mine sources disagree on pre-close day precision; both preserve the closing date and selected consideration.

**Task unlocked:** A later dated negotiation-history case, once the conflicting event identities are resolved.

**Usable now:** Use the agreed closing date and amount; present earlier events without selecting one disputed exact day.

**Next action:** If a chronology exercise is commissioned, prepare a dated correction matching each disputed event across both sources for owner review.

**Acceptance boundary:** Do not silently choose dates or rewrite pinned history; accepted correction is required.

**Sources:** [01_RW_TRANSACTION_FILE.md](../../../industrial/transaction/01_RW_TRANSACTION_FILE.md), [TRANSACTION_AND_COMMERCIAL_INSTRUMENTS.md](../../../red_wash/agreements/TRANSACTION_AND_COMMERCIAL_INSTRUMENTS.md), [INDUSTRIAL_CLOSEOUT_2026-09-05.md](../../../docs/canon/INDUSTRIAL_CLOSEOUT_2026-09-05.md), [RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md](../../../docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md), [chronology.json](../../../industrial/source/chronology.json), [core_operating_data.json](../../../red_wash/source/core_operating_data.json).

## LEGAL-GAP-LAND

Accepted runtime canon establishes the fictional acquisition; the finance successor explicitly leaves settlement unresolved.

**Task unlocked:** A future land-to-clearing reconciliation, followed by a settlement test only when funding evidence exists.

**Usable now:** Use the $3M planning event and unresolved settlement clearing; the mock deed is neither a bank record nor real title evidence.

**Next action:** For an optional land case, link the existing finance bridge. Request a source-specific settlement record through LEGAL-FIELD-009 before proposing a cash, loan or payable counterpart.

**Acceptance boundary:** Do not reopen accepted fictional ownership. New settlement facts need separate acceptance.

**Sources:** [RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md](../../../docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md), [MOCK_DEED_NORTHERN_NEVADA_DATA_CENTER_2026-09-04.md](../../../docs/legal/MOCK_DEED_NORTHERN_NEVADA_DATA_CENTER_2026-09-04.md), [RUNTIME_INFRASTRUCTURE_FINANCE_RECONCILIATION_2026-09-11.md](../../../docs/finance/RUNTIME_INFRASTRUCTURE_FINANCE_RECONCILIATION_2026-09-11.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-RW-TITLE

The mine instrument lists transfer limits, scheduled rights and title/environmental escrow mechanics; it does not prove every consent or cure.

**Task unlocked:** A future closing-deliverable completeness test for one selected easement, permit or consent.

**Usable now:** Use the instrument and native permit register to identify what must be evidenced, retaining any transfer limitation.

**Next action:** Choose one right and trace its native record before requesting a specific consent/cure artifact; preserve the escrow boundary until actual support is accepted.

**Acceptance boundary:** New fictional consents or completed cures require owner acceptance; an instrument list is not confirmation.

**Sources:** [TRANSACTION_AND_COMMERCIAL_INSTRUMENTS.md](../../../red_wash/agreements/TRANSACTION_AND_COMMERCIAL_INSTRUMENTS.md), [core_operating_data.json](../../../red_wash/source/core_operating_data.json).

## LEGAL-GAP-FORMATIONS

The accepted six-entity formation record and entity register establish the fictional company chain and source-status limits.

**Task unlocked:** Identify buyer, target, parent and separate operating ledgers without equating a business-line name with a corporation.

**Usable now:** Use the internal formation record and legal entity IDs; preserve year precision where exact formation day is not established.

**Next action:** Link the internal formation record as background; do not commission certificates, seals, state file numbers or government replicas.

**Acceptance boundary:** No new document or owner decision is needed for the current exercise.

**Sources:** [LEGAL_STRUCTURE_AND_FORMATION.md](../../../industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md), [entities.json](../../../industrial/source/entities.json).

## LEGAL-GAP-ADVISORY-CONTRACTS

The term sheet specifies contract architecture and the pricing standard supplies policy, not universal executed customer agreements.

**Task unlocked:** A future policy-to-SOW completeness comparison for a selected accepted matter.

**Usable now:** Use the standards as requirements, or choose the existing logistics contract route for actual case-specific terms.

**Next action:** First select a matter already represented in an accepted scenario, then identify missing SOW fields; only prepare proposed missing terms if that extension is requested.

**Acceptance boundary:** Matter parties, negotiated terms and execution status cannot be inferred from the standard.

**Sources:** [LEGAL_AND_CONTRACTING_TERM_SHEET.md](../../../docs/advisory/LEGAL_AND_CONTRACTING_TERM_SHEET.md), [COMMERCIAL_CONTRACTING_AND_PRICING_STANDARD.md](../../../docs/advisory/COMMERCIAL_CONTRACTING_AND_PRICING_STANDARD.md).

## LEGAL-GAP-HOST-RIGHTS

Canon establishes host authority, equipment ownership and capture-point rights while intentionally leaving permanent price, percentage and tonnage unfixed.

**Task unlocked:** A future recovery-rights and host-settlement exercise tied to one explicitly selected quantitative case.

**Usable now:** Use the accepted rights boundary; keep quantitative model assumptions inside their selected scenario.

**Next action:** If extending into host settlement, identify the accepted model and its assumption lineage before requesting a scoped agreement through LEGAL-FIELD-006.

**Acceptance boundary:** Do not convert scenario percentages into permanent canon or host assets into Sable Harbor property.

**Sources:** [CRADLE_CLOSEOUT_2026-09-06.md](../../../docs/canon/CRADLE_CLOSEOUT_2026-09-06.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-FINANCING-DOCUMENTS

Board minutes record approximate financing approvals and governance boundaries, not complete subscription agreements or side letters.

**Task unlocked:** A later board-approval versus definitive-financing-document comparison.

**Usable now:** Use minutes only for what the Board approved; avoid invented thresholds, dilution mechanics or exact investment terms.

**Next action:** Search for a separately accepted definitive source if that exercise is selected; otherwise retain the minutes and gap without generating financing paper.

**Acceptance boundary:** New definitive fictional terms require owner acceptance.

**Sources:** [2021-06-18_harrison-vale-growth-financing-minutes.md](../../../docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md), [2022-10-28_wolf-ridge-industrial-financing-minutes.md](../../../docs/governance/board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md).

## LEGAL-GAP-TENURE

Facility coverage and concept programs distinguish modeled plans from parcel tenure, occupancy dates and construction evidence.

**Task unlocked:** A future site-specific lease or property-record review after a tenure source is accepted.

**Usable now:** Use the coverage record to report known site function and exact status; never use a render date as lease or occupancy date.

**Next action:** Select a stable site ID and obtain the unresolved tenure evidence through LEGAL-FIELD-007 before preparing lease abstraction material.

**Acceptance boundary:** New tenure dates, leases, or construction completion are not authorized by this prioritization.

**Sources:** [README.md](../../../geospatial/facilities/README.md), [RESEARCH_CAMPUSES.md](../../../geospatial/facilities/RESEARCH_CAMPUSES.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-CARRY

The carry standard governs phantom economics and eligibility; it does not grant units or settle counsel drafting.

**Task unlocked:** A future eligibility and grant-authority exercise after an eligible award has an accepted source.

**Usable now:** Use the plan as policy only; no individualized serving-J2 preview or implied equity grant.

**Next action:** Retain LEGAL-FIELD-008 for any future instrument request; obtain eligibility and authority before proposing an individual award.

**Acceptance boundary:** Counsel-ready terms and specific owner acceptance are needed before new fictional grants.

**Sources:** [CARRY_PLAN_STANDARD.md](../../../docs/advisory/CARRY_PLAN_STANDARD.md), [decision-register.json](../../../docs/legal/evidence/proposals/decision-register.json).

## LEGAL-GAP-MARK-CLEARANCE

The operating name is accepted; external clearance and registration remain distinct and unestablished.

**Task unlocked:** No current reader task requires a new trademark artifact.

**Usable now:** Use Sable Harbor Advisory as the accepted operating name with the existing clearance-status boundary.

**Next action:** Retain the status note. Qualified external review is only needed if real commercialization is pursued.

**Acceptance boundary:** Do not invent a clearance opinion, filing or registration, or reopen the operating name.

**Sources:** [ADVISORY_NAME_AND_EXTERNAL_CLEARANCE_STATUS_2026-09-09.md](../../../docs/legal/ADVISORY_NAME_AND_EXTERNAL_CLEARANCE_STATUS_2026-09-09.md).
