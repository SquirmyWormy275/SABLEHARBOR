# Database and accounting architecture

## Design

The executable reference uses SQLAlchemy with SQLite for zero-setup generation and PostgreSQL compatibility for larger runs. Stable UUIDv5 identifiers, effective dates, scenario codes, fact states, and source provenance separate canon from assumptions and generated instances.

The first implemented domains are:

- organization: legal entities, sites, workers and reporting segments;
- commercial: parties and contracts;
- general ledger: entity books, periods, accounts, balanced immutable journals, reversals and close;
- acquisition/fixed assets: asset class, service date, cost, useful life and acquisition layer;
- mine: monthly production, staged inventory and environmental/ARO obligations;
- logistics: movements, commodity, custody state, revenue and intercompany flag;
- planning: scenario values with units, provenance and fact state;
- reporting: consolidated trial balance, income statement, balance sheet bridge and assumption register.

## Dimensional model

Journal lines carry account, entity through book, period, segment, cost center, project, counterparty, currency and fact state. Operational records retain site and source-specific dimensions instead of being flattened into one universal transaction.

The baseline segments are `FOUNDRY_FIELD`, `DELIVERY`, `ATLAS`, `WILLOW`, `PALE_SUN`, `CRADLE`, `ARU_BST`, `ADVISORY`, `CORPORATE`, and `ELIMINATION`. Emberline remains a historical predecessor dimension with successor lineage and no 2026 standalone P&L.

## Accounting kernel

- Each posted journal must contain nonzero, balanced debit and credit lines.
- Posted journals and lines are immutable; correction uses a linked reversal.
- Closed periods reject new posting and cannot close with drafts.
- Transaction, functional and reporting amounts are retained separately.
- Intercompany counterparty dimensions support matching and eliminations.
- Consolidation eliminations are journalized in a dedicated book and never overwrite entity records.

## Reproducibility and public boundary

`shfin generate --profile full --scenario base --seed 20260831` produces deterministic, public-safe synthetic identifiers and values. It does not generate real personal data or hidden benchmark truth. Re-running the same scenario and seed is idempotent within a database.

## Known next increments

Monthly AR/AP, payroll, procurement, maintenance work orders, fixed-asset depreciation/depletion, detailed PPA, tax, debt amortization, revenue-performance obligations, budgets/forecasts, and full cash-flow statements require additional subledger detail. The current schema supplies stable boundaries for those additions without claiming that summary journals are source-level evidence.

