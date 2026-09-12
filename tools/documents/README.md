# Controlled-publication builds

Canonical Markdown and approved brand assets are the inputs. PDFs and the institutional
catalog are generated representations; they cannot independently approve a decision.

The renderer needs LibreOffice (`libreoffice` or `soffice`) and Ghostscript (`gs`). PDF
normalization uses qpdf when available. The owner-approved compatibility path uses pypdf
6.10.0 instead; install `tools/documents/requirements.txt` in the publication environment.
It is a separate dependency from the finance application.

```bash
python tools/documents/build_controlled_publications.py --normalizer pypdf
python tools/documents/build_institutional_catalog.py
python -m unittest discover -s tests/publications
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
```

`--normalizer auto` is the default: prefer qpdf, otherwise require pypdf. Explicitly selecting
an unavailable qpdf fails; it does not silently change the selected backend. The pypdf path
copies generated page objects into a fresh document, excludes source document/page metadata,
removes the information dictionary, and derives new identifiers from the copied object
structure. It rejects encrypted or interactive inputs. It is not a signature-preserving
editor or a general document-conversion service.

The build records the normalizer on newly generated manifest entries. Different renderers,
fonts, office/GS versions, and normalizers may produce different bytes; cross-toolchain byte
identity is not promised. A repeated build using the same inputs and toolchain must reproduce.

The default build retains an existing publication only when its source path, publication
path, brand, source SHA-256, and PDF SHA-256 all match its prior manifest entry. It does not
label a retained PDF as newly built by the selected backend. Changed or missing inputs and
outputs are rebuilt. `--force` rebuilds all publications; review and explain resulting drift.
Use repeatable `--rebuild-source <repository-relative-path>` arguments to verify a selected
set of publications again without rewriting unrelated historical outputs.

The office HTML adapter joins wrapped Markdown paragraphs, preserves explicit hard breaks
and list boundaries, repeats table headings, reserves width for short table labels/counts,
and uses compact controlled footers. Visual acceptance includes pagination and table text.

Versioned prior PDFs remain historical files. The publication manifest/catalog identify the
current version. Never hand-edit the PDF, catalog, or checksum to conceal source drift.
Before merge, render changed PDFs for visual inspection and follow the remaining checks in
`MAINTAINERS.md`. September 6 compatibility and canon evidence is recorded in
`docs/internal/validation/CANON_CLOSEOUT_2026-09-06.md`.

## Accounting and legal evidence discovery

The institutional SQLite catalog also exposes `reader_evidence_package`. Each row preserves
its package ID, review state, Markdown entry, source-register path/hash and complete provenance
JSON. The builder reads explicit `evidence-register.json` files under the accounting and legal
evidence directories, verifies source hashes, and rejects duplicate identities or unsafe paths.
A source-only package can have `visual_manifest: null`; it does not imply an accepted PDF or
workbook. The separately accepted Foundry Field packet retains its original schema and hashes.

```sql
SELECT package_id, title, status, markdown_path, register_path
FROM reader_evidence_package ORDER BY package_id;
```

Native transaction tables remain in the pinned release databases. Discovery records link to
those populations; they do not replace the ledger or turn proposed documents into executed
instruments. Run `python scripts/validate_reader_navigation.py --check-regeneration` to check
source hashes, database contents and reader links after rebuilding.

Dated counterpart reviews are applied only to unchanged source hashes. Verified artifact
hashes must also match; a changed publication fails the build. Historical audit evidence
remains in its dated register when current source edits return a document to review.

The institutional full-text index uses an external-content view over existing object rows.
This avoids storing the same controlled-document text twice while preserving the public
search columns and full-text query behavior. Catalog regeneration and search tests verify
logical content; SQLite byte layout can change when the schema changes.

Reader full-text search likewise uses an external-content view. Controlled Markdown reuses
its institutional normalized search text (including title/path); other files retain their
complete search body in `reader_text`. Search bodies are discovery text, not byte-exact source
exports. Original Markdown and its checksum remain available through `reader_file`.
Counterpart audit rows omit the duplicated source excerpt from database JSON; the complete
dated register and searchable source retain it. No evidence disposition or artifact hash is
removed. These storage choices keep the generated catalog within the repository file limit.
