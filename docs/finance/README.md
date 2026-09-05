# Sable Harbor finance platform

The platform is a Python/SQLAlchemy financial-data foundation with SQLite local execution and
PostgreSQL migrations/CI. It currently implements deterministic identities, explicit canon/model
states, balanced immutable journals, reversals, period close, trial balance, causal transaction
slices, synthetic 2023–2026 monthly scenario/calibration generation, earlier calibration anchors,
scenarios, named SQL queries, six workbook outputs with an explicit valuation limitation, scoped
business-unit evidence packages, and an allowlisted public-demo release generator. Generated values
are not observed company history or audited records. The current Alembic target is `0015`; final
SQLite/PostgreSQL and artifact acceptance evidence for the current worktree is still required.

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
