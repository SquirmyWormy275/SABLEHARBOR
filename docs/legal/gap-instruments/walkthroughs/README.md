# Follow a transaction into the books

These three public walkthroughs test the evidence already in the repository. They create no transactions and do not turn draft agreements, forecasts or internal reconstructions into independent evidence. **The new workbook is a draft for exact-file review.**

Open [the workbook](walkthroughs.xlsx) for nine working views, or [the SQLite database](walkthroughs.sqlite3) for complete selected rows. [The source register](source-register.json) records exact input hashes, filters and row counts. All native columns remain in the [source directory](source/). Amounts are USD; debit-positive signs are preserved in native journals.

## 1. ARU: closing to the full-year model

1. Read the [closing statement](../../../../industrial/transaction/05_ARU_CLOSING_AND_TAX_DELIVERY.md), especially ARU-CL-02/03 and the funding table. The buyer pays $48,000,000 for stock and refinances $13,500,000 of old debt. $22,500,000 new debt plus $39,000,000 parent equity funds those $61,500,000 uses before fees. Retained leases are not paid off a second time.
2. Open **ARU opening**. Match all 16 accounts to `PPA-2026-01-07` in [the complete 2026 journal](source/aru_2026_journal.csv). Every opening account agrees. Refinancing and the $300,000 debt issuance cost (account 1700) are included in the pushdown opening; do not post them again. The separate $900,000 transaction-services expense belongs to the buyer and is outside this ARU opening. Total parent cash including both fee categories is $40,200,000.
3. Open **Monthly trace**. Month zero is the opening, followed by months 1–12. The 1,926 journal legs preserve individual journal IDs, source IDs, descriptions and effective dates. Filter one month, then one journal ID; both sides must remain visible.
4. Open **ARU closing**. Sum the entire journal by account and compare all 44 closing accounts with [the native trial balance](source/aru_2026_trial_balance.csv). This comparison includes opening balances and all subsequent activity.
5. Read [financial statements](source/financial_statements.csv), filtered to `entity=ARU_GROUP`. Numeric account IDs map to closing balances; liabilities, equity and revenue reverse debit-positive signs for presentation. Cash account 1000 ends at $4,198,440. Statement summary lines without numeric account IDs remain native reported summaries; the automated comparison does not pretend those lines are individual accounts.

The arithmetic chain is complete **within the current industrial reconstruction**. Its September 5, 2026 cutoff means post-cutoff months are a management scenario, not actual year-end results. The separate base-2027 operating release is not added to these books. Bank confirmations, lien releases, independent valuation support and filed tax-election evidence remain distinct requests below.

## 2. Foundry Field: invoice to monthly revenue

1. Read the [accepted Foundry Field invoice packet](../../../finance/evidence/SH-FIN-HUMAN-001/README.md). Select invoice `INV-base-FF-003-TERM-0`, base scenario, 2027: face $1,740,000; total collection $609,000, including $174,000 recovery; credits $159,500. Written-off claim remaining after credits and recovery is $971,500, not a recognized receivable.
2. Open **FF invoice events**. The 12 accepted journal legs match the complete close extract exactly, including every original column. Billing credits deferred revenue; billing alone does not establish revenue recognition.
3. Open **FF service trace**. This extends the original packet to 82 journal legs whose native source ID contains `FF-003`: billing, service recognition and related credit events. Retain their actual descriptions and IDs. This is a literal native-ID selection, not a claim that every customer transaction shares one invoice ID.
4. Open **FF statements**. Sum `BIZ_REVENUE` from the complete 2,847-leg Foundry Field journal for each month, reverse its credit sign, and compare the monthly statement's revenue. All 12 months agree exactly. **The FF-003 subset must not be compared to total unit revenue as if other customers did not exist.** Full-unit evidence is saved in [ff_journal.csv](source/ff_journal.csv); the selected contract subset is [ff_contract_trace.csv](source/ff_contract_trace.csv).
5. Read statement liabilities, equity and assets together. Each monthly balance sheet equation agrees. The unit view retains its released signed reporting-clearing treatment; it is not a standalone bank account or separate legal-entity balance sheet.

This trace demonstrates internal consistency of public synthetic forecasts. It does not establish that a customer was billed, services were accepted, or cash arrived. Proposed billing identities and tax terms are not adopted here.

## 3. Red Wash: closure obligation to the successor books

1. Read the transaction in [core operating data](../../../../red_wash/source/core_operating_data.json): the July 18, 2025 acquisition assumes $16,000,000 ARO. The $3,000,000 escrow and $500,000 holdback are components of consideration, not extra purchase price or proven present balances.
2. Open **RW closure liability**. The 2026 successor opening has a $16,467,716 credit to account 2200 under `RW-OPENING-SCENARIO`. The native `closure_schedule` computes the $467,716 bridge as acquisition-to-January-1 accretion using the source discount rate and actual days/365. This is a supported modeled bridge between dates, not independent engineering evidence or a proposed adjustment.
3. Follow every account-2200 movement through the [complete successor journal](source/red_wash_2026_journal.csv). The closing liability is $17,281,868. The full 575-leg journal reconciles to all 20 closing accounts and the numeric-account statement lines.
4. Read the [mine and funding explanation](../../../../industrial/finance/RED_WASH_AND_FUNDING.md). The closure cash-flow calibration uses the liability as an input. It is not an independently engineered estimate corroborating that same liability.

The acquisition record, successor opening and management forecast must remain separately identifiable. Do not infer a signed escrow release, regulator-approved closure estimate or actual future expenditure from this chain.

## Evidence to request before stronger conclusions

| ID | Obtain | What remains unsupported |
|---|---|---|
| WALK-REQ-ARU-01 | Funding, payoff and creditor-release confirmations | Actual cash transfers and discharged liens |
| WALK-REQ-ARU-02 | Filed election evidence and final valuation support | Tax filing/acceptance and independently verified fair values |
| WALK-REQ-ARU-03 | Post-cutoff actual journals and source vouchers | Actual full-year 2026 results |
| WALK-REQ-FF-01 | Executed customer terms, service acceptance, billing identity and bank evidence | Actual billing, earned revenue and receipt of cash |
| WALK-REQ-RW-01 | Independent engineering estimate and approved closure timing | Independently measured closure obligation |
| WALK-REQ-RW-02 | Escrow confirmation and supported successor opening rollforward | Current escrow custody and historically corroborated opening balances |

[The request register](source/evidence_requests.csv) preserves the purpose, exact source scope and blocked conclusion for every request. These are evidence limitations, not legal opinions or new assignments to invented employees.

## Reproduce and inspect

```bash
python tools/legal_gaps/walkthroughs.py
python tools/legal_gaps/walkthroughs.py --check
python -m pytest -q tests/publications/test_legal_walkthroughs.py
```

The builder regenerates the native industrial package in a temporary directory, selects its 2026 populations, and reads the committed base-2027 close extract separately. [All 1,395 monetary comparisons](source/checks.csv) retain both compared amounts, difference, tolerance and result. The current build has zero differences: 1,239 balanced-journal comparisons, 16 opening accounts, 64 journal-to-trial-balance accounts, 51 numeric statement lines, one funding bridge and 24 Foundry Field monthly comparisons. These are internal consistency checks of derivatives, including outputs of the same native generator; they are not 1,395 independent controls or corroborating sources. Exact membership of all 12 accepted invoice legs in the full 2,847-leg unit population is recorded separately in the source register. The workbook is a readable selection; complete journal evidence lives in CSV and SQLite. Validation compares every generated CSV, JSON and workbook byte and all SQLite contents. It fails on missing or stale outputs and failed reconciliations.
