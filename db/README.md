# Sable Harbor database and SQL index

The finance platform uses one enterprise schema with entity, segment, site, project, counterparty, period, scenario, generation, provenance, and fact-state dimensions. The current implementation is a release candidate in PR #9; it does **not** yet produce seven accepted standalone unit databases.

## Structure

- `migrations/` — Alembic schema history; migration immutability remains an acceptance item.
- `sql/` — named analytical queries executed by `src/sable_harbor/reporting_queries.py`.
- `src/sable_harbor/accounting/` — books, periods, chart, journals, dimensions, shared asset/workforce/operating records.
- domain subledgers — `commercial`, `operations`, `mining`, `logistics`, `recovery`, and `research`.

## Unit filter map

| Unit | Entity | Segment | Site | Principal named queries |
|---|---|---|---|---|
| Foundry Field | SHI | CORE, FOUNDRY_FIELD, DELIVERY | SAC | customer_arr_bridge, customer_profitability, deferred_revenue_rollforward, engagement_margin_wip, employee_loaded_cost, entity_trial_balance, journal_to_source_trace |
| Willow | SHI | WILLOW, CORE | SAC | assumption_impact, employee_loaded_cost, entity_trial_balance, journal_to_source_trace, source_to_journal_trace, release_coverage_lineage |
| Atlas Meridian | SHI | ATLAS, CORE | SAC | assumption_impact, customer_profitability, employee_loaded_cost, entity_trial_balance, journal_to_source_trace, source_to_journal_trace, release_coverage_lineage |
| Pale Sun | RWH | PALE_SUN | RED_WASH | red_wash_unit_cost_bridge, mine_inventory_shipment_reconciliation, fixed_asset_rollforward, vendor_spend_concentration, debt_covenant_calculation, entity_trial_balance, journal_to_source_trace, intercompany_mismatch_elimination |
| Project Cradle | SHI | CRADLE | SAC | cradle_project_economics, customer_profitability, vendor_spend_concentration, fixed_asset_rollforward, entity_trial_balance, journal_to_source_trace |
| American Resource Utility | ARU | ARU_BST | ARU_HUB | aru_route_customer_margin, intercompany_mismatch_elimination, fixed_asset_rollforward, vendor_spend_concentration, debt_covenant_calculation, employee_loaded_cost, entity_trial_balance, journal_to_source_trace |
| Advisory | SHI | ADVISORY | SAC | engagement_margin_wip, customer_profitability, ar_ap_aging, employee_loaded_cost, entity_trial_balance, journal_to_source_trace |

Entity/segment/site filtering alone is insufficient for accepted exports. Every report/export must also identify its generation run, scenario, profile, seed, period coverage, fact states, and shared/intercompany treatment.

## Reproduce a local enterprise database

```bash
uv sync --all-extras
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run alembic upgrade head
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run shfin generate \
  --profile standard --scenario base --seed 20260831
SHFIN_DATABASE_URL=sqlite:///var/sable_harbor.db uv run shfin validate
```

For the finance-owned standalone package contract, see
[`docs/finance/UNIT_PACKAGE_CONTRACT.md`](../docs/finance/UNIT_PACKAGE_CONTRACT.md).
