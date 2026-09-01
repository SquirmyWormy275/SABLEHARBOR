# Sable Harbor finance platform

The platform is a Python/SQLAlchemy financial-data foundation with SQLite local execution and PostgreSQL migrations/CI. It currently implements deterministic identities, explicit canon/model states, balanced immutable journals, reversals, period close, trial balance, causal transaction slices, 2023–2026 monthly standard generation, historical anchors, scenarios, named SQL queries, six workbook outputs, SOTP/QOE valuation, and a checksummed public-demo release.

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin generate --profile standard --scenario base
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin validate
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin workbooks
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin package-release
```

Read `KNOWN_LIMITATIONS.md` before interpreting any output. Quantitative values and proposed entity structures are not locked canon.
