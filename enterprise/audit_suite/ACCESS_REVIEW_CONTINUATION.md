# Declared-subject access review continuation

`company_access_review_continuation.generate(destination, repository=..., source_roots=..., recipe=...)` creates three original company records before any audit: a review population, decisions and reconciliation. The destination must be new, private, and outside the original stores. It creates no grants or audit state.

`AccessReviewContinuationRecipe` declares company, new branch and campaign, a UTC calendar-quarter start and exclusive end, ordered population/decision/reconciliation timestamps, explicit local requirements and three `ReviewContinuationSourceGroup` values. Each group retains its caller-declared producer label, exact `LifecycleSourceRef` native identities/content hashes and selected metadata digest. The `source_roots` keys are exactly:

- `identity`: five prior application, HR, population, decision and reconciliation originals.
- `remediation_initial`: the first six exact remediation chain originals.
- `remediation_final`: the remaining five originals, from the same physical store, native branch and producer label as `remediation_initial`.

The identity store must be separate. No federation routing metadata is invented. The original 16 native documents are retained byte-for-byte with their separate pins. Every input must be available by export. The adapter validates the original review query/cutoff, population and decision backlinks, predecessor event/availability ordering, and the complete baseline → request → resolver → execution → state → verification → followup → corrected resolver/execution/state/verification chain. It replays the local entitlement operations and compares each recorded execution, state and probe. An unsupported terminal assertion prevents publication.

The new population includes only the declared subject and the exact verified terminal rights. It does not reconstruct an intervening quarter. Decisions are computed from those rights and the prior explicit authorization: excess rights remain removal candidates; missing authorized rights produce an unresolved decision rather than an invented restoration instruction. Earlier omitted people and unsupported prior members remain in an unresolved register. A clean declared-subject comparison never closes the whole review.

Scoped coordination/review assignments and their controlling source hashes are retained as proposed local assignments. Code/parser/store and organization pins are checked again before publication, as are all selected native source pins. Staged publication never overwrites a previous run. The three output originals can be separately registered in an operating-period ledger under their own common branch; their upstream cross-branch lineage is not an implicit shared company runtime.

This is a local reference exercise. It establishes neither employment, deployment, population completeness, a full quarter of operations, corporate acceptance nor professional assurance. UTC quarters are the supported date convention. Fixtures and negative tests are in `tests/audit_suite/test_company_access_review_continuation.py`.
