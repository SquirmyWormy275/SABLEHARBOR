# SABLE HARBOR — CODEX EXECUTION HANDOFF

**Date:** September 1, 2026  
**Repository:** `SquirmyWormy275/SABLEHARBOR`  
**Primary working branch:** `finance/enterprise-financial-platform-v0.1`  
**Primary pull request:** PR #9  
**State:** RELEASE CANDIDATE — REVIEW BLOCKED — NOT ACCEPTED  
**Controlling instruction file:** `/AGENTS.md`

---

## 1. Mission

Continue the Sable Harbor enterprise financial/data-platform program and turn the repository into a coherent, auditable company system.

The final user experience must support both directions:

1. start with Sable Harbor as one consolidated enterprise; and
2. drill into any current business line or material operating component and see its identity, lore, organization, data scope, operational records, inventory or WIP, financial statements, controls, intercompany relationships, source lineage, and reproducible audit package.

The target is not a folder of unrelated spreadsheets. The target is:

> **one governed enterprise source of truth, consolidated reporting, and deterministic business-unit audit views and packages.**

Excel is a reporting and analysis surface. SQL is the queryable system of record. Unit SQLite/CSV/XLSX packages are generated evidence bundles, not independently maintained shadow systems.

---

## 2. Read before changing code

Read these sources in order:

1. `/AGENTS.md`
2. `docs/canon/DECISION_REGISTER.md`
3. `docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`
4. `docs/governance/PUBLIC_REPOSITORY_AND_WIKI_POLICY.md`
5. all existing `docs/finance/` acceptance, state, limitation, and handoff documents
6. PR #9 body, comments, reviews, and changed files
7. PR #10 body and changed files
8. PR #13 body and changed files
9. relevant open issues and CI logs

Use the repository and GitHub state as evidence. Do not treat a chat summary, PR description, or previous agent completion statement as proof that code or artifacts exist or satisfy acceptance criteria.

Recommended inspection commands:

```bash
git status --short --branch
git remote -v
git fetch --all --prune
git log --oneline --decorate --graph -30
gh pr view 9 --comments
gh pr checks 9
gh pr view 10 --comments
gh pr view 13 --comments
gh issue list --state open
```

Also inspect the actual diffs:

```bash
gh pr diff 9 --name-only
gh pr diff 10 --name-only
gh pr diff 13 --name-only
```

PR #10 and PR #13 overlap in enterprise/dossier/repository-organization work but use different bases and structures. Do not blindly merge both. Inventory unique files, identify the stronger implementation for each concern, and later reconcile them into one accepted information architecture after the finance base is stable.

---

## 3. Current live program state

At creation of this handoff, GitHub exposes these open PRs:

### PR #9 — finance platform

- Branch: `finance/enterprise-financial-platform-v0.1`
- Base: `main`
- Status: review blocked, not accepted
- Contains a substantial accounting/data-platform implementation and passing checks for the assertions currently encoded.
- Must not be merged merely because CI is green.

### PR #10 — stacked enterprise dossiers

- Branch: `integration/enterprise-audit-and-dossiers-v0.1`
- Base: the finance branch
- Status: draft stacked integration PR
- Contains company-first navigation, current-unit dossiers, brand/collateral recovery, Wiki source, database indexes, and unit-export specification work.
- Must not be merged directly to `main` while its finance base remains unaccepted.

### PR #13 — main-based enterprise portal/hygiene candidate

- Branch: `docs/enterprise-portal-and-repo-hygiene-v0.1`
- Base: `main`
- Status: review candidate
- Contains overlapping portal, dossier, governance, registry, audit, and Wiki work.
- Must be reconciled with PR #10 rather than treated as automatically additive.

The repository is public. Public-safety boundaries are mandatory.

---

## 4. Controlling canon boundary

Repository v0.2 canon controls.

Current enterprise scope includes:

- Sable Harbor parent/shared enterprise functions;
- Foundry and Foundry Field;
- Project Willow;
- Atlas Meridian;
- Pale Sun and the operating Red Wash mine;
- Project Cradle;
- American Resource Utility and its BS&T railway component;
- emerging Advisory;
- historical Emberline obligations, contracts, assets, employees, or lineage where applicable.

Do not restore the older operating-model perimeter as controlling canon.

Specific locked interpretation:

