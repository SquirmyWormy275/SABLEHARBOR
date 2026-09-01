# Sable Harbor Repository Audit v0.1

## Executive finding

The repository has a credible institutional core but was organized primarily by artifact type rather than by enterprise and business-line accountability. Accepted `main` contained canon, production logos, canon-derived organization charts, an editable/rendered organization briefing, and public-repository governance. The active finance branch adds substantial shared data infrastructure but remains unaccepted and does not yet publish independently reviewable packages for every unit.

## Scope inspected

- Accepted baseline: `main` at `c111ec6f4900edea656a52a391c71c600b880be1`
- Active finance candidate: `finance/enterprise-financial-platform-v0.1` at `1f294440a11e724e5f1bdcd3a7f59f7342169bfe`, PR #9
- Other material: legacy operating model, diverged collateral/wiki branch, merged source branches, duplicate/minimal Blackridge branches, and earlier logo work

## Principal findings

### P0 — No enterprise-to-unit audit layer

There was no single ARU page indexing its logo, stationery, ARU/BS&T organization, canon, logistics schema, finance queries, inventory perimeter, release status, and unresolved facts. The same structural gap existed across the enterprise.

**Remediation:** standardized dossiers for thirteen current, component, historical, and case identities; central directory and registry; company portal; audit matrix; controlled wiki source.

### P0 — Wiki policy and repository setting were inconsistent

Repository policy anticipated a public wiki while the repository reported `has_wiki: false`.

**Remediation:** version-controlled `docs/wiki/` source and publication-status register. Actual wiki enablement remains a repository-setting action.

### P0 — Finance/data acceptance state was unclear in navigation

PR #9 was substantial and green, while the accepted baseline had no finance directory and the independent acceptance boundary was not visible from the repository home.

**Remediation:** pinned release-candidate register and unit source maps. Nothing in this portal accepts or merges PR #9.

### P1 — Collateral existed on a diverged branch

Brand standards, font provenance, master letterhead, memo, report, presentation, Evalon identity, and preliminary wiki source existed on `assets/brand-integration-and-collateral-v0.2`, a branch diverged from current `main`.

**Remediation:** selectively import coherent brand/legal source trees, builder, and validator onto a fresh branch rather than merging the stale branch wholesale.

### P1 — No accepted standalone unit databases or releases

PR #9 models units through shared entity and segment dimensions. No accepted ARU SQLite file, ARU inventory register, or ARU financial package is committed.

**Remediation:** define the unit package standard and state the gap explicitly. Materialization remains a finance-platform task.

### P1 — Branch and pull-request hygiene

Fourteen branches were observed. Multiple Blackridge branches pointed to duplicate commits; merged source branches remained; PR #1 was a stale draft; PR #9 was active; the branch listing did not identify `main` as protected.

**Remediation:** branch/PR register and owner-action backlog. Destructive deletion is deferred until unique work is preserved.

### P1 — Repository metadata and release management

At audit time, repository description was unset, topics were empty, no GitHub Releases existed, merged-source auto-deletion was disabled, and Wiki, Pages, and Discussions were disabled.

**Remediation:** owner-action backlog. These are repository settings, not content changes.

### P2 — Contributor and security controls

The accepted baseline lacked repository-level contribution/security guides, CODEOWNERS, a PR template, a unit-gap issue form, and an enterprise-portal validator.

**Remediation:** add those controls in this workstream.

## Conclusion

After review, the repository will be navigable as an institutional archive from company to unit. It will not yet be a set of independently accepted financial and operating releases. That requires remediated, unit-scoped, reconciled, validated artifacts from PR #9.
