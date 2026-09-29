# Import a completed decision workbook

Use this tool after filling a **copy** of the [existing decision workbook](../review-support/decisions.xlsx).
It turns explicit replacement instructions into reviewable JSON proposals and diffs.
It never edits the repository, approves a document, closes a gap or updates a PDF.

## Fill the copy

Keep the three sheets, row order, IDs, questions, source details and links unchanged.
Filtering and normal spreadsheet formatting are fine; do not sort or delete rows.
Enter a response in **Review → Reviewer response** or the corresponding response cell
in **Source details**, but not both for the same item. Do not add comments, formulas,
sheets or rows. Save as `.xlsx`.

| Response | What the importer records |
|---|---|
| Blank | Unanswered; no change. |
| `KEEP` | Keep the current wording; no change and no approval. |
| `DISCUSS: Need the lender evidence first.` | Discussion note; no change. |
| Ordinary prose, including “approve” or “reject” | Comment only; no inferred legal change or acceptance. |
| `SET {"term":"Exact proposed replacement wording."}` | An explicit replacement proposal for the current draft term. |
| `SET {"basis":"Exact proposed replacement basis."}` | An explicit replacement proposal for its source-basis description. |
| `SET {"field":"Revised description of the unresolved question."}` | Changes the question text in a proposed copy; does not resolve it. |
| `SET {"next_action":"Request the missing evidence for separate review."}` | Proposes a revised next action; does not establish receipt of evidence. |

`SET` takes one JSON object with exact, nonempty string values. Draft-term rows allow
only `term` and `basis`; unresolved-field rows allow only `field` and `next_action`.
Both allowed fields can appear in one object. Quote and escape text using JSON syntax.
A repeated key, unknown key, null, empty value, malformed control instruction or formula
fails the entire import before any output is written. `SET` is case-sensitive.

These fields describe the review records. They are **not structured legal execution
fields**. For example, writing a party name into a question does not complete an
agreement's party schedule. A proposed resolution requiring a new field, execution
record or accepted canon decision must be developed separately.

## Run and inspect

From the repository, with the legal review Python dependencies installed:

```bash
python tools/legal_gaps/import_decisions.py \
  --workbook /absolute/path/to/completed-decisions.xlsx \
  --output /tmp/sable-decision-import-001
```

The output directory must not exist and must be outside the repository. The command
checks the frozen workbook and decision-register hashes, all 125 IDs and source
contexts, every instrument's JSON and Markdown hash, source pointers and hyperlinks.
Missing, duplicate, unknown or reordered items fail. Source changes require a separately
reviewed importer baseline update; the command cannot silently rebase a filled workbook.

Open `REPORT.md`, then inspect:

- `report.json`: every response, disposition, source hash and exact field-level before/after value.
- `proposed/docs/legal/gap-instruments/source/*.json`: complete proposed copies of affected files only.
- `*.diff`: before/after JSON differences for each affected file, comparing the actual frozen source text with the complete proposed JSON file.
- `review.sqlite3`: queryable response, proposed-change and metadata tables.

No replacement means no proposed source copies. An explicit replacement identical to
the current value remains a recorded instruction but produces no difference.
The report records the input workbook hash. Keep the completed copy with your review
evidence; the importer does not copy potentially private reviewer notes into Git.

## Adoption is a separate action

All output is `PROPOSAL_ONLY_NOT_APPROVED_OR_APPLIED`. Original instrument sources,
financial releases, review workbook, PDFs, HTML and acceptance records remain untouched.
The JSON proposal is not a publication-ready legal instrument. Reconcile each proposed
change with controlling Markdown and canon, assess accounting dependencies, regenerate
successor editions as appropriate, and review the exact resulting files under the
[revision policy](../revision-policy.md). Do not copy proposed JSON into the repository
and claim that existing PDFs or prior approvals cover the changed terms.

This tool verifies content, not the author's identity, legal authority or truth of a
replacement. It does not authenticate an approval receipt or provide a source writeback
option. Its text reports use ordinary Markdown; it introduces no new corporate design.
