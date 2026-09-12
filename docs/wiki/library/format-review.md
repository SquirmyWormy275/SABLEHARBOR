# Document-format review queue

[Library](../Library.md)

Generated reconciliation queue, not an assertion that every unpaired record lacks a publication. The repository maintainer owns reconciliation of this queue; these work queues are not in-universe appointments. Review other domain manifests and release members before proposing new documents. Historical releases remain immutable. Native accounting record completeness is outside this discovery index.

| State | Records |
|---|---:|
| COUNTERPART_REVIEW_REQUIRED | 20 |
| HISTORICAL_COUNTERPART_UNRESOLVED | 57 |
| NAVIGATION_ALIAS_NO_PUBLICATION | 3 |
| READER_MAINTENANCE_NO_LETTERHEAD | 113 |
| READER_OR_MAINTENANCE_PAGE | 140 |
| UNRESOLVED_DOCUMENT_COUNTERPART | 227 |
| VERIFIED_ACCEPTED_EVIDENCE_PACKET | 1 |
| VERIFIED_CHART_PUBLICATION | 40 |
| VERIFIED_DOCUMENT_PAIR | 131 |
| VERIFIED_IDENTICAL_SOURCE_PUBLICATION | 3 |

## Records requiring counterpart reconciliation

Finance records route to [SH-FIN-HUMAN-001](../../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md). Other corporate records require scoped format review before any batch rendering. Existing approved visuals are retained; this queue does not authorize automatic publication.

- [Branch and Pull Request Register](../../audit/BRANCH_AND_PR_REGISTER.md) — SH-FIN-HUMAN-001
- [Outstanding issue review — September 12, 2026](../../audit/ISSUE_CLOSEOUT_2026-09-12.md) — SH-FIN-HUMAN-001
- [Accounting, finance and audit practice](../../finance/READER_EXERCISES.md) — SH-FIN-HUMAN-001
- [Current industrial transaction and tax support](../../finance/evidence/tax-transaction/TRANSACTION_SUPPORT.md) — SH-FIN-HUMAN-001
- [Actionable CCF procedure deltas](../../internal/development/CCF_ACTIONABLE_CONTROL_DELTAS_2026-09-12.md) — Corporate document-format reconciliation
- [ARU share purchase, closing and tax bridge](../../legal/evidence/assets-rights/SH-LEGAL-READ-ARU-001.md) — SH-FIN-HUMAN-001
- [Cradle host rights and material title](../../legal/evidence/assets-rights/SH-LEGAL-READ-HOST-001.md) — SH-FIN-HUMAN-001
- [Northern Nevada planning deed and cost boundary](../../legal/evidence/assets-rights/SH-LEGAL-READ-NV-001.md) — SH-FIN-HUMAN-001
- [Red Wash purchase and closing-rights schedule](../../legal/evidence/assets-rights/SH-LEGAL-READ-RW-001.md) — SH-FIN-HUMAN-001
- [Campus and operating-site tenure review](../../legal/evidence/assets-rights/SH-LEGAL-READ-TENURE-001.md) — SH-FIN-HUMAN-001
- [Advisory engagement and outcome terms](../../legal/evidence/commercial/SH-LEGAL-READ-ADV-001.md) — SH-FIN-HUMAN-001
- [Atlas licensing and amendment evidence](../../legal/evidence/commercial/SH-LEGAL-READ-ATL-001.md) — SH-FIN-HUMAN-001
- [Colocation orders and SLA review](../../legal/evidence/commercial/SH-LEGAL-READ-COLO-001.md) — SH-FIN-HUMAN-001
- [Taylor–Red Wash service terms](../../legal/evidence/commercial/SH-LEGAL-READ-IC-001.md) — SH-FIN-HUMAN-001
- [Financing approvals and capital boundaries](../../legal/evidence/corporate/SH-LEGAL-READ-CAPITAL-001.md) — SH-FIN-HUMAN-001
- [Advisory carry and workforce instrument boundaries](../../legal/evidence/corporate/SH-LEGAL-READ-CARRY-001.md) — SH-FIN-HUMAN-001
- [Legal entities and separate books](../../legal/evidence/corporate/SH-LEGAL-READ-ENTITY-001.md) — SH-FIN-HUMAN-001
- [ARU transition and retention obligations](../../legal/evidence/corporate/SH-LEGAL-READ-HR-001.md) — SH-FIN-HUMAN-001
- [Facility atlas controlled releases](../../releases/FACILITY_ATLAS_RELEASES.md) — Corporate document-format reconciliation
- [Geo canon reconciliation and program closeout matrix](../../../geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md) — Corporate document-format reconciliation

## Dated counterpart dispositions

The [complete dated audit](../../reader/reconciliation/README.md) records verified artifacts, maintenance exemptions and unresolved document counterparts. Its dispositions are applied only while each source hash matches; changed sources return to review. The database table `reader_counterpart_audit` retains the exact evidence for each applied row.
