# Industrial planning and enterprise successor

Version 2.0.0 extends Pale Sun, Red Wash, American Resource Utility and Blood, Sweat & Tears Railway with a five-year operating and financial plan, capital alternatives, linked transaction evidence, disruption scenarios, whole-enterprise consolidation and an offline case browser.

The planning date is September 6, 2026. December 2026 is the accepted forecast starting point. Every 2027–2031 month is a prospective scenario. The [v1.0.0 release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/sable-harbor-industrial-case-v1.0.0) remains preserved; every one of its 199 selected artifact hashes is checked during successor acceptance.

## Start with the case

Extract the complete participant ZIP and open `case_browser.html`. The browser works locally without a server, account or network connection. Choose a scenario, entity and year; inspect the cash chart, capital comparison, operating constraints and documents. Selecting an identifier follows related invoices, purchase orders, receipts, journal lines and payments. CSV downloads retain the selected data. The SQLite database offers the same reviewed source tables with artifact lineage, and the workbook provides indexed financial extracts.

Read the controlled explanations in order:

1. [Five-year financial plan](docs/FIVE_YEAR_FINANCIAL_PLAN.md): opening accounts, monthly recognition, funding, debt, taxes and feasibility.
2. [Operating scenarios](docs/OPERATING_SCENARIOS.md): realized volumes, capacity, disruptions, inventory and conditional expansion.
3. [Capital investment review](docs/CAPITAL_INVESTMENT_REVIEW.md): common demand, incremental cash flows and demand/discount/residual sensitivities.
4. [Transaction evidence](docs/TRANSACTION_EVIDENCE.md): procurement inputs, reconstructed service/payroll records and bank clearing.
5. [Enterprise integration](docs/ENTERPRISE_INTEGRATION.md): legacy replacement, parent funding, legal books, eliminations and operating-unit extracts.

The [planning decision record](../../docs/canon/INDUSTRIAL_PLANNING_SUCCESSOR_2026-09-06.md) defines the authorized implementation scope. No forecast creates capital, borrowing or regulatory approval. A scenario may have balanced accounts and still exhaust funding or miss customer demand. Those failures remain explicit.

## Reproduce from the source checkout

Use the repository's locked Python environment:

```bash
uv sync --frozen --all-extras
uv run python -m industrial.planning.build
uv run python -m pytest industrial/planning/tests
```

The build regenerates the preserved mine and industrial anchors, then operations, finance, capital, linked evidence, enterprise accounts and independent acceptance checks. It packages only the explicit participant catalog. A release requires a clean source commit. During implementation, use `--allow-working-tree`; its manifest visibly identifies the development state. `--skip-package` runs the models and reconciliation only.

Canonical scenario policies live in `source/`. Generated model exports live under `industrial/generated/planning/`; distributable artifacts live under `industrial/dist/v2.0.0/` and are published as versioned release assets. Generated ZIPs and transient legacy-engine databases do not belong in Git. The release manifest binds the selected artifact bytes, source revision, toolchain and model identity. Rebuilding the entire pipeline twice is the reproducibility check; merely writing the same staged files twice is an additional ZIP-format check.

The retained enterprise Core is a disclosed synthetic envelope. Its unit views do not imply a complete replacement of every unresolved enterprise policy or a new set of legal corporations. Public synthetic planning records are separate from private assessment material.
