# Standalone business-unit export specification v0.1

A business-line dossier is an index. A business-line **audit package** is a generated evidence bundle. The repository must not call a unit independently auditable until the bundle below can be produced from an explicit run and reconciled to the enterprise consolidation.

## Required package layout

```text
releases/generated/business-units/<unit-id>/<generation-run-id>/
├── manifest.json
├── README.md
├── database/<unit-id>.sqlite
├── csv/
├── financials/
│   ├── trial-balance.csv
│   ├── income-statement.csv
│   ├── balance-sheet.csv
│   ├── cash-flow.csv
│   ├── changes-in-equity.csv
│   └── intercompany-bridge.csv
├── operations/
│   ├── asset-register.csv
│   ├── inventory-register.csv
│   ├── workforce-summary.csv
│   └── domain-registers/
├── controls/
│   ├── reconciliation.json
│   ├── validation-results.json
│   ├── source-lineage.csv
│   └── public-safety-report.json
├── workbooks/<unit-id>-audit-workbook.xlsx
└── SHA256SUMS.txt
```

## Mandatory manifest fields

- package and schema versions;
- unit ID and display name;
- repository, source commit, controlling canon commit, and Alembic head;
- generation run ID, profile, scenario, seed, generator version, and controlled build timestamp;
- period coverage and actual/forecast boundary;
- entity, segment, site, project, counterparty, and fact-state filters;
- included and excluded tables/columns;
- row counts and monetary/operational units;
- validation/reconciliation results;
- artifact inventory and SHA-256 checksum for every file;
- public classification, limitations, and license/use terms.

## Filtering rule

Filtering must occur during export into a new empty database. A raw backup of the enterprise database is not a unit export. Shared records may be included only when the manifest states the relationship—for example, allocated shared service, intercompany counterparty, consolidation adjustment, or source-lineage dependency.

## Minimum reconciliations

1. unit journal debits equal credits;
2. unit trial balance maps to unit financial statements;
3. ending cash and all rollforwards reconcile by period;
4. asset and inventory records reconcile to general-ledger control accounts;
5. intercompany balances/activity reconcile to the counterparty and enterprise eliminations;
6. source events trace to posted journal entries;
7. unit results bridge exactly to the enterprise consolidated result;
8. no unexpected scenario, generation run, entity, site, or fact state appears;
9. all workbook values tested against database/report values;
10. all package hashes verify and the generated-artifact safety scan passes.

## Unit-specific minimum registers

- **Foundry Field:** customers, contracts, obligations, invoices, revenue recognition, collections, engagements, time, project costs, WIP, deployments, and unit economics.
- **Willow:** experiments, hypotheses, budgets, costs, observations, gate decisions, transfer targets, assets/compute, and authority boundaries.
- **Atlas Meridian:** evaluations, model/version record, investigation question, validation/compute cost, fees, decision-ownership flag, and lineage.
- **Pale Sun / Red Wash:** mine/mill assets, production batches, ore/WIP/concentrate inventory, shipments, price, COGS, capex, ARO, environmental obligations, and technical limitations.
- **Project Cradle:** host operator, ownership classification, feed/recovery, recovered units, project costs, host share, sale, participation accounting, and abandonment/impairment status.
- **ARU / BS&T:** customers, waybills, routes, custody, carloads/tons/ton-miles, rates, fuel, crew, locomotives, railcars, terminals, parts/tools/fuel inventory, maintenance, fixed assets, and intercompany traffic.
- **Advisory:** clients, engagements, scope, staffing, time, WIP, billings, collections, project cost, margin, deliverables, and method-transfer boundaries.

## Publication rule

Unit packages are generated outputs. Publish them as CI or release artifacts only after validation and safety scanning. Do not commit mutable databases or recurring workbook builds directly to the source tree.
