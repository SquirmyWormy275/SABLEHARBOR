# Contract clauses and accounting evidence

All legal instruments remain DRAFT_FOR_REVIEW. Native model records are evidence for exercises, not independent execution evidence. No cross-population aggregate is permitted.

Generated from [source.json](source.json). [Workbook](links.xlsx) · [SQLite](links.sqlite3).

## Reconciliation

| Check | Population | Verified USD | Result |
| --- | --- | ---: | --- |
| BIZ-base-0000014 | FF-2027-BASE | 1,740,000.00 | PASS |
| BIZ-base-0000138 | FF-2027-BASE | 435,000.00 | PASS |
| BIZ-base-0000904 | FF-2027-BASE | 1,305,000.00 | PASS |
| BIZ-base-0001186 | FF-2027-BASE | 14,500.00 | PASS |
| BIZ-base-0001401 | FF-2027-BASE | 145,000.00 | PASS |
| BIZ-base-0001754 | FF-2027-BASE | 174,000.00 | PASS |
| FF cash including recovery | FF-2027-BASE | 609,000.00 | PASS |
| FF economic claim bridge | FF-2027-BASE | 971,500.00 | PASS |
| FF ending AR | FF-2027-BASE | 0.00 | PASS |
| Eight retention allocations | ARU-2026-INPUT | 500,000.00 | PASS |
| ARU consideration allocation | ARU-2026-MODEL | 48,000,000.00 | PASS |
| ARU sources and uses before fees | ARU-2026-MODEL | 61,500,000.00 | PASS |
| ARU opening balance | ARU-2026-MODEL | 70,650,000.00 | PASS |
| ARU term principal bridge | ARU-2026-MODEL | 21,375,000.00 | PASS |
| RW acquired net assets | RW-2025-ACQUISITION | 28,000,000.00 | PASS |

Each amount belongs to its stated population. Do not total this table.

## LEGAL-GAP-RW-CHRONOLOGY

Preserved disposition: `SOURCE_CONFLICT_PRESERVED`. New posting authorized: **No**.

### SH-LEGAL-ACCT-RW-CHRONOLOGY-01

