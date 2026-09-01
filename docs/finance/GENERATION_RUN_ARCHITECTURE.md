# Generation-run and scenario architecture

**State:** implemented Stage 1 correctness architecture; broader platform remains review blocked.

## Ownership model

The platform uses an explicit common-actual layer plus self-contained scenario forecast runs.

- One deterministic `actual_common` generation run exists for each seed and owns opening
  balances, workforce, fixed assets, production, inventory, freight, environmental obligations,
  and other observed or opening operational facts generated for that seed.
- Every base, low, high, stress, baseline, full, full-history, or benchmark-safe run has its own
  `generation_run` row and run marker.
- Scenario runs reference their included common-actual run through
  `generation_run.actual_generation_run_id`.
- Scenario-dependent journals and scenario values belong directly to the scenario run.
- Actual periods through August 2026 use invariant multipliers. Scenario multipliers apply only
  to forecast periods beginning September 2026.
- Shared legal entities, books, periods, accounts, sites, customers, and vendors are master
  dimensions. They do not represent scenario facts and are not duplicated by run.

## Deterministic inclusion rule

`run_context(session, generation_run_id)` is the only supported read context. It resolves:

1. the selected scenario run; and
2. its referenced common-actual run, when present.

Reports, statements, named queries, workbooks, validation, and exports must use only those resolved
run IDs. A database containing multiple runs must reject an omitted selector. Direct unfiltered
aggregation is unsupported.

## Installation and execution

Alembic is the schema installation authority. Normal generation and read commands verify the
database is at migration head and never call `Base.metadata.create_all()`.

Generate first, then pass the explicit run ID to every read command:

```bash
uv run alembic upgrade head
uv run shfin generate --profile standard --scenario base --seed 20260831
RUN_ID=$(uv run shfin run-id standard --scenario base --seed 20260831)
uv run shfin validate --generation-run-id "$RUN_ID"
uv run shfin statements --generation-run-id "$RUN_ID"
uv run shfin workbooks --generation-run-id "$RUN_ID"
```

The public release implementation remains review blocked because its SQLite snapshot mechanism is
not yet the required new-empty-database, versioned table-and-column allowlist construction and its
generated-artifact safety scan is incomplete.