- Emberline is not a standalone 2026 division.
- Evalon is historical and was rechartered into Willow.
- Pale Sun operates Red Wash.
- Cradle does not automatically own host mines or host assets.
- ARU remains operationally distinct; BS&T is its railway or short-line component.
- Advisory is emerging, not automatically a mature scaled practice.
- exact legal entities, leadership, HR reporting, routes, sites, reserves, asset counts, customers, workforce, and economics remain OPEN or scenario-controlled where canon says so.

The old 426-FTE / $124.5M model is historical calibration only.

---

## 5. Known finance-platform acceptance findings

Treat the following as merge-blocking until code and tests prove closure.

### P0 — migrations

The baseline migration must not depend on live application metadata.

Required outcome:

- explicit frozen Alembic operations;
- explicit downgrade behavior;
- no `Base.metadata.create_all()` in committed historical migrations;
- SQLite and PostgreSQL upgrade/downgrade/upgrade tests;
- schema-equivalence or schema-fingerprint validation;
- proof that adding an unrelated application model does not mutate historical migration behavior.

### P0 — generation-run and scenario isolation

Multiple runs and scenarios must coexist in one database without contamination.

Required outcome:

- generated journals and relevant subledger/operational records tied to an explicit generation context;
- uniqueness constraints scoped appropriately;
- all reports, queries, validations, workbooks, and exports require an explicit run/scenario;
- unfiltered incompatible aggregation rejected;
- integration test generating at least base and stress in the same database and proving isolation and idempotency.

### P0 — workbook semantics

Current workbook routing must not rely on sheet-title substring heuristics.

Required outcome:

- explicit workbook and sheet specification registry;
- correct query/report for every sheet;
- correct units, columns, sort order, formulas, checks, tolerances, and empty-state behavior;
- predicate-specific controls rather than one generic positive-number formula;
- database-to-workbook value tests;
- tests that detect P&L data in balance-sheet/cash-flow sheets or lineage data in operating sheets.

### P0 — public release boundary

The public SQLite artifact must be built into a new empty database from a versioned table-and-column allowlist. It must never be a full raw backup of the source database.

Required outcome:

- explicit public schema/table/column allowlist;
- excluded-table and excluded-column rejection;
- manifest derived from real Git, Alembic, run, scenario, period, row-count, and validation state;
- no hardcoded PASS;
- deterministic controlled timestamp support;
- stale-output cleanup;
- same-input deterministic package test;
- changed scenario/seed changes expected outputs.

### P0 — generated-artifact safety

Scan the generated artifacts themselves, not only tracked repository text.

Required scope:

- CSV headers and values;
- SQLite schema inventory and selected textual values;
- XLSX ZIP/XML contents and relationships;
- manifests and checksum files;
- nested archives where produced;
- external links, macros, unexpected embedded objects, secrets, private names/paths, hidden benchmark truth, and proprietary NAILEX implementation.

### P1 — integrated monthly three-statement model

Summary cash-in/cash-out journals are not sufficient as the principal model.

Build integrated monthly chains for applicable periods and entities:

- contract, obligation, invoice, revenue recognition, deferred revenue, AR, collection;
- procurement, receipt, vendor bill, AP, payment, accrual;
- payroll, taxes, benefits, bonus/equity assumptions where supported;
- fixed assets, construction in progress, depreciation/depletion, disposals;
- debt, interest, draws, repayments, fees, liquidity, covenants;
- Red Wash production, ore/WIP/concentrate inventory, shipments, COGS, receivables, capex, ARO;
- ARU/BS&T waybills, external/intercompany billing, fuel, crews, terminals, maintenance, collections/payments, assets;
- Cradle host-safe ownership, recovered value, host share, participation or service economics;
- Willow and Atlas experiment/evaluation costs and controlled commercial boundaries;
- Advisory and other professional-services engagements, time, WIP, billing, collection, and margin.

Generate and reconcile monthly:

- income statement;
- balance sheet;
- statement of cash flows;
- statement of changes in equity;
- working-capital rollforward;
- debt rollforward;
- fixed-asset rollforward;
- inventory rollforward;
- intercompany matching and elimination.

### P1 — driver-based scenarios

Replace two global revenue/cost multipliers with business-line drivers and attribution bridges.

At minimum include relevant drivers for:

- Foundry/Foundry Field bookings, ARR, renewal, churn, expansion, implementation, collection, hosting, support, headcount;
- Willow/Atlas programs, commercial relationships, validation labor, compute, timing, cancellation/delay, release constraints;
- Red Wash price, contracted/spot mix, tons, grade, recovery, availability, shipment timing, labor, power, consumables, contractor cost, capex, ARO;
- ARU/BS&T carloads or ton-miles, rates, fuel, crew, asset availability, terminal use, maintenance, traffic mix, collections;
- Cradle projects, recovered units/value, participation, host share, project cost, success/abandonment;
- capital availability, interest rates, minimum cash, covenants, integration costs, and capex deferral.

