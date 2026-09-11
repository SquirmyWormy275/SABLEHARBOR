# Runtime estate releases

Version 1.0.0 is the PR119 synthetic runtime design and enterprise financial successor.
The release tag is `runtime-estate-v1.0.0`; the complete artifact is
`sable-harbor-runtime-estate-v1.0.0.zip` with `SHA256SUMS.txt` at
[GitHub Releases](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/runtime-estate-v1.0.0).
Published and accepted on September 11, 2026 through
[PR119](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/119).

The bundle contains the complete tracked source snapshot (including controlled
publications, geographic products, editable visuals and the reviewed workbook),
the integrated financial successor and exact predecessor bridge, and runtime query
SQLite. `MANIFEST.json` records the source commit, runtime content identity and
SHA-256 of every member. The packaging command refuses dirty or mismatched financial
builds, verifies all financial hashes and never overwrites an archive.

## Accepted snapshot and verification

- Packaged candidate: `45e145614407c933739ff7143275268b55f11b4c`.
- GitHub test merge: `b7bf168c51f221f2e567a2f17d0dafbefe7d2192`.
- Accepted merge: `b83e4be2182a5e4143808a3dab5f8d929a133caf`; its tree matches the candidate.
- ZIP SHA-256: `cf0f0a7f1f5dfddf1ad277375c1d9be94c79c6151ba9bd59f1c40d6df55b5276`.

The published [final checks](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/runtime-estate-v1.0.0/FINAL_CHECKS.json),
[reproduction record](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/runtime-estate-v1.0.0/REPRODUCTION.json),
[native QGIS evidence](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/runtime-estate-v1.0.0/QGIS_VALIDATION.json)
and [checksums](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/runtime-estate-v1.0.0/SHA256SUMS.txt)
record 13 successful acceptance jobs across 11 candidate workflows, two identical
clean financial builds and two byte-identical complete archives. Local and CI
financial payloads match; the documented provenance fields differ between candidate
and test-merge commits. Visual review covered 13 PDFs / 38 pages, seven workbook
sheets and 12 concept plates.

All nine workflows triggered on the accepted merge commit subsequently passed,
including [business operations](https://github.com/SquirmyWormy275/SABLEHARBOR/actions/runs/34648327444).
A public-release download check verified every external checksum and all 1,693
embedded manifest members against the packaged candidate. Later documentation
closeout and [PR121 facility-atlas integration](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/121)
do not repin or replace the v1.0.0 release.

To reproduce this historical release, use a clean checkout of the packaged candidate
with its locked dependencies before running:

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
