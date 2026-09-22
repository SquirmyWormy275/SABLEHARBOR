# Explicit source-impact reassessment dispositions

This ordinary audit command records an author's decision about an exact retained
original or directly linked work after a currently authorized source comparison.
It never invalidates a workpaper, changes a result or applicability, performs a
retest, clears review points, or establishes professional acceptance. Company
sources and retained original bytes remain unchanged. Source reads use existing
authorized discovery/access journals; they do not grant access.

## Inputs and command

`source_impact_disposition.inputs(engine, actor_id, engagement_id, artifact_id)`
returns the current engagement ID/revision, selected artifact ID, a server-pinned
comparison, observation timestamps, at most 256 targets/retests and current
predecessor pins. The inputs route is read-only with respect to the audit.
Only an ACTIVE engagement and current learn/instruct authority are supported.
Review-only members cannot author this command.

The report compares only the explicitly selected learner-visible AVAILABLE
company original. Missing, denied or unavailable comparison is an error, never
an unchanged-source assertion. `comparison.sha256` binds exact old/new source
versions and content hashes, native identity and portfolio routing where present,
source qualifiers, scope/source/acquisition basis, simulation cutoff and company
binding. Wall-clock discovery/recheck timestamps are retained separately in
`observed`; they do not change the stable comparison digest.

Targets include the retained artifact itself and existing typed impact links:
exact workpaper versions, populations, selections, tasks, item observations,
reviews, findings and remediation evidence. Each choice contains `reference`,
`record_sha256` and a server-generated `sha256`. The latter binds exact identity
and record digest, excluding descriptive current/historical/successor labels.
A newer workpaper version therefore does not silently create a new disposition
lineage for an unchanged older version. Historical target content is never
replaced with latest. No text/title/control-name inference creates a link.

Retest choices are existing linked workpapers, item observations, reviews,
findings or remediation records referring to the selected original or an exact
retained copy of the observed newer source. A distinct record must be selected.
Linking it asserts an author's choice of existing work, not that a retest passed,
that new source bytes were examined, or that the work is sufficient.

The ordinary command envelope uses CAS and idempotency:

```text
kind: source.impact.disposition.record
command_id: explicit unique ID
expected_revision: current engagement revision
payload: {
 artifact_id, comparison_sha256, target_sha256,
 disposition: ACKNOWLEDGED | REASSESSMENT_NEEDED | RETEST_LINKED |
              NOT_APPLICABLE_TO_SELECTED_WORK,
 rationale, intended_action, retest_sha256: null | exact choice,
 predecessor: null | {id, sha256}
}
```

Rationale is 1–4,000 characters, intended action 1–2,000. There are at most 2,000
immutable disposition rows per engagement; bounds reject, never truncate. The
command freshly rechecks the comparison, chosen work and predecessor, then
rechecks again before append. Source operation snapshots are individually
verified; this does not create a globally atomic multi-store snapshot. Later
appends outside the observed comparison interval remain outside its claim.

`NOT_APPLICABLE_TO_SELECTED_WORK` concerns relevance to one exact target; it does
not alter control/framework applicability. ACKNOWLEDGED explicitly leaves the
reassessment decision open. No enum changes existing effectiveness or test status.

## History, corrections and visibility

Rows in `source_impact_dispositions` retain ID, actor, recorded/simulation times,
`revision` (saved engagement revision), `version` (disposition lineage version),
comparison/observation pins, target, optional retest, rationale/intended action,
explicit predecessor and qualification. The simulation clock does not advance.
The same current target leaf requires an explicit exact predecessor for a new
row. Earlier rows remain immutable; superseded branches cannot be continued.
No automatic owner, reviewer or action assignment is made.

Ordinary projections mark history CURRENT, CONTEXT_CHANGED or TARGET_UNAVAILABLE.
Changed scope/source/acquisition basis or unavailable exact artifact/work hides
rationale, source and target details, returning only basic historical metadata.
This is formal shared audit work, not another user's private draft. Current
history visibility does not mean a source comparison was just rerun. Revoking
native-source access prevents a new comparison but does not erase authorized
retained-original history. Exact command replay preserves its original revision,
adds no row, and evaluates displayed history against current authorized context,
including current artifact audience; it cannot revive hidden rationale.

Tests exercise actual local source correction, stable comparison pins across
clock reads, explicit successor/CAS, source change/revocation/publication races,
exact replay, retained-original-only target, distinct retest link, unchanged
originals/work results, scope/visibility redaction and review-only denial. All
activity is in disposable fixtures. No actual audit disposition is created by
these tests or this guide.