Persist driver provenance, units, scenario, effective period, rationale, sensitivity, owner, and fact state.

### P1 — historical claims

Either:

- build defensible annual 2016–2022 statements and a bridge to January 2023 opening balances; or
- describe those years accurately as historical revenue calibration anchors.

Do not describe seven revenue anchors as complete financial history.

### P1 — CI review artifacts

CI must make human review possible.

Publish, after safety gates pass:

- six enterprise workbooks;
- public release candidate;
- reconciliation report;
- validation report;
- schema fingerprint;
- assumption/scenario summaries;
- eventually, business-unit audit packages.

---

## 6. Target information architecture

After finance acceptance, reconcile the enterprise/dossier work into this conceptual navigation:

```text
Sable Harbor enterprise
├── canon and history
├── enterprise organization and authorities
├── brand system and corporate collateral
├── consolidated accounting, finance, and operations
├── database/schema/query catalog
├── auditability and release controls
└── business units
    ├── Foundry Field
    ├── Willow
    ├── Atlas Meridian
    ├── Pale Sun / Red Wash
    ├── Project Cradle
    ├── American Resource Utility / BS&T
    └── Advisory
```

Each current business-unit dossier must provide:

- role and canon boundary;
- parent/component relationships;
- logo variants;
- letterhead and collateral;
- current organization chart or source;
- entity, segment, site, project, and counterparty scope;
- applicable tables and domain models;
- named SQL queries;
- workbook/report surfaces;
- operations, inventory, assets, WIP, or portfolio coverage appropriate to that unit;
- intercompany relationships;
- reproduction/export commands;
- package status;
- exact gaps and OPEN facts.

Do not duplicate normalized source assets into every dossier folder. Link to the controlled asset, chart, schema, or generator. Put recurring generated data in immutable run-addressed packages.

---

## 7. Standalone business-unit audit package contract

A unit is not independently auditable until a reproducible package exists and reconciles to the enterprise source.

Required general shape:

```text
releases/generated/business-units/<unit-id>/<generation-run-id>/
├── README.md
├── manifest.json
├── SHA256SUMS.txt
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
└── workbooks/<unit-id>-audit-workbook.xlsx
```

The exporter must create a new empty unit database and copy only explicitly allowed structures/rows/columns for the selected run and scenario. A full enterprise database backup is not a unit export.

Every unit package must prove:

1. journal debits equal credits;
2. trial balance maps to statements;
3. cash and all applicable rollforwards reconcile;
4. asset/inventory records reconcile to GL control accounts;
5. intercompany records match counterparties and elimination entries;
6. source records trace to posted journals;
7. unit results bridge to enterprise consolidation;
8. no unexpected run, scenario, entity, site, project, or fact state appears;
9. workbook values match database/report values;
10. all hashes and generated-artifact safety checks pass.

---

## 8. Execution sequence

Do not attempt all stages concurrently before their dependencies stabilize.

### Stage 1 — finance/accounting kernel remediation

Own the finance branch and close:

- immutable migrations;
- run/scenario isolation;
- integrated monthly subledgers;
- three-statement and rollforward reporting;
- intercompany and consolidation;
- driver-based scenarios;
- accurate historical coverage claims.

This is the immediate priority.

### Stage 2 — reporting, workbooks, and release controls

After reporting interfaces stabilize:

- replace workbook heuristics with semantic specs;
- complete six enterprise workbooks;
- add database-to-workbook tests;
- rebuild the public release pipeline;
- scan generated outputs;
- publish review artifacts through CI.

### Stage 3 — reconcile enterprise portal work

After the finance base is accepted or technically stable enough for integration:

- compare PR #10 and PR #13 file by file;
- preserve all unique and stronger work;
- resolve registry/count/classification differences deliberately;
- select one normalized company/business-unit information architecture;
- eliminate duplicate/conflicting dossier systems;
- keep Blackridge as a separate case universe rather than a Sable Harbor business unit;
- preserve historical identities without presenting them as current business lines;
- retarget or supersede PRs transparently;
- run link, organization, brand, portal, finance, and safety validation.

### Stage 4 — ARU/BS&T pilot package

