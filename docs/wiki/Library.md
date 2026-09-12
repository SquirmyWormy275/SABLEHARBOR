# Document library

[Company index](Home.md) · [Use cases](../reader/USE_CASES.md) · [Source and format guide](../reader/SOURCES_AND_FORMATS.md)

Use the subject pages for a guided introduction. Use this complete file inventory to reach the underlying Markdown records, PDFs and Excel workbooks without parsing source data. Current and historical files remain visible; read each document's status and successor references.

| Collection | Files |
|---|---:|
| [Businesses and professional practice](library/business.md) | 62 |
| [People, governance and departments](library/people.md) | 228 |
| [Finance, transactions and operating cases](library/finance.md) | 217 |
| [Controls, services and runtime](library/controls.md) | 69 |
| [Geography and facilities](library/places.md) | 300 |
| [Identity and collateral](library/identity.md) | 15 |
| [Canon, history and decisions](library/history.md) | 41 |
| [Reader guides and subject pages](library/reader.md) | 65 |
| [Implementation, source guides and delivery evidence](library/technical.md) | 82 |

## Format coverage

The inventory contains 738 Markdown files, 337 PDFs and 4 Excel workbooks. The existing publication manifest verifies 131 Markdown/PDF pairs.

Every inventoried file has a path, title, format, collection, size and SHA-256 in `reader_file` within the [institutional database](../internal/institutional_catalog.sqlite3). `reader_publication_pair` records verified source/PDF links; `reader_search` supports text search. `reader_evidence_link` separately connects validated evidence packets to their native accounting IDs and MD/PDF/XLSX files without declaring publication approval. These are discovery tables. Native accounting and operating databases retain their transaction records.
`reader_evidence_package` preserves accounting/legal package registers and review states; `reader_counterpart_audit` records applicable dated counterpart evidence.

The [format-review queue](library/format-review.md) lists every unpaired non-navigation Markdown record for reconciliation. Unpaired documents have not been certified against the new three-form requirement. Release-only records are reached through release guides; their archive contents are not silently counted as files in this checkout. Code, raw data, imagery and packaged binaries are reached through their domain guides and manifests. Generated library pages are excluded from their own inventory.

## Rebuild

Run `python tools/documents/build_institutional_catalog.py` from the repository root. The generator updates this library and the existing database together. It does not change source records or issue new publications.
