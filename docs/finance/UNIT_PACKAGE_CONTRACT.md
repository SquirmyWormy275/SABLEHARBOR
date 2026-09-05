# Finance unit-package contract

**Status:** MODEL_PROPOSED release-candidate contract

Unit packages are deterministic, read-only slices of an explicitly selected completed enterprise
generation run. They do not establish legal entities, operating divisions, canon, audited results,
or independent auditability.

Each package records its generation run, included common-actual run, profile, scenario, seed,
source commit, controlling-canon reference, entity/segment/site filters, row counts, reconciliation,
artifact-safety result, manifest, and SHA-256 inventory. It contains scoped journal evidence, trial
balance and statement extracts, source lineage, relevant operational registers, a SQLite evidence
database, and a workbook.

The generator must fail for incomplete runs, mixed incompatible run contexts, out-of-scope entity
data, an unbalanced package, or a failed recursive safety scan. The scope map is versioned at
`config/finance/unit_scopes.json`; its legal-entity, segment, and site assignments remain finance
model assumptions wherever current canon leaves those structures open.
