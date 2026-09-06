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
| Emberline | 3 | 3 | 3 |
| Red Wash / Pale Sun | 3 | 3 | 3 |

## Notes

The QA contact sheet used during generation is intentionally excluded from `assets/brand/logos/` and from the GitHub production package. It is not a production logo asset.
