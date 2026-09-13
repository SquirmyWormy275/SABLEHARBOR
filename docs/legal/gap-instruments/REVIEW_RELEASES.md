# Legal review bundle releases

Review bundles supplement the independently saved instruments. They do not
supersede source files or establish owner acceptance. Published package bytes
receive a new version for any correction.

## 0.2.0-review.1 — prepared for draft release

The current implementation builds all 17 instruments, the consolidated decision
sheet, contract-to-accounting links and four public practice packets into one
portable review bundle. Open `START_HERE.html` after extraction.

The release remains held for exact-file review. This index will record the actual
source commit, retrievable draft-release assets and verified checksum after the
clean committed build. No unbuilt asset is represented here as delivered.

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
