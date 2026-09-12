# Accounting, finance and audit practice

This guide is for a person opening the Sable Harbor archive in a browser and a spreadsheet application. No AI assistant, SQL query or text parser is required for the exercises below. Source code and databases remain available for deeper verification.

For a ready-to-read example, open the [accepted Foundry Field evidence memo and workbook](evidence/SH-FIN-HUMAN-001/README.md). It follows one invoice through collection, writeoff, credits and recovery; it is reconstructed evidence, not an original invoice.

All company financial records in these exercises are synthetic. The operating release retains a 2026 calibration and provides conditional 2027–2031 scenarios. It does not contain observed company results, audited statements, actual bank confirmations or executed customer agreements. Read the [operating model's boundaries](../../enterprise/operations/README.md) before interpreting results. Use one release, scenario, reporting unit and period consistently; do not combine successive versions as additional transactions.

## Get the evidence

1. Open the [business operations v1.0.0 release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/business-operations-v1.0.0), download `sable-harbor-business-operations-v1.0.0.zip`, and extract it into a new folder.
2. Open `operating-review-v1.0.0.xlsx`. Its six sheets are **Results**, **Cash obligations**, **Control reviews**, **Customer ARR**, **Financial source**, and **Forecast review**. Start here before opening transaction extracts.
3. Choose a unit folder under `units/`: `foundry-field`, `atlas-meridian`, `advisory`, `willow`, `project-cradle`, `pale-sun`, or `american-resource-utility`. Read its `README.md`. Shared corporate and Treasury populations are in the parent package.
4. Open the named CSV files below in a spreadsheet application. Import identifiers as text and preserve the supplied amounts and dates. Save your own working papers outside the extracted evidence folder. CSV files have data but lack the reviewed workbook's presentation; individual invoice PDFs and complete document-style transaction packets are not supplied by this release.
5. Put the release tag, scenario, unit, period and record identifiers on each working paper. Record unsupported assertions separately from calculation errors.

The release was verified on September 11, 2026: published at `2026-09-11T04:43:14Z`, source `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`, ZIP size 73,713,427 bytes, SHA-256 `b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817`. The archive contains 566 files, one enterprise SQLite export, seven unit SQLite exports and the six-sheet workbook. These are inspection facts for that release, not a claim that every financial topic is complete. The [release index](../releases/BUSINESS_OPERATIONS_RELEASES.md) records the verified publication identity.

Paths in the exercise tables below are **inside the extracted ZIP**, not missing repository files. The reviewed workbook is also [available directly in the repository](../../enterprise/operations/publications/operating-review-v1.0.0.xlsx). Database users can open `enterprise.sqlite3` or a unit's `evidence.sqlite3`; `export_schema.json`, `export_scope.json` and each unit's `schema.json` describe the corresponding export. These are reporting extracts, not production accounting systems.

## Exercises available now

### 1. Follow a customer invoice through collection and credit loss

**Purpose:** practice invoice reconciliation, credit assessment and journal tracing. Use Foundry Field and one scenario; choose an invoice with multiple rows in its collection history rather than assuming every invoice has the same events.

| Evidence | ZIP path |
|---|---|
| Invoice register | `units/foundry-field/invoices.csv` |
| Dated movements and credits | `units/foundry-field/credit_history.csv`, `units/foundry-field/credit_notes.csv` |
| Estimates and close | `units/foundry-field/credit_allowance.csv`, `units/foundry-field/subledger_rollforward.csv` |
| Accounting and source events | `units/foundry-field/journal.csv`, `units/foundry-field/events.csv` |

Filter by `scenario` and `invoice_id`. Put dated movements in order, distinguish receipts, credits, write-offs and recoveries, and reconcile the surviving claim. Compare the period's allowance with its supported population and trace the associated source events to journal entries. Document a receipt as a modeled collection event; there is no independent bank statement here.

**Hand in:** an invoice movement working paper, selected journal references, and a short list of additional evidence you would request before relying on the balance. See [credit treatment](../../enterprise/operations/docs/credit.md) for the model's conventions.

### 2. Explain subscription revenue separately from ARR and cash

**Purpose:** practice deferred-revenue reconciliation and avoid treating annual recurring revenue as booked revenue or receipts. Choose Foundry Field or Atlas Meridian, one contract and a defined year.

In that unit's folder, open `contracts.csv`, `contract_versions.csv`, `invoices.csv`, `commercial_arr_bridge.csv`, `commercial_deferred_rollforward.csv` and `monthly_statements.csv`. Read the workbook's **Customer ARR** sheet and the [commercial guide](../../enterprise/operations/docs/commercial.md). Follow contract changes into the appropriate period, reconcile the deferred-revenue movement, and explain why billing, revenue, ARR and cash differ.

**Hand in:** four clearly labeled schedules and a one-page explanation citing the contract/version IDs. Contract registers are synthetic terms; a full executed agreement is not implied.

### 3. Investigate a cash shortfall

**Purpose:** practice a finance postmortem using evidence of requested, funded and unpaid obligations. Use the workbook's **Cash obligations** sheet, then `tables/treasury_obligations.csv`, `tables/treasury_obligation_history.csv`, `tables/treasury_reconciliation.csv` and `enterprise/enterprise_funding.csv`.

Select one scenario and period with outstanding obligations. Reconcile opening arrears, new deferrals and repayments to closing arrears. Trace several requests to their source IDs and cash-flow categories. Explain which conclusions depend on the declared allocation priority. Compare a second scenario only after completing the first reconciliation.

**Hand in:** an arrears bridge, a chronology, and a decision memo distinguishing evidence from assumptions. Monthly attributed funding cannot establish daily cash sufficiency, actual nonpayment to a named employee, creditor consent or a unit's bank balance.

### 4. Reperform a control and assess an exception

**Purpose:** practice population selection, evidence sufficiency, independent review and follow-up. This is an internal-control exercise, not a completed SOC examination.

Start with **Control reviews** and [the control guide](../../enterprise/operations/docs/controls.md). Open `tables/control_occurrences.csv`, `tables/control_population.csv`, `tables/control_evidence.csv`, `tables/control_results.csv`, `tables/control_completeness.csv`, `tables/control_exceptions.csv` and `tables/control_retests.csv`. Select an occurrence; use its IDs and population references to locate the underlying accounting or operational evidence. State the test before consulting its recorded outcome, then compare your result and explain any disagreement. The supplied package is an open-book reference, not an examination with concealed solutions.

**Hand in:** scope, selected population, procedure, inspected evidence, result and missing-evidence request; for an exception, include the original result and subsequent review chronology. An expired waiver or later-period PASS cannot erase an original failure. The release retains FAIL and NOT_RUN results; software validation passing is a separate conclusion.

### 5. Reconstruct a management forecast variance

**Purpose:** practice budget-versus-revision explanation without inventing a residual balancing amount. Open **Forecast review**, `tables/forecast_vintage_register.csv`, `tables/forecast_vintage_metrics.csv` and `tables/forecast_variance_contributions.csv`. Read the [management guide](../../enterprise/operations/docs/management.md).

Choose one unit, metric, scenario and revised period. Reconcile prior to revised amounts using price, volume, timing and workforce contributions. Check an earlier frozen period as a separate control. Explain the attribution order and where interactions fall.

**Hand in:** a variance bridge and a short management memo. “Synthetic outturn” is not observed performance. Requested Core cash is not a consolidated funded-cash reforecast.

### 6. Reconcile business reporting to legal books

**Purpose:** practice consolidation and distinguish reporting lines from legal entities. Use `enterprise/unit_monthly_trial_balances.csv`, `enterprise/legal_monthly_trial_balances.csv`, `enterprise/enterprise_journal.csv`, `enterprise/unit_monthly_statements.csv` and `enterprise/enterprise_monthly_statements.csv`. Consult the [business finance design](BUSINESS_DRIVEN_SUCCESSOR_2026-09-09.md).

Choose one scenario, month and account. Reconcile the unit attribution to legal reporting, inspect corporate/elimination treatment, then expand to a full trial balance. Investigate sign conventions before treating a negative amount as an exception.

**Hand in:** a unit-to-legal reconciliation, a statement cross-check and an explanation of scope. Do not sum parent and subsidiary presentations as independent businesses or treat management allocations as a second legal posting.

### 7. Investigate industrial economics and acquisition assumptions

**Purpose:** practice volume/price support, reported-to-normalized earnings and transaction-accounting review. Start with the [industrial finance guide](../../industrial/finance/README.md), [transaction treatment](../../industrial/finance/TRANSACTION_ACCOUNTING.md), [driver support](../../industrial/finance/DRIVERS_AND_COST_SUPPORT.md), and [industrial release index](../releases/INDUSTRIAL_CASE_RELEASES.md). Select one identified industrial release and use its manifest to locate the finance output schedules listed in the guide.

Reconcile one contract's physical quantities and pricing; explain payroll versus external cost support; inspect the reported-to-normalized EBITDA bridge. For acquisition practice, trace opening balances and identify which tax, consideration and allocation inputs are explicitly assumed. Keep this industrial exercise separate from the operating successor until using its documented replacement/reconciliation bridge.

**Hand in:** a price/volume working paper, normalization schedule and missing diligence-evidence list. Do not present modeled contracts as signed originals, selected budgets as supplier quotations, closure timing as independent engineering, or the legacy capital workbook as a completed valuation opinion.

## Readiness and remaining work

| Reader need | Current readiness | Missing evidence or interface |
|---|---|---|
| Spreadsheet-based reconciliations and finance postmortems | Usable with workbook and CSV imports | More task-specific, formatted evidence workbooks and plain-language record dictionaries |
| Internal-control sampling and exception follow-up | Usable as an open-book synthetic exercise | Document-style evidence packets and complete topic-specific assurance scope |
| Human inspection of invoices, bills of sale, SLAs and supporting approvals | Partial; structured events and some canonical documents exist | Inventoried, source-bound MD plus letterhead PDF or XLSX counterparts for applicable records |
| SOC audit practice | Useful control and governance components | SOC/CCF completion is a separate active workline; consult the [accepted CCF surfaces](../../enterprise/ccf/README.md) and their stated scope. This finance guide does not assert a completed SOC report |
| Daily liquidity, bank confirmation and complete employee payment testing | Unsupported at that level | Current Treasury evidence is monthly and attributed; independent bank/individual payment evidence is absent |
| Complete M&A diligence or valuation | Partial industrial transaction case | The data-room index is a readiness architecture, not a complete room; full supporting instruments and broader valuation work are not asserted |

The source-bound Foundry Field evidence memo and reconciliation workbook were accepted as exact files and merged in [PR #134](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/134). Open the [accepted packet](evidence/SH-FIN-HUMAN-001/README.md). It remains a derivative of one invoice population, not a customer-facing invoice original or a replacement release. The [finance evidence completion handoff](../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md) defines the bounded successor work. Financial platform history and its [known limitations](KNOWN_LIMITATIONS.md) remain separately interpretable; later operating depth does not retroactively complete every earlier profile.
