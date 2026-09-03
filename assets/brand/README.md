# Sable Harbor Logo System — v0.1.0

This directory contains individual, production-oriented logo assets for the Sable Harbor corporate identity, business lines, and approved internal identities in the August 31–September 2, 2026 narrative map.

## Controlling naming source

Business-line names and status are grounded in `docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md` and subsequent locked governance/organization decisions. Artwork files do **not** independently create or change canon. Legal-entity, reporting-line, and exact organizational details that remain OPEN in canon remain open here.

## File rule

- One logo per file.
- No contact sheets or composite logo boards are stored in the production logo directory.
- SVG is the production source of truth; PNG and office-document renders are convenience/generated forms where supplied.
- Reverse variants use a dark background; all other raster convenience variants preserve transparency.

## Canonical 2026 business-line set

| Identity | Classification | Variants |
|---|---|---:|
| Sable Harbor | corporate master brand | 5 |
| Foundry Field | core business line | 5 |
| Willow | core business line | 5 |
| Atlas Meridian | core business line | 5 |
| Pale Sun | core operating business line | 5 |
| Project Cradle | core business line | 5 |
| American Resource Utility | distinct operating company and core line | 5 |
| Advisory | core business line | 5 |

The seven business lines are **Foundry Field, Willow, Atlas Meridian, Pale Sun, Project Cradle, American Resource Utility, and Advisory**. Sable Harbor is the corporate master brand.

## Supplemental and internal identities

| Identity | Classification | Canon note |
|---|---|---|
| Foundry | product substrate | LOCKED distinction: Foundry is the substrate; Foundry Field is the deployable operational product/service configuration. |
| Red Wash Mine | operating asset | LOCKED fictional mine name under Pale Sun; transaction and legal details remain OPEN. |
| Blood, Sweat & Tears Railway | ARU operating component | LOCKED name and relationship to ARU. |
| Emberline | historical business line | LOCKED historical status: active through 2025, then absorbed into enduring 2026 work. |
| Red Wash / Pale Sun | endorsed operating lockup | Supplemental endorsed lockup joining the Pale Sun line to its Red Wash operating asset. |
| J2 — Judgment & Junction | internal enterprise directorate identity | LOCKED September 2, 2026. Approved production assets are `j2__mark.svg` and `j2__primary-horizontal.svg`; J2 is not a separate legal entity or customer-facing business line. |

## Naming convention

`<brand-slug>__<variant>.<format>`

Examples:

- `sable-harbor__primary-horizontal.svg`
- `atlas-meridian__mark.png`
- `american-resource-utility__reverse-horizontal.svg`
- `j2__mark.svg`
- `j2__primary-horizontal.svg`

## Intended use

- **Primary horizontal:** README headings, wiki section headers, reports, and letterheads.
- **Stacked:** covers, title pages, square placements, and presentation dividers.
- **Mark:** favicons, avatars, small section identifiers, org charts, and document furniture.
- **Reverse horizontal:** dark interfaces, dark presentation fields, signage, and video.
- **One-color horizontal:** monochrome printing, stamps, engraving, and constrained reproduction.

J2 currently has two explicitly approved production forms: mark and primary horizontal. Do not manufacture additional J2 variants without an identity decision.

## Production constraints

- Do not distort, rotate, bevel, shadow, or add gradients.
- Do not combine two separate identities into one lockup unless an endorsed combined asset is provided here.
- Do not substitute literal lighthouse, compass, shield, wave, mountain, mine-pick, generic intelligence, military, target, eye, brain, or AI/circuit clip art.
- Preserve appropriate clear space around the full lockup.
- Use the SVG files as the source of truth; raster files are convenience renders.

## J2 stationery

Approved J2 stationery is maintained under:

- `assets/brand/collateral/letterhead/j2/j2-letterhead-us-letter.svg`
- `assets/brand/collateral/letterhead/j2/j2-letterhead-a4.svg`

The controlling identity/stationery record is `docs/organization/J2_IDENTITY_AND_STATIONERY.md`.

## Package

Generated collateral packages may be produced under `assets/brand/packages/`.

## Manifest and validation

- `manifest.json` records production brand assets where the current generator has populated them.
- `VALIDATION.md` records automated checks for the established brand system.
- Newly approved identities should be added to deterministic manifest/validation tooling as that tooling is extended; approval does not depend on silently altering historical manifests.

All rights reserved unless a specific repository file states otherwise.
