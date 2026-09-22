# Final company records — enterprise import contract

**Contract:** SH-FINAL-RECORDS-20260922 v1.0.0  
**Target edition:** 1.2.0, pending accepted source, final validation and publication. This contract extends the existing enterprise CSV/SQLite distribution. It creates no second database and does not modify frozen predecessor schema or edition bytes.

## Exact table populations

The original **98 tables** remain unchanged in scope. The eleven v1.1 successor tables retain their **260 rows**, including the explicitly empty host-order table; see the [predecessor contract](SUCCESSOR_RECORDS_IMPORT_CONTRACT_2026-09-22.md). Their original source assertions remain historical evidence even where later administrative records advance a state.

| New table | Complete declared population | Rows |
|---|---|---:|
| final_personnel_profiles | Existing ten J2 leaders/current-office incumbents; six preserved and four newly supplied names, bounded career/qualification histories | 10 |
| final_completed_people | Complete August 2026 employee/person-position master with scoped profile name/title/hire-year joins | 702 |
| final_information_policy_classes | Explicit source-defined information record classes | 7 |
| final_information_policy_subjects | Policy subject census referencing the same 702 August persons; no implied entitlement or current active-employment assertion | 702 |
| final_debt_asset_identifiers | Identified assets corresponding to the existing 64-asset limited grant | 64 |
| final_debt_fixture_sites | Two expressly scoped fixture sites | 2 |
| final_debt_filings | Three authored synthetic filing/acknowledgement records | 3 |
| final_debt_payoff_releases | Two later authored release records linked to original payoff components | 2 |
| final_advisory_carry_disposition | One sponsored-plan record, zero participants and zero issued units | 1 |
| **New total** | **Nine tables** | **1,493** |
| **Wrapper total** | **Eleven preserved plus nine new tables** | **1,753** |

The full explicit enterprise contract therefore has **118 tables**. The 1,753-row figure concerns only the wrapper populations, not the number of financial/operating rows in the original 98 tables or the number of files in a composed release. Per-unit packages use the existing declared routing rules; their row counts are not additional company populations.

## IDs, joins and effects

Every row uses the existing successor envelope: stable `record_id`, `record_type`, legal `entity`, reporting `unit`, effective dates/precision, `available_at`, `recorded_at`, authored day, fact state/origin, scenario, source path/hash, provider source-hash JSON, source commit, publication/acceptance status, canonical `payload_json` and `additional_cash_usd`.

Join personnel by `person_id`, then `position_id` and source role/office/commission IDs. Names are display attributes, never identity keys. The four newly supplied names belong to existing employees: Miriam Solano, Owen Faraday, Nadia Ivers and Leila Soren. Other unnamed personnel retain stable fictional identifiers; the complete census does not require 702 biographies. The personnel overlay changes only supported name, title and original-hire-year fields. Salary, employer, FTE, person count, position identity and payroll postings remain unchanged. A year-precision company joining date is not an exact appointment or commission date.

Policy subjects reference the personnel population and policy document ID. Inclusion creates **zero implicit grants** and does not assert an authenticated principal, current employment or runtime enforcement. Record classes preserve their native source rules and retention terms. Route membership is publication scope, not authorization; do not infer permissions from entity, business unit, seniority or possession of an exported row.

Join legal asset identifiers by `asset_id` to the original limited grant; fixture sites by native site/facility references; filings by their native filing/asset/scope references; releases by `payoff_component_id`. The three filing payloads may reference the same $250 administrative cost allocation. That is one component within existing ARU operating expense/provider advance, **not three costs and not new cash**. The sponsored plan preserves zero awards/participants, excluded equity/control rights and no new financial posting. All wrapper envelope `additional_cash_usd` values are zero; historical principal or existing expense referenced inside payloads is not zero and must not be reposted.

## Time, provenance and state

The complete-person master represents August and has exclusive `effective_to=2026-09-01`. It is not a September active headcount: separately dated exit and access events remain authoritative for later state. Profiles can describe earlier historical careers while their knowledge boundary remains September authoring/source availability.

Known-on availability is the later of the actual source commit and explicit authored timestamp/day. A provider authored at 18:35 or 18:38:42 UTC cannot become available at midnight merely because its document is dated September 22. Personnel payloads also carry the actual source floor, preventing a direct nested query from using older source availability. Dirty working-copy previews are nonpublishable and excluded from `visible(...)`; the personnel provider does not expose its new name joins through that dirty-preview path.

Call `visible(tables, effective_on='YYYY-MM-DD', known_on='<timezone-aware timestamp>')` for the envelope's effective and knowledge boundaries. Legal payloads retain precise event timestamps and provider as-of states. A day-precision envelope alone does not prove an intraday filing acknowledgement or release had occurred: compare the payload timestamp or call the native `debt_administration.build(context=..., as_of=...)` for that event boundary. Receipt, effectiveness, search scope, perfection and priority are distinct assertions. The earlier unsubmitted/unreleased grant population is retained; later evidence does not rewrite what was known earlier.

Primary source paths and SHA-256 values identify exact bytes. Nested source-hash JSON preserves the providers' source chain. Hash integrity is not proof of truth or completeness: population guards and substantive source validators supply separate evidence. Authored synthetic execution/agency records are not real third-party confirmation. `PENDING_REPOSITORY_ACCEPTANCE` labels inside frozen source payloads are not silently rewritten; the final accepted-source release receipt supplies actual acceptance authority and scope.

## Integration and reproducibility

The wrapper `enterprise.closeout.final_records` exposes:

- `collect(context=None)`: return all twenty added-table populations, using the previous successor adapter and native personnel, policy, debt-administration and Advisory providers.
- `contracts()`: return `(schema, scope)` using the unchanged predecessor contracts, preserved successor extension and explicit `enterprise/closeout/source/final_export_extension.json`; reject collisions and changed predecessor pins.
- `validate_tables(tables, context=None)`: require the exact table and member populations, unique IDs, explicit routes, source hashes, payloads, known-on state and zero added cash.
- `visible(...)`: apply effective/known-on boundaries and deny dirty-preview records, subject to the intraday payload qualification above.

The integration-owned finance export builder checks collisions, adds these rows to the native 98 populations, and calls the existing `enterprise.operations.exports.write_packages(..., schema=schema, scope=scope)`. Shared CSV encoding, canonical JSON strings, SQLite import/verification, manifest/checksum production and seven-unit routing remain in force. CORPORATE/SHI maps to the composite coverage label `corporate`; this does not authorize arbitrary case-insensitive joins. No routes are inferred dynamically from incoming records.

Run the final-wrapper tests and native provider tests in the supported dependency environment. Meaningful guards include omitted/duplicate employee, stale profile payload or earlier known-on, wrong entity, unchanged original schema/tables, new-name joins without pay changes, legal event authoring floors, exact legal populations and actual SQLite reopen verification. Run the standard independent import and composite financial/operating reperformance on the **final accepted derivative**, not solely on a small fixture. The release receipt must provide exact commands/results, source commit, version and artifact hashes. These docs supply the import contract; they do not claim a final accepted v1.2 test run or published package.
