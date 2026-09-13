# Legal review bundle releases

Review bundles supplement the independently saved instruments. They do not
supersede source files or establish owner acceptance. Published package bytes
receive a new version for any correction.

## 0.3.0-review.1 — practical-work addendum, downloadable draft

[Download the draft release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/untagged-29cc41b454eeb35cd3e5).
Repository draft-release access and GitHub sign-in are required. Extract the complete
ZIP and open `START_HERE.html`. [The practical-work guide](PRACTICAL_WORK.md) also
opens directly in GitHub. This edition remains held in PR #158 for exact-file review.

- Source: `1d86f78944c95d3fdde72c4dcc31cd9b50c2ada9`; accepted main integrated: `9cc0d2a5c31700dcd166ef9acf1dd284bddb6e8d`.
- Tag: `sable-harbor-legal-review-v0.3.0-review.1`.
- ZIP: `sable-harbor-legal-review-v0.3.0-review.1.zip`, 5,088,414 bytes.
- ZIP SHA-256: `ccc62baa261c4502a3ff389f269cdac6e3b48fb5e1f5d904fa2549baffbbeee7`.
- Companion assets: `legal-review-manifest.json` and `SHA256SUMS.txt`.
- 303 manifested files. Two clean builds produced identical ZIP bytes; downloaded
  assets matched the checksum inventory and the extracted package passed every
  file/hash/local-HTML-link check.

Adds three transaction-to-reporting walkthroughs, five reconciliation workpapers,
11 scoped further-evidence requests across those packages, and a completed-workbook
importer that produces proposals without modifying source or approval records.
The three new workbooks contain 23 sheets, rendered across 43 manually inspected
pages. Five new HTML guides and the revised start page passed full manual review;
prior layouts remain pixel-identical. Desktop/mobile route tests and exact PDF/
worksheet checks are retained in [reader QA](../../reader/usability/REVIEW_2026-09-13.md).

The 1,395 walkthrough comparisons check internal monetary consistency; 1,239 of
those are balanced-journal checks. They are not independent assurance procedures.
Twelve accepted invoice legs are checked separately for exact row membership.
The five workpapers add nine arithmetic checks. Bank-issued records, performance
acceptances, tax filings and valuation evidence are still separate requirements.

```sh
python tools/legal_gaps/package_v3.py --output /tmp/sable-harbor-legal-review-v0.3.0-review.1
python tools/legal_gaps/package.py --verify /tmp/sable-harbor-legal-review-v0.3.0-review.1
```

Run from the recorded clean source revision. The extension reuses the preserved
packager, manifest and HTML styles. It does not overwrite the prior release,
original 17 instruments, prior review workbook or prior QA receipt. The older
version below remains retrievable and unchanged.

## 0.2.0-review.1 — downloadable draft

The current implementation builds all 17 instruments, the consolidated decision
sheet, contract-to-accounting links and four public practice packets into one
portable review bundle. Open `START_HERE.html` after extraction.

[Download the draft release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/untagged-f401537a3e72d61c316d).
GitHub authentication with repository draft-release access is required. This is
held for exact-file review in [PR #158](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/158), not merged or accepted canon.

- Tag: `sable-harbor-legal-review-v0.2.0-review.1`.
- Source: `c39974070ccdae1205e71fa1b0f86eb7b3b6d000`; integrated main: `19e92a08438dbc3e03dc18862750bf38577a602a`.
- ZIP: `sable-harbor-legal-review-v0.2.0-review.1.zip` (4103564 bytes).
- ZIP SHA-256: `859e3168ac2f0906c4933ffea183b5366c410174d58dee4237bad833b6baed64`.
- Companion assets: `legal-review-manifest.json` and `SHA256SUMS.txt`.
- 247 manifested files; every local HTML file and anchor link validates.
- Two clean builds produced identical ZIP bytes. All three release assets were
  downloaded again and checked; the retrieved ZIP was extracted and validated.

Review evidence is retained under `review-support/qa/`, `accounting/qa/` and
`practice/qa/`. All 10 new workbooks (71 sheets, 182 printed pages) and 14 new HTML
surfaces were manually inspected. The 17 original reading companions are
pixel-identical to their reviewed HTML editions. Original instrument bytes are
unchanged from `076485ccd954d3292fb5ad1940129027b6590284`.

Reproduce from the recorded source commit:

```sh
python tools/legal_gaps/package.py --output /tmp/sable-harbor-legal-review-v0.2.0-review.1
python tools/legal_gaps/package.py --verify /tmp/sable-harbor-legal-review-v0.2.0-review.1
```

A new output directory is required. `--allow-dirty` creates an explicitly labeled
local preview; it is not a release build. Manifest checks reject changed, missing
or additional files and broken local HTML links. Original instrument bytes are
copied without modification. Additional repository references require internet.

[Review workflow](REVIEW_WORKFLOW.md) · [Individual instruments](PACKAGE_INDEX.md)
