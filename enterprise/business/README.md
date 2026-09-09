# Business-driven enterprise finance successor

This separately versioned model replaces the **2027–2031 Core operating forecast** with business events. It retains the complete 2026 enterprise reconstruction, existing Core asset/debt balances, the industrial physical/financial models, legal ownership, funding limits and consolidation. Neither finance v0.1 nor industrial release v2 is rewritten.

The [financial design](../../docs/finance/BUSINESS_DRIVEN_SUCCESSOR_2026-09-09.md) and [unit export contract](../../docs/audit/UNIT_EXPORT_SPECIFICATION.md) define interpretation and evidence. The [release index](../../docs/releases/BUSINESS_FINANCE_RELEASES.md) identifies distribution. All new prices, contracts, future occupancy and process assumptions are public synthetic conditional inputs, not observed history, approved price lists or commitments.

```bash
uv sync --frozen --all-extras
uv run python -m pytest enterprise/business/tests
uv run python -m enterprise.business.build
```

A release build requires a clean Git checkout and fails if source bytes or HEAD change during execution. For local investigation use `--allow-working-tree`; the identity explicitly marks that development build. This flag is not used in release CI. `--skip-package` omits only the ZIP. The generator replaces its own `enterprise/generated/business-v1` directory, rejects other output paths and never writes an execution database into a distribution.

## Source and behavior

| Source | Business behavior |
|---|---|
| `source/policy.json` | Explicit scenario drivers, 591 conditional authorized Core positions, 506 occupied positions, one employed-person cost, fractional borrowed assignments, inflation, support and collection rules |
| `source/contracts.json` | Foundry deployments/subscriptions and separate Atlas institutional licenses; annual billing, monthly service, renewal, churn and compute costs |
| `source/engagements.json` | Three Advisory practices on one bench; acceptance roles, baselines, committed/variable fees, rework, capacity, transfer; separately staffed Atlas product work |
| `source/projects.json` | Bounded Willow experiments and continue/change/kill/transfer gates |
| `source/assets.json` | Owned reusable equipment, depreciation and qualified same-entity transfers without profit |
| `source/recovery.json` | Separate mineral-tonne Stream 17 and water-volume Demotte economics; bypass, assay, costed lots, downstream acceptance and host obligations |
| `source/capital_cases.json` | Standalone mine-upgrade and closure-support sensitivities, outside booked industrial accounts |

Modeled Advisory handovers contain client-owned workflows and tests. Atlas subscriptions remain independent contracts; a matter does not automatically grant or transfer an Atlas license. The reference transfer validator rejects licensed-product components unless a separate contract-rights validator confirms them.

`model.py` generates source events, four-decimal balanced journals and operational subledgers. `advisory.py` implements matter contracts. `boundaries.py` supplies executable institutional boundary examples; it is not deployed Alexandria IAM. `industrial/planning/enterprise.py` accepts an optional provider while retaining its original behavior when omitted. `validation.py` recomputes ledger/subledger, unit/legal and distribution relationships independently of statement rendering.

## Outputs

The build creates the enterprise legal and unit statements, full removal/addition bridge from v2, three scenario comparisons, nonposting shared-support and intangible-quality views, capital cases, Core operating evidence and seven standalone unit packages. Each unit includes CSV, an allowlisted SQLite database, an audit workbook, explicit schema and source identity. Existing industrial physical and 2025–2026 reference registers are copied with source hashes and are not posted again as forecast transactions.

`manifest.json`, `SHA256SUMS.txt` and `validation.json` inventory and verify the entire package. The release ZIP lives under ignored `enterprise/dist/v1.0.0`; accepted distributions belong in GitHub Releases. The source fingerprint covers executable inputs, canon references and the locked environment. The preserved legacy adapter supplies its own run/profile/seed/migration identity.

## Limits that remain material

- Core 2026 is retained calibration. Conditional 2027 occupancy does not invent a 2026 personnel census.
- Planned payments are cash requests. Finite Treasury support can leave operating, capital or debt obligations unpaid. These scenarios are infeasible without changed decisions; the model does not grant vendor credit, covenant waivers, operating authority or financing.
- Deferred cash obligations remain an aggregate Treasury overlay. The export cannot identify which real invoice or employee went unpaid, and it is not a bank statement.
- Industrial waybills and role-based payroll evidence keep their existing reconstruction granularity. The reference populations disclose where detailed transactions are not modeled.
- The $30 million legacy intangible calibration remains separately visible. The management equity view excluding it is not a booked impairment.
- Legal tax elections, Advisory legal form/name, carry economics, exact sites, uranium custody and production Atlas runtime remain open in their controlling records.
