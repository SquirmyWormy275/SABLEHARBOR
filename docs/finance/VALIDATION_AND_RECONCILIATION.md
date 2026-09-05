# Validation and reconciliation

The enterprise financial-validation registry verifies a compatible migration head, a nonempty
selected run context, completed included runs, independently valid posted journals, exactly one run
marker, complete generation ownership, execution of every named query, AR/AP exposure-to-GL
reconciliation, reciprocal intercompany matching, nonnegative debt schedules, and balanced monthly
and final statements. Workbook, unit-package, release, checksum, and artifact-safety gates consume
or supplement that registry. A passing gate establishes technical consistency; it does not make
generated 2023–2026 values observed company results or audited records.

Migration and test suites separately cover deterministic IDs, assumption schema, posting and
completed-run immutability, reversals, period close, idempotence, shared synthetic pre-cutoff/
forecast partitioning, scenario isolation, canon states, and causal subledger/GL flows. The current
Alembic target is `0015`; final fresh SQLite and PostgreSQL evidence for this integration state must
be recorded before acceptance.

Domain equations tested include:

- contract → invoice → deferred revenue → recognition → receipt;
- payroll/procurement/assets/debt source records → journal IDs;
- Red Wash feed tons × 2,000 × grade × recovery = produced pounds;
- opening/produced quantity − shipped quantity = closing quantity;
- waybill tons × route miles = ton-miles, with fuel and crew direct costs;
- Cradle feed × grade × recovery = recovered units and host share;
- Willow gates and Atlas authority constraints;
- aggregate trial-balance debits = credits;
- invoice/vendor-bill documents + disclosed residual source-event exposure = AR/AP GL exposure,
  with AR due-date buckets and AP due dates explicitly unavailable;
- workbook database controls and release SHA-256 digests.

The configured CI job performs PostgreSQL 16 migration, generation, and validation. Earlier local
PostgreSQL execution was unavailable due Docker socket permissions; neither that limitation nor
older green checkpoint results constitute final evidence for the current `0015` worktree.
