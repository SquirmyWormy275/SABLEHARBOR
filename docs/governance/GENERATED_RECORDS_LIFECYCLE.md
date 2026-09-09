# Generated institutional records lifecycle

**Document ID:** `SH-GOV-GEN-001`
**Version:** 1.0.0
**As of:** September 9, 2026
**State:** PROVISIONAL implementation decision
**Owner:** Repository maintenance

## Decision

Keep `docs/internal/institutional_catalog.json` and `docs/internal/institutional_catalog.sqlite3` in Git as generated convenience artifacts. Keep the publication manifest beside the controlled governance publication sources. This explicit decision preserves the existing placement and resolves the location choice in issue #37 on accepted integration. It creates no new source authority.

Canonical Markdown/canon decisions and deliberately maintained structured source registers control. The publication manifest inventories generated representations and hashes; the JSON catalog and SQLite full-text index are downstream discovery surfaces. Query guides document their public schema and supported searches. None is approval evidence by itself.

## Update transaction

1. Edit the controlling source or source register and its version/decision record as appropriate.
2. Run `python tools/documents/build_controlled_publications.py --normalizer pypdf` (or the supported qpdf backend).
3. Run `python tools/documents/build_institutional_catalog.py`.
4. Run the publication tests and governance, catalog, organization, business-record and repository-hygiene validators.
5. Review changed PDF pages, source/publication pairing, source hashes, object identities and search results. Explain material source or generator changes in the delivery record.
6. Commit the source, required publications and generated indexes together. Do not hand-edit a PDF, manifest or SQLite row to suppress drift.

Unchanged source/publication pairs are retained by verified hashes. Normalization removes volatile PDF metadata. If a supported rendering backend changes page content, identify the environment and inspect the changed pages; do not disguise the change as source drift. Catalog regeneration is deterministic for a fixed manifest/source set.

## Retention and release

Current catalog rows select current controlled publications. Historical release artifacts and explicitly preserved predecessor PDFs retain their bytes and disposition labels. Do not overwrite a released package with a new build under the same version. New full distribution packages belong in indexed GitHub Releases with manifests/checksums under the delivery policy. Scratch databases, raw enterprise backups and unreviewed generated files are excluded.

Discovery acceptance tests verify useful questions, unique object identities, exact source/PDF hash pairing and schema relationships. They must not freeze an arbitrary total object count. An intentional new document changes the count; a lost document, stale source or duplicate identity fails reconciliation.

This is a repository artifact lifecycle decision. It does not resolve employee/client data retention, deletion or legal holds in Alexandria (#24), nor supply runtime authorization (#21/#22/#34).
