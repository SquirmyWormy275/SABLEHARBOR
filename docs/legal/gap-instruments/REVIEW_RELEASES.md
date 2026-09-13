# Legal review bundle releases

Review bundles supplement the independently saved instruments. They do not
supersede source files or establish owner acceptance. Published package bytes
receive a new version for any correction.

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
