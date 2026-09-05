# Excel model guide

Run `shfin workbooks --generation-run-id RUN_ID` after completing the selected migrated generation
run. The command refuses an unknown or incomplete run and executes the enterprise
financial-validation registry before writing the six named v0.1 workbooks under
`workbooks/outputs/` (or the selected output directory).

Every logical sheet has an exact semantic specification with a purpose, query/report source,
required columns, units, deterministic query ordering, tolerance, and explicit empty-state behavior.
Each rendered sheet identifies the scenario, the synthetic calibration boundary, forecast start,
seed, source commit, retrospective epistemic mode, current-canon effective date, and canon-source
reconciliation date. The Cover and Run Control sheets additionally record generator/input versions
and digests plus the source-snapshot IDs and digests pinned by `CANON_SOURCE_LOCK.json`. August 31,
2026 is a synthetic calibration boundary, not the workbook's knowledge cutoff: these workbooks are
prepared retrospectively under canon effective through September 3 and reconciled September 5.
Check sheets contain formula-backed local controls and the full database validation registry; they
do not replace database validation. The capital workbook contains an explicit valuation scope
limitation rather than a completed valuation model.

Workbooks disable automatic conversion of database strings to formulas or URLs and use no external
workbook links. Each build is safety-scanned and also writes
`workbook-suite-manifest.json`, recording scenario/input/generator identity, effective period,
source snapshots, build time, and SHA-256 output hashes. An external `SHA256SUMS.txt` covers every
workbook and the finalized manifest. Named-query rows are emitted completely rather than silently
truncated. The test contract reopens generated files
and checks the required sheet structure, formulas, links, metadata, hashes, and selected
database-to-sheet semantics. Passing those technical controls does not make any workbook an audited
statement or a system of record, and final current-tree workbook evidence must still be produced
during acceptance.

Excel forbids `/` in sheet names and limits names to 31 characters. Required logical labels such as `ARU/BS&T` use `ARU-BS&T`; unusually long labels are shortened without changing their meaning. Generated `.xlsx` files are ignored by default and are release artifacts rather than systems of record.
