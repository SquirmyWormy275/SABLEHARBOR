# Known limitations

- The baseline profile is an FY2026 calibration snapshot. The `standard` profile provides a
  synthetic 2023–2026 monthly model. The seven 2016–2022 values in `full_history` are revenue
  calibration anchors only; they are not complete historical financial statements.
- Summary journals remain available as a compact calibration profile. The standard profile now
  replaces part of each forecast-month SHI, Red Wash, and ARU control with generated causal
  contract-to-cash, mine production/sale, waybill, payroll, procurement/AP/payment, fixed-asset/
  depreciation, debt/interest, Cradle recovery, Willow/Atlas, and Advisory engagement chains.
  Explicit repayments now accompany each forecast debt draw. Aging and debt schedules reconcile to
  the GL and separately expose amounts retained in summary journals rather than causal subledgers;
  those allocation-control amounts must be eliminated before the P1 model gate can be accepted.
- The initial proof workbook remains available for compatibility. The completed suite generates six database-controlled workbooks covering consolidation, software/services, industrial operations, close/subledgers, capital/valuation, and release control.
- All six workbooks now route every sheet through an exact semantic specification rather than title
  substring matching. Some optional industrial and valuation sheets correctly render explicit empty
  states until their underlying monthly detail queries are populated by the next model stage.
- Forecast scenarios now derive revenue and cost multipliers from attributable business-line drivers
  for software/services, Red Wash, ARU/BS&T, Cradle, research, Advisory, and capital constraints.
  The driver set is scenario input, not LOCKED canon; monthly causal subledger expansion remains in
  progress.
- Legal entities, acquisition terms, mine economics, ARU estate, Cradle structure, headcount, and consolidated values remain `MODEL_PROPOSED` or `SCENARIO_INPUT`.
- Local PostgreSQL verification on 2026-09-01 was unavailable because Docker API access to `/var/run/docker.sock` was denied, the system PostgreSQL service was inactive, and no Podman fallback was installed. CI is configured to run migrations plus the all-profile, two-seed, scenario-coexistence, violation, lifecycle, and cutoff matrix against PostgreSQL 16; that uncommitted matrix still needs remote evidence.
- Migrations `0008` through uncommitted `0012` persist the intended actual cutoff, repository-relative generation
  input manifest, and content-addressed build and actual-dataset identity. Standard monthly
  accounting controls and driver values are partitioned at the cutoff between the shared actual
  layer and scenario forecast layer. Production, freight movements, and ending inventory are also
  partitioned, with an Alembic-installed semantic regression using a non-default persisted cutoff
  to reject generator literals and ownership on the wrong side of the contract. Effective-dated
  master and commitment records remain whole records rather than periodic facts. SQLite now proves two-seed
  natural-key namespacing and explicit non-lossy downgrade refusal for populated duplicate keys;
  Migration `0011` adds non-null ownership, same-run composite relationships, compatible
  actual-dataset attachment, and database lifecycle guards. Their equivalent PostgreSQL 16
  matrix is now encoded in CI and passes a SQLite backend surrogate, but remains open pending a
  remote PostgreSQL run. Migration `0012` and scoped APIs isolate trial balances, lineage,
  and accounting-period close state by compatible run context. Close markers cover both the
  selected scenario and included common-actual layer, and active sessions reject unrelated
  journal posting and reversal. Same-seed sibling scenarios reuse one completed pre-cutoff monthly
  actual layer and can add their own close markers around one idempotently shared actual marker.
  Every profile that completes the common-actual layer first materializes the same monthly actual
  superset and completion marker. A bidirectional baseline/standard order matrix proves identical
  standard journal counts and debit totals without enriching a completed actual layer.
  Legacy global closes are preserved during `0012` upgrade; downgrade preserves uniform closes
  and rejects unrepresentable mixed run state. Trial-balance comparison now requires distinct,
  completed runs with the same profile, actual dataset, cutoff, forecast start, and schema, and
  rejects cross-seed comparisons. Broader comparison coverage beyond trial balances remains open;
  Stage 1 is not closed.
- The public package now uses a versioned table/column allowlist and a new empty SQLite target, and
  its CSV, SQLite, XLSX, manifest, and nested archive contents pass the recursive artifact scanner.
  Publication remains review blocked with the platform until the remaining workbook, monthly-model,
  reconciliation, and audit-package gates close.
- This is a synthetic enterprise reference platform, not audited financial statements, a reserve report, legal advice, tax advice, or a production mine/rail safety system.
