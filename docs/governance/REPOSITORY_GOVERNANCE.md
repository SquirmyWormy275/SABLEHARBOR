# Repository governance

## Source hierarchy

1. `docs/canon/` and its decision register control accepted corporate facts.
2. `docs/governance/` controls publication, repository, and audit rules.
3. `config/` contains explicit model/scenario inputs and machine-readable registries; it does not independently canonize them.
4. `src/`, `db/`, and `tests/` implement and validate systems against those boundaries.
5. `docs/company/`, `docs/business-lines/`, and `docs/wiki/` are navigation/publication layers. They summarize and link; they do not create canon.
6. Generated databases, workbooks, CSVs, and release bundles are evidence artifacts, not source-of-truth documents.

## Normalized locations

- corporate and unit logos: `assets/brand/logos/`;
- letterhead/templates: `assets/brand/collateral/`;
- organization source and renders: `docs/organization/`;
- business-line dossier pages: `docs/business-lines/`;
- enterprise finance documentation: `docs/finance/`;
- SQL queries and migrations: `db/`;
- unit registry: `config/enterprise/business_units.json`;
- wiki source: `docs/wiki/`;
- generated outputs: ignored `var/`, `workbooks/outputs/`, `reports/`, `data/generated/`, and `releases/generated/` paths.

Do not duplicate a logo, chart, database, or workbook inside every business-line folder. Dossiers should link to normalized source assets; generated unit bundles should be immutable artifacts identified by a generation run.

## Change control

- Use a dedicated branch and pull request for every material workstream.
- State whether each changed fact is LOCKED, PROVISIONAL, OPEN, SUPERSEDED, MODEL_PROPOSED, SCENARIO_INPUT, SYNTHETIC_INSTANCE, or DERIVED.
- Never merge a release-candidate implementation merely because arithmetic/tests pass; acceptance claims must match the tested boundary.
- Update the unit registry and affected dossier/wiki pages together.
- Require enterprise-structure, canon, organization, brand, finance, and public-safety checks as applicable.
- Delete merged/superseded branches after unique content is recovered and the audit trail records the disposition.

## Generated-artifact policy

Generated databases and workbooks should not be committed repeatedly. CI/release publication must supply a manifest, checksums, source commit, schema version, scenario/run/seed, validation report, and retention policy. Intentional static publications—such as a reviewed organization briefing—may be committed when accompanied by source builders and a manifest.

## Wiki synchronization

`docs/wiki/` is the reviewed source. The live GitHub Wiki is a derivative publication. Publish only from an accepted default-branch commit using the manual workflow, then verify links and images. The wiki does not supersede versioned repository documents.
