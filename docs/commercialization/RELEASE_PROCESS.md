# Release process

Run `shfin package-release --generation-run-id RUN_ID` against an explicitly selected, completed
`standard` run. Before writing artifacts, the command executes the enterprise financial-validation
registry. It then builds in a governed sibling staging directory, writes allowlisted CSVs (including headers for empty
tables), constructs an allowlisted SQLite evidence extract, generates the six-workbook suite, and
records the selected/included runs, effective period, synthetic calibration and forecast boundaries,
scenario/input/generator versions and digests, row counts, validation results, limitations, and
SHA-256 output hashes in the manifest. The release is explicitly
`RETROSPECTIVE_CURRENT_CANON`: its source-lock metadata records current canon effective through
September 3, 2026 and reconciled/prepared September 5. August 31 is a synthetic calibration
boundary, not a knowledge cutoff. Source-snapshot IDs and content digests come from Git blobs
resolved at every `commit:path` in the pinned `CANON_SOURCE_LOCK.json` contract; live controlling
files must byte-match those blobs. This requires a full, non-shallow governed repository checkout.

The command marks the manifest `PASS` only after its recursive artifact-safety scan succeeds, then
writes `SHA256SUMS.txt` over the finalized manifest and package artifacts. CSV strings are guarded
against spreadsheet formula injection and XLSX automatic formula/URL conversion is disabled.
Successful builds atomically replace only a dedicated generated target; broad paths and unmarked
external directories are refused. Treat an already published version as immutable; publication
controls must assign a new version and changelog for corrections.
Before publication, run the current SQLite/PostgreSQL, workbook, release, checksum, and safety gates
and confirm that no prohibited evaluator truth, answer key, credential, sensitive-looking PII, or
workstation-specific path is present. Documentation of these controls is not evidence that the final
PR worktree has passed them.

For reproducible publication, retain an immutable snapshot of the completed source database and
provide the same controlled package timestamp. Repackaging that selected run from the unchanged
snapshot is byte deterministic. Shared master dimensions are not run-owned in v0.1, so any master
mutation constitutes a different source snapshot. Independent fresh runs keep
real posting/completion times and source commit as provenance, so cross-build byte identity is not a
release guarantee even when stable IDs and modeled values agree.
