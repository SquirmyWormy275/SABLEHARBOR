# Runtime estate releases

Version 1.0.0 is the PR119 synthetic runtime design and enterprise financial successor.
The release tag is `runtime-estate-v1.0.0`; the complete artifact is
`sable-harbor-runtime-estate-v1.0.0.zip` with `SHA256SUMS.txt` at
[GitHub Releases](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/runtime-estate-v1.0.0).
Publication and repository acceptance require the final candidate checks; a planned
link alone is not evidence that a release exists.

The bundle contains the complete tracked source snapshot (including controlled
publications, geographic products, editable visuals and the reviewed workbook),
the integrated financial successor and exact predecessor bridge, and runtime query
SQLite. `MANIFEST.json` records the source commit, runtime content identity and
SHA-256 of every member. The packaging command refuses dirty or mismatched financial
builds, verifies all financial hashes and never overwrites an archive.

```bash
uv run python -m enterprise.runtime.build_finance
uv run python -m enterprise.runtime.workbook --output enterprise/runtime/publications --verify
uv run python -m enterprise.runtime.release --output /tmp/runtime-release-v1.0.0
```

Existing releases and 2026 calibration remain immutable. The September land entry
is a separate balanced $3M noncash overlay with unresolved settlement clearing;
future requests obey finite Treasury limits. Public-reference providers remain
uncontracted and uninstalled; owned land is acquired/preconstruction with no
commissioned capacity. Actual execution gates are in
[readiness.json](../../enterprise/runtime/readiness.json).

The successor workbook uses XlsxWriter with explicit caches and independent
source-to-cell/formula verification. Artifact Tool was unavailable locally; the
owner allowed selection of the execution environment. This disclosed substitution
preserves all previously reviewed Artifact Tool workbook bytes and checks.
