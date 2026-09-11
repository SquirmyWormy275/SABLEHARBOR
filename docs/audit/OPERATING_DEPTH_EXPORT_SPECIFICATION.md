# Operating-depth evidence export specification

**Document ID:** `SH-AUDIT-OPERATIONS-001`
**Version:** 1.0.0
**As of:** September 9, 2026
**State:** SYNTHETIC RELEASE CONTRACT
**Owner:** Finance release owner / business records stewards

## Package and identities

`business-operations-v1.0.0` is a separately versioned successor. Its ZIP includes
enterprise books, seven unit CSV/SQLite packages, source/financial bridges, operating
histories, executed client handovers, control exercises and a reviewed workbook.
Every release records the clean source revision, model input fingerprint, source-file
hashes, legacy-generation identity and explicit synthetic/calibration period role.

The seven package keys are `foundry-field`, `atlas-meridian`, `advisory`, `willow`,
`project-cradle`, `pale-sun` and `american-resource-utility`. Corporate and shared
Treasury/control populations remain available in the parent distribution.
Original physical measurement units are retained separately from reporting-unit keys.

## Fail-closed population contract

Reviewed source JSON declares every approved table and column, allowed scope values
and unit/entity routing combination. Normal builds fail on new columns/tables,
missing required scope, unexpected fact states or invalid reporting relationships.
Only development mode can propose changes; proposed rules cannot publish a release.

SQLite exports contain reporting tables only. Integrity, exact table/column lists,
source row order and every serialized cell are verified. Seven unit packages are
explicit subsets of the validated parent population. CSV text is neutralized where
it could be interpreted as an untrusted spreadsheet formula; numeric values remain
usable. Source hashes and financial records retain provenance and timing.

## Client and authority boundary

Client handovers are a separate allowlisted surface: generated workflow, executable
tests, runbook, agreed scope, dependency/rights evidence, manifest and test results.
The verifier rejects missing or extra files, modified bytes, wrong client/matter
identity, missing proof and failed execution. This does not grant access to employee
Pinakes, Collection sources, other clients or private evaluation material.

Synthetic export clearance is not production IAM. Source-owner authorization,
tenant/client purpose, retention, legal holds and real deployment controls remain
governed by their existing decision records and unresolved implementation issues.

## Workbook and complete-artifact acceptance

The controlled six-sheet workbook presents regenerated financial source data,
cash-obligation and ARR bridges, control outcomes and forecast attribution.
The report-year selector recalculates its summary. All source cells, exact summary
formula ranges, cached results and reconciliation formulas are independently checked
against regenerated data. A stale input identity or changed workbook digest fails.
No external links, macros or formula errors are accepted.

After the final workbook, client packages and reports are present, the complete
output is scanned for credential markers, workstation paths, PII-shaped values,
private evaluation field names, CSV injection, embedded objects and external links.
This technical check complements the strict population contract; it does not prove
production authorization or control effectiveness.

Every file, including nested manifests and checksum files, is covered by a parent
manifest and SHA-256 list. Sorted archive paths, fixed timestamps and normalized
modes support byte reproduction from the same clean revision. CI rebuilds twice,
compares the ZIP digest and publishes only the exact checked main-run artifact.
Existing release tags and assets must never be replaced with different bytes.

Control FAIL/NOT_RUN outcomes, unpaid requests, infeasible schedules and unapproved
operating authority stay visible. Passing software integrity is not an assertion
that these business conditions are resolved.

Implementation: [operating successor](../../enterprise/operations/README.md).
Financial boundary: [successor design](../finance/OPERATING_DEPTH_SUCCESSOR_2026-09-09.md).
