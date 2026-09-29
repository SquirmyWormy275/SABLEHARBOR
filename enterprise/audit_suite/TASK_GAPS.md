# Recorded procedure gaps

`task.gap.record` stores a bounded, attributed gap against one existing task in an
active engagement. It names an explicit cause, assigned scoped auditor owner, authored
narrative, and disposition. A collected artifact can be pinned by its exact ID and
SHA-256; if it came from a native company source, the matching ordinary collection
receipt's source metadata is retained with the gap. A retest link requires an
existing workpaper version explicitly linked to the same task. An optional
predecessor forms an append-only correction/reopening chain; it never rewrites an
earlier observation.

The command is available to `learn` and `instruct` members. `review` members can
read projected gaps but cannot write them. Learner views and learner snapshots omit
the entire gap row when its pinned artifact is instructor-only, including successor
rows, so a hidden source does not leak through a count or predecessor reference.
Exact command replay is idempotent and stale engagement revisions fail closed.
The named owner is an author assignment, not evidence that the recipient accepted
the work; each successor preserves its own actor and timestamp.

These are auditor-authored observations, not source creation or inferred audit
findings. Recording, linking a retest, or reopening a gap does not change task
status/conclusion, workpaper content, artifacts, company source history, or a
professional sufficiency decision. A reason in `audit_readiness.py` remains an
ephemeral cue until a person records a gap; reason codes are not backfilled into
the durable register automatically. The current feature does not migrate private
2027 gap adjudications into the frozen A1938/B2064 workrooms.
