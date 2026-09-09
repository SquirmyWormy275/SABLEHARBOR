# Business, Finance and Alexandria interfaces

**Document ID:** `SH-BIZ-ALX-FIN-001`
**Version:** 1.0.0
**As of:** September 9, 2026
**State:** PROVISIONAL implementation contract
**Owner:** Business source owners / CFO office / Alexandria stewardship

## Purpose and ownership

This contract implements the content/source boundaries of issues #38 and #44. It uses the existing nine Pinakes doors and creates no new portal, entity, executive authority or entitlement. The machine-readable companion is `docs/structured/business-lines/interfaces.json`.

Each business owns its operating sources and accountable decisions. Its records steward works with Alexandria stewardship to publish a discoverable, appropriately cleared entry point. Finance owns ledger sources, analytical environments, assumptions, reconciliations and release of its numbers. The CFO office is accountable for Finance content; the Finance & Investment Committee owns its committee records and decision process, not the underlying operating books. Alexandria connects these records and their histories. It does not command business or finance execution.

Orientation’s Finance observation post can trace beliefs into assumptions, question them and publish its own authorized observation. It does not change the ledger, approve a forecast, release capital or direct Finance. Atlas can inform capital and operating decisions; the decision remains with the authorized human owner and governance process.

## Business entry contracts

Every row carries source, owner, steward, access, purpose, knowledge timing and the relationships to Canon, Judgment, Collection, JAG and Education. The seven dossier entries and Emberline history are explicit; historical Klein is reached through Willow and the historical boundary register.

| Entry | Source owner | Canon / Judgment / Collection relationship |
|---|---|---|
| Foundry Field | Foundry Field product and deployment leadership | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Atlas Meridian | Atlas product leadership / Simone Vale transition | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Willow | Gid Voss experimental authority / Rachel Sloane institutional seam | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Cradle | Cradle operating leadership and accountable host interfaces | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Pale Sun / Red Wash | Evan Vilander / Mari / Red Wash operating leadership | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| American Resource Utility / BS&T | Nora Ashcombe / Seth Kettering rail authority | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Advisory | Advisory accountable commercial leadership; permanent appointment open | Dossier locates current canon; decisions link to Judgment; underlying sources require independent Collection entitlement. |
| Emberline history | Corporate records and receiving business | Historical effective periods and transfers; later judgments do not rewrite contemporary knowledge; original restrictions persist. |

JAG links approved internal interventions and follow-up learning. Commercial Advisory is not JAG. Education uses cleared cases and learning material; a teaching copy does not carry privileged client files. Foundry’s representation of a claim or authority does not certify physical truth. Physical measurements retain methods, units, limitations and custody where relevant.

## Finance source contract

| Source class | Accountable owner | Authoritative purpose | Review route |
|---|---|---|---|
| Ledger and subledger | Controller | Legal/entity books and supported close | Reconciliation, preparer/reviewer, Finance release |
| Planning model | CFO office / model owner | Conditional scenario and assumptions | Assumption changes, sensitivity, analytical review |
| Capital record | Finance & Investment Committee records steward | Alternatives, reserved-matter review and recorded decision | Committee/Board authority under existing charter |
| Orientation observation | Finance owns observed sources; Orientation owns its observation | Challenge and understanding of beliefs expressed as numbers | Source entitlement and independent authored observation |

A finance assumption record carries assumption ID, units, scope, source/version, effective period, available-at date, owner, reason, range, status and supersession. It may link to a Judgment question, accepted Canon statement, Semaphore thread and after-action review. These links are references, not approval inheritance. A changed estimate preserves both its predecessor and the information available to each decision.

Ledger evidence retains legal entity, reporting unit, run, scenario, seed, period and source/master fingerprints. A model output also retains its calculation version and fact state. A synthetic calibrated balance, management forecast and observed measurement remain distinguishable. Numbers and charts never become physical truth merely by appearing on the Finance door.

## Access and release

The entry point may expose an approved summary and the existence of an appropriately discoverable record. Detailed access requires the source owner’s authorization for the reader, purpose, client/tenant and material. Collection detail is the most heavily gated; summary access never implies raw-source rights. Personnel, client contracts, restricted operational sources and private evaluator material retain their own boundaries.

The default for absent or unresolved detail entitlement is denial with a nonrevealing explanation and owner request route. Do not reveal restricted titles, snippets, counts or derived answers when that disclosure itself is disallowed. Daedalus operates only within disclosed material and does not alter an authoritative record. Atlas client workspaces do not acquire employee Pinakes or Collection rights.

