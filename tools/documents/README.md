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
