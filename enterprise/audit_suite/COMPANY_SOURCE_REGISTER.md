# Selected-source ownership and migration register

`company_source_register.py` is a trusted local read-only operator. It produces a
private register for explicitly selected portfolio profiles, their pinned historical
inventories, a documentary custody migration, and an accepted finance reference.
It does not import sources, change grants, repair company facts, or initialize audits.

Run the maintained CLI with absolute private paths:

```sh
.venv/bin/python tools/audit_suite/company_source_register.py \
  --config /private/register/CONFIG.json \
  --output /private/register/run-v1
```

The output must be new, outside every selected source tree and canonical documentation.
Source databases must be private, ordinary files without aliases, hard links or active
SQLite sidecars. Reads use an explicit read-only transaction. Source changes during
capture or before publication reject the report; retry with a new destination after
obtaining a stable capture interval. Separate stores are not globally atomic.

The input schema is `COMPANY_SOURCE_REGISTER_INPUT_V1`, with exactly these fields:

- `profiles`: one to four objects with `id`, `profile_id`, `registry`, `inventory`, and
  `component_domains`. Both file selections are `{path, sha256}`. Every selected registry
  component has one explicit domain: `identity_hr`, `tickets_changes`,
  `infrastructure_security`, `incidents`, `vendors`, `governance_risk`, `continuity`,
  `training`, `documentary_cross_domain`, or `finance_reference`. This mapping is an
  operator declaration, not a business fact inferred from filenames.
- `migration`: pinned `plan` and `receipt`, plus the exact `legacy_root` containing the
  original artifact bytes. The operator reads the listed originals, never hidden worlds.
- `finance`: pinned `acceptance` and `source_lock` JSON files. Accepted packet files must
  still match their recorded bytes. Historical controlling files are read with local
  `git show` at the locked immutable commit, separately from current file hashes. Missing
  local historical Git objects remain unresolved; the tool never fetches or rewrites them.
- `previous`: `null` for the first register, otherwise the prior manifest `{path, sha256}`.
  Its members are verified, the register version increments, and the successor retains
  the predecessor manifest pin. Prior files remain unchanged.

The package contains the exact input `CONFIG.json`, `DOMAIN_MAP.json`,
`MIGRATION_REGISTER.json`, `FINANCE_REFERENCES.json`, `INPUT_PINS.json`, `VALIDATION.json`
and a pinned `MANIFEST.json`. Implementation and supporting helper hashes are retained.

The historical inventory establishes the explicit selection, not current source
integrity. Each selected native company/branch/system/record/version/hash, original
content, event date, availability and origin is checked against the current physical
store. Unexpected missing or changed originals fail. Additional current versions are
reported outside the historical selection, without silently expanding coverage.
Current database pins also retain the exact metadata and access-journal capture.

Current system owner registration, historical inventory control assignments, and
provisional documentary custody are separate fields. Unknown business dates and
historical ownership remain unknown. Native relationships retain their declared full
identity and producer labels; equal bytes or similar names never merge physical stores,
companies or branches. Shared documentary references across profiles count once as a
physical version and separately as profile references.

The per-document reconciliation records exact legacy-to-company copies and explicit
unresolved dispositions. It does not infer document business meaning, reconstruct
operating history, accept proposed appointments, or make a professional sufficiency
judgment. New standalone runtime operations enter only through a new explicit inventory
selection. Accepted synthetic finance bytes are references only; packet acceptance does
not establish an executed invoice, signature, corroboration or approved forecast.

Validation: `tests/audit_suite/test_company_source_register.py` uses neutral real SQLite
stores and a local Git fixture to test preservation, exact native verification, extra
versions, unresolved historical ownership, source corruption, finance locks, private
boundaries, successor integrity and publication races.