For point-in-time reading, use both effective time and availability time. A retrospective record created September 9 about an earlier event cannot be presented as knowledge available before September 9 without an independently supported contemporary source. Corrections preserve predecessor IDs and reasons. Exact retention periods, deletion/legal-hold mechanics, runtime stack and executable Daedalus leakage defenses remain issues #21/#22/#24/#34; this content contract does not assert their deployment.

Publication requires source-owner clearance, current-source metadata, an approved-format controlled publication where required and regenerated manifest/catalog hashes. Generated catalogs locate sources; they do not approve them.

## Local common-control implementations

The following records consume business processes already described in the dossiers. They use existing CCF IDs and role accountability, and assert design scope rather than historical operating effectiveness.

### LC-REVENUE — SH-REV-003

Owner: Revenue accounting. Scope: foundry-field,atlas-meridian,advisory. Frequency: Every billing/close.

Match contract obligation and accepted event to invoice and journal; separately reconcile deferred/unbilled amounts. Advisory hours may support cost but never substitute for accepted outcomes.

Evidence population: contracts; acceptance; invoices; receipts; journal; AR/deferred rollforwards.

### LC-CREDIT — SH-REV-005

Owner: Finance collections. Scope: commercial businesses. Frequency: Monthly and dispute event.

Age by contractual due date; distinguish dispute/late payment from missing invoice; retain approved credit-loss and write-off rationale.

Evidence population: invoice due dates; receipts; disputes; aging; allowance estimate.

### LC-RECOVERY — SH-AST-002

Owner: Cradle operations and inventory accounting. Scope: project-cradle. Frequency: Every lot and monthly close.

Reconcile mineral tonnes and water/chemistry in their own units; retain title, custody, assay, lot lineage, acceptance and host settlement. Hard bypass excludes unavailable recovery.

Evidence population: feed/run; recovered lot; Bedford batch; acceptance; inventory; settlement.

### LC-TRANSFER — SH-TRN-004

Owner: Receiving operating owner. Scope: willow,project-cradle,foundry-field. Frequency: Every production transfer.

Require receiving owner, qualification and maintenance responsibility. Failed/unfinished qualification leaves the item experimental.

Evidence population: project gate; qualification; transfer; asset/custody record.

### LC-WORKFORCE — SH-PPL-003

Owner: People Operations / Finance. Scope: all. Frequency: Monthly and assignment change.

Reconcile authorized billets, occupied positions and paid FTE separately; stable person/position IDs prevent counting dual roles or borrowed staff twice.

Evidence population: employment roster; assignments; contractors; payroll reconciliation.

### LC-ESTIMATE — SH-FIN-004

Owner: Accountable model owner and Finance reviewer. Scope: all. Frequency: Each material assumption change.

Record source/version/unit/date, range, reason and outcome sensitivity; do not call a conditional forecast a measured historical result.

Evidence population: assumptions; source/master hashes; scenario comparison; estimate review.

### LC-CONSOLIDATION — SH-FIN-005

Owner: Consolidation owner. Scope: all. Frequency: Each build and close.

Exclude superseded financial scope before adding successor rows; reconcile legal entities, seven units, corporate and eliminations. Internal charges must net to zero.

Evidence population: replacement bridge; legal/unit statements; eliminations; funding and allocation bridges.

### LC-ATLAS — SH-IAM-002

Owner: Client workspace owner. Scope: atlas-meridian,advisory. Frequency: Each access and export.

Check tenant/client purpose and source rights before showing detail; deny absent/unresolved entitlement and record reason; no implicit Alexandria raw-source access.

Evidence population: workspace scope; source rights; access decision; export review.

### LC-INDUSTRIAL — SH-OPS-002

Owner: Accountable mine/rail/nonrail operator. Scope: pale-sun,american-resource-utility. Frequency: Planning cycle and exception.

Constrain demand by qualified equipment, labor, route and capacity; uranium custody remains gated independently of ordinary inbound availability.

Evidence population: operating plan; service/production rows; qualification and capacity exception.

## Acceptance and remaining scope

Content acceptance requires all eight business/history and four Finance entries to identify source, owner/steward, disclosure posture and temporal/authority relationships. Every local control must resolve to an existing CCF control and natural evidence population. The repository validator checks these structural claims and the distinction between historical/external names and current legal books.

This supplies the requested source-boundary refinements for #38/#44. Runtime access enforcement and tests require their own implementation evidence and remain outside a documentation-only closeout. A fully generated unit package additionally needs operational populations, subledger/statement reconciliation and its own tested safety allowlist under #12.
