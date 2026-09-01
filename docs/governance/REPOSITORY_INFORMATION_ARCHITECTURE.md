# Repository Information Architecture

## Authority layers

1. `docs/canon/` controls corporate lore and decision state.
2. `assets/brand/` controls production identity/collateral files and provenance.
3. `docs/organization/` controls canon-derived organization/reference artifacts.
4. Accepted finance/data releases control quantitative records; PR #9 remains a release candidate.
5. `docs/company/` and `docs/business-lines/` index those sources.
6. `docs/wiki/` mirrors approved summaries for publication; it never controls canon.

## Navigation model

Enterprise → business line or component → identity/collateral → organization/authority → financials/accounting → inventory/assets/operations → database/exports → controls and unresolved facts.

## Duplication rule

Binary logos, charts, workbooks, and databases remain centralized. Dossiers link to them rather than copying them. A business-line release may package scoped copies only when its manifest, provenance, reconciliation, and checksums make the derivation auditable.
