# Selected-edition portal review rehearsal

This optional closeout adapter uses the portal's exact committed APIs without
changing portal code or opening its active databases. It collects selected
edition originals, links retained artifacts to two preparer workpaper versions,
rejects self-review without a revision change, records a distinct review actor
bound to the current version digest, and retains an EVIDENCE export. Exported
original bytes must match every selected transport-part hash.

Run the existing rehearsal with `--review-engagement`; repeat `--review-member`
with exact paths from the edition CONTRACT to select material source originals:

```sh
python -m tools.company_closeout.portal_rehearsal \
  --edition /path/to/frozen-edition \
  --portal /path/to/existing-portal-git-checkout \
  --revision 8f9b8eabed3af1d2c050afc9bfe8935fd41f48ae \
  --output /path/to/new-isolated-rehearsal \
  --review-engagement --review-member exact/edition/member.csv
```

The adapter uses `git archive` at that commit to extract a public source snapshot
under the new rehearsal directory. A subprocess imports only that pinned portal
snapshot, using the caller's Python dependency environment. It never imports the
active worktree's dirty files. Install the portal's locked supported dependencies
when needed (`uv sync --extra dev --extra audit-suite --frozen` in an isolated
checkout), and invoke this adapter with that environment's Python.

If explicit member paths are absent, the default is one smallest nonempty
original per component (lexical path breaks ties; an all-empty component uses
its explicit empty transport). This default is an API smoke exercise, not a
materiality-based audit selection. Receipts retain the selection rule, every
selected path/hash, stable transport ID, available date, and each component's
complete declared surrounding member population. Selection never asserts that
all surrounding records were reviewed. The simulated review clock is no earlier
than the latest edition component availability; accounting periods are separate.

Outputs include SELECTED_REVIEW_PLAN.json, SELECTED_REVIEW_RECEIPT.json,
SELECTED_REVIEW_EXPORT.zip and SELECTED_REVIEW.log, plus the existing rehearsal
receipt. A source-hash mismatch fails without a successful selected-review
receipt. The pre-existing CompanyStore backup/restore equality checkpoint occurs
before the new engagement collection and therefore does not claim backup coverage
of the subsequently created engagement workpapers/export.

The committed [small-fixture receipt](evidence/portal-selected-fixture-2026-09-22/RECEIPT.json)
records an actual one-row public CSV exercise against the pinned portal and an
adverse changed-hash rejection. It is not a completed company-edition run. The
initial development run omitted required pinned CCF documentation from the code
snapshot and failed at Engine initialization; the implementation now archives
the complete committed tree, and the corrected positive/negative run passed.

All actors and review comments are synthetic software-role exercises, with
LIMITATION conclusions. There is no audit opinion, private reviewer edition,
instructor key, private grading payload or model inference. Hold/disposal restore
and comprehensive indirect-disclosure behavior remain unresolved scope. A full
edition run is required before claiming this selected-edition integration passed.
