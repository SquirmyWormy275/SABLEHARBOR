# Geographic decisions and final source review

This edition records the owner's delegated geographic choices in the [controlling addendum](../../docs/canon/GEOGRAPHIC_COMPLETION_2026-09-13.md). It preserves original source bindings, approved artwork and existing geometry while adding three screened fictional site footprints, explicit dispositions for all 34 site/component records, three rejected prospects and five career/education references.

`DECISIONS.json` preserves the previous docket beside each new decision. `SITE_SELECTIONS.geojson` supplies authored design coordinates; `SITE_SCREEN.json` reproduces acreage, elevation, flood-map and archived transportation/water checks from the retained public reference bytes. `REJECTED_ALTERNATIVES.json` explains why the nine earlier options were rejected. No site footprint represents survey accuracy, real title or an executed lease.

The [source interpretation record](SOURCE_REVIEW.md) explains the fixed 6,896-carrier review, source-text correspondences, supersession rules and recovered references. `VISUAL_REVIEW.json` records 135 unique embedded images and 290 appearances, including the separately inspected PDF soft-mask composites. Source-image and approved publication bytes are preserved.

From the repository root, with the geographic requirements installed:

```sh
python -m geospatial.finalization.sync
python -m geospatial.finalization.source_review
python geospatial/scripts/build_geopackage.py
python -m geospatial.finalization.build --output var/geographic-decisions
python -m pytest geospatial/tests/test_finalization.py -q
```

The build produces searchable offline decision, source-carrier and source-ledger readers, three context-map plates, a PDF atlas and machine-readable review records. The main evidence-package builder incorporates them and adds registered GeoPackage attribute tables. Package publication additionally requires a clean accepted source, native QGIS checks, browser checks and sealed-release verification. Current delivery status belongs in the release record; source adjudication alone does not assert issue closure.

Reference downloads are retained for offline reproducibility. `screen.py` verifies and reads them without network access. `fetch_context.py` is a research acquisition helper, not a build step; running it creates a fresh acquisition manifest that must be reviewed before replacing the selected reference archive.

`SOURCE_LEDGER.json.gz` verifies all 919 original file fingerprints and records every changed path through the pinned accepted main. Its 17 canonical delta findings came from full-text review; other paths retain explicit domain/derivation dispositions rather than claiming a full-domain audit. Later source changes are not automatically approved.
