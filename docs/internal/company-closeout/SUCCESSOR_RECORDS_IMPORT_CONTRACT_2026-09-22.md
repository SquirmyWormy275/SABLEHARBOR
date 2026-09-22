# Current successor records — enterprise import contract

**Contract:** SH-SUCCESSOR-RECORDS-2026-09-22 v1.0.0. Reviewable implementation; repository acceptance and release packaging remain separate. This extends the existing enterprise CSV/SQLite distributions, not a new company database. Frozen v1.0.0, predecessor schema and scope bytes remain unchanged.

## Explicit populations

| Table | Complete declared population | Rows |
|---|---|---:|
| successor_j2_administration | Six accepted leaders and four existing anonymous current-office incumbencies | 10 |
| successor_orientation_commissions | All 18 occupied Orientation positions, including retained admission failures | 18 |
| successor_debt_payoff | Existing ARU term/revolver principal payoff allocation | 2 |
| successor_asset_screen | Seven original asset-source classes; review of ownership assertions, not a new asset book | 149 |
| successor_finance_source_inventory | Selected secretary source inventory; no universal historical side-letter absence claim | 7 |
| successor_capital_rights | Two prospective investor designation schedules with full policy and existing board IDs | 2 |
| successor_capital_assents | Five synthetic existing-holder assents | 5 |
| successor_host_instruments | Two prospective Cradle host frameworks with common terms | 2 |
| successor_host_orders | Accepted work orders; none currently accepted | 0 |
| successor_debt_instruments | Approved ARU-only secured successor, including reporting/notice obligations and source limits | 1 |
| successor_debt_collateral | Exact identified limited grant population; no blanket lien | 64 |
| **Total** | **Versioned administrative/right/qualification records** | **260** |

The asset-screen population retains the original source-owner descriptions: ARU, BST and RWH where explicit; UNRESOLVED where no legal owner was established; EXTERNAL for the source-described crossing arrangement. A screening inference never becomes an ARU title finding. The separate 64-row prospective grant contains the authored current ownership confirmations and its own filing/perfection/priority states. The source-screen rows are the review of those predecessor source assertions, not a statement contradicting the scoped later confirmation. Seven context-only facilities and 78 exclusions remain in the secured-instrument payload.

Existing payoff allocations are preserved historical modeled cash events, not new cash postings. Every envelope's `additional_cash_usd` is zero; that field does not mean the underlying historical principal was zero. The instrument's first reporting obligation remains future due, and unsubmitted filings, unknown priority/perfection and unreleased old liens remain visible. Capital rights retain replacement/eligibility-loss rules and all five assents without new units, money or automatic director changes. Host eligibility starts October 1; no work order, current access, new revenue or settlement is invented.

## Row contract and joins

Each row has a stable `record_id`, `record_type`, legal `entity`, reporting `unit`, effective dates/precision, actual `available_at` and `recorded_at`, authored day, fact origin/state, blank scenario for these nonscenario successor records, primary source path/hash, complete provider source-hash JSON, source commit, publication/acceptance status, and canonical `payload_json`.

Payloads retain native IDs and exact primitive types. Join administrative and commission records to people by `person_id` and positions by `position_id`; payoff records to native principal by component/source reference; asset screens and grants by `asset_id`; rights/assents to the five-holder register by `holder_id`; hosts to site and instrument IDs. Never join anonymous people by display name or equate an administrative asset review date with original in-service date. Related source IDs in nested payloads are not duplicate financial postings.

J2 and holding-company governance populations stay in the parent enterprise package under CORPORATE/SHI. ARU/BST-related records route to the existing american-resource-utility extract, the explicit RWH asset-source row to pale-sun, and host frameworks to project-cradle. Unknown ownership stays explicit. No new grants, classification permissions or routes are inferred from rows.

## Integration API

`enterprise.closeout.successor_records.collect(context=None)` returns the eleven tables, revalidates native providers/source hashes and declared populations, and creates no files or journal entries. `contracts()` returns `(schema, scope)` combining the exact pinned predecessor contracts with `enterprise/closeout/source/successor_export_extension.json`. It refuses collisions and altered predecessor bytes.

The integration-owned export builder adds these tables only after checking for name collisions, obtains the combined contracts, and calls the existing `enterprise.operations.exports.write_packages(..., schema=schema, scope=scope)` explicit-contract path. Existing CSV encoding, spreadsheet escaping, SQLite creation/verification, per-unit extraction, manifests and checksums remain the shared publication mechanism. No global schema monkeypatch or competing database is used. `validate_tables(new_tables, context=None)` independently re-reads the providers and compares every identity, route, payload and availability against current source.

## As-of and known-on

`visible(tables, effective_on='YYYY-MM-DD', known_on='<timezone-aware ISO timestamp>')` applies separate effective and knowledge boundaries, including exclusive commission expiry. It never returns dirty-preview records. New historical January appointments/2021 commissions cannot appear as known before their September source publication. Host frameworks remain future-effective even after their source becomes available. This is a record-state query, not permission to treat an old payoff event as a current cash balance or a future framework as active access.

Availability is the later of the source HEAD commit and explicit authoring timestamp/day. Accepted-release authority is established by the composite release receipt; source `PENDING_REPOSITORY_ACCEPTANCE` labels are preserved rather than rewritten by a reporting generator. A new frozen edition must actually consume these tables before readers can claim it contains them.

## Validation and reproduction

Run `python -m pytest -q tests/closeout/test_successor_records.py`. **14 tests passed**, including entire-table/member omission, duplicate collateral, entity swaps, missing zero-population declaration, stale payload/hash, earlier known-on promotion, prohibited cash addition, exclusive expiry, future framework timing and dirty-preview denial. Real shared CSV/SQLite writers reimport all 260 rows with exact payload strings, and predecessor contract entries remain identical. Ruff and `git diff --check` passed. The first integration run correctly rejected a host-proposal pin mismatch; the integration owner's reviewed correction `898a8026` resolved it without weakening the source check.

This contract adds no accounting journal or cash, no real-world filing/authorization and no professional audit conclusion. It is the explicit import interface for the bounded new records, preserving their substantive source qualifications.
