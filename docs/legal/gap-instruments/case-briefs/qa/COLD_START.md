# Independent agent cold-start review — ARU January 2027

Review date: 2026-09-12. Reviewer: a separate agent acting as a cold-start reader, **not a human reviewer**. This is a navigation and numerical completion exercise, not a native spreadsheet UI or print-layout inspection, an audit opinion, or approval of this draft design.

## Starting point and method

After reading `MAINTAINERS.md`, the reviewer started only at [case-briefs README](../README.md), followed [SH-CASE-CLOSE-01](../SH-CASE-CLOSE-01.md), the linked [period-close instructions](../../period-close/README.md), `blank.xlsx`, `inputs.json`, its eight source CSVs, and the linked evidence-tracking instructions/workbook. Neither generator implementation nor `WORKED.md` / `worked.xlsx` was read until independent results had been saved. Published input comparisons necessarily remain visible in the blank workbook; this is not a blind assessment.

The reviewer used Python/openpyxl to complete a real saved copy of the blank workbook with independently computed numerical responses. The method uses the source rows, not the worked formulas. It verifies all eight selected-file hashes and row counts against the published input register; it does not independently download or authenticate the immutable release archive. The period-close designer confirmed workbook/source content remained stable during this review.

Initial temporary outputs are listed below. The final numerical results and corrected proposal were subsequently retained as public QA evidence; see the durable evidence section. Scratch paths themselves are not release delivery:

- `/tmp/aru-cold-start-v4/completed.xlsx`: completed opening/activity rollforward, five reconciliation areas, adjustments, closing TB, income statement, balance sheet and cash-flow summary.
- `/tmp/aru-cold-start-v4/independent-results.json`: results and five evidence-limited conclusions, saved before opening the worked example; contains the eight source hashes and tested blank-workbook hash.
- `/tmp/aru-cold-start-v4/worked-comparison.json`: subsequent comparison of 270 worked formula cached values with the independent responses; no mismatches.
- `/tmp/aru-cold-start-v4/evidence-update.xlsx` and `evidence-proposal/PROPOSAL.md`: actual initial bank evidence update and successful importer output, including JSON, workbook, SQLite and receipt.
- `/tmp/aru-cold-start.py`: independent calculation script, outside the repository.

## Independently reproduced close

All eight source populations were discoverable through published instructions: 22 opening rows, 274 January journal rows, 34 trial-balance rows, one monthly-statement row, eight PPE rows, one debt row, one bank-reconciliation row and 33 bank events. Month 0 was counted once as opening, excluded from activity. All 137 January journals individually balance. The 34-account closing TB sums to zero and every account matches the released comparison without an adjustment.

| Result | USD |
|---|---:|
| Opening cash | 4,198,440 |
| Closing cash | 3,494,528 |
| External receivables net of allowance | 4,668,132 |
| Trade payables, credit-negative TB | -1,607,584 |
| Legacy term principal | 21,000,000 |
| Replacement term principal | 0 |
| Lease principal | 1,966,552 |
| PPE gross | 61,833,250 |
| PPE accumulated depreciation, positive schedule amount | 2,969,579 |
| PPE net | 58,863,671 |
| Assets | 86,966,303 |
| Liabilities | 27,952,890 |
| Equity including current income | 59,013,413 |
| January net income | -82,694 |
| Operating cash flow | -3,995 |
| Investing cash flow | -283,250 |
| Financing cash flow | -416,667 |

All 18 cells `Five reconciliations!D5:D22`, all 34 `Closing TB!H5:H38` cells and all nine `Statements!D5:D13` cells are zero. `Debt!F5:F7`, `PPE!F5:F12`, complete financial-statement account rows, and `Adjustments!B5:C5` were also completed. After recording these results, the reviewer opened the public worked narrative and workbook: all 270 formula-response cells agree with the independently saved values. No numerical correction was identified.

## Scope and five conclusions

The instructions adequately explain January 2027 as a conditional base forecast for the ARU_GROUP native industrial reporting scope, not an actual close or separate statutory books. They clearly exclude Core and enterprise replacement or allocated books. Account 1700 is a contra-liability despite its debit balance; source classifications made the statement presentation reproducible. PPE accounts 1400/1490 remain separate from finance-lease ROU accounts 1500/1590.

- **Bank:** adjusted modeled cash ties at $3,494,528, with modeled deposits $4,639,240 and outstanding payments $5,343,152. The 33 modeled events total -$703,912; their supplied clearing dates are February 2. This does not establish independent cash existence or actual settlement. Obtain the January bank-issued statement and subsequent clearing evidence.
- **Receivables:** opening $6,120,000 plus complete net activity -$1,451,868 gives $4,668,132. This is a net ledger rollforward. Independent January ARU gross aging, allowance support, invoices and receipts remain missing.
- **Payables:** opening -$3,090,000 plus complete signed activity $1,482,416 gives -$1,607,584. A dated ARU supplier open-item schedule, invoices and subsequent payments are still needed; model agreement does not establish completeness.
- **Debt:** legacy term, replacement term and lease principal independently roll forward to $21,000,000, $0 and $1,966,552. Executed terms and lender/lessor confirmations remain missing; no covenant or contractual compliance conclusion follows.
- **PPE:** all eight PPE rows reproduce gross, accumulated depreciation and net movement. Independent physical existence, title, useful lives and commissioning support remain missing.

