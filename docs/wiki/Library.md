# Document library

[Company index](Home.md) · [All files](Files.md) · [Audit practice](Audit.md) · [Source and format guide](../reader/SOURCES_AND_FORMATS.md)

Browse company documents by subject, including Markdown records, PDFs and Excel workbooks. For datasets, maps, artwork, programs and every other repository file, open [All files](Files.md). Each collection links directly to the originals. Earlier editions remain available with their dates and status.

| Collection | Files |
|---|---:|
| [Businesses and professional practice](library/business.md) | 62 |
| [People, governance and departments](library/people.md) | 238 |
| [Finance, transactions and operating cases](library/finance.md) | 474 |
| [Controls, services and runtime](library/controls.md) | 82 |
| [Geography and facilities](library/places.md) | 318 |
| [Identity and collateral](library/identity.md) | 15 |
| [Canon, history and decisions](library/history.md) | 56 |
| [Reader guides and subject pages](library/reader.md) | 81 |
| [Implementation, source guides and delivery evidence](library/technical.md) | 348 |

## Format coverage

The inventory contains 1172 Markdown files, 454 PDFs and 48 Excel workbooks. The existing publication manifest verifies 148 Markdown/PDF pairs.

## Published formats

The [format-review list](library/format-review.md) tracks source documents whose formatted companions need checking. The [release guides](../reader/USE_CASES.md#downloads-and-tools) link complete downloadable packages and their manifests.

<details>
<summary>Catalog and maintenance</summary>

The [institutional database](../internal/institutional_catalog.sqlite3) stores file paths, titles, formats and hashes in `reader_file`. `reader_search` provides text search; `reader_publication_pair` records verified source/PDF links. Evidence-package and counterpart tables retain the associated review records. Transaction data remains in the relevant accounting and operating databases.

<a id="rebuild"></a>
Run `python tools/documents/build_institutional_catalog.py` from the repository root to update this library and its database. The build updates discovery records; it does not issue new publications. Generated library pages are excluded from their own inventory.

</details>
