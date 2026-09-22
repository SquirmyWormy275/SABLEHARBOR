# Private reasoned work guidance

`WorkGuidance` supplies optional administrative context within the existing workspace.
It reads only the caller's current authorized engagement projection and the deterministic
`audit_readiness.summarize` reasons. It does not consult company stores, hidden instructor
material, models, filenames or inferred intent, and issues no formal audit commands.

Two independent gates are required. Raw authorized stored configuration must contain
`work_guidance_allowed: true`, enabled through the instructor policy command. Missing
policy is false. Its `work_guidance_policy_revision` is part of the private authority
basis, so disabling and re-enabling the policy, including an explicit repeat setting,
requires a new personal opt-in. CLEAN/MESSY is never an assistance authorization.
The individual must then explicitly opt in with a rationale. Read-only `status` never
computes or returns candidates; exact control choices are returned only while both gates
and the personal context are current.

## Private API and responses

Create an owned 0700 directory and instantiate `WorkGuidance(root, engine)`. Its database
is 0600, rejects aliases/hard links, and contains append-only events with command digests,
per-principal/per-engagement version chains and immutable triggers.

- `status(actor, engagement_id)` returns policy metadata, personal event `version`, current
  engagement revision, opt-in status and eligible control contexts.
- `opt_in(actor, engagement_id, enabled, rationale, expected_version=…,
  expected_engagement_revision=…, command_id=…)` explicitly enables or disables personal
  guidance. `enabled` is a real boolean and the rationale is nonblank, at most 2,000
  Unicode characters. This never changes instructor policy.
- `reveal(actor, engagement_id, context_ref, expected_engagement_revision=…, command_id=…)`
  records a deliberate disclosure before returning its candidates. The exact control
  reference comes from `status`, with `{kind,id,version,sha256}`. No reference is inferred
  from a title or replaced by the latest version.
- `decide(actor, engagement_id, candidate_id, candidate_sha256, action, rationale,
  expected_engagement_revision=…, command_id=…)` records `REVIEW` or `DISMISS` for an exact
  previously disclosed current candidate. These are private user dispositions, not audit
  completion or agreement with a conclusion.

Every response includes `engagement_id`, `current_engagement_revision`, private `version`,
`policy_allowed`, `policy_version`, `opted_in`, `personal_content_visible`, `status`,
`contexts` and `backup_status`. Current personal context may include `preference`.
Status values are `POLICY_DISABLED`, `OPT_IN_REQUIRED`, `AVAILABLE`, `CONTEXT_CHANGED`
and `INPUT_LIMIT_EXCEEDED`. Context changes redact old personal rationale and choices.

An explicit reveal adds `reveal_id` and bounded `candidates`. Each candidate records
`id`, `sha256`, `code`, `title`, `reason`, `classification: ADMINISTRATIVE_OBSERVATION`,
`context_ref`, exact `references`, existing-workspace `navigation`, engagement revision
and basis digest. References are `CURRENT` with an exact pin, or `UNAVAILABLE` with no
navigable reference. Workpapers name an exact retained version and its digest. Requests
and reviews pin their complete current projected row. Missing links are not proof that
company records do not exist. The seven maintained administrative reason codes neither
judge control effectiveness nor establish population completeness or professional
independence.

Reveals also show current matching private decisions. Exact command retry does not create
another disclosure event; it overlays current matching decisions so dismissed guidance
is not presented as undecided. A retry after opt-out, policy change or context change
cannot return old candidate content. A changed candidate or engagement revision requires
an explicit new reveal and decision; an old dismissal cannot suppress new facts.

Actor access, policy, scope, permissions, source binding, simulated date, controls and
retained source metadata are rechecked before returning content and around writes.
Changes to this authority/source basis require a new opt-in. Ordinary work changes that
leave the basis intact still invalidate old candidate revisions. The implementation does
not promise an atomic transaction across the audit database and the private guidance
store.

## Bounds and inert recovery

The private store allows 512 events per principal/engagement plus one reserved final
opt-out, with a 1 MiB event and 64 MiB database-content limit. Inputs are bounded at
20,000 recorded objects, 256 control choices, 64 candidates and 64 references per reason.
A bound failure returns no partial candidate disclosure. The service should explain the
limit without hiding the surrounding engagement.

`snapshot()` produces `PRIVATE_WORK_GUIDANCE_ARCHIVE_V1`; `validate_archive()` checks
exact fields/types, owner/version/command chains, candidate pins, disclosed-candidate
relationships, rule text and bounds. Recovery is **inert only**: it preserves private
history for explicit operator inspection and never reactivates opt-ins or decisions.
There is no active-store import API. `INERT_ARCHIVE_ONLY` describes supported recovery,
not a claim that a backup was actually performed. Existing source grants, credentials,
audit history and instructor releases are outside this module.

Tests use neutral stored engagements and authorized projections. They cover both gates,
no-candidate status reads, exact reference navigation, reloaded private decisions,
redaction/re-opt-in, actor/engagement separation, revocation rollback, CAS/replay,
non-navigable missing records, bounded disclosure, final opt-out and typed inert archives.
