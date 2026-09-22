# Company information policy implementation

**ID:** SH-INFORMATION-POLICY-20260922. **Prepared:** September 22, 2026. **Authority:** owner instruction to finish the company closeout, implementing accepted Alexandria/Daedalus doctrine. **Status:** implementation pending repository acceptance. No real deployment or general professional compliance opinion is asserted.

## Scope and policy

The [source](../../../enterprise/ccf/company_closeout/source/information_policy_2026_09_22.json) pins controlling doctrine; the [provider](../../../enterprise/ccf/company_closeout/information_policy.py) emits and checks a contract consumed by the existing runtime. It adds no database, storage engine or competing portal. It separates seven record classes: preserved approved public synthetic originals, disposable public working copies, working operations, workforce personal information, privileged/legal records, audit work product and segregated personal memory.

Approved public synthetic originals remain open for their declared purposes. Unknown classification never means public. Restrictions require a named owner, actual authority record, reason, purpose, challenge route and review date. The 90-day review interval is a newly authored internal reconsideration schedule, **not** a statutory destruction period. Role titles identify responsibility; rank, manager status and model identity confer no automatic restricted access. A source grant identifies the subject, purpose, permitted actions, start/end and revocation state. The runtime authenticates the issuer and user; this policy library cannot authenticate a human merely from an input string.

Every user-visible read, search, snippet, citation, count, graph, vector, tool response, answer, memory return and export checks the same user context and all transitive source permissions. Denial does not return an existence hint, identity or count. The institution may separately approve a minimal existence notice; this implementation denies it absent an explicit permitted source grant and complete source disclosure permission. An approved existence-only grant returns only EXISTS_RESTRICTED, never payload permission; a runtime may emit the literal generic notice without a record identity, title, quantity or graph shape. This selected implementation does not promise institution-wide discovery notices. Missing sources or cycles fail closed. Legal hold preserves bytes without authorizing disclosure.

Daedalus's institutional ability to traverse evidence does not authorize user disclosure. This module governs **disclosure to a requesting person**, not background institution-authorized model reading. No automatic authoritative write, self-promotion, institutional judgment, cross-user memory sharing or shared-model training is permitted. Personal memory additionally requires its individual owner; even an otherwise entitled manager or model cannot consume another user's memory. Derivatives retain all parent restrictions and provenance; exporting them never promotes their authority.

## Retention and disposal

The accepted edition/source archive remains immutable. A separately managed working copy or export can be disposed of without changing its accepted original. The existing runtime's seven-year capacity assumption is not adopted as a blanket legal retention law. Each disposable record needs a specific retention authority and delete-not-before instant. Unsourced deadlines remain UNSCHEDULED_REQUIRES_REVIEW; not-yet-due records remain retained.

Disposal requires distinct authenticated human preparer/reviewer identities, the approval/reason record, every affected owner's approval and exact version/hash pins for the root and its complete transitive derivative closure. Approval must follow the reviewed source's availability and effective time. Models cannot authorize destruction. Any active hold blocks disposal; immutable release membership independently blocks it. Approval is only APPROVED_FOR_ADAPTER_EXECUTION, not evidence that deletion occurred.

The adapter must actually delete authorized working bytes and derived copies, preserve nonpayload tombstones/custody history, retain protected held content and record execution evidence. Before exposing an older restored backup it must replay the newest durable deletion/hold/revocation checkpoint; missing or stale checkpoint fails closed. It must not weaken CompanyStore immutable-version triggers. Backup restoration that merely removes an access grant while leaving a deleted working copy readable through another path fails this contract.

## Interface and population

- `build_policy(people_rows, record_rows, expected_person_ids=..., expected_record_ids=...)`: stable IDs, duplicate rejection and explicit population equality. Without expected populations, counts describe only submitted rows and cannot prove enterprise completeness.
- `decide(records_by_id, record_id, subject, action, now, revoked_ids=(), tombstones=())`: ALLOW/DENY/EXISTS_RESTRICTED (the latter is never payload authority), offset-qualified instants, tenant/purpose matching, no future source availability and transitive restrictions.
- `disposal_decision(records_by_id, record_id, request, now)`: due/hold/immutable/approval state and exact affected IDs. It performs no file mutation.

Record fields and request fields are demonstrated by adversarial tests. Restriction metadata, grants and human approvals must be supplied from authenticated, source-bound company decisions; an external API must never accept a user's self-declared owner or HUMAN flag as authority. The adapter controls durable checkpoint binding and actual filesystem/store operations.

## Verification and acceptance limit

Focused tests cover all named deterministic surfaces, revoked subjects and source tombstones, personal separation, future availability, malformed tenant, source cycles/missing parents, duplicate populations, unchanged original preservation, legal hold, retention due time, stale approval, complete derivative closure, distinct review and model denial. This verifies policy decisions; actual backup/restore, current-checkpoint validation and byte destruction require separate runtime evidence. Model-specific inference/prompt-injection effectiveness remains distinct from deterministic filtering. The 13 external facility/provider readiness gates are not reclassified by this implementation.

## Institutional coverage map

Classes follow the nature and approved publication status of each record, rather than its prestige or portal. Canon, Semaphore, Judgment Problems, EIB history and Alexandria institutional records use preserved-public-original class only when public approval exists; protected originals retain their appropriate working/legal/personal classification and independently set immutable-release status. Collection raw sources require their actual privacy, privilege or working-source class. Generated disposable copies use PUBLIC_WORKING_COPY only when the original content is approved public; protected derivatives retain parent permissions. Daedalus personal artifacts use PERSONAL_MEMORY and remain non-authoritative. A portal name never grants access or makes a record immortal. The same lawful retention review and hold precedence apply across these domains.
