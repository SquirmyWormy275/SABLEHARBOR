# Sable Harbor finance platform

The current selected industrial successor is the [Pale Sun / Red Wash / ARU / BS&T case](../../industrial/README.md), with its [finance bridge](INDUSTRIAL_FINANCE_BRIDGE_v1.0.md). The platform described below remains the reproducible enterprise v0.1 snapshot; industrial legal names and current operating assumptions are controlled by that successor.

The platform is a Python/SQLAlchemy financial-data foundation with SQLite local execution and
PostgreSQL migrations/CI. It currently implements deterministic identities, explicit canon/model
states, balanced immutable journals, reversals, period close, trial balance, causal transaction
slices, synthetic 2023–2026 monthly scenario/calibration generation, earlier calibration anchors,
scenarios, named SQL queries, six workbook outputs with an explicit valuation limitation, scoped
business-unit evidence packages, and an allowlisted public-demo release generator. Generated values
are not observed company history or audited records. The current Alembic target is `0015`; final
SQLite/PostgreSQL and artifact acceptance passed for v0.1 and is recorded in
`PLATFORM_ACCEPTANCE_v0.1.md`.

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin generate --profile standard --scenario base
RUN_ID=$(SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin run-id standard --scenario base --seed 20260831)
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin validate --generation-run-id "$RUN_ID"
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin workbooks --generation-run-id "$RUN_ID"
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin package-release --generation-run-id "$RUN_ID"
```

Read `KNOWN_LIMITATIONS.md` before interpreting any output. Quantitative values and proposed legal
implementation details are not locked canon. The relationship shapes Sable Harbor → controlled ARU
→ wholly owned BS&T and Sable Harbor → dedicated Red Wash operator are locked and are not optional
entity scenarios.
