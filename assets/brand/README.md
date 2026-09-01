# Sable Harbor identity and collateral system

This directory is the normalized source for Sable Harbor corporate and business-line identity assets. Logos are production assets accepted on `main`; recovered collateral and the business-line letterhead layer are production-oriented candidates on the integration branch.

> Artwork does not create canon. Business-line names, status, ownership, legal entities, reporting lines, addresses, and operating facts remain governed by `docs/canon/` and the decision register.

## Navigate

- [Enterprise dossier](../../docs/company/README.md)
- [Business-line control index](../../docs/business-lines/README.md)
- [Brand standards](BRAND_STANDARDS.md)
- [Font provenance](FONT_PROVENANCE.md)
- [Corporate and unit collateral](collateral/README.md)
- [Production manifest](manifest.json)
- [Validation record](VALIDATION.md)

## Current 2026 identity set

| Identity | Classification | Dossier | Letterhead |
|---|---|---|---|
| Sable Harbor | Corporate master brand | [Company](../../docs/company/README.md) | [Corporate collateral](collateral/README.md) |
| Foundry Field | Current core business line | [Dossier](../../docs/business-lines/FOUNDRY_FIELD.md) | [US Letter SVG](collateral/letterhead/business-lines/foundry-field-letterhead-us-letter.svg) |
| Willow | Current core business line | [Dossier](../../docs/business-lines/WILLOW.md) | [US Letter SVG](collateral/letterhead/business-lines/willow-letterhead-us-letter.svg) |
| Atlas Meridian | Current core business line | [Dossier](../../docs/business-lines/ATLAS_MERIDIAN.md) | [US Letter SVG](collateral/letterhead/business-lines/atlas-meridian-letterhead-us-letter.svg) |
| Pale Sun | Current operating business line | [Dossier](../../docs/business-lines/PALE_SUN.md) | [US Letter SVG](collateral/letterhead/business-lines/pale-sun-letterhead-us-letter.svg) |
| Project Cradle | Current core business line | [Dossier](../../docs/business-lines/PROJECT_CRADLE.md) | [US Letter SVG](collateral/letterhead/business-lines/project-cradle-letterhead-us-letter.svg) |
| American Resource Utility | Distinct operating company and current core line | [Dossier](../../docs/business-lines/AMERICAN_RESOURCE_UTILITY.md) | [US Letter SVG](collateral/letterhead/business-lines/american-resource-utility-letterhead-us-letter.svg) |
| Advisory | Emerging current business line | [Dossier](../../docs/business-lines/ADVISORY.md) | [US Letter SVG](collateral/letterhead/business-lines/advisory-letterhead-us-letter.svg) |

## Production logo files

`assets/brand/logos/` follows the rule **one logo per file**. Each production lockup is supplied as self-contained SVG with outlined lettering and a rendered PNG.

Naming convention:

```text
<brand-slug>__<variant>.<format>
```

Five standard variants are used where supplied:

- `primary-horizontal` — README, wiki, reports, and letterheads;
- `stacked` — covers, square placements, and dividers;
- `mark` — avatars, icons, and document furniture;
- `reverse-horizontal` — dark fields and signage;
- `one-color-horizontal` — monochrome reproduction.

The production manifest records path, identity, classification, dimensions, variant, format, and SHA-256 digest for every logo asset.

## Supplemental and historical identities

- **Foundry** — product substrate, distinct from Foundry Field.
- **Red Wash Mine** — operating asset under Pale Sun.
- **Blood, Sweat & Tears Railway** — ARU operating component.
- **Emberline** — historical line absorbed into enduring work.
- **Red Wash / Pale Sun** — endorsed lockup; does not replace either canonical name.

## Reproduction constraints

- Do not distort, rotate, bevel, shadow, or add gradients.
- Do not combine identities unless an endorsed combined asset is supplied.
- Do not substitute generic lighthouse, compass, shield, wave, mine-pick, mountain, circuit, or AI clip art.
- Preserve clear space equal to at least one central accent square.
- Use SVG as the logo source of truth; PNG is a convenience render.
- Replace all collateral placeholders before external use.

## Source versus generated packages

Individual logos, editable template sources, standards, manifests, and intentionally reviewed publication packages belong in Git. Reproducible recurring exports should be generated, validated, checksummed, and attached to CI/releases rather than duplicated across business-line directories.

All rights reserved unless a specific repository file states otherwise.
