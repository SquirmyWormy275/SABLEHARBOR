# Overnight accounting, legal and reader delivery

Source implementation: [PR #142](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/142). Its merge record establishes accepted repository delivery. New designs remain on `review/overnight-human-evidence-2026-09-12` for exact-file review; source integration does not approve them. The owner started this run with “ok. let er rip”.

## Sources and scope

Initial main: `8898d2d0310a60bdf0e4753036790c6eda1388cd`. Compatibility refresh incorporates accepted CCF PR #143 at `035304bf8860e9bc393ae73382a3e60501a23757`; no CCF implementation is authored by this workline.

The immutable operations release is `business-operations-v1.0.0`, source `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`, ZIP SHA-256 `b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817`. The archive was retrieved and verified; every CSV member was inventoried. Human schedules select complete declared base-2027 populations, with the 2026 transaction/tax population separate. Other scenarios and 2028–2031 retain native-release access and are not claimed as new human-document completion.

| Accounting package | Extracted row instances | Source and reconciliation |
|---|---:|---|
| Customer | 5,390 | [Register](../../finance/evidence/customer/evidence-register.json), [guide](../../finance/evidence/customer/README.md) |
| Treasury/payables | 12,223 | [Register](../../finance/evidence/treasury/evidence-register.json), [guide](../../finance/evidence/treasury/README.md) |
| Close | 15,084 | [Register](../../finance/evidence/close/evidence-register.json), [guide](../../finance/evidence/close/README.md) |
| Workforce/inventory/assets/debt | 16,236 | [Register](../../finance/evidence/supporting-schedules/evidence-register.json), [guide](../../finance/evidence/supporting-schedules/README.md) |
| Release transaction/tax | 73 | [Register](../../finance/evidence/tax-transaction/evidence-register.json), [guide](../../finance/evidence/tax-transaction/README.md) |
| Separate current industrial transaction/tax | 70 | [Current-source bridge](../../finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json) |

The 49,076 total counts row instances across working papers, including repeated source mirrors and static inputs. It is not unique transactions, people or headcount. Thirty-one registered reconciliation checks pass with zero residuals; additional validators check full populations, issuance/collection/posting joins, payroll scope, source hashes and acquisition identities. Unit and legal books remain alternate presentations.

[Legal records](../transactions/README.md) cover 56 source documents, 493 sections, 35 existing controlled PDF links and 13 clause-level reading dossiers. Source/section/dossier tables and native references are queryable in the legal SQLite database. Seventeen precise evidence gaps and nine field-level dispositions retain execution, tax, custody, ownership and billing boundaries.

[Wiki coverage](../WIKI_COVERAGE.json) reconciles seven business pages, 23 department/institution/capability pages and nine historical/external/cross-cutting pages. [Format reconciliation](../reconciliation/README.md) disposes all 448 pinned review rows: 44 verified representations, 118 maintenance/alias dispositions and 286 explicitly unresolved historical/document counterparts. A verified chart representation is not an equivalent letterhead rendering of its navigation prose. A follow-up examined 26 release manifests and 32 candidate records without promoting unsupported pairs.

## Review files and preservation

The held branch contains five accounting PDFs, five complete workbooks with 69 sheets, and 13 legal PDFs with editable HTML. Open `docs/reader/overnight/REVIEW.md` there for every workbook sheet preview and document link. The finance browser index is `docs/finance/evidence/coverage/draft-review/index.html`; legal indexes are under each `docs/legal/evidence/*/drafts/` directory. These are local/static repository assets, not a new hosted service.

The accepted Foundry Field packet from PR #134 remains immutable. Its acceptance validator checks all pinned bytes. The selected V08 map and organization source hashes also remain unchanged. Existing billing proposal PR #138 is referenced without adopting its fictional fields or changing booked amounts. No earlier visual is replaced by these drafts.

## QA findings and corrections

- Independent review found omitted industrial sales invoices and contract revenue. The final customer population adds 570 invoices, 348 contract-revenue rows and 54 contract/customer inputs, with source and journal lineage.
- Cross-book checks now compare unit/legal account-month totals and Core/enterprise imported source postings, instead of merely showing that each book balances independently. Negative tests reject account and source-ID corruption.
- All 127 Core invoice issuance events are traced through their actual `source_id` route, including invoices without collection history.
- Cradle capitalized labor is separated from payroll expense. Workbook conversion preserves inputs exceeding Excel's numerical precision as text and checks every source cell.
- Actual LibreOffice workbook previews revealed touching numeric fields, overlapping settlement IDs and narrow PPA labels; these were corrected. Legal Advisory pagination was corrected without shrinking body text. Every legal PDF page and every finance worksheet/PDF preview was reviewed by the team; main also inspected all 13 legal PDF pages.
- The reader browser check covered 28 desktop/mobile surfaces with no page-width overflow or broken images. New source routes passed local link checks.
- Catalog storage reuses controlled search text and omits duplicated source excerpts from audit metadata. Original sources, hashes, dispositions and search access remain; the file-size gate was preserved.
- Hosted validation caught an unavailable pinned revision in shallow checkout and a copied legacy private-project reference in an audit excerpt. CI now fetches the exact pinned revision, and the audit stores source references/hashes rather than copied prose.

Exact visual QA and artifact hashes are retained on the held branch in `docs/finance/evidence/coverage/draft-review/QA.json`, the five finance draft manifests, and `docs/legal/evidence/assets-rights/drafts/qa/PAGE_REVIEW.json`.

## Verification

Local checks include:

```bash
python docs/finance/evidence/coverage/validate.py
python -m pytest -q docs/finance/evidence/coverage/test_extracts.py
python docs/reader/transactions/validate.py
python docs/reader/reconciliation/build.py --check
python scripts/validate_reader_workqueue.py
python scripts/validate_finance_evidence_acceptance.py
python geospatial/facilities/visitor/validate_acceptance.py
python tools/documents/build_controlled_publications.py
python tools/documents/build_institutional_catalog.py
python scripts/validate_reader_navigation.py --check-regeneration
python -m unittest discover -s tests/publications
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
python scripts/validate_organization_maps.py
python scripts/validate_repository_hygiene.py
python scripts/validate_business_records.py
python scripts/check_public_safety.py
python -m pytest -q --import-mode=importlib
python -m pytest -q geospatial/tests/test_runtime_integration.py
git diff --check
```

Use the documented dependency environment and `PYTHONPATH=src` for the public-safety CLI. The held branch additionally runs `validate_drafts.py` and legal `validate.py --drafts`. Exact CSV/SQLite/source comparisons and logical catalog regeneration pass; repeated legal PDFs reproduce. Hosted required checks and the final accepted SHA are recorded directly on PR #142 rather than inferred from local results.

## Remaining decisions and evidence

New designs need exact-file owner review. PR #138 billing details remain unaccepted. [The legal gap register](../transactions/RECONCILIATION.md) identifies each missing instrument, source conflict or external fact and its next action, including Red Wash pre-close day conflicts, tax submission, lender/title/settlement evidence and contract execution. Modelled or proposed evidence is never promoted to actual execution. The 286 unresolved format counterparts retain individual source IDs, search evidence and next actions in the dated reconciliation; they are not proof that 286 publications do not exist.
