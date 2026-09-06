# Governance controlled publications

These PDFs are generated from canonical Markdown under document standard `SH-GOV-DOC-001`. They are U.S. Letter, use the approved identity assigned by the publication builder, and must not be edited manually. [`../publication_manifest.json`](../publication_manifest.json) reconciles every source and PDF by SHA-256.

The directory includes the board/capital instrument, governance constitution, Assumption of Risk form, all five committee charters, and the controlled Red Wash records:

- [Red Wash Transaction and Operating Record](SH-PS-RW-TOR-001_v1.0.0.pdf), using the owner-approved Pale Sun source identity; and
- [ARU/BS&T Interface and Dependency Record](SH-PS-RW-LOG-001_v1.0.0.pdf), using the owner-approved Red Wash source identity.

The source logos are embedded as presentation identity only. They do not alter the authority, canon state, or public/private boundary of either source record.

Rebuild the complete controlled set with `python tools/documents/build_controlled_publications.py`. The builder requires LibreOffice, Ghostscript, and qpdf; it removes mutable PDF metadata and derives each document ID from page content so an unchanged source and toolchain produce byte-identical publications. Then run `python tools/documents/build_institutional_catalog.py` to reconcile the derived JSON and SQLite catalogs.
