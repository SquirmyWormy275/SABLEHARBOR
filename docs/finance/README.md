# Sable Harbor finance and data platform

> **Status: RELEASE CANDIDATE — NOT ACCEPTED.** PR #9 contains a substantial enterprise accounting/data foundation, but migration, generation-run/scenario isolation, workbook semantics, integrated three-statement modeling, public-release allowlisting, generated-artifact scanning, historical-coverage, and review-artifact findings remain open.

## Scope implemented so far

- Python/SQLAlchemy foundation with SQLite local execution and PostgreSQL CI;
- deterministic identities and explicit canon/model fact states;
- multi-entity books, periods, dimensions, balanced immutable journals, reversals, close, and eliminations;
- contract-to-cash, payroll, procurement/AP, fixed assets, debt, professional-services, mining, logistics, recovery, and research-domain records;
- 2023–2026 monthly summary generation;
- 2016–2022 historical revenue calibration anchors;
- base, low, high, and stress cases;
- named SQL queries, reporting code, six-workbook generator, valuation/QoE code, provenance records, and release-package code.

Passing current tests proves the assertions currently encoded; it does not establish audited statements, a reserve report, complete unit inventories, production safety, or acceptance of OPEN facts.

## Navigate

- [Platform architecture](DATABASE_AND_ACCOUNTING_ARCHITECTURE.md)
- [Data model](DATA_MODEL.md)
- [Chart of accounts](CHART_OF_ACCOUNTS.md)
- [Accounting policies](ACCOUNTING_POLICIES.md)
- [Validation and reconciliation](VALIDATION_AND_RECONCILIATION.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
- [Platform acceptance document](PLATFORM_ACCEPTANCE_v0.1.md) — subject to the independent PR #9 review-blocking findings
- [Database and SQL index](../../db/README.md)
- [Business-line dossiers](../business-lines/README.md)
- [Standalone unit export specification](../audit/UNIT_EXPORT_SPECIFICATION.md)
- [Repository audit](../audit/REPOSITORY_AUDIT_2026-09-01.md)

## Business-line access

The current database is an enterprise model. Unit dossiers document the working entity, segment, site, tables, queries, and workbook surfaces for Foundry Field, Willow, Atlas Meridian, Pale Sun/Red Wash, Project Cradle, ARU/BS&T, and Advisory.

No dossier link converts the enterprise database into an accepted unit database. A standalone unit package requires a new filtered database, unit statements, asset/inventory registers, intercompany bridge, lineage, validations, manifest, and checksums.

## Reproduce the release candidate

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin generate \
  --profile standard --scenario base --seed 20260831
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin validate
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin workbooks
SHFIN_DATABASE_URL=sqlite:///var/standard.db uv run shfin package-release
```

Read `KNOWN_LIMITATIONS.md` and the PR #9 acceptance gate before interpreting output. Quantitative values and proposed entity structures are not locked canon.
