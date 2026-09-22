# Procedure trace metadata readiness

`procedure_trace_readiness.summarize(projection)` accepts an already authorized
Engine projection. `audit_readiness.summarize` attaches its per-task result as
`controls[].procedures[].sample_trace_readiness`. This adds no commands, original
reads, source grants, automatic task status changes or testing credit.

Each valid trace preserves its exact task, immutable population/selection,
historical workpaper version and visible retained-artifact metadata pins. Item
hashes and selection membership are compared to the pinned population. Current
scope, source binding, explicit procedure link and source accessibility metadata
must remain compatible. Trace-recorded reliability enum/provisional flags and the current pinned population
status/selection provisional flag are displayed separately; differences alone do not
erase a historical trace. Actual changed immutable population/selection digests still
make an exact reference unavailable. Source query/period
claims stay recorded assertions; the report does not establish an independent
business denominator, corroboration, extraction correctness or period completeness.
Original files are not reread by this report.

Correction chains require an exact predecessor digest, consecutive revisions,
unchanged task/selection/population identity and sampled-item membership. Each
unambiguous chain contributes only its current leaf to observation-status counts;
older trace IDs, statuses and exact historical workpaper links remain visible.
These are counts of recorded observations, not unique business items or completed
professional tests. Independently authored trace roots can overlap the same items.
Selected items lacking observations are reported separately.

Malformed references, changed task pins, inaccessible originals, forks, cycles,
duplicate identities and missing predecessors are unavailable, never passing.
A procedure with an unavailable chain has null current counts, not a misleading
zero. Valid historical traces can remain visible with their original metadata while
an unavailable chain prevents aggregate current counts. No unresolvable reference
is redirected to a newer workpaper or population. `NO_RECORDED_TRACES` means only
that the supplied projection contains no associated recorded traces.

The optional report bounds traces to 2,000, item observations to 20,000, each trace
to 1 MiB and total serialized traces to 32 MiB. Existing bounded sample input-pin
validation handles linked workspace collections. A malformed or excessive input
returns `INPUT_UNAVAILABLE` and null counts without breaking the ordinary workspace
read. Unknown task references contribute only an unavailable count, not leaked
linked identities. This is an optional metadata index, not a complete audit history
or a replacement for explicit population acceptance and independent review gates.

Validation uses real supplied populations, retained originals and maintained
sample-execution recording/correction handlers. It covers correction histories,
provisional historical selections after later reliability decisions, exact-version
pins, revoked audience visibility, malformed/ambiguous lineages, bounded failures,
and preservation of all input state.
