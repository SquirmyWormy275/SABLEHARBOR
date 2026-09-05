# Finance unit-package contract

**Status:** MODEL_PROPOSED release-candidate contract

Unit packages are deterministic, read-only evidence slices of an explicitly selected, completed
`standard` enterprise generation run. The generator runs the enterprise financial-validation
registry before packaging. These artifacts do not establish legal entities, operating divisions,
canon, observed history, audited results, or independent auditability.

Here, deterministic means byte reproducible when the same persisted run is repackaged from the same
unchanged, immutable source-database snapshot with the same controlled `generated_at` value. Shared
master dimensions are not run-owned in v0.1 and therefore form part of that retained snapshot.
Independent fresh materializations intentionally retain real
execution provenance, including posting/completion timestamps and source commit, and are not
promised to be byte-identical even when their modeled values and stable identifiers match.

Each package records its generation run and build, included shared synthetic calibration run,
unambiguous output profile/role, scenario ID/code/version, seed, generator version/source digest,
input version/manifest digest, source commit, effective period, synthetic calibration boundary,
forecast boundary, schema, entity/segment/site filters, and row counts. It also records
`RETROSPECTIVE_CURRENT_CANON`, canon effective through September 3, 2026, source-lock reconciliation
and preparation on September 5, and the source-snapshot IDs/digests derived from
`CANON_SOURCE_LOCK.json`. August 31 is never represented as a package knowledge cutoff.

The manifest includes enterprise validation status, reconciliation, artifact-safety result, and a
per-output SHA-256 inventory; each unit's `SHA256SUMS.txt` additionally covers its finalized
manifest, and the package-root checksum covers the complete seven-unit delivery. The
package contains scoped journal lines; trial-balance, income-statement, balance-sheet, cash-movement,
equity-movement, and intercompany extracts; source lineage; shared and domain-specific operational
registers; a SQLite extract containing only `journal_line_evidence` and `trial_balance`; and a
one-sheet trial-balance workbook. The SQLite file is evidence, not a filtered replica of the
enterprise source schema, and the workbook is not a full audit workbook.

The generator must fail for an incomplete or non-`standard` selected run, failed enterprise
validation, empty unit evidence, an unbalanced aggregate or included journal, out-of-scope segments,
missing source identity, a failed unit-to-enterprise bridge, or either of its recursive safety scans.
The generator proves that the unique union of packaged journal lines plus excluded corporate,
consolidation, elimination, and unassigned activity equals the enterprise population; it also
rejects duplicate and unknown packaged lines. The delivered bridge discloses the excluded scope
categories, line count, and debit/credit totals, not an excluded-line ID inventory. Reporting
segments are assigned to at most
one unit. Unsegmented entries are included only when the registry expressly permits them; the
current registry permits none, so unallocated enterprise activity remains in the disclosed bridge
rather than being duplicated into business lines.

The versioned scope map is `config/finance/unit_scopes.json`. Its entity, segment, and site filters
are `MODEL_PROPOSED_FINANCE_REPORTING_SCOPE`, not a resolution of open legal names, jurisdictions,
agreements, physical-site assignments, or organizational boundaries. Any mismatch with controlling
canon must be flagged and corrected in the registry; package generation must not silently invent the
missing fact.
