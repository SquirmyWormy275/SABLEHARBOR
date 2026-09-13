# Geographic discovery adjudication

This is the first bounded semantic review batch for [#108](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/108).
It adds dispositions alongside the immutable rc4 discovery inventory. It does not overwrite
the 919-source baseline, extracted wording, occurrence IDs, curated object register or maps.

## Blackridge batch — September 12, 2026

Reviewed source: `blackridge/data/public/databases/blackridge_m00_v0.1.0.sqlite3` at
`d91a22c35c91b213204411421de88815f27d8e16`, SHA-256
`2e6622d0e710f784c49cd6b773514820dbe247c4ec50a18f4c9cbbcf784587d5`.
The source database and its generator were inspected together. Exact rules and both source
hashes are in [BLACKRIDGE_RULES.json](BLACKRIDGE_RULES.json). These rules are specific to
that archived source and reviewed column values; they are not keyword rules for other sources.

| Disposition | Occurrences | Interpretation |
|---|---:|---|
| Repeated location reference | 59,130 | One `BLACKRIDGE-PIT` token used by separate resource assignments; all 59,130 assignments and intervals survive. |
| Non-geographic domain label | 1,666 | `mine` and `plant` classify ledger events; they do not each identify a new mine or plant. Event and availability times remain separate. |
| Non-geographic record label | 89 | 87 generic plant-hourly labels, one capital-project label and one mine-plan-version label do not supply geographic claims. |
| Unlocated component reference | 11 | Facility/location IDs and names, plant unit, storage location and warehouse remain source-local, unlocated component candidates. |
| **Total reviewed in this batch** | **60,896** | **17,249 baseline occurrences remain outside this review.** |

The 59,130 assignments follow the pinned generator's 365 days × two shifts ×
(27 trucks + 54 operators). This arithmetic explains the repeated token; it does not
collapse different events into duplicates. The database also contains component assignments
with `HOST-*` tokens that did not match the original discovery vocabulary. They remain in
the archived source; this batch does not pretend the keyword inventory exhausts the database.

Each reviewed occurrence retains its original ID, locator, exact wording, a rule/reason ID,
a source-local grouping key and the entire archived source row. The row includes its
primary/canonical/event/resource identifiers and every available time field. Row ordinals
are reproduced using the original extractor's query against the pinned database, then
cross-checked against exact wording; they are not treated as permanent entity identifiers.
The [compressed review](BLACKRIDGE_REVIEW.csv.gz) is indexed by the
[hash/count summary](BLACKRIDGE_REVIEW.json).

`BLACKRIDGE-PIT` is not automatically an alias for `Pit 1`, `Location 1`, or a surveyed
mine footprint. The existing census separately identifies Blackridge as `SH-SITE-0009`
and generated components such as `SH-BR-PIT-001`; those records and their uncertainty stay
unchanged. Generated event timestamps do not become occupancy dates. Blackridge remains an
external founding-history case, not a newly owned Sable Harbor asset.

## Reproduce and validate

Use Python 3.12, matching geospatial CI, with the archived Git commit available locally:

```bash
python geospatial/adjudication/review_blackridge.py --check
python -m pytest geospatial/tests/test_blackridge_adjudication.py -q
```

Omit `--check` only to regenerate the two review outputs from the reviewed rules. The
validator binds the original occurrence archive, coverage hash, source commit and source
bytes; rechecks every selected wording against the archived SQLite row; checks exact rule
coverage/counts; and compares deterministic output bytes. Changed inputs, unexpected values,
ambiguous rules and altered outputs require explicit review rather than automatic acceptance.

This batch finishes source-local classification for the **60,896 discovery hits from one
source**, not semantic review of all 919 source files or all their geographic content.
Eleven appearances still require spatial adjudication. Remaining source review, subsequent
canon deltas, raster/OCR review, historical occupancy and the temporal map program keep
#108 open. No geometry, access rights, construction or institutional canon is promoted.

## Reference-layer batch — September 12, 2026

The second batch reviews **7,844 occurrences** in three archived public reference layers
at the same pinned discovery commit. [REFERENCE_LAYER_RULES.json](REFERENCE_LAYER_RULES.json)
binds each source hash and expected coverage. All 3,912 existing features explicitly carry
`REAL_REFERENCE`, `REAL` and `REFERENCE_ONLY`; these are map context, not company assets.

| Archived layer | Features | Discovery occurrences |
|---|---:|---:|
| Wyoming local roads | 3,195 | 6,410 |
| Wyoming waterbodies | 540 | 1,080 |
| Wamsutter highways | 177 | 354 |

The review separates 3,912 feature identifiers, 3,912 repeated source-layer links and
20 appearances of three road names. Each appearance resolves to an exact archived JSON
pointer and the existing feature ID. The output preserves every source property, including
provider identifiers and available dates, and binds the geometry by type and canonical JSON
SHA-256. Provider dates do not become occupancy dates. Road-name variants are preserved;
this review does not infer that separately identified road segments are duplicate features.

The [review output](REFERENCE_LAYER_REVIEW.csv.gz) and [summary](REFERENCE_LAYER_REVIEW.json)
bring cumulative occurrence classification to **68,740 of 78,145**, leaving **9,405**
outside these two disjoint batches. This is occurrence classification, not complete review
of every geographic claim in the 919 sources. The Blackridge spatial questions, later
canon deltas, OCR and temporal-map requirements remain unresolved; #108 stays open.

```bash
python -m geospatial.adjudication.review_reference_layers --check
python -m pytest geospatial/tests/test_reference_layer_adjudication.py -q
```
