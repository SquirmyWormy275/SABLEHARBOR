# Data, Financials, Inventory, and Release Architecture

## Current source

- Branch: `finance/enterprise-financial-platform-v0.1`
- Audit head: `1f294440a11e724e5f1bdcd3a7f59f7342169bfe`
- Pull request: [#9](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/9)
- State: **RELEASE CANDIDATE — NOT ACCEPTED**

PR #9 contains a shared SQLAlchemy/Alembic schema, accounting kernel, commercial and operational subledgers, mining/logistics/recovery/research models, named SQL, reports, workbook generators, valuation, release packaging, and tests.

## Enterprise versus unit view

The current platform identifies units through legal-entity, segment, project, site, counterparty, scenario, and provenance dimensions. The repository portal maps those records to each dossier. It does not claim separate unit databases already exist.

## Unit-release target

An accepted unit package must include an allowlisted unit SQLite database, CSV extracts, applicable financial statements, inventory/asset registers, query catalog, source lineage, enterprise reconciliation, validation results, manifest, and checksums.

- [Finance release-candidate register](FINANCE_RELEASE_CANDIDATE.md)
- [Independent unit package standard](../audit/UNIT_PACKAGE_STANDARD.md)
- [Business-line audit matrix](../audit/BUSINESS_LINE_AUDIT_MATRIX.md)
- [Business-line directory](../business-lines/README.md)

## Acceptance caveat

Green CI proves the assertions currently implemented. It does not by itself establish audited financial statements, reserve estimates, a production ERP, standalone unit releases, or closure of the independent PR #9 acceptance findings.
