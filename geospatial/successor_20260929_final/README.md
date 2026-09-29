# Final accepted PR #185 geographic source delta

This issue #108 source review pins accepted main
`e4ed29b2b6410e4c736b90dddef37a735487dada` through the actual PR #185
merge `bcdf3ade1d83d04774da9a914deb269442ee52f6`. It inventories **all
18 changed paths** with exact Git blob IDs and SHA-256 bytes and records a
path-specific geographic-authority disposition for each. There is no changed
controlling canon in this interval. The prior [83-path review](../successor_20260929/README.md)
already covers accepted main from `3dd5e15f` through `e4ed29b2`, including
full-text geographic review of the changed issue #18 scope canon. Together
these dated intervals leave no unreviewed accepted main path through the
frozen `bcdf3ade` cutoff. They do not promise coverage of future commits.

The two new geographic sources in #185 pin the corrected 40-mile site and
turnout register and a visibly provisional 1954 history case. Six derivatives,
three implementation tests, three explanatory guides and one criterion review
are classified at their own authority. A generated map or test does not
corroborate its source. The 12 facilities, 31 tracks, 26 structures and eight
proposed connections are a declared synthetic population; no real title,
survey, external client parcel, construction certification, in-service lead,
mine spur or finished-uranium custody is established. The operating/finance
successor previously reperformed 180 months and 13 finance datasets with a
zero modeled journal/cash/tax delta.

This ledger stops **before** the [narrow synthetic geographic scope decision](../../docs/canon/GEOGRAPHIC_SYNTHETIC_SCOPE_DISPOSITION_2026-09-29.md)
and its own acceptance artifacts. Those are newly authored in the later
successor. Record their final accepted tree/merge SHA, reader/catalog
generation and release checks in that successor's acceptance receipt; adding
them to the prior accepted-source interval would be self-referential.

```bash
python -m geospatial.successor_20260929_final.source_delta
uv run --with-requirements geospatial/requirements.txt --with pytest \
  python -m pytest -q geospatial/tests/test_source_delta_20260929_final.py
```

The builder fails if the changed-path population, any exact source blob, or
the expected absence of a controlling-canon change differs. It does not mark
issue #107 or #108 closed; the separate scope decision and edition acceptance
must be reviewed through the normal repository process.

`geospatial/scripts/validate_geospatial.py` still reports
`program_complete=false` for the frozen 1.4 validation package it checks.
That historical field is not rewritten to claim #107/#108 were complete in
1.4. The later scope decision, this accepted-source ledger and the final
release/issue receipt control the newer edition's bounded completion state.

## Complete 1.5 distribution

The separately versioned 1.5 package nests the **unchanged** accepted 1.4 ZIP
and includes the dated source/decision/rail supplement, an offline entry index,
an exact member manifest and checksums. It is one downloadable asset; the
accepted 1.4 archive remains available independently and is never relabeled or
modified. The package preview is **not** an accepted release. After this PR
merges, rebuild from the clean accepted main commit, independently import it,
record its final SHA-256 and publish a new `geographic-evidence-v1.5.0` release.

```bash
python -m geospatial.successor_20260929_final.package \
  --base /path/to/sable-harbor-geographic-evidence-v1.4.0.zip \
  --output var/geographic/sable-harbor-geographic-evidence-v1.5.0.zip
python -m geospatial.successor_20260929_final.verify_package \
  var/geographic/sable-harbor-geographic-evidence-v1.5.0.zip \
  --import-to var/geographic/import-v1.5.0
```

The builder rejects any 1.4 input except the 237,264,171-byte archive with
SHA-256 `f106e164a7578d64c32ba1bcc9444b3a96d89881d7c7b92b51bb97cf2bef6df4`.
The verifier independently hashes the outer and all 1,907 predecessor source
members, checks the geographic population and finance limits, runs SQLite
integrity on the imported GeoPackage and resolves the offline reader links.
Open `var/geographic/import-v1.5.0/index.html` in a browser; use the nested
1.4 native QGIS project or GeoPackage for spatial inspection. The current
route and historical alternative have different source/status layers.

For a review-only build on an unaccepted branch, add `--preview`; its manifest
explicitly says `PREVIEW_UNACCEPTED` and records the branch HEAD. The final
build requires a clean checkout and is pinned to the accepted source commit.

The controlled-publications builder was also run during this successor review.
It rendered zero PDFs but tried to remove fifteen older `qpdf` entries from
`docs/governance/publication_manifest.json` because its default invocation
only retained the 131 `pypdf` entries. Those fifteen accepted source/PDF pairs
remain byte-valid and outside this rail-only source change. The attempted
manifest drift was discarded; the accepted 146-pair manifest is retained, and
the institutional reader was regenerated against it. A publications builder
run alone is not a no-drift check for this scoped release.
