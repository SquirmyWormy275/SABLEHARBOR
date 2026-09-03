# Controlled-Publication Reproducibility Audit — 2026-09-03

**Status:** PASS WITH NONDETERMINISTIC-BYTE DRIFT DOCUMENTED

Commands run:

```text
python tools/documents/build_controlled_publications.py
python tools/documents/build_institutional_catalog.py
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
git diff --check
git status --short
```

Both validators and `git diff --check` passed. Regeneration changed PDF bytes, publication hashes in `docs/governance/publication_manifest.json`, and the derived JSON/SQLite catalog hashes. Source hashes and extracted publication content did not change. Inspection identified Ghostscript `CreationDate`/`ModDate` metadata as the cause (existing artifact: `2026-09-03 01:08:07 PDT`; audit build: `2026-09-03 09:33:33 PDT`).

Disposition: the audit-generated PDFs, manifest, JSON, and SQLite changes were not committed because no authoritative Markdown/source change required regeneration. This is metadata-level nondeterminism to monitor or correct in the generator in a later hygiene change. Canonical Markdown and canonical structured sources remain authoritative; generated PDFs and catalogs are subordinate representations and create no canon.
