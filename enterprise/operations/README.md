# Business operations successor

This executable successor deepens all seven business lines beyond the accepted
[business-finance release](../business/README.md). Customer histories, credit events,
workforce changes, Advisory evidence and research/recovery records drive financial
journals. Industrial dated detail refines the retained monthly model. The 2026
reconstruction and previously released source files remain unchanged.

All new operating histories are public synthetic 2027–2031 scenarios. A passing
build means that records, accounting and disclosed outcomes reconcile. It does
not mean every scenario is funded, every schedule is feasible or every control passed.

## Run and review

```bash
uv sync --frozen --all-extras
uv run python -m pytest enterprise/operations/tests enterprise/business/tests industrial/planning/tests
uv run python -m enterprise.operations.build
```

The clean-source build writes its owned `enterprise/generated/operations-v1`
directory and a deterministic ZIP in `enterprise/dist/operations-v1.0.0`.
The package includes enterprise books, seven scoped CSV/SQLite exports, source and
financial bridges, executed client handovers, control results and a reviewed workbook.
Unknown columns, unapproved row scope, changed source bytes, stale workbook inputs
and accounting discrepancies fail acceptance.

Development requires `--allow-working-tree`. With `--schema-draft --prepare-review`,
the build proposes schema/scope rules and workbook inputs for review; it cannot
produce an accepted release. Approved JSON rules must be retained in source before
normal export. Scope permissions are never inferred dynamically by a release build.

## Implementation guides

| Workstream | Guide |
|---|---|
| Collections and Treasury | [Credit, receipts and cash obligations](docs/credit.md) |
| Foundry Field / Atlas | [Customers, contracts, support and ARR](docs/commercial.md) |
| Advisory | [Matter gates and client handovers](docs/matters.md) |
| Willow / Cradle / industrial | [Research, recovery, custody and service detail](docs/research.md) |
| Workforce / management | [Staffing, service costs and forecast revisions](docs/management.md) |
| Controls | [Scheduled evidence, exceptions and independent retests](docs/controls.md) |

See the [financial design](../../docs/finance/OPERATING_DEPTH_SUCCESSOR_2026-09-09.md),
[export specification](../../docs/audit/OPERATING_DEPTH_EXPORT_SPECIFICATION.md)
and [release record](../../docs/releases/BUSINESS_OPERATIONS_RELEASES.md).

## Reviewed workbook

`build_review.mjs` authors the six-sheet workbook using Artifact Tool and generated
`review_inputs.json`. Use the supplied primary Node runtime and a temporary directory
whose `node_modules` points to its installed runtime dependencies. Arguments are the
input JSON, publication directory and preview directory. Visually inspect every sheet.

The XLSX and `review_manifest.json` are retained in `publications`. Portable CI
regenerates the model and verifies every source cell, summary formula, cached result
and reconciliation before copying the reviewed bytes into the release. It does not
substitute another workbook writer. The report-year selector changes the displayed
year; it does not change model assumptions. Unit cash attribution is not a bank balance.

## Limits that remain explicit

Treasury attribution is a conditional request-order model, not employee-level payment
or banking evidence. Monthly schedules do not prove daily/weekly
liquidity. Industrial detail may identify infeasible shifts and confers no operating
authority. Detailed Advisory histories cover six selected matters. Forecast-vintage
cash is Core requested cash before enterprise Treasury/tax, not a consolidated
financing revision. Control exercises do not establish production effectiveness.

Legal/tax elections, permanent appointments, production Alexandria/Daedalus access
and retention, exact geography and the approved headquarters image remain separately
gated decisions. Earlier releases remain immutable and separately interpretable.
