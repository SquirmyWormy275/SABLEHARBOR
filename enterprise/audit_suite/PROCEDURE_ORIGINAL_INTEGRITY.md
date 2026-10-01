# Recorded procedure original-byte check

`GET /api/engagements/{engagement_id}/procedure-original-integrity` is an
authorized, read-only companion to `work-status`. It first verifies the visible
sample-trace metadata and correction lineages, then reads only the retained
artifact versions cited by metadata-valid traces. It checks their bytes against
the exact retained SHA-256 and size. No source-system collection, company query,
task update, audit credit, or engagement mutation occurs.

The report separates `MISSING_RETAINED_BYTES` (a cited retained file is absent),
`RETAINED_BYTE_INTEGRITY_FAILURE` (a cited file is present but invalid),
`RETAINED_BYTE_READ_UNAVAILABLE` (an operating-system read fails), and
`NO_RETAINED_ORIGINAL_REFERENCED` (the recorded procedure cited none). Broken
trace metadata or correction lineage is `METADATA_UNAVAILABLE`; its bytes are
not reported as verified. An explicit 256-original/128 MiB budget returns
`RECHECK_INPUT_UNAVAILABLE` rather than silently skipping reads.

Byte integrity proves only the custody of cited copies at request time. The
recorded observations and locators remain author assertions; the report does
not compare locator text with content, establish original company source
freshness, accept population completeness or accuracy, validate actor authority
or reviewer independence, assess period coverage, or satisfy a procedure. It
always returns `automatic_testing_credit=false`. A later change to retained
storage requires another check.