No evidence supports a new journal. The missing evidence cannot justify a balancing plug.

## Evidence workflow finding and initial execution

The initial [evidence tracker](../../evidence-tracking/README.md) had 11 fixed requests. `Requests!A8:D8` and `A11:D11` correctly covered ARU January bank and debt. However, `Requests!A9:D10` covered Atlas Meridian Core AR/AP and `Requests!A12:D12` covered Willow / FORT-TEST-RIG PPE. The corresponding `Updates!A9:A10` and `A12` IDs therefore could not truthfully capture this ARU close's AR/AP/PPE deficiencies. This was a substantive gap in the brief's instruction to use that tracker after the close. It was reported to the coordinating agent before completion.

Proposed correction: retain the 11 original IDs and their exact scopes, add distinct source-backed ARU January receivables, payables and PPE request IDs, and publish their relationship to the period-close case. Do not repurpose the Core/Willow IDs or claim the requests were already fulfilled.

Using the original matching bank request, the reviewer entered `incomplete`, a unique event ID, observed date, substantive limitation, an existing source CSV path, full SHA-256 and exact row excerpt. Running the published importer command succeeded with one retained event. The generated proposal cites `period-close/source/industrial_bank_reconciliations.csv`, SHA-256 `397114b6de513e8f259132f8d36f335712aebc042de515962505a6f848f91df5`, line 2. The cited original was inspected. The proposal correctly preserves synthetic/model limitations and applies nothing to the repository.

The initial close calculation and bank update are reproducible from the published packet. Full five-area tracker follow-through requires the scope correction described above. Corrected-packet retest is recorded below when performed.

## Corrected tracker retest

The tracker maintainer added three distinct requests without repurposing the original 11. The reviewer reread the published evidence-tracking README, which now explicitly routes ARU close bank/debt to the existing matching IDs and AR/AP/PPE to `SH-CLOSE-ARU-2027-01-AR-REQ`, `SH-CLOSE-ARU-2027-01-AP-REQ` and `SH-CLOSE-ARU-2027-01-PPE-REQ`.

A fresh copy of the corrected 14-request workbook was completed for **all five areas**, using real existing CSV records, exact excerpts, SHA-256 values and explicit remaining deficiencies. All five proposed statuses were `incomplete`; no external confirmation receipt was claimed. The published command succeeded:

```text
python tools/legal_gaps/evidence_tracking.py import \
  --workbook /tmp/aru-cold-start-v4/evidence-update-corrected.xlsx \
  --output /tmp/aru-cold-start-v4/evidence-proposal-corrected
PASS: 5 retained events; proposal only at /tmp/aru-cold-start-v4/evidence-proposal-corrected
```

The reviewer read the resulting `PROPOSAL.md` and the source records. The bank citation is bank-reconciliation CSV line 2; debt is debt CSV line 2; receivables is journal CSV line 2; payables is journal CSV line 61; PPE is assets CSV line 2. The proposal preserves the correct request scopes and records the missing independent originals. Output includes the updated workbook, JSON register, SQLite mirror and import receipt. This retest starts from the corrected published initial state; it is not a continuation of the original 11-request scratch proposal.

**Outcome:** the initial tracker scope gap is corrected and successfully retested through an actual five-event proposal. From the current published entry point a reader with spreadsheet/accounting competence can find the inputs, complete the five model reconciliations and complete TB/statements, explain the forecast/evidence limitations, and record follow-through under the correct scopes. No remaining numerical or navigation blocker was found in this exercise. Human usability, native spreadsheet interaction and visual/print quality remain outside this independent agent review; the local scratch paths are not a retained release; the selected QA evidence below is now repository-retained.


## Durable public QA evidence

At the coordinating maintainer’s request, the completed source-derived workbook, independent results, worked comparison, corrected evidence-input workbook and proposal artifacts are retained under [cold-start/](cold-start/). They are public learning/QA examples, not hidden assessment material or asserted evidence receipts. No accepted tracker state was changed.

- [Completed close workbook](cold-start/completed.xlsx) and [independent results](cold-start/independent-results.json).
- [Worked comparison](cold-start/worked-comparison.json): 270 formula-response values compared, zero mismatches.
- [Corrected five-area update input](cold-start/evidence-update-corrected.xlsx) and [generated proposal](cold-start/evidence-proposal/PROPOSAL.md).
- [Import receipt](cold-start/evidence-proposal/import-receipt.json), [actual captured stdout](cold-start/import.stdout.txt) and [stderr](cold-start/import.stderr.txt). A fresh rerun of the same published command returned exit code 0 and five retained events before these outputs were copied into the repository.
- [SHA-256 manifest](cold-start/manifest.json) pins all eleven retained output files and records the actual command/exit code.

The retained proposal’s source links are generated absolute paths from this shared workspace; its textual repository-relative evidence paths, hashes and line ranges remain the portable references. The supplied bytes and results are preserved; the proposal was not rewritten for publication.

FINAL RESULT: PASS
