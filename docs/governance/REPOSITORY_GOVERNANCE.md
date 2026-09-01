# Repository Governance

## Source hierarchy

1. `docs/canon/` and its decision register control accepted corporate facts.
2. `docs/governance/` controls publication, repository, audit, and artifact-state rules.
3. `docs/business-lines/registry.json` defines the machine-readable unit/component/case index; it does not independently canonize facts.
4. Accepted `src/`, `db/`, and test/release artifacts implement and validate systems against those boundaries. PR #9 remains a separate release candidate.
5. `docs/company/`, `docs/business-lines/`, and `docs/wiki/` are navigation/publication layers. They summarize and link; they do not create canon.
6. Generated databases, workbooks, CSVs, and release bundles are evidence artifacts, not source-of-truth documents.

## Normalized locations

- Corporate and unit logos: `assets/brand/logos/`
- Letterhead and document templates: `assets/brand/collateral/`
- Organization source and renders: `docs/organization/`
- Business-line/component/case dossiers: `docs/business-lines/`
- Enterprise data and finance status: `docs/data/`
- Accepted SQL queries and migrations: `db/` when the finance platform is accepted
- Unit registry: `docs/business-lines/registry.json`
- Wiki source: `docs/wiki/`
- Generated outputs: ignored `var/`, `workbooks/outputs/`, `reports/`, `data/generated/`, and `releases/generated/` paths

Do not duplicate a logo, chart, database, or workbook inside every dossier folder. Dossiers link to normalized source assets. Generated unit bundles are immutable artifacts identified by an explicit generation run.

## Change control

- Use a dedicated branch and pull request for each material workstream.
- State whether each changed fact is accepted, provisional, open, superseded, model-proposed, scenario input, synthetic, derived, historical, or not materialized.
- Never merge a release candidate merely because arithmetic or existing tests pass; acceptance claims must match the tested boundary.
- Update the unit registry and affected dossier/wiki pages together.
- Require enterprise-portal, canon, organization, brand, finance, reconciliation, generated-artifact, and public-safety checks as applicable.
- Retire merged, superseded, or duplicate branches only after unique content is recovered and the disposition is recorded.

## Generated-artifact policy

Generated databases and workbooks should not be committed repeatedly. CI or release publication must supply a manifest, checksums, source commit, schema version, scenario/run/seed, controlled build timestamp, validation report, safety report, and retention policy. Intentional static publications—such as a reviewed organization briefing—may be committed when accompanied by source builders and a manifest.

## Wiki synchronization

`docs/wiki/` is the reviewed source. The live GitHub Wiki is a derivative publication. Publish only from an accepted `main` commit through the manual workflow, then verify links and images. The wiki does not supersede versioned repository documents.
