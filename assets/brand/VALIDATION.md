# Logo Package Validation

**Result:** PASS

Automated validation completed against the generated identity assets and current
repository source-art overlays. The historical archive is separately quarantined
below and is not a current distribution candidate.

## Required conditions

- Corporate master brand variants: **5**.
- Canonical business lines checked: **7**.
- Each canonical business line has at least three distinct variants: **PASS**.
- Exactly one identity/lockup is rendered in each production file: **PASS**.
- SVG text elements remaining: **0**; all lettering is outlined: **PASS**.
- Every SVG has a matching PNG convenience render: **PASS**.
- Production directory contains no composite sheets: **PASS**.

## Approved J2 identity

- Controlling primary-horizontal PNG is byte-identical to the approved source: **PASS** (`SHA-256 9ee44d72f7cf52474d10ab37662c4690e56a01b6d621a52d26ec22bbd0a7a1e2`).
- Controlling mark PNG is byte-identical to the approved source: **PASS** (`SHA-256 383f2f27108a8379171a220517a8c2e6c834cd82f821fc72d6d4f0566efe5af9`).
- Both approved PNGs decode as RGB PNG files at their recorded dimensions: **PASS**.
- Current package boundary contains no dedicated J2 letterhead or J2 stationery manifest: **PASS**.
- Logo, approved-raster, and package-state manifests parse as JSON: **PASS**.
- Exploratory J2 concepts are designated historical only: **PASS**.

## Approved Pale Sun / Red Wash raster sources

- Manifest identity and approval state: **PASS**.
- Exact path, byte count, dimensions, and SHA-256 for all four sources: **PASS**.
- Pale Sun working letterhead references the approved canonical PNG, not the legacy SVG: **PASS**.

| Controlled source | SHA-256 |
|---|---|
| `assets/brand/logos/pale_sun__canonical.png` | `eedcabfca73460e8ff5ad72864c9f669ba2375097b05daa2912f30c9ff35c025` |
| `assets/brand/logos/red_wash__canonical.png` | `7c26b8afd7954045d9dd4b5c691ba820cdce2e3ccb8e41ac6873b103f0c59720` |
| `assets/brand/maps/red_wash__site_overview.png` | `8dbb0053c4a563d57d5a24be4f4687dc11e2e00e2b1e62c279d9be945f68d77a` |
| `assets/brand/maps/red_wash__underground_plan.png` | `0658de3b7c63ecc9757b545f29895eab51801b2148cb3862935620b6049a7dda` |

## Historical archive quarantine

- `sable-harbor-logo-system-v0.1.0.zip` hash matches its package record: **PASS**.
- Archive state is `SUPERSEDED` / `HISTORICAL_SNAPSHOT` / `DO_NOT_DISTRIBUTE`, effective only through September 2, 2026: **PASS**.
- The record discloses that the archive predates the September 5 approved raster sources and contains no-longer-current J2 stationery: **PASS**.

## Coverage

| Identity | SVG files | PNG files | Variant count |
|---|---:|---:|---:|
| Sable Harbor | 5 | 5 | 5 |
| Foundry Field | 5 | 5 | 5 |
| Willow | 5 | 5 | 5 |
| Atlas Meridian | 5 | 5 | 5 |
| Pale Sun | 5 | 5 | 5 |
| Project Cradle | 5 | 5 | 5 |
| American Resource Utility | 5 | 5 | 5 |
| Advisory | 5 | 5 | 5 |
| Foundry | 3 | 3 | 3 |
| Red Wash Mine | 3 | 3 | 3 |
| Blood, Sweat & Tears Railway | 3 | 3 | 3 |
| Emberline | 0 | 1 | 1 |
| Red Wash / Pale Sun | 3 | 3 | 3 |

## Notes

The QA contact sheet used during generation is intentionally excluded from `assets/brand/logos/` and from the GitHub production package. It is not a production logo asset.

## September 7 Emberline source approval

- Exact owner-selected image copied to `logos/emberline__primary-horizontal.png`; 2172 × 724 RGB pixels, 939,954 bytes.
- SHA-256: `ddf4273bca6f9e0c9b050a1fc741b151550b86af5e2d2a98c46fdadfaf849312`.
- PNG structural verification and full pixel decode: PASS.
- Selected-output comparison: PASS, byte-for-byte; no recompression or background removal.
- All six prior Emberline SVG/PNG sources: PASS, preserved with their original SHA-256 in `history/emberline/2026-09-07/manifest.json` and excluded from the current production inventory.
- Current Emberline production entry: one approved horizontal PNG. The generic requirement that each SVG has a convenience PNG remains applicable to the retained vector system; it does not require inventing a vector source for this approved raster override.
- Historical brand distribution ZIP and all prior release/source-lock files remain unchanged.

The integration PR records the repository validation and full CI results before merge. The [controlling decision](../../docs/canon/EMBERLINE_VISUAL_IDENTITY_2026-09-07.md) defines the approval and supersession scope.

## September 7 Kelly Gang Mining source approval

- Exact selected-output comparison, PNG structural verification and full pixel decode: PASS.
- Approved source: `logos/kelly-gang-mining__stacked.png`, 1254 × 1254 RGB pixels, 1,509,892 bytes.
- SHA-256: `2b6958413abe5989120a5ed9b85480750cb385a397cb8228fa871f1a392f22e6`.
- One approved stacked form is recorded in the production inventory and [dedicated manifest](kelly_gang_mining_visual_manifest.json).
- Kelly Gang Mining remains an external host operator. Its addition does not change the seven-current-business-line set.
- Earlier approved source art, finance inputs and historical archives remain byte-preserved.

The integration PR records canon, catalog, organization, hygiene, public-content and full CI checks before merge.

## September 7 Quality Forest Communications source approval

- Exact selected-output comparison, PNG structural verification and full pixel decode: PASS.
- Approved source: `logos/quality-forest-communications__primary-horizontal.png`, 1821 × 864 RGB pixels, 1,099,423 bytes.
- SHA-256: `d72708de214894d0184cc0c1211bcb99647c5df6bbf61a2323d668451f91060d`.
- One approved horizontal form is recorded in the production inventory and [dedicated manifest](quality_forest_communications_visual_manifest.json).
- The radio and both protective handles fit within the yellow Q; the selected tree antenna depicts the classic 2055 SATCOM form.
- QFC remains a historical external company; the seven-current-business-line set is unchanged.
- Earlier approved artwork, finance inputs and historical archives remain byte-preserved.

The integration PR records canon, catalog, organization, hygiene, public-content and full CI checks before merge.

## September 7 Demotte Reclamation Services source approval

- PNG structural verification, full pixel decode and exact generated-source comparison: PASS.
- Source: `logos/demotte-reclamation-services__primary-horizontal.png`, 2079 × 756 RGB pixels, 881,116 bytes.
- SHA-256: `cb5bdbc6cb950dac198312222eb47659547ae6a30994c90dff514b0707cfd15f`.
- The production manifest contains one complete horizontal form, classified as an external host identity.
- QFC remains Quality Forest Communications and uses its exact selected yellow-Q/117G/2055 PNG, SHA-256 `d72708de214894d0184cc0c1211bcb99647c5df6bbf61a2323d668451f91060d`.
- The rejected Demotte Communications/tree-D image is absent from the repository.
- Finance-pinned source files, historical archives and prior approved artwork are byte-preserved.

The integration PR records focused checks and the required full CI results before merge.

The owner explicitly approved the final blue-and-white Demotte revision for locking and repository delivery after viewing it.
