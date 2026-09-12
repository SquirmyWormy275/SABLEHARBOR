# Complete legal source publication — delivery record

The owner rejected the earlier 13 abbreviated legal dossiers as a substitute for complete documents and authorized autonomous full-length publication on September 12, 2026. This package corrects that scope error. New designs remain in [draft PR #145](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/145) for exact-file owner review.

## Delivered scope

- **56 complete source editions:** 56 PDFs, 56 editable HTML documents and the original controlling Markdown files, linked individually from [the index](README.md).
- **200 PDF pages:** every source heading, paragraph, list, table cell and code block is retained. The independent comparison covers 3,277 source blocks.
- **Full-text database:** `full-text.sqlite3` contains exact original Markdown, source IDs, statuses, revision/hash provenance and all publication paths/hashes. It does not substitute excerpts for the originals.
- **One source revision:** `79437a778d4a4d5097a3cdaa36d7d8ab13217536`. All 56 source bytes were checked against that accepted main revision. The original inventory was assembled at `8898d2d`; these are distinct provenance dates, not conflicting authority.

The selected sources contain 49,846 whitespace-delimited words. This is document size, not a transaction or clause count. A complete edition of an existing summary, term sheet, policy, proposal or historical index retains that source's character. It is not a newly authored definitive agreement or an executed original. The [source audit](SOURCE_AUDIT.md) identifies those boundaries individually; all 17 existing legal evidence gaps remain in the [gap register](../../reader/transactions/RECONCILIATION.md).

## Quality and preservation

The renderer uses complete source Markdown and approved identity assets, with readable multi-page layouts rather than one-page limits. Independent tests reject omitted paragraphs, table cells, changed amounts, reordered sections and redacted PDF content even when artifact hashes are recomputed.

Manual review covered every PDF page and each edition's desktop/mobile HTML view. [The QA manifest](QA_MANIFEST.json) binds those inspections and saved images to exact final PDF/HTML hashes. Global DOM inspection additionally checks the whole HTML body for hidden content, overflow and broken images. Implementation QA does not grant owner design acceptance.

Corrected defects included metadata lines running together, narrow identifier/date columns, lone words stranded on continuation pages, publication-provenance-only final pages and cramped mobile tables. Changed pages were reinspected. The [determinism record](qa/render/DETERMINISM.json) records two complete builds with identical artifact manifests.

The accepted Foundry Field packet, V08 map, organization art, existing controlled publications and prior accounting drafts retain their bytes. Regeneration retained all 131 existing hash-verified controlled publications. The 13 older summaries remain supplementary reading aids and are no longer the primary legal delivery route.

## Reproduction and validation

Install `requirements.txt` in the documented publication environment. Rendering uses `/usr/bin/chromium`; validation uses Git and PDF inspection tools. Run from the repository root:

```sh
python docs/legal/full-text/build.py
python docs/legal/full-text/build_index.py
python tools/documents/build_evidence_review_index.py
python docs/legal/full-text/validate.py --browser
python -m pytest -q docs/legal/full-text/test_full_text.py
python docs/legal/full-text/validate_qa.py
python tools/documents/build_controlled_publications.py
python tools/documents/build_institutional_catalog.py
python scripts/validate_reader_navigation.py --check-regeneration
python scripts/validate_governance_j2.py
python scripts/validate_repository_hygiene.py
python scripts/validate_institutional_catalog.py
python scripts/validate_organization_maps.py
python scripts/validate_business_records.py
python scripts/validate_finance_evidence_acceptance.py
python geospatial/facilities/visitor/validate_acceptance.py
PYTHONPATH=src python scripts/check_public_safety.py
python -m unittest discover -s tests/publications
python -m pytest -q --import-mode=importlib
git diff --check
```

Full-source validation passes for 56 sources, 200 pages, 3,277 blocks and 112 browser viewports. Thirteen adversarial tests and 20 publication tests pass. Full repository pytest passes with three existing skips and the existing SQLite datetime deprecation warning. Applicable hosted check results and the delivered commit remain recorded on PR #145; the PR stays draft until exact-file owner review.
