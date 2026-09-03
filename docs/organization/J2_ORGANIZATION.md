# J2 ORGANIZATION CHARTS

**Map ID:** `SH-ORG-J2-001` | **Version:** 1.0.0 | **State:** LOCKED DIRECTION  
**Edge rule:** Solid arrows are work-product flows. Dotted lines are advisory, collection-direction, assignment, or standards relationships—not HR reporting unless explicitly stated.

## Rendered chart suite

| View | SVG | PNG |
|---|---|---|
| High-level organization | [SVG](assets/j2/j2-high-level.svg) | [PNG](assets/j2/j2-high-level.png) |
| Contact → Judgment → Orientation loop | [SVG](assets/j2/j2-loop.svg) | [PNG](assets/j2/j2-loop.png) |
| Five-person JAG package | [SVG](assets/j2/jag-team.svg) | [PNG](assets/j2/jag-team.png) |
| Contact / Judgment interface | [SVG](assets/j2/contact-judgment-interface.svg) | [PNG](assets/j2/contact-judgment-interface.png) |
| Orientation / decision interface | [SVG](assets/j2/orientation-decision-interface.svg) | [PNG](assets/j2/orientation-decision-interface.png) |

The machine register with checksums and edge semantics is [J2_CHART_REGISTER.json](J2_CHART_REGISTER.json).

## Contact / Judgment interface

```mermaid
flowchart LR
  O[Orientation enterprise questions] -. broad collection priority .-> C[Contact intake]
  JO[Judgment Officer problem owner] -. requirement / RFI .-> C
  HQ[J2 HQ] -. scarce-capacity arbitration .-> C
  JW[Judgment Watch<br/>Judgment home] -. embedded intake triage / correlation .-> C
  C -->|raw evidence + provenance| JO
  JW -->|route/propose; never owns| JO
```

## Orientation / decision interface

```mermaid
flowchart TB
  OR[Orientation profession<br/>~20–25 commissioned working target]
  OR -. dedicated separate assignment .-> CEO[Office of CEO]
  OR -. dedicated separate assignment .-> BOARD[Board]
  OR -. standing observation posts .-> FIN[Finance<br/>senior CFO-office + ~2–3 embeds]
  OR -. temporary consequential environment .-> TEMP[Acquisition / Red Wash / major capital / regulated exposure]
```

Executive assignments rotate about 24–36 months. Presence follows decision environment, not prestige. See `docs/j2/J2_OPERATING_MODEL.md` for the high-level loop and `docs/j2/JUNCTION_ADVISORY_GROUP.md` for the five-billet JAG chart.
