# Sable Harbor repository audit — September 1, 2026

**Scope:** repository metadata, branches, pull requests, committed source tree, corporate lore, brand assets, organization materials, finance/data platform, generated-output design, wiki source, and business-line auditability.

**Audit conclusion:** the repository contains strong individual work products but has not yet functioned as one controlled enterprise archive. The accepted canon, logos, and organization publications live on `main`; a major finance platform remains in PR #9; useful business-line/collateral/wiki work was stranded on an unmerged branch; GitHub Wiki is disabled; branch protection/rulesets are absent; and no current business line has a complete independently generated audit bundle.

## 1. Control status by domain

| Domain | Current source | Status | Principal issue |
|---|---|---|---|
| Corporate lore | `docs/canon/` on `main` | **CONTROLLING** | OPEN facts must not be inferred from models or artwork |
| Organization | `docs/organization/` on `main` | **CONTROLLING, CANON-DERIVED** | Functional/authority maps are not complete HR or legal trees |
| Logo system | `assets/brand/logos/` on `main` | **PRODUCTION ASSET** | Duplicate and older branches remain |
| Corporate collateral | recovered from `assets/brand-integration-and-collateral-v0.2` | **PRODUCTION CANDIDATE** | Previously stranded; business-line editable/PDF variants incomplete |
| Business-line pages | `docs/business-lines/` on integration branch | **RELEASE-CANDIDATE INDEX** | Shared sources indexed; standalone unit exports absent |
| Finance/database platform | PR #9 | **RELEASE CANDIDATE — NOT ACCEPTED** | Prior acceptance audit identified migration, release, workbook, scenario, and three-statement blockers |
| Wiki | `docs/wiki/` source | **SOURCE ONLY** | Repository setting `has_wiki=false`; no live wiki |
| Blackridge | historical branches and canon summary | **PARTIAL** | old probe/scaffolding branches do not constitute the complete executable case build |

## 2. Repository hygiene findings

### H-01 — Branch sprawl and stale branches

Fourteen pre-audit branches existed. Several are merged work branches or obsolete probes. In particular:

- `blackridge/m00-foundation` and `blackridge/m00-v0.1.0-final` point to the same old commit and are fully behind `main`;
- `blackridge/m00-v0.1.0-review` adds only a connector probe;
- `blackridge/m00-ci-fix` adds a connector probe and a minimal build-status file;
- `brand/logo-system-v0.1` is an older diverged brand branch and included a tracked Python cache artifact;
- merged canon, logo, organization-map, and briefing branches remain undeleted;
- `assets/brand-integration-and-collateral-v0.2` contained unique useful material but was never integrated;
- `architecture/corporate-operating-model-v0.1` remains an open draft PR despite being superseded as a controlling model.

**Treatment:** unique collateral/wiki/business-line material was recovered into the integration branch without replacing accepted assets. A branch/PR disposition register is now versioned. Physical branch deletion requires repository administration after the stacked PR is accepted.

### H-02 — No enforced default-branch controls

No repository rulesets were detected. The repository also has branch deletion after merge disabled, automatic branch updating disabled, and no repository description, topics, or detected license file.

**Treatment:** add repository governance and validation workflows; open an administrator action issue for settings that cannot be changed through the present connector.

### H-03 — Generated and source artifacts were mixed conceptually

The repository contains legitimate publication binaries under the organization briefing and brand packages, while finance databases/workbooks/releases are generated and ignored. Some old branches also contain redundant ZIP bundles. Without an explicit policy, users cannot tell a source artifact from a generated release or review artifact.

**Treatment:** retain source code, canonical documents, individual production assets, manifests, and intentional publication packages. Keep reproducible databases and workbooks out of Git history; publish them as validated CI/release artifacts with checksums. Do not duplicate the same binary merely to create a business-line folder.

### H-04 — Root navigation was domain-oriented, not enterprise-oriented

The prior root README linked canon, organization, briefing, and finance documents, but did not provide a current-business-line control plane or an audit coverage matrix.

**Treatment:** replace the README with a company-first index and link each business line to a dossier that gathers its identity, organization, canon, data, finance, operations, and gaps.

