# Sable Harbor Brand Standards

**Version:** 0.2.1
**Date:** 2026-09-05
**Status:** Production candidate identity system; does not independently create or change canon

## 1. Governing idea

> **Variation is normal. The work is to encounter it, represent it, understand it, and choose consciously what happens next.**

The identity system translates that proposition into explicit geometry: visible seams, strata, channels, junctions, bounded enclosures, and controlled points of integration. It deliberately avoids literal harbor imagery, generic AI/circuit clip art, faux heraldry, gradients, shadows, and invented claims.

## 2. Identity hierarchy

1. **Sable Harbor** is the corporate master brand.
2. **Foundry Field, Willow, Atlas Meridian, Pale Sun, Project Cradle, American Resource Utility, and Advisory** are the seven 2026 business lines represented in the narrative map.
3. **Foundry, Red Wash Mine, Blood, Sweat & Tears Railway, and Red Wash / Pale Sun** are supplemental identities or endorsed relationships.
4. **Emberline and Evalon** are historical identities. Evalon is an archival advanced-engineering outpost that was closed and rechartered as Willow; it is not an eighth current business line.

## 3. Master-brand configurations

The Sable Harbor master brand has five controlled configurations:

- `sable-harbor__primary-horizontal` - default for README headings, wiki headers, reports, and letterhead;
- `sable-harbor__stacked` - covers, title pages, and square placements;
- `sable-harbor__mark` - avatars, favicons, navigation, and small document furniture;
- `sable-harbor__reverse-horizontal` - dark fields and video;
- `sable-harbor__one-color-horizontal` - stamps, engraving, fax, monochrome printing, and restricted reproduction.

Never stretch one configuration to imitate another.

## 4. Clear space and minimum size

- Preserve clear space at least equal to the central accent square around the entire lockup.
- Horizontal lockup: minimum 32 mm in print or 180 px in digital use.
- Stacked lockup: minimum 22 mm or 120 px.
- Compact mark: minimum 6 mm or 24 px, subject to a legibility check.
- At unusually small sizes, use the one-color mark rather than retaining an accent that cannot reproduce cleanly.

## 5. Color

Digital HEX/RGB values are controlling. CMYK values below are mathematical working conversions and require a printer proof. No Pantone or proprietary spot-color designation is asserted.

| Color | HEX | RGB | CMYK approximation |
|---|---|---|---|
| Sable Harbor Ink | `#101214` | `16, 18, 20` | `20, 10, 0, 92` |
| Sable Harbor Orange | `#C45124` | `196, 81, 36` | `0, 59, 82, 23` |
| Field Green | `#315F4D` | `49, 95, 77` | `48, 0, 19, 63` |
| Meridian Blue | `#2E6F96` | `46, 111, 150` | `69, 26, 0, 41` |
| Pale Sun Gold | `#C38B1F` | `195, 139, 31` | `0, 29, 84, 24` |
| Advisory Steel Blue | `#456C98` | `69, 108, 152` | `55, 29, 0, 40` |
| Red Wash Oxide | `#B94C2C` | `185, 76, 44` | `0, 59, 76, 27` |
| Evalon Steel | `#687C86` | `104, 124, 134` | `22, 7, 0, 47` |
| Paper | `#F4F1EA` | `244, 241, 234` | `0, 1, 4, 4` |
| Reverse Field | `#101419` | `16, 20, 25` | `36, 20, 0, 90` |
| Reverse White | `#F7F5EF` | `247, 245, 239` | `0, 1, 3, 3` |
| Muted Gray | `#747A80` | `116, 122, 128` | `9, 5, 0, 50` |

## 6. Reproduction rules

- Use SVG as the production source of truth for identities without an approved
  source-art exception.
- The controlling J2 mark and primary-horizontal PNGs are approved source artwork;
  their SVGs are vector derivatives.
- The four owner-approved Pale Sun/Red Wash PNGs listed in
  `red_wash_visual_manifest.json` are later byte-exact source-art overrides. Do not
  regenerate, recompress, redraw, or supersede them with legacy generated variants.
- Use the supplied reverse asset rather than manually inverting a primary file.
- Do not distort, rotate, bevel, shadow, outline, add gradients, or recolor outside the approved palette.
- Do not place the mark on visually noisy imagery without an adequate solid field.
- Do not substitute literal lighthouse, compass, shield, wave, mine-pick, locomotive, atom, or generic circuit/AI imagery.
- Do not create new combined identities. Use only supplied endorsed lockups.
- Do not present historical identities as current business lines.
- Do not use logo contact sheets as production art. Every file under `assets/brand/logos/` contains one lockup only.

## 7. Document and presentation use

- **Letterhead:** primary horizontal lockup; no invented address or contact information.
- **Memoranda:** primary horizontal lockup with explicit `TO`, `FROM`, `DATE`, and `SUBJECT` fields.
- **Reports:** stacked lockup on covers; primary horizontal in body headers.
- **Presentations:** reverse lockup on dark title fields; current business-line lockup on unit-specific sections.
- **Wiki and README:** use the applicable controlling source form from
  `assets/brand/`; do not substitute a legacy SVG where an approved PNG override
  controls.

## 8. Governance

The controlling naming source is [`docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md`](../../docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md), together with later controlled canon and decision-register addenda. Artwork does not lock legal entities, reporting lines, titles, economics, offices, public domains, contact details, or other OPEN decisions. Where this document's earlier v0.2.0 PDF reproduction differs from the September 5 approved-raster manifest, the later manifest controls the artwork source and preservation rule.

Before external commercial adoption, review [`docs/legal/PRELIMINARY_NAME_AND_MARK_SCREEN.md`](../../docs/legal/PRELIMINARY_NAME_AND_MARK_SCREEN.md) and obtain qualified trademark counsel.