Use ARU as the first complete unit package because it exercises physical assets, inventory, workforce, customers, logistics, maintenance, debt, and intercompany activity.

Minimum ARU coverage:

- customers and routes;
- waybills, custody, carloads, tons, ton-miles, rates;
- locomotives, railcars, terminals, facilities;
- parts, fuel, tools, consumables, and maintenance records;
- employees/contractors and loaded labor cost;
- vendors, POs, receipts, bills, and payments;
- fixed assets, depreciation, debt, interest, and covenants;
- external and intercompany revenue/cost;
- trial balance and four financial statements;
- working-capital, debt, asset, and inventory rollforwards;
- ARU–Red Wash matching and consolidation elimination;
- source-to-ledger lineage;
- ARU audit workbook;
- manifest, checksums, validation, safety report, and CI artifact.

### Stage 5 — remaining current business units

Generalize the proven exporter and controls for:

- Foundry Field;
- Willow;
- Atlas Meridian;
- Pale Sun / Red Wash;
- Project Cradle;
- Advisory.

Use unit-appropriate evidence. Do not fabricate physical inventory for software or Advisory, and do not reduce Red Wash or ARU to generic SaaS metrics.

### Stage 6 — final repository hygiene and publication

Only after unique work is safely integrated:

- retire or archive superseded branches;
- close superseded PRs with disposition notes;
- remove probes, caches, stale generated debris, and duplicate packages;
- normalize repository indexes;
- publish the reviewed Wiki source from accepted `main` if Wiki settings permit;
- apply branch/ruleset protections where authorized and technically available;
- establish an accepted tag/release only after acceptance evidence exists;
- produce a final repository inventory, branch disposition register, release manifest, and acceptance report.

---

## 9. Git and progress rules

- Work on the intended existing branch unless a genuinely isolated workstream requires a separate branch.
- Do not create an unbounded swarm of agents on shared migrations/models.
- One principal agent owns integration.
- Additional agents may operate only on bounded, low-conflict worktrees after interfaces are defined.
- Commit coherent slices atomically.
- Push each completed slice.
- Do not amend published commits unless explicitly authorized.
- Do not force-push.
- Do not merge any PR.
- Do not delete branches or files until unique content has been inventoried and preserved.

Keep `docs/finance/OVERNIGHT_RUN_STATE.md` or a successor state file current with:

- current branch and exact SHA;
- completed acceptance items;
- current in-progress item;
- commands/tests run;
- failures and fixes;
- generated artifacts;
- blockers;
- exact next command and resume point.

---

## 10. Immediate start directive

Begin with Stage 1.

1. Confirm repository, branch, head, and worktree state.
2. Read all controlling instructions and PR #9 acceptance findings.
3. Run the existing full local test/static-analysis suite and record the baseline.
4. Inspect current Alembic migrations and generation/run/scenario models.
5. Produce a concrete dependency map for P0 remediation, then immediately implement the first coherent vertical slice rather than stopping at the plan.
6. Prefer migration immutability and run/scenario isolation before expanding more financial features.
7. Add tests that would have failed under the old behavior.
8. Commit, push, update state, and continue to the next acceptance slice.

Do not report completion after one slice. Continue through the ordered acceptance work for as long as the active session permits.

---

## 11. Required reporting at every checkpoint

Report only evidence:

- branch and exact head SHA;
- files changed;
- behavior implemented;
- tests added;
- exact commands run;
- pass/fail/skip counts;
- reconciliation metrics;
- generated artifacts and where to inspect them;
- remaining P0/P1 findings;
- exact resume point.

Never report a feature as complete when only an interface, placeholder, empty table, structural workbook, or untested generator exists.

---

## 12. Definition of program completion

The broader program is complete only when:

- PR #9’s P0/P1 acceptance findings are demonstrably closed;
- finance/accounting behavior works on SQLite and PostgreSQL;
- multiple runs/scenarios coexist safely;
- integrated monthly statements and rollforwards reconcile;
- workbooks are semantically correct and tested against database results;
- public and unit exports are allowlisted and generated-artifact safety-scanned;
- review artifacts are downloadable;
- the enterprise portal and one coherent dossier/Wiki architecture are integrated;
- ARU and every other current business line have validated unit packages appropriate to their operations;
- every unit package reconciles to enterprise consolidation;
- branch/PR/repository hygiene is complete without loss of unique evidence;
- final documentation, manifests, CI, and release claims match the actual tested boundary;
- a second independent review approves merge/release.

Until then, use precise intermediate states and keep working through the acceptance sequence.
