# Sable Harbor database and SQL index

The finance platform uses one enterprise schema with entity, segment, site, project, counterparty,
period, scenario, generation, provenance, and fact-state dimensions. The current PR #9 implementation
can derive seven scoped release-candidate evidence packages from that enterprise source; it does not
produce seven standalone source-system databases or independently audited unit statements.

## Structure

- `migrations/` — Alembic schema history; migration immutability remains an acceptance item.
- `sql/` — named analytical queries executed by `src/sable_harbor/reporting_queries.py`.
- `src/sable_harbor/accounting/` — books, periods, chart, journals, dimensions, shared asset/workforce/operating records.
- domain subledgers — `commercial`, `operations`, `mining`, `logistics`, `recovery`, and `research`.

## Unit filter map

| Unit | Entity | Segment | Site | Implemented primary register |
|---|---|---|---|---|
| Foundry Field | SHI | SHI, CORE, FOUNDRY_FIELD, DELIVERY | SAC | Customer contracts |
| Willow | SHI | WILLOW | PIT, SAC | Willow experiments |
| Atlas Meridian | SHI | ATLAS | SAC | Atlas evaluations |
| Pale Sun | RWH | RWH, PALE_SUN | RED_WASH | Mine production batches |
| Project Cradle | SHI | CRADLE | SAC | Recovery runs |
| ARU Group — BS&T Railway | ARU, BST | ARU, ARU_BST | ARU_HUB | BS&T waybills |
| Advisory | SHI | ADVISORY | SAC | Engagements |

These entries mirror the current `MODEL_PROPOSED_FINANCE_REPORTING_SCOPE` registry; they do not lock
legal names, jurisdictions, organizational boundaries, or physical-site assignments where canon
leaves them open. Every package also includes scoped journal/financial evidence, shared asset,
inventory and workforce registers where its filters select records, source lineage, validation,
reconciliation, manifest, safety results, and checksums. Entity/segment/site filtering alone is
insufficient: every report/export must identify its generation run, scenario, profile, seed, period
coverage, fact states, and shared/intercompany treatment.

## Reproduce a local enterprise database

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run shfin generate \
  --profile standard --scenario base --seed 20260831
RUN_ID=$(SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run shfin run-id standard \
  --scenario base --seed 20260831)
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run shfin validate \
  --generation-run-id "$RUN_ID"
```

For the scoped evidence-package contract, see
[`docs/finance/UNIT_PACKAGE_CONTRACT.md`](../docs/finance/UNIT_PACKAGE_CONTRACT.md).
