# Sable Harbor finance platform

Follow the money from a business question to the workbook and the records behind it. You can use the accounting exercises without running the financial platform.

## Start with a question

| Work | Open first |
|---|---|
| Trace an invoice or investigate a balance | [Finance exercises](READER_EXERCISES.md) and the [invoice exercise](../reader/exercises/INVOICE.md). |
| Inspect supporting accounting records | [Accounting evidence packages](evidence/coverage/README.md), with reconciliations and CSV/SQLite extracts. |
| Compare the seven businesses | The [business finance model](../../enterprise/business/README.md) and [release guide](../releases/BUSINESS_FINANCE_RELEASES.md). Its 2027–2031 figures are conditional forecasts. |
| Work through an industrial acquisition | The [Pale Sun, Red Wash, ARU and BS&T case](../../industrial/README.md) and [finance bridge](INDUSTRIAL_FINANCE_BRIDGE_v1.0.md). |

Keep each exercise's period, scenario and source edition together. The [business model design](BUSINESS_DRIVEN_SUCCESSOR_2026-09-09.md) explains which later assumptions replace the earlier platform forecast and which historical records remain unchanged.

## Reproduce the original v0.1 platform

The instructions below describe the original, reproducible enterprise v0.1 edition—not the whole company's current financial or legal position.

The platform is a Python/SQLAlchemy financial-data foundation with SQLite local execution and
PostgreSQL migrations/CI. It implements deterministic identities, explicit record and model
states, balanced immutable journals, reversals, period close, trial balance, causal transaction
slices, synthetic 2023–2026 monthly scenario/calibration generation, earlier calibration anchors,
scenarios, named SQL queries, six workbook outputs with an explicit valuation limitation, scoped
business-unit evidence packages, and an allowlisted public-demo release generator. Generated values
are not observed company history or audited records. The v0.1 acceptance target is `0015`; final
SQLite/PostgreSQL and artifact acceptance passed for v0.1 and is recorded in
`PLATFORM_ACCEPTANCE_v0.1.md`.

```bash
make bootstrap
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin generate --profile standard --scenario base
RUN_ID=$(SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin run-id standard --scenario base --seed 20260831)
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin validate --generation-run-id "$RUN_ID"
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin workbooks --generation-run-id "$RUN_ID"
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin package-release --generation-run-id "$RUN_ID"
```

Read [the v0.1 limitations](KNOWN_LIMITATIONS.md) before interpreting this edition. Its generated values and proposed implementation details do not replace later company decisions. For the current industrial legal structure, use the [industrial case](../../industrial/README.md) and its linked legal records rather than treating this earlier snapshot as a current ownership chart.

## Current Willow / Klein model

The [Willow/Klein finance and corporate model](WILLOW_KLEIN_FINANCE_AND_CORPORATE_MODEL_2026-09-06.md) uses the owner-selected historical name under the [September 7 decision](../canon/KLEIN_NAME_AND_IDENTITY_2026-09-07.md). Klein is a closed historical program, not a new current reporting segment. All prior finance source-lock files and release inputs remain unchanged.
