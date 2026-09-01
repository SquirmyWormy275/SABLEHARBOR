# Sable Harbor Logo System — v0.1.0

This directory contains individual, production-oriented logo assets for the Sable Harbor corporate identity and each business line in the August 31, 2026 narrative map.

## Controlling naming source

Business-line names and status are grounded in `docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`. These artwork files do **not** independently create or change canon. Legal-entity, reporting-line, and exact organizational details that remain OPEN in canon remain open here.

## File rule

- One logo per file.
- No contact sheets or composite logo boards are stored in the production logo directory.
- Every production asset is supplied as self-contained SVG with outlined lettering and as a rendered PNG.
- Reverse variants use a dark background; all other PNG variants preserve transparency.

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

## Supplemental identities

| Identity | Classification | Canon note |
|---|---|---|
| Foundry | product substrate | LOCKED distinction: Foundry is the substrate; Foundry Field is the deployable operational product/service configuration. |
| Red Wash Mine | operating asset | LOCKED fictional mine name under Pale Sun; transaction and legal details remain OPEN. |
| Blood, Sweat & Tears Railway | ARU operating component | LOCKED name and relationship to ARU; exact legal and route details remain OPEN. |
| Emberline | historical business line | LOCKED historical status: active through 2025, then absorbed into enduring 2026 work. |
| Red Wash / Pale Sun | endorsed operating lockup | Supplemental endorsed lockup joining the Pale Sun line to its Red Wash operating asset; does not replace either canonical name. |

## Naming convention

`<brand-slug>__<variant>.<format>`

Examples:

- `sable-harbor__primary-horizontal.svg`
- `atlas-meridian__mark.png`
- `american-resource-utility__reverse-horizontal.svg`

## Intended use

- **Primary horizontal:** README headings, wiki section headers, reports, and letterheads.
- **Stacked:** covers, title pages, square placements, and presentation dividers.
- **Mark:** favicons, avatars, small section identifiers, and document furniture.
- **Reverse horizontal:** dark interfaces, dark presentation fields, signage, and video.
- **One-color horizontal:** monochrome printing, stamps, engraving, and constrained reproduction.

## Production constraints

- Do not distort, rotate, bevel, shadow, or add gradients.
- Do not combine two separate identities into one lockup unless an endorsed combined asset is provided here.
- Do not substitute literal lighthouse, compass, shield, wave, mountain, mine-pick, or generic AI/circuit clip art.
- Preserve clear space equal to at least one central accent square around the full lockup.
- Use the SVG files as the source of truth; PNG files are convenience renders.

## Package

A ZIP archive containing the complete individual SVG and PNG set is generated under `assets/brand/packages/`.

## Manifest and validation

- `manifest.json` records every asset, dimensions, variant, classification, and SHA-256 digest.
- `VALIDATION.md` records automated checks proving the one-logo-per-file rule and per-line variant coverage.

All rights reserved unless a specific repository file states otherwise.
