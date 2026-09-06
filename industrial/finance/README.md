# Industrial financial case

**Record:** SH-IND-FIN-20260905-001. **Case publication cutoff:** September 5, 2026. **Nature:** public synthetic company case, with separately identified derived and provisional assumptions. This is a successor scenario; the released enterprise finance v0.1 configuration, source locks and historical package bytes are preserved.

The controlling inputs are [finance.json](../source/finance.json), the cost and operating records in [operations.json](../source/operations.json), and the selected mine inputs in [core_operating_data.json](../../red_wash/source/core_operating_data.json). The builder produces contracts, customers, payroll, journals, trial balances, financial statements, acquisition accounting, fixed-asset and debt schedules, reciprocal intercompany invoices, financing, legal-book views and sensitivities.

```bash
python industrial/tools/build_financials.py
python -m unittest discover -s industrial/tests -p 'test_financials.py' -v
```

The canonical output directory is `industrial/generated/finance/`. It is reproducible build output, not another hand-maintained source. `financial_summary.json` identifies all result scopes; `manifest.json` binds exact source and artifact hashes. Complete distributable packages are assembled by the industrial package builder and delivered under the repository's release policy.

| Output | Purpose |
|---|---|
| `customer_register.csv`, `contract_register.csv` | 25 fictional customers, 29 contracts, annual price/physical-volume support and concentration |
| `contract_monthly_2025.csv` | Monthly contract quantities, tariffs, fixed reservation/accessorial fees and invoiced revenue |
| `employee_census_payroll.csv` | 131 FTE, 14 named leaders, anonymized remaining staff, functions, labor representation, salaries and burden |
| `external_cost_budget_support.csv`, `rail_opex_class_bridge.csv` | Nonpayroll budgets and rail expense-class decomposition into census payroll, shared allocation and external costs |
| `receivables_aging_and_allowance.csv` | Gross-to-net AR, specific allowance and opening/closing allowance movement |
| `parts_fuel_materials_inventory.csv` | Inventory classes, equivalent quantities, blended costs and net carrying amounts |
| `reported_to_normalized_ebitda.csv` | Income-to-EBITDA bridge and explicit zero unsupported earnings addbacks |
| `aru_2025_journal.csv`, `aru_2025_trial_balance.csv` | Double-entry historical synthetic baseline |
| `aru_2025_monthly_statements.csv` | Cumulative monthly balance sheet, income and cash-flow summaries |
| `aru_acquisition_opening_trial_balance.csv` | January 7 acquisition opening after PPA, refinancing and financing fees |
| `aru_acquisition_tax_allocation.csv` | Independent assumed-liability/asset tax allocation, tax goodwill and initial book/tax component |
| `aru_2026_journal.csv`, `aru_2026_trial_balance.csv` | January 7–December 31 acquired-entity model, including postclose cash funding |
| `aru_2026_fixed_assets.csv`, `aru_2026_debt_leases.csv` | Capital, depreciation, debt principal/interest, lease and financing-fee rollforwards |
| `aru_2026_tax_rollforward.csv` | Cumulative current tax, tax-goodwill amortization, deferred taxes and quarterly modeled cash payments |
| `red_wash_2026_journal.csv`, `red_wash_2026_trial_balance.csv` | Separate changed mine/platform scenario with the interface and corrected ARO timing |
| `financial_statements.csv` | Income statement, balance sheet and cash-flow statement lines with explicit sign conventions |
| `separate_legal_entity_trial_balances.csv` | ARU/BST and Pale Sun/Red Wash closing books, including disclosed ownership and treasury allocations |
| `ownership_and_treasury_eliminations.csv` | Parent investments, subsidiary capital, treasury current accounts and platform service eliminations |
| `interface_normalized_economics.csv` | 215 billable physical cars; 10 unbilled buffer cars are outside revenue |
| `intercompany_invoices_2026.csv` | Exact reciprocal invoice IDs, parties, quantities, segment rates, costs and payment timing |
| `intercompany_eliminations.csv` | ARU/Red Wash income-statement and balance-sheet eliminations |
| `parent_equity_funding_2026.csv` | Funding by month, recipient and purpose; never booked as income |
| `red_wash_closure_cashflow_calibration.csv` | Explicit liability-calibrated closure cash-flow timing, with independent engineering limitations |
| `seller_cap_table.csv`, `scenario_sensitivities.csv` | Seller allocations and changes in tax, volume, renewal and interface utilization |

The five customer concentration anchors are $4.62M, $3.75M, $3.30M, $2.70M and $2.43M: exactly $16.8M, or 40% of $42M. None is a real asserted counterparty. Contracts make the annual volume-times-price arithmetic visible. Cost schedules distinguish locked segment envelopes from independently priced physical interface work; allocating a selected budget is not represented as evidence of a supplier quotation.

See [accounting and transaction treatment](TRANSACTION_ACCOUNTING.md), [operating drivers and cost support](DRIVERS_AND_COST_SUPPORT.md), [mine and funding bridge](RED_WASH_AND_FUNDING.md), and [assumptions, temporal controls and limitations](ASSUMPTIONS_AND_TEMPORAL_CONTROLS.md).
