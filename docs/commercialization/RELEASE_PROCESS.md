# Release process

Run `shfin package-release` against a validated standard database. The command exports public-safe CSVs, a SQLite snapshot, the six workbook suites, usage terms, limitations, a row-count inventory, and SHA-256 digests.

Versioned packages are immutable. Corrections require a new package version and changelog. Before publication, rerun tests, scan for secrets and sensitive-looking PII, verify every digest, and confirm that private benchmark truth is absent.