[6. Accounting preservation schedule](../../../../docs/legal/gap-instruments/source/rw-chronology.md#6-accounting-preservation-schedule) → [red_wash/source/core_operating_data.json](../../../../red_wash/source/core_operating_data.json)

`MODELED_SCHEDULE` · `RW-2025-ACQUISITION`

Same transaction as RW title; duplicate reference must not be counted twice. Chronology correction authorizes no accounting change.

Exact native selector: `{"pointer": "/transaction"}`.

```json
{
  "close_date": "2025-07-18",
  "seller_display_name": "Northstar Minerals, Inc.",
  "seller_display_name_state": "LOCKED",
  "seller_legal_name": "Northstar Minerals, Inc.",
  "seller_legal_name_state": "LOCKED",
  "seller_jurisdiction": "Wyoming",
  "seller_jurisdiction_state": "LOCKED",
  "operating_assets_usd": 42000000,
  "current_assets_usd": 4500000,
  "aro_assumed_usd": 16000000,
  "other_liabilities_usd": 2500000,
  "cash_consideration_usd": 28000000,
  "goodwill_usd": 0,
  "transaction_debt_usd": 0,
  "environmental_title_escrow_usd": 3000000,
  "holdback_usd": 500000,
  "h2_2025_stabilization_usd": 11000000,
  "capitalized_rehabilitation_usd": 8000000,
  "repair_stabilization_expense_usd": 3000000
}
```

## LEGAL-GAP-TAX-FILING

Preserved disposition: `EXTERNAL_EVIDENCE_NOT_ESTABLISHED`. New posting authorized: **No**.

### SH-LEGAL-ACCT-TAX-FILING-01

[6. Allocation and accounting workpaper](../../../../docs/legal/gap-instruments/source/tax-filing.md#6-allocation-and-accounting-workpaper) → [docs/finance/evidence/tax-transaction/acquisition_ppa.csv](../../../../docs/finance/evidence/tax-transaction/acquisition_ppa.csv)

`MODELED_SCHEDULE` · `ARU-2026-MODEL`

Conditional election model: stock consideration 48,000,000; identifiable net assets 33,237,500; book goodwill 14,762,500; tax goodwill 13,000,000; DTA 587,500. Filing-ready is not filed. No alternative tax outcome is invented.

Exact native selector: `{"csv": true}`.

| measure | amount_usd |
| --- | --- |
| net_book_equity_after_excess_cash_distribution_usd | 13350000 |
| book_ppe_net_usd | 22700000 |
| fair_ppe_usd | 42000000 |
| fair_ppe_step_up_usd | 19300000 |
| identifiable_net_assets_before_refinancing_usd | 33237500 |
| stock_consideration_usd | 48000000 |
| goodwill_usd | 14762500 |
| tax_goodwill_basis_usd | 13000000 |
| initial_book_goodwill_excess_over_tax_usd | 1762500 |
| close_sources_before_fees_usd | 61500000 |
| close_uses_before_fees_usd | 61500000 |
| deferred_tax_asset_usd | 587500 |
| deferred_tax_basis_usd | 2350000 |
| new_debt_upstream_acquisition_distribution_usd | 9000000 |
| parent_cash_before_fees_usd | 39000000 |
| parent_cash_including_fees_usd | 40200000 |
| working_capital_usd | 4500000 |
| working_capital_true_up_usd | 0 |

### SH-LEGAL-ACCT-TAX-FILING-02

[6. Allocation and accounting workpaper](../../../../docs/legal/gap-instruments/source/tax-filing.md#6-allocation-and-accounting-workpaper) → [docs/finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv](../../../../docs/finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv)

`MODELED_SCHEDULE` · `ARU-2026-MODEL`

Sixteen ARU_GROUP opening balances reconcile independently. Account 1600 goodwill, 1800 deferred tax asset, 2200 environmental reserve and 2300 claims remain modeled balances.

Exact native selector: `{"csv": true}`.

| entity | year | account | account_name | type | debit_balance_usd | credit_balance_usd | signed_usd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ARU_GROUP | 2026 | 1000 | Cash | asset | 2000000 | 0 | 2000000 |
| ARU_GROUP | 2026 | 1100 | External receivables, net of allowance | asset | 6000000 | 0 | 6000000 |
| ARU_GROUP | 2026 | 1200 | Inventory cash cost | asset | 1800000 | 0 | 1800000 |
| ARU_GROUP | 2026 | 1300 | Prepaids | asset | 700000 | 0 | 700000 |
| ARU_GROUP | 2026 | 1400 | PPE gross | asset | 42000000 | 0 | 42000000 |
| ARU_GROUP | 2026 | 1500 | Finance lease ROU gross | asset | 2500000 | 0 | 2500000 |
| ARU_GROUP | 2026 | 1600 | Goodwill | asset | 14762500 | 0 | 14762500 |
| ARU_GROUP | 2026 | 1700 | Debt issuance cost, contra term debt | liability | 300000 | 0 | 300000 |
| ARU_GROUP | 2026 | 1800 | Deferred tax asset on reserved liabilities | asset | 587500 | 0 | 587500 |
| ARU_GROUP | 2026 | 2000 | Trade payables | liability | 0 | 3000000 | -3000000 |
| ARU_GROUP | 2026 | 2100 | Operating accruals | liability | 0 | 1000000 | -1000000 |
| ARU_GROUP | 2026 | 2200 | Environmental reserve / ARO | liability | 0 | 1750000 | -1750000 |
| ARU_GROUP | 2026 | 2300 | Claim reserve / other liabilities | liability | 0 | 600000 | -600000 |
| ARU_GROUP | 2026 | 2400 | Term debt face value | liability | 0 | 22500000 | -22500000 |
| ARU_GROUP | 2026 | 2600 | Finance lease obligation | liability | 0 | 2500000 | -2500000 |
| ARU_GROUP | 2026 | 3000 | Contributed equity | equity | 0 | 39300000 | -39300000 |

### SH-LEGAL-ACCT-TAX-FILING-03

[5. Filing control and delivery workpaper](../../../../docs/legal/gap-instruments/source/tax-filing.md#5-filing-control-and-delivery-workpaper) → [docs/finance/evidence/tax-transaction/aru_2026_tax_rollforward.csv](../../../../docs/finance/evidence/tax-transaction/aru_2026_tax_rollforward.csv)

`MODELED_SCHEDULE` · `ARU-2026-MODEL`

Monthly modeled tax accrual, settlement and goodwill bases; this is not a return, tax payment confirmation or IRS acceptance.

Exact native selector: `{"csv": true}`.

| month | book_pretax_income_usd | cumulative_book_pretax_income_usd | cumulative_goodwill_tax_deduction_usd | cumulative_taxable_income_usd | current_tax_expense_usd | deferred_tax_expense_usd | current_tax_cash_paid_usd | current_tax_settlement_signed_balance_usd | deferred_tax_asset_reserves_usd | deferred_tax_asset_interim_loss_usd | deferred_tax_liability_goodwill_usd | goodwill_tax_basis_usd | goodwill_book_basis_usd | initial_goodwill_excess_excluded_from_opening_dtl_usd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | -139925 | -139925 | 72222 | -212147 | 0 | -34981 | 0 | 0 | 587500 | 53037 | 18056 | 12927778 | 14762500 | 1762500 |
| 2 | -134103 | -274028 | 144444 | -418472 | 0 | -33526 | 0 | 0 | 587500 | 104618 | 36111 | 12855556 | 14762500 | 1762500 |
| 3 | 224350 | -49678 | 216667 | -266345 | 0 | 56088 | 0 | 0 | 587500 | 66586 | 54167 | 12783333 | 14762500 | 1762500 |
| 4 | 231627 | 181949 | 288889 | -106940 | 0 | 57906 | 0 | 0 | 587500 | 26735 | 72222 | 12711111 | 14762500 | 1762500 |
| 5 | 627492 | 809441 | 361111 | 448330 | 112083 | 44791 | 0 | -112083 | 587500 | 0 | 90278 | 12638889 | 14762500 | 1762500 |
| 6 | 613024 | 1422465 | 433333 | 989132 | 135200 | 18055 | 247283 | 0 | 587500 | 0 | 108333 | 12566667 | 14762500 | 1762500 |
| 7 | 579659 | 2002124 | 505556 | 1496568 | 126859 | 18056 | 0 | -126859 | 587500 | 0 | 126389 | 12494444 | 14762500 | 1762500 |
| 8 | 574969 | 2577093 | 577778 | 1999315 | 125687 | 18056 | 0 | -252546 | 587500 | 0 | 144445 | 12422222 | 14762500 | 1762500 |
| 9 | 584672 | 3161765 | 650000 | 2511765 | 128112 | 18055 | 380658 | 0 | 587500 | 0 | 162500 | 12350000 | 14762500 | 1762500 |
| 10 | 587860 | 3749625 | 722222 | 3027403 | 128910 | 18056 | 0 | -128910 | 587500 | 0 | 180556 | 12277778 | 14762500 | 1762500 |
| 11 | 194900 | 3944525 | 794444 | 3150081 | 30669 | 18055 | 0 | -159579 | 587500 | 0 | 198611 | 12205556 | 14762500 | 1762500 |
| 12 | 177112 | 4121637 | 866667 | 3254970 | 26223 | 18056 | 185802 | 0 | 587500 | 0 | 216667 | 12133333 | 14762500 | 1762500 |

## LEGAL-GAP-FORMATIONS

Preserved disposition: `INTERNAL_RECONSTRUCTION_ONLY`. New posting authorized: **No**.

### SH-LEGAL-ACCT-FORMATIONS-01

[2. Schedule A — existing perimeter to be carried into the books](../../../../docs/legal/gap-instruments/source/formations.md#2-schedule-a--existing-perimeter-to-be-carried-into-the-books) → [industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md](../../../../industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md)

`NO_ENTRY` · `NO-POSTING-FORMATIONS`

Internal ownership acknowledgments do not issue new equity or supply missing subscription postings.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "industrial/corporate/LEGAL_STRUCTURE_AND_FORMATION.md",
  "posting": null
}
```

## LEGAL-GAP-FINANCING-DOCUMENTS

Preserved disposition: `APPROVAL_RECORD_ONLY`. New posting authorized: **No**.

### SH-LEGAL-ACCT-FINANCING-DOCUMENTS-01

[7. Completion schedules](../../../../docs/legal/gap-instruments/source/financing-documents.md#7-completion-schedules) → [docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md](../../../../docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md)

`NO_ENTRY` · `NO-POSTING-FINANCING-DOCUMENTS`

Approximately 48M and 135M board financing economics are historical approval evidence, not a new subscription receipt or posting. No exact cap table is inferred.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md",
  "posting": null
}
```

## LEGAL-GAP-DEBT-LIENS

Preserved disposition: `MODEL_AND_SUMMARY_ONLY`. New posting authorized: **No**.

### SH-LEGAL-ACCT-DEBT-LIENS-01

[2. Proposed term-credit agreement](../../../../docs/legal/gap-instruments/source/debt-liens.md#2-proposed-term-credit-agreement) → [docs/finance/evidence/tax-transaction/aru_2026_debt.csv](../../../../docs/finance/evidence/tax-transaction/aru_2026_debt.csv)

`MODELED_SCHEDULE` · `ARU-2026-MODEL`

Term-debt monthly schedule; 6.75% ACT/365 modeled convention. Contract maturity, lender release and covenant compliance remain unverified. Rounded source dollars retained.

Exact native selector: `{"csv": true}`.

| month | opening_term_usd | term_principal_usd | term_interest_usd | closing_term_usd | lease_principal_usd | lease_interest_usd | closing_lease_usd | debt_issue_amortization_usd | deferred_debt_issue_cost_usd | revolver_draw_usd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 22500000 | 0 | 104024 | 22500000 | 34246 | 8503 | 2465754 | 4032 | 295968 | 0 |
| 2 | 22500000 | 0 | 116507 | 22500000 | 38356 | 9384 | 2427398 | 5000 | 290968 | 0 |
| 3 | 22500000 | 0 | 128990 | 22500000 | 42466 | 10218 | 2384932 | 5000 | 285968 | 0 |
| 4 | 22500000 | 375000 | 123164 | 22125000 | 41096 | 9717 | 2343836 | 5000 | 280968 | 0 |
| 5 | 22125000 | 0 | 126840 | 22125000 | 42466 | 9863 | 2301370 | 5000 | 275968 | 0 |
| 6 | 22125000 | 0 | 122748 | 22125000 | 41096 | 9373 | 2260274 | 5000 | 270968 | 0 |
| 7 | 22125000 | 375000 | 125106 | 21750000 | 42466 | 9508 | 2217808 | 5000 | 265968 | 0 |
| 8 | 21750000 | 0 | 124690 | 21750000 | 42466 | 9328 | 2175342 | 5000 | 260968 | 0 |
| 9 | 21750000 | 0 | 120668 | 21750000 | 41096 | 8855 | 2134246 | 5000 | 255968 | 0 |
| 10 | 21750000 | 375000 | 122956 | 21375000 | 42466 | 8973 | 2091780 | 5000 | 250968 | 0 |
| 11 | 21375000 | 0 | 118587 | 21375000 | 41096 | 8512 | 2050684 | 5000 | 245968 | 0 |
| 12 | 21375000 | 0 | 122540 | 21375000 | 42465 | 8618 | 2008219 | 5000 | 240968 | 0 |

### SH-LEGAL-ACCT-DEBT-LIENS-02

[7. Reconciled source schedules](../../../../docs/legal/gap-instruments/source/debt-liens.md#7-reconciled-source-schedules) → [docs/finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv](../../../../docs/finance/evidence/tax-transaction/aru_acquisition_opening_trial_balance.csv)

`MODELED_SCHEDULE` · `ARU-2026-MODEL`

Opening accounts 1700 debt issuance contra debt, 2400 face debt, 2600 retained leases. This is ARU_GROUP model opening balance, not individual statutory books.

Exact native selector: `{"csv": true, "where": {"account": ["1700", "2400", "2600"]}}`.

| entity | year | account | account_name | type | debit_balance_usd | credit_balance_usd | signed_usd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ARU_GROUP | 2026 | 1700 | Debt issuance cost, contra term debt | liability | 300000 | 0 | 300000 |
| ARU_GROUP | 2026 | 2400 | Term debt face value | liability | 0 | 22500000 | -22500000 |
| ARU_GROUP | 2026 | 2600 | Finance lease obligation | liability | 0 | 2500000 | -2500000 |

## LEGAL-GAP-WORKFORCE

Preserved disposition: `PARTIAL_SYNTHETIC_TERMS`. New posting authorized: **No**.

### SH-LEGAL-ACCT-WORKFORCE-01

[7. Individual retention schedules](../../../../docs/legal/gap-instruments/source/workforce.md#7-individual-retention-schedules) → [industrial/source/finance.json](../../../../industrial/source/finance.json)

`MODELED_SCHEDULE` · `ARU-2026-INPUT`

Eight accepted allocations total 500,000; neither draft signatures nor payment confirmations are supplied. Do not add eight people to enterprise headcount.

Exact native selector: `{"pointer": "/transaction/retention_allocations"}`.

```json
{
  "Nora Ashcombe": 100000,
  "Gareth Pike": 60000,
  "Tessa Rourke": 60000,
  "Owen Halberg": 50000,
  "Seth Kettering": 80000,
  "Derek Fenwick": 50000,
  "Marta Ellery": 50000,
  "Inez Calderon": 50000
}
```

### SH-LEGAL-ACCT-WORKFORCE-02

[2. Retention consideration and payment](../../../../docs/legal/gap-instruments/source/workforce.md#2-retention-consideration-and-payment) → [industrial/tools/build_financials.py](../../../../industrial/tools/build_financials.py)

`MODEL_RULE` · `ARU-2026-GENERATOR`

Native IDs RETENTION-POOL (5700/2110), RETENTION-PAYMENT (2110/cash), TOLMAN-CONSULTING (5700/cash). This links rules only; generated payroll or bank evidence is not claimed. July modeled installment 250,000 differs from full award pool.

Exact native selector: `{"start": "        retention = retention_schedule[month - 1]", "end": "        is_payment_month = ("}`.

```python
        retention = retention_schedule[month - 1]
        ledger.pair(
            month,
            "5700",
            "2110",
            retention,
            "Retention compensation accrued by service days",
            "RETENTION-POOL",
        )
        if month == 7:
            ledger.cash(
                month,
                "2110",
                usd(Decimal(t["retention_pool"]) / 2),
                "Six-month retention installment paid July 7",
                "RETENTION-PAYMENT",
            )
        consult = consulting_schedule[month - 1]
        if consult:
            ledger.cash(
                month,
                "5700",
                consult,
                "Seller knowledge-transfer consulting, no operating authority",
                "TOLMAN-CONSULTING",
            )
```

### SH-LEGAL-ACCT-WORKFORCE-03

[8. Separate Fred Tolman consultancy](../../../../docs/legal/gap-instruments/source/workforce.md#8-separate-fred-tolman-consultancy) → [industrial/source/finance.json](../../../../industrial/source/finance.json)

`MODELED_SCHEDULE` · `ARU-2026-INPUT`

225,000 consultancy is separate from the 500,000 retention pool; no new payable or actual payment arises from this draft.

Exact native selector: `{"pointer": "/transaction/seller_consulting_total"}`.

```json
225000
```

## LEGAL-GAP-CARRY

Preserved disposition: `POLICY_NOT_INDIVIDUAL_GRANT`. New posting authorized: **No**.

### SH-LEGAL-ACCT-CARRY-01

[5. Grant instrument and vesting](../../../../docs/legal/gap-instruments/source/carry.md#5-grant-instrument-and-vesting) → [docs/advisory/CARRY_PLAN_STANDARD.md](../../../../docs/advisory/CARRY_PLAN_STANDARD.md)

`NO_ENTRY` · `NO-POSTING-CARRY`

No individual grant exists; do not recognize a draft award or invent units, valuation or liability.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "docs/advisory/CARRY_PLAN_STANDARD.md",
  "posting": null
}
```

## LEGAL-GAP-ADVISORY-CONTRACTS

Preserved disposition: `DESIGN_STANDARD_NOT_EXECUTED`. New posting authorized: **No**.

### SH-LEGAL-ACCT-ADVISORY-CONTRACTS-01

[4. Fees, invoices and changes](../../../../docs/legal/gap-instruments/source/advisory-contracts.md#4-fees-invoices-and-changes) → [docs/advisory/LEGAL_AND_CONTRACTING_TERM_SHEET.md](../../../../docs/advisory/LEGAL_AND_CONTRACTING_TERM_SHEET.md)

`NO_ENTRY` · `NO-POSTING-ADVISORY-CONTRACTS`

No executed client-specific SOW, consideration or performance facts; draft fees cannot create revenue or receivables.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "docs/advisory/LEGAL_AND_CONTRACTING_TERM_SHEET.md",
  "posting": null
}
```

## LEGAL-GAP-COLO

Preserved disposition: `PROVIDER_SELECTED_CONTRACT_DRAFT`. New posting authorized: **No**.

### SH-LEGAL-ACCT-COLO-01

[6. Commencement and invoice verification](../../../../docs/legal/gap-instruments/source/colo.md#6-commencement-and-invoice-verification) → [enterprise/runtime/docs/CONTRACT_DOSSIER.md](../../../../enterprise/runtime/docs/CONTRACT_DOSSIER.md)

`NO_ENTRY` · `NO-POSTING-COLO`

Selection and draft orders create no supported vendor payable or acceptance date; conditional runtime forecasts remain separate.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "enterprise/runtime/docs/CONTRACT_DOSSIER.md",
  "posting": null
}
```

## LEGAL-GAP-LAND

Preserved disposition: `SYNTHETIC_ACQUISITION_UNRESOLVED_SETTLEMENT`. New posting authorized: **No**.

### SH-LEGAL-ACCT-LAND-01

[6. Proposed accounting instruction](../../../../docs/legal/gap-instruments/source/land.md#6-proposed-accounting-instruction) → [enterprise/runtime/finance.py](../../../../enterprise/runtime/finance.py)

`MODEL_RULE` · `RUNTIME-2026-OVERLAY`

Existing RT-LAND-20260904 rule debits RT_LAND 3,000,000 and credits RT_SETTLEMENT_UNRESOLVED 3,000,000 in each scenario. Scenarios are alternatives, never summed. No second land debit, paid cash, lender or vendor liability is inferred.

Exact native selector: `{"start": "        if (year, month) == (2026, 9):", "end": "        if year < 2027:"}`.

```python
        if (year, month) == (2026, 9):
            books.post(
                "SHI",
                year,
                month,
                [("RT_LAND", D(3000000)), ("RT_SETTLEMENT_UNRESOLVED", D(-3000000))],
                "RT-LAND-20260904",
                "Synthetic land effective September 4; recorded September 11; settlement unresolved, no cash or vendor financing asserted",
                kind="RUNTIME_DATED_RECONCILIATION_ADJUSTMENT",
            )
```

## LEGAL-GAP-HOST-RIGHTS

Preserved disposition: `CANON_RIGHTS_WITH_UNFIXED_TERMS`. New posting authorized: **No**.

### SH-LEGAL-ACCT-HOST-RIGHTS-01

[6. Settlement and supporting accounts](../../../../docs/legal/gap-instruments/source/host-rights.md#6-settlement-and-supporting-accounts) → [docs/canon/CRADLE_CLOSEOUT_2026-09-06.md](../../../../docs/canon/CRADLE_CLOSEOUT_2026-09-06.md)

`NO_ENTRY` · `NO-POSTING-HOST-RIGHTS`

Host title and recovery rights do not fix rates or volumes; no new royalty, host consolidation or permanent participation term.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "docs/canon/CRADLE_CLOSEOUT_2026-09-06.md",
  "posting": null
}
```

## LEGAL-GAP-TENURE

Preserved disposition: `SITE_PLAN_NOT_TITLE_RECORD`. New posting authorized: **No**.

### SH-LEGAL-ACCT-TENURE-01

[8. Financial and risk allocation](../../../../docs/legal/gap-instruments/source/tenure.md#8-financial-and-risk-allocation) → [geospatial/facilities/README.md](../../../../geospatial/facilities/README.md)

`NO_ENTRY` · `NO-POSTING-TENURE`

Plans and access draft do not establish a lease commencement, rent, right-of-use asset or title.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "geospatial/facilities/README.md",
  "posting": null
}
```

## LEGAL-GAP-RW-TITLE

Preserved disposition: `INSTRUMENT_SCHEDULE_NOT_INDEPENDENT_CONFIRMATION`. New posting authorized: **No**.

### SH-LEGAL-ACCT-RW-TITLE-01

[8. Consideration and escrow reconciliation](../../../../docs/legal/gap-instruments/source/rw-title.md#8-consideration-and-escrow-reconciliation) → [red_wash/source/core_operating_data.json](../../../../red_wash/source/core_operating_data.json)

`MODELED_SCHEDULE` · `RW-2025-ACQUISITION`

28,000,000 acquisition consideration reconciles to 42,000,000 operating assets plus 4,500,000 current assets less 16,000,000 ARO and 2,500,000 other liabilities. 3,000,000 escrow and 500,000 holdback are closing components, not present balances or authorized releases.

Exact native selector: `{"pointer": "/transaction"}`.

```json
{
  "close_date": "2025-07-18",
  "seller_display_name": "Northstar Minerals, Inc.",
  "seller_display_name_state": "LOCKED",
  "seller_legal_name": "Northstar Minerals, Inc.",
  "seller_legal_name_state": "LOCKED",
  "seller_jurisdiction": "Wyoming",
  "seller_jurisdiction_state": "LOCKED",
  "operating_assets_usd": 42000000,
  "current_assets_usd": 4500000,
  "aro_assumed_usd": 16000000,
  "other_liabilities_usd": 2500000,
  "cash_consideration_usd": 28000000,
  "goodwill_usd": 0,
  "transaction_debt_usd": 0,
  "environmental_title_escrow_usd": 3000000,
  "holdback_usd": 500000,
  "h2_2025_stabilization_usd": 11000000,
  "capitalized_rehabilitation_usd": 8000000,
  "repair_stabilization_expense_usd": 3000000
}
```

## LEGAL-GAP-URANIUM-CUSTODY

Preserved disposition: `OPEN_GATED_EXCLUDED_FROM_BASE_SERVICE`. New posting authorized: **No**.

### SH-LEGAL-ACCT-URANIUM-CUSTODY-01

[9. Activation schedule and current disposition](../../../../docs/legal/gap-instruments/source/uranium-custody.md#9-activation-schedule-and-current-disposition) → [industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md](../../../../industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md)

`NO_ENTRY` · `NO-POSTING-URANIUM-CUSTODY`

OPEN_GATED and excluded from base service; no shipment, service revenue or custody liability implied.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md",
  "posting": null
}
```

## LEGAL-GAP-BILLING

Preserved disposition: `PENDING_PR138_NO_ADOPTION`. New posting authorized: **No**.

### SH-LEGAL-ACCT-BILLING-01

[6. Separate retrospective reconciliation attachment](../../../../docs/legal/gap-instruments/source/billing.md#6-separate-retrospective-reconciliation-attachment) → [docs/finance/evidence/SH-FIN-HUMAN-001/source.json](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json)

`SOURCE_LEDGER` · `FF-2027-BASE`

Twelve released conditional-forecast journal legs for INV-base-FF-003-TERM-0; six balanced events. These are synthetic forecast postings, not actual customer payments. Credits and recovery do not reinstate AR.

Exact native selector: `{"pointer": "/rows/journal"}`.

| account | account_type | available_at | cash_flow | credit_usd | debit_usd | description | entity | fact_state | journal_id | month | month_index | period | scenario | segment | signed_usd | source_id | source_type | unit | year |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BIZ_AR | asset | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 0.0000 | 1740000.0000 | Annual subscription billing | SHI | CONDITIONAL_FORECAST | BIZ-base-0000014 | 1 | 1 | 2027-01-31 | base | FOUNDRY_FIELD | 1740000.0000 | base-01-INVOICE-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_DEFERRED | liability | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 1740000.0000 | 0.0000 | Annual subscription billing | SHI | CONDITIONAL_FORECAST | BIZ-base-0000014 | 1 | 1 | 2027-01-31 | base | FOUNDRY_FIELD | -1740000.0000 | base-01-INVOICE-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| 1000 | asset | 2026-09-09T00:00:00Z | OPERATING | 0.0000 | 435000.0000 | Modeled customer receipt | SHI | CONDITIONAL_FORECAST | BIZ-base-0000138 | 2 | 2 | 2027-02-28 | base | FOUNDRY_FIELD | 435000.0000 | base-02-COLLECTION-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_AR | asset | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 435000.0000 | 0.0000 | Modeled customer receipt | SHI | CONDITIONAL_FORECAST | BIZ-base-0000138 | 2 | 2 | 2027-02-28 | base | FOUNDRY_FIELD | -435000.0000 | base-02-COLLECTION-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_CREDIT_LOSS | expense | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 0.0000 | 1305000.0000 | Explicit synthetic default writes off remaining claim; allowance releases at close | SHI | CONDITIONAL_FORECAST | BIZ-base-0000904 | 6 | 6 | 2027-06-30 | base | FOUNDRY_FIELD | 1305000.0000 | base-06-CREDIT_WRITEOFF-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_AR | asset | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 1305000.0000 | 0.0000 | Explicit synthetic default writes off remaining claim; allowance releases at close | SHI | CONDITIONAL_FORECAST | BIZ-base-0000904 | 6 | 6 | 2027-06-30 | base | FOUNDRY_FIELD | -1305000.0000 | base-06-CREDIT_WRITEOFF-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_REVENUE | revenue | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 0.0000 | 14500.0000 | Credit reduces open claim, then written-off claim, then cash-backed refund | SHI | CONDITIONAL_FORECAST | BIZ-base-0001186 | 7 | 7 | 2027-07-31 | base | FOUNDRY_FIELD | 14500.0000 | base-07-CREDIT_NOTE-SYN-INC-FF-003-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_CREDIT_LOSS | expense | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 14500.0000 | 0.0000 | Credit reduces open claim, then written-off claim, then cash-backed refund | SHI | CONDITIONAL_FORECAST | BIZ-base-0001186 | 7 | 7 | 2027-07-31 | base | FOUNDRY_FIELD | -14500.0000 | base-07-CREDIT_NOTE-SYN-INC-FF-003-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_DEFERRED | liability | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 0.0000 | 145000.0000 | Credit reduces open claim, then written-off claim, then cash-backed refund | SHI | CONDITIONAL_FORECAST | BIZ-base-0001401 | 8 | 8 | 2027-08-31 | base | FOUNDRY_FIELD | 145000.0000 | base-08-CREDIT_NOTE-SYN-AMEND-003-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_CREDIT_LOSS | expense | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 145000.0000 | 0.0000 | Credit reduces open claim, then written-off claim, then cash-backed refund | SHI | CONDITIONAL_FORECAST | BIZ-base-0001401 | 8 | 8 | 2027-08-31 | base | FOUNDRY_FIELD | -145000.0000 | base-08-CREDIT_NOTE-SYN-AMEND-003-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| 1000 | asset | 2026-09-09T00:00:00Z | OPERATING | 0.0000 | 174000.0000 | Modeled post-writeoff recovery | SHI | CONDITIONAL_FORECAST | BIZ-base-0001754 | 10 | 10 | 2027-10-31 | base | FOUNDRY_FIELD | 174000.0000 | base-10-CREDIT_RECOVERY-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |
| BIZ_CREDIT_LOSS | expense | 2026-09-09T00:00:00Z | NONCASH_OR_OPENING | 174000.0000 | 0.0000 | Modeled post-writeoff recovery | SHI | CONDITIONAL_FORECAST | BIZ-base-0001754 | 10 | 10 | 2027-10-31 | base | FOUNDRY_FIELD | -174000.0000 | base-10-CREDIT_RECOVERY-INV-base-FF-003-TERM-0 | BUSINESS_DRIVEN_FORECAST | foundry-field | 2027 |

### SH-LEGAL-ACCT-BILLING-02

[3. Proposed billing statement](../../../../docs/legal/gap-instruments/source/billing.md#3-proposed-billing-statement) → [docs/finance/evidence/SH-FIN-HUMAN-001/source.json](../../../../docs/finance/evidence/SH-FIN-HUMAN-001/source.json)

`MODELED_SCHEDULE` · `FF-2027-BASE`

Invoice face 1,740,000; cash collected 609,000 includes 174,000 recovery. Written-off claim remaining after credits and recovery is 971,500, not a recognized receivable. No fictional billing detail is adopted.

Exact native selector: `{"pointer": "/rows/invoices"}`.

| amount_usd | collected_usd | collection_month | credit_profile | credit_state | credit_usd | customer_id | due_date | due_month | host_settled_usd | host_share | invoice_id | issue_month | recovered_usd | refunded_usd | remaining_usd | scenario | source_id | unit | writtenoff_credit_usd | writtenoff_usd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1740000.0000 | 609000.0000 | 2 | DEFAULT-003 | DEFAULT | 159500.0000 | SYN-CUSTOMER-003 | 2027-02-28 | 2 | 0.0000 | 0 | INV-base-FF-003-TERM-0 | 1 | 174000.0000 | 0.0000 | 0.0000 | base | FF-003-TERM-0 | foundry-field | 159500.0000 | 1305000.0000 |

## LEGAL-GAP-TAX-BILLING

Preserved disposition: `NOT_ESTABLISHED`. New posting authorized: **No**.

### SH-LEGAL-ACCT-TAX-BILLING-01

[5. Calculation schedule with no assumed rate](../../../../docs/legal/gap-instruments/source/tax-billing.md#5-calculation-schedule-with-no-assumed-rate) → [industrial/source/entities.json](../../../../industrial/source/entities.json)

`NO_ENTRY` · `NO-POSTING-TAX-BILLING`

Tax base, jurisdiction, treatment and rate are unresolved. No zero/exempt default, tax amount or tax entry. Existing invoice remains unchanged.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "industrial/source/entities.json",
  "posting": null
}
```

## LEGAL-GAP-MARK-CLEARANCE

Preserved disposition: `EXTERNAL_EXECUTION_OPEN`. New posting authorized: **No**.

### SH-LEGAL-ACCT-MARK-CLEARANCE-01

[8. Present disposition](../../../../docs/legal/gap-instruments/source/mark-clearance.md#8-present-disposition) → [docs/legal/ADVISORY_NAME_AND_EXTERNAL_CLEARANCE_STATUS_2026-09-09.md](../../../../docs/legal/ADVISORY_NAME_AND_EXTERNAL_CLEARANCE_STATUS_2026-09-09.md)

`NO_ENTRY` · `NO-POSTING-MARK-CLEARANCE`

External counsel execution and fee are not established; no invented legal-fee accrual or registration asset.

Exact native selector: `{"whole_document": true}`.

```json
{
  "evidence_path": "docs/legal/ADVISORY_NAME_AND_EXTERNAL_CLEARANCE_STATUS_2026-09-09.md",
  "posting": null
}
```
