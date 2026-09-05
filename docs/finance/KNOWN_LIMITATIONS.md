# Known limitations

- The baseline profile is an FY2026 synthetic scenario/calibration snapshot. The `standard`
  profile provides a synthetic 2023–2026 monthly model. The seven 2016–2022 values in
  `full_history` are calibration anchors only; neither profile represents observed company history
  or audited financial statements.
- Summary journals remain available as a compact calibration profile. The standard profile now
  replaces part of each forecast-month SHI, Red Wash, and BS&T railway control with generated causal
  contract-to-cash, mine production/sale, waybill, payroll, procurement/AP/payment, fixed-asset/
  depreciation, debt/interest, Cradle recovery, Willow/Atlas, and Advisory engagement chains.
  Explicit repayments now accompany each forecast debt draw. The AR/AP exposure reconciliation
  distinguishes formal invoice/vendor-bill documents from disclosed source-event receivables and
  accruals. AR documents have due-date buckets; vendor bills do not currently carry due dates, so AP
  document exposure is explicitly labeled due-date unavailable. Document exposure plus the residual
  source-event bridge reconciles to the GL. Debt schedules distinguish causal forecast facilities
  from provisional acquisition opening balances; unavailable covenant thresholds remain OPEN.
- The initial proof workbook remains available only as an explicitly labeled internal synthetic
  preview and is not a release artifact. It runs current identity, financial-integrity, formula/URL,
  and artifact-safety gates, but publishable workbook delivery uses the governed suite. The suite implements
  six run-pinned, database-controlled workbooks covering consolidation, software/services,
  industrial operations, close/subledgers, capital/valuation scope, and release control. The capital
  workbook expressly states that no completed M&A, purchase-price-allocation, DCF, NAV, or valuation
  opinion is included.
- All six workbooks now route every sheet through an exact semantic specification rather than title
  substring matching. Sheets with no selected-run records render an explicit empty state, while the
  capital workbook renders an explicit valuation scope limitation.
- Forecast generation applies configured revenue and cost driver families only to
  SHI/software-services, Red Wash (`RWH`), and the ARU-group railway in v0.1; the latter's modeled
  railway economics are booked to BS&T, not ARU. Cradle, Research, Advisory, and Capital families are
  persisted as governed `SCENARIO_INPUT` records with
  `application_status=RECORDED_ONLY_NOT_APPLIED`; they do not drive generated amounts and v0.1 makes
  no causal attribution claim for them. All driver values remain scenario input, not LOCKED canon.
- The legal relationship shapes are not open: Sable Harbor is principally one operating company;
  ARU is a controlled subsidiary; BS&T is a wholly owned legal subsidiary beneath ARU; and Red
  Wash has a dedicated legal operator while Pale Sun remains its business-line identity. Exact
  names, suffixes, jurisdictions, tax elections, agreements, acquisition terms, mine economics, ARU
  estate, Cradle structure, occupancy, headcount, and consolidated values remain `MODEL_PROPOSED`,
  `SCENARIO_INPUT`, or `OPEN` as applicable.
- The 708-person scenario predates the September 3 J2 establishment closure. J2 has a locked
  237-billet design establishment, but establishment is not occupancy; no 237-person hiring claim is
  inferred. J2 occupancy and ESS/Internal Audit cost-center allocation remain explicit scenario
  work, with Internal Audit independence and J2/ESS separation preserved.
- Local PostgreSQL verification on 2026-09-01 was unavailable because Docker API access to
  `/var/run/docker.sock` was denied, the system PostgreSQL service was inactive, and no Podman
  fallback was installed. The PostgreSQL 16 matrix is committed in CI; current remote evidence must
  be taken from the PR checks rather than this historical local limitation.