## 3. Business-line auditability findings

### A-01 — Unit identity and organization are generally locatable

The current seven lines have production logo variants. Foundry Field, Willow, Atlas Meridian, Pale Sun/Red Wash, Project Cradle, and ARU/BS&T have dedicated canon-derived organization materials; Advisory has a briefing-grade organization view. The dossier layer now gathers these assets from one page per unit.

### A-02 — Accounting and data boundaries are incomplete

The finance platform models shared entities, segments, sites, journals, workers, assets, commercial records, mine production, logistics waybills, recovery runs, and research/evaluation records. Most shared tables require entity/segment/site filters. Generation-run and scenario isolation is not yet complete enough to issue accepted unit databases.

### A-03 — Standalone unit products do not exist

No current line has all of the following as a generated, validated package:

- filtered database;
- CSV table extracts;
- unit trial balance and three statements;
- inventory/asset register;
- source-to-ledger reconciliation;
- intercompany bridge;
- assumptions and fact-state report;
- validation report;
- manifest and checksums;
- CI-published workbook/release artifact.

Dossier links now distinguish existing sources from planned outputs and say **NOT IMPLEMENTED** where appropriate.

### A-04 — Some domain registers are materially partial

- ARU lacks a complete locomotive, railcar, terminal, parts, fuel, tools, and maintenance inventory.
- Pale Sun/Red Wash lacks an accepted full asset/reserve/technical inventory and must preserve reserve-report and safety boundaries.
- Foundry Field/Advisory lack accepted complete engagement/customer/contract populations as canon.
- Willow/Atlas records model experiments and evaluations but are not evidence of unrestricted research truth or final decision authority.
- Cradle host-owned and Sable Harbor-owned assets require explicit ownership and participation boundaries.

## 4. Finance-platform acceptance findings carried forward

PR #9 should remain review-blocked until its previously identified P0/P1 issues are closed, including:

1. explicit immutable Alembic migrations rather than historical migrations importing live models;
2. generation-run/scenario isolation in records, reports, workbooks, and exports;
3. semantic workbook sheet mappings and correct control predicates;
4. an integrated monthly three-statement model rather than summary cash-in/cash-out journals as the principal model;
5. driver-based scenarios rather than only global revenue/cost multipliers;
6. truthful historical-coverage language or expanded 2016–2022 statements;
7. public release construction from a versioned allowlist instead of a raw database backup;
8. safety scans over generated CSV, SQLite, XLSX, manifest, and nested package contents;
9. CI publication of validated review artifacts.

The current finance head added a professional-services engagement subledger and raised the local test count, but that does not close the above acceptance blockers.

## 5. Wiki findings

Versioned wiki source exists, but the GitHub repository setting reports the wiki disabled. A workflow source is being added for controlled publication after an administrator enables the wiki. Until that occurs, `docs/wiki/` is the reviewable source and the repository business-line pages are the functional navigation layer.

## 6. Work completed in the integration branch

- recovered unique brand standards, font provenance, corporate collateral, business-line pages, legal screen, wiki source, and brand validation tooling from the stranded collateral branch;
- excluded redundant package ZIPs and avoided overwriting the accepted production logo/organization trees;
- created an enterprise dossier and company-first root README;
- created a machine-readable registry for all seven current business lines;
- rebuilt the seven business-line pages as audit-control dossiers;
- added unit letterhead working templates;
- added a unit export specification, branch/PR register, database index, repository governance, validation script, CI workflow, and controlled wiki-publish workflow;
- corrected wiki publication status to state that the live Wiki remains disabled.

## 7. Remaining administrator and implementation actions

The integration branch should remain a stacked draft over PR #9. Before merging to `main`:

- close the finance acceptance blockers;
- make the stacked PR green and review its content classifications;
- enable the GitHub Wiki, run the manual publishing workflow, and verify the live pages;
- configure a `main` ruleset/branch protection and required checks;
- set repository description/topics and decide the formal license posture;
- enable deletion of merged branches and remove the branches classified as DELETE AFTER ACCEPTANCE;
- generate and review one complete unit package—ARU is the recommended pilot—before declaring all seven units independently auditable.
