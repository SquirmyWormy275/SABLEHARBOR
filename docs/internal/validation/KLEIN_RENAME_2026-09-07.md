# Klein rename and artwork — validation and delivery record

**Date:** September 7, 2026
**Base revision:** `498421e4e209880e167a6357ac92d9d9031c0791`
**Controlling decision:** [KLEIN-001](../../canon/KLEIN_NAME_AND_IDENTITY_2026-09-07.md)

## Change boundary

The owner-selected name Klein replaces the former fictional outpost name throughout the current reading of its history. The accepted horizontal PNG is copied exactly, indexed in the production inventory, and recorded in a dedicated visual manifest. The defective former-name PNG is removed from the current tree, with its old hash and commit recorded.

Naming successors preserve the finance-pinned corporate lore, decision register and organizational lineage. The September 6 Willow closeout, corporate record and finance model have renamed current files and compatibility pointers at the old paths. Organization, wiki and README navigation and the organization-chart generator use the current naming sources.

The [preserved source inventory](KLEIN_RENAME_PINNED_SOURCES.json) records all 16 finance source-lock paths present at the base revision. Their bytes remain unchanged. The separately pinned legacy calibration source exists only in its historical Git snapshot and is not materialized or rewritten by this change. Source-lock validation is unchanged.

Historical v0.2 documents, old changelog, prior organizational snapshots, legal screening citations and forensic reconciliation records remain historical. KLEIN-001 explicitly supersedes their old fictional outpost name. Existing financial values, legal entities, people, chronology, Willow and Emberline identities, publications and release archives are outside the change.

## Verification

- Governance/J2 validator: PASS.
- Institutional catalog validator: PASS; 84 controlled objects and 9 Pinakes portals.
- Organization-map validator: PASS; 9 charts and 162 source decision IDs.
- Repository hygiene: PASS, including JSON, links, historical checksums and source boundaries.
- Organization-chart regeneration: PASS; no drift on repeated generation.
- Approved logo source: PASS; exact bytes, SHA-256, dimensions and full PNG decode.
- All 71 current brand PNGs: PASS full decode; the prior defective file is absent.
- Production inventory: PASS; Klein source path and checksum match the dedicated visual manifest.
- Current lore, decision register, Willow closeout, corporate/finance records and lineage: PASS; no former-name references remain in their narrative text.
- All 16 present finance source-lock paths: PASS; byte-identical to the base commit. All 18 pinned historical blob entries resolve after fetching the legacy calibration commit.
- Public-repository content scan: PASS.
- Whitespace validation: PASS.
- Full Python suite: not claimed as locally passed. The first attempt lacked the pinned legacy calibration commit. After fetching that snapshot, a fresh run passed its first six tests but was interrupted after several minutes without further reported progress. The PR's finance CI runs the complete suite in its standard environment. No test or source-lock check was weakened.

## Remaining limits

The approved PNG is the only Klein artwork form. This delivery does not claim a vector master, newly issued controlled PDF, rebuilt historical package, or real-world name clearance.
