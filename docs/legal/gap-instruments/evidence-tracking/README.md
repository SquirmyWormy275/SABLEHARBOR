# Evidence request follow-through

Track **14 requests**: the 11 existing requests from the [case walkthroughs](../walkthroughs/README.md) and [five reconciliations](../reconciliations/README.md). Three additional requests cover ARU Group’s January 2027 base-scenario close. All 14 start **unresolved**, with no asserted receipt. Each request retains its exact source scope and the conclusion that its evidence does not yet support. This is a draft tool for exact-file review.

Open [tracker.xlsx](tracker.xlsx). **Requests** explains what is needed; **Updates** provides filterable IDs and yellow input cells; **History** records earlier events; **Context** pins the source records. The [structured register](tracker.json) and [SQLite mirror](tracker.sqlite3) carry the same information.

## Record a proposed update

1. Save a copy of the workbook outside the repository.
2. In Updates, select a new status for a request. Add a unique event ID, observed date in `YYYY-MM-DD` form and a substantive review note.
3. For incomplete, received or disputed, supply an existing public repository text file path, its full SHA-256 and an exact excerpt of at least 12 characters. The import verifies the bytes and records the matched line range. Identify why the record is relevant and what remains missing in the note.
4. Run from the repository root:

   ```bash
   python tools/legal_gaps/evidence_tracking.py import --workbook /tmp/completed.xlsx --output /tmp/new-evidence-review
   ```

5. Read the generated `PROPOSAL.md`, then inspect the cited original file. Nothing is applied to the repository. The output includes an updated workbook, JSON register, SQLite mirror and import receipt.

For a subsequent event, complete a copy of the output `tracker.xlsx` and supply its parent state:

```bash
python tools/legal_gaps/evidence_tracking.py import --workbook /tmp/next.xlsx --state /tmp/new-evidence-review/tracker.json --output /tmp/next-review
```

Earlier events remain in order with their original content and a SHA-256 chain. The import rejects duplicate event IDs, altered workbook context, formulas, unknown IDs, unchanged/unknown status transitions, stale or missing evidence, unsafe paths and nonexistent citations. A changed accepted source requires rebuilding and reviewing the context before importing an old workbook. A hash chain detects changes relative to the provided parent; it does not authenticate a reviewer or prevent someone constructing a new independent history. Retain the external parent folders and receipts for comparison.

## What each status means

| Status | Meaning | What it does not establish |
|---|---|---|
| unresolved | No usable support has been supplied, or a prior status has been withdrawn with a reason. | Repository-wide absence of evidence. |
| incomplete | A supplied record supports part of the request; the note identifies the remaining deficiency. | Completeness or sufficient audit evidence. |
| received | The cited record has been supplied for review. | Reliability, execution, acceptance, closure or permission to post an entry. |
| disputed | The supplied record or its sufficiency is under a documented objection. | An adjudicated dispute or legal conclusion. |

Any change between these four states requires a new event and a note. There is no closed status and no apply command. The original request and blocked conclusion remain visible even after a record is received. One workbook import permits one event per request; use a new copy of the updated workbook to continue.

## Supported evidence and limitations

The importer accepts existing public UTF-8 `.md`, `.txt`, `.csv` and `.json` files under the repository's document, business, industrial, enterprise and Red Wash trees. It rejects private/internal paths and symlinks. Binary originals need a reviewed text transcript before this tool can verify a citation; the transcript should identify the original and its hash. Do not substitute an invented transcript or synthetic model for missing third-party originals.

For example, attaching the existing ARU closing delivery memo to `WALK-REQ-ARU-01` could support an **incomplete** review proposal. It would not supply the missing external funding and payoff confirmations. The populated automated exercise uses that real memo, preserves its exact citation and hash, then records an objection without claiming a confirmation was received. This exercise does not change the published tracker.

Build: `python tools/legal_gaps/evidence_tracking.py build`. Validate: `python tools/legal_gaps/evidence_tracking.py validate`. Tests: `pytest tests/publications/test_legal_evidence_tracking.py`. Workbook/JSON regeneration is byte checked; SQLite schema and complete rows are checked across engines.

## ARU January close requests

The [period close](../period-close/README.md) uses `SH-RECON-BANK-REQ` and `SH-RECON-DEBT-REQ` for the matching ARU_GROUP January 2027 bank and debt scope. Use these added IDs for its remaining three areas:

| Request ID | Scope and requested originals |
|---|---|
| SH-CLOSE-ARU-2027-01-AR-REQ | Account 1100: gross external aging, allowance calculation and subsequent receipts. |
| SH-CLOSE-ARU-2027-01-AP-REQ | Account 2000: dated supplier open items, invoices and subsequent disbursements. |
| SH-CLOSE-ARU-2027-01-PPE-REQ | Accounts 1400/1490: invoices, title, commissioning, inspection and useful lives; finance-lease ROU remains separate. |

These three requests are tied to the exact limitations in [case.json](../period-close/case.json) and the close README. They do not repurpose the original Atlas Meridian receivables/payables requests or Willow fixed-asset request. Original IDs, scope and content remain unchanged.