- Migrations `0008` through `0015` persist the intended synthetic calibration cutoff,
  repository-relative generation input manifest, and content-addressed build and shared-dataset
  identity. Deprecated physical database columns containing `actual` remain internal
  migration/storage aliases only; current APIs and outputs use synthetic-calibration semantics.
  Standard monthly accounting controls and driver values are partitioned at the cutoff between the
  shared synthetic calibration layer and scenario forecast layer. Production, freight movements,
  and ending inventory are also
  partitioned, with an Alembic-installed semantic regression using a non-default persisted cutoff
  to reject generator literals and ownership on the wrong side of the contract. Effective-dated
  master and commitment records remain whole records rather than periodic facts. SQLite now proves two-seed
  natural-key namespacing and explicit non-lossy downgrade refusal for populated duplicate keys;
  Migration `0011` adds non-null ownership, same-run composite relationships, compatible
  shared-dataset attachment, and database lifecycle guards. Their equivalent PostgreSQL 16
  matrix is now encoded in CI and passes a SQLite backend surrogate, but remains open pending a
  remote PostgreSQL run. Migration `0012` and scoped APIs isolate trial balances, lineage,
  and accounting-period close state by compatible run context. Close markers cover both the
  selected scenario and included shared calibration layer, and active sessions reject unrelated
  journal posting and reversal. Same-seed sibling scenarios reuse one completed pre-cutoff monthly
  calibration layer and can add their own close markers around one idempotently shared marker.
  Every profile that completes the `synthetic_common` layer first materializes the
  same monthly synthetic pre-cutoff superset and completion marker. A bidirectional
  baseline/standard order matrix proves identical standard journal counts and debit totals without
  enriching a completed calibration layer.
  Legacy global closes are preserved during `0012` upgrade; downgrade preserves uniform closes
  and rejects unrepresentable mixed run state. Trial-balance comparison now requires distinct,
  completed runs with the same profile, shared dataset, cutoff, forecast start, and schema, and
  rejects cross-seed comparisons. Broader comparison coverage beyond trial balances remains open;
  Stage 1 is not closed. Revision `0013` widens cutoff-marker period codes and guards lossy
  downgrade; `0014` adds the run-owned debt-repayment subledger; the current `0015` target adds
  customer/vendor ownership, same-run links, ledger and period constraints, completed-run content
  guards, and database-side completion checks. Final fresh SQLite and PostgreSQL evidence for the
  current `0015` integration state has not yet been recorded.
- Generation, validation, workbook, and packaging commands in v0.1 require the full governed
  SABLEHARBOR repository checkout, its repo-level configuration/docs/migrations/release schemas,
  and all Git objects pinned by `CANON_SOURCE_LOCK.json`. A shallow checkout or standalone wheel is
  intentionally rejected because it cannot authenticate historical and noncontrolling snapshots.
  Packaging those governed resources into a standalone distribution remains future work.
- The public package now uses a versioned table/column allowlist and a new empty SQLite target, and
  its generator records enterprise financial-validation results and marks the manifest `PASS` only
  after recursive scanning of generated CSV, SQLite, XLSX, manifest, and nested-archive contents.
  CSV text is neutralized against spreadsheet formula injection, XLSX string formula/URL detection
  is disabled, and an external `SHA256SUMS.txt` authenticates the finalized manifest. Package
  replacement uses a validated, marked staging directory and refuses broad or unowned targets.
  Publication remains review blocked until the current-tree SQLite/PostgreSQL, workbook, unit,
  release, checksum, reconciliation, and artifact-safety gates run and their evidence is reviewed.
- Deterministic generation means stable identifiers, modeled values, and ordering for unchanged
  governed inputs. Repackaging one persisted run from an unchanged, immutable source-database
  snapshot with the same controlled package timestamp is byte reproducible. Shared legal-entity,
  site, book, period, and account dimensions are not run-owned in v0.1; changing one changes the
  source snapshot even when the run ID remains fixed. Persisting a separate master-snapshot identity
  remains future work. Real execution provenance (`started_at`, `completed_at`, journal `posted_at`, and
  source commit) can differ between independent fresh materializations, so cross-build CSV,
  workbook, manifest, and checksum identity is not claimed.
- This is a synthetic enterprise reference platform. Its generated records are scenario/calibration
  material—not observed company results, historical books, audited financial statements, a reserve
  report, legal advice, tax advice, or a production mine/rail safety system.
