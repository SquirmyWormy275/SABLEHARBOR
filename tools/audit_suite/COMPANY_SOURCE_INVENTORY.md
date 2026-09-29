# Company source inventory

Run this local read-only operator tool against an existing engagement and the repository:

```bash
uv run --extra audit-suite python tools/audit_suite/company_inventory.py \
  --repository . --store PRIVATE_STATE_DIRECTORY --engagement ENGAGEMENT_ID \
  --output NEW_PRIVATE_DIRECTORY/INVENTORY.json
```

The output inventories every scoped control and task, authored procedure references, prepared request schemas, people and organizational scope, and files under explicitly declared canon/business/operations source roots. It retains exact source hashes and structured source records. Output is private; the command never reads principal/session tables, inference configuration or a hidden scenario bank. An inventory is not evidence-sufficiency approval. Additional-duty matches use actual task/duty IDs; other source links remain control-level candidates until a reproducible source query and procedure-specific attributes are established.

The database is opened read-only in one transaction. Frozen world files are separately hashed, and missing units remain gaps. The tool never starts company operations, generates evidence, migrates history or changes an engagement. A running owner's later work is a later revision; retain each census separately. File existence and reference matches do not prove an independently operating source system.

Recommended implementation follows the repository's existing business and operations model:

| Layer | Reuse and boundary |
|---|---|
| Controlling canon | Preserve accepted decisions, dated ownership, organizational authority and immutable financial releases. Derived registries do not override these. |
| Existing operations | Reuse `enterprise/operations/source`, business model inputs, export schemas and approved export scopes; preserve their public synthetic origin and disclosed periods. |
| Persistent company records | Add an operational record/version index over existing company identities and events, independently of engagements. Keep event time, source effective time and actual import time separate. |
| Migration | Bind original source hashes to stable company record IDs and version history. Record unresolved joins and conflicts. Never import an evaluator conclusion as an operating fact. |
| Authorized collection | Produce source exports from declared source queries and permissions; retain exact versions, filters, retrieval time and hashes. Existing parent-support source projection provides a bounded reuse pattern, not a complete company system. |
| Audit work | Link each procedure to exact required fields, population scope and corroborating sources. Policy, operating records, reconciled populations and independent testing remain separate. |
| Isolation and recovery | Branch company operations explicitly for training conditions; preserve company history across audits. Demonstrate backup/restore and immutable retained audit copies before migration acceptance. |

The next engineering deliverable should be a source-system and record-relationship bridge grounded in the inventoried canon, not a replacement fictional organization. Where the existing records lack a period, owner, source version or causal link, keep that gap explicit until a defined company activity or justified migration resolves it. Independent human review remains necessary for applicability, realism and audit sufficiency.

The bounded operating bridge is `enterprise.audit_suite.operating_source_bridge.import_operating_tables`. It accepts an already built existing `OperatingModel`, explicit company/scenario-branch identities and existing custody IDs for its four allowlisted operating tables. It preserves original rows and input/code hashes, uses stable natural-key record identities and source ordering, and records real import time separately. Exact event time remains unknown. Availability after a source month closes is an explicit conservative disclosure rule. Source sentinel zero for an unapplied change remains a non-date. The importer grants no access, creates no engagement and cannot promote forecasts or provisional custody into accepted canon. Replaying the same import returns its original receipts; different source versions require an explicit correction migration.

`enterprise.audit_suite.company_population.export_population` queries those imported versions with an exact table, source scenario, month interval, unit list and trusted as-of clock. The query includes all matching source versions, so a contract-change population is explicitly different from a unique-contract census. All pages share one database read transaction. A separate manifest pins query/schema, members, versions and hashes; `verify_export` requires the independently retained manifest hash. Unknown source schemas, unauthorized scope, premature period closure and incomplete pagination fail closed. Concurrent corrections belong to a subsequent snapshot. An exact temporary grant is needed for a local collection check and can be revoked afterward.

These utilities establish reproducible imported-source populations. They do not establish completeness of unimported company operations, independent population review, SOC2/HIPAA applicability or professional sufficiency. Existing browser engagements remain bound to their explicitly selected company-store version; creating a newer import does not redirect them.
