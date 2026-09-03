# J2 OPERATING MODEL

**Document ID:** `SH-J2-OPS-001` | **Version:** 1.0.0 | **State:** LOCKED DIRECTION
**Owner:** J2 Headquarters | **Related:** Contact, Judgment, Orientation, JAG, Education | **Cross-reference:** `J2_CHARTER.md`; `J2_HEADQUARTERS.md`

## High-level organization

```mermaid
flowchart TB
  HQ[J2 Headquarters]
  HQ -. doctrine / standards .-> C[Contact]
  HQ -. doctrine / standards .-> J[Judgment]
  HQ -. doctrine / standards .-> O[Orientation]
  HQ -. cross-cutting arm .-> JAG[Junction Advisory Group]
  HQ -. cross-cutting arm .-> EDU[Education]
```

## Functional loop

```mermaid
flowchart LR
  HQ[J2 Headquarters] -. doctrine / priorities / arbitration .-> C[Contact]
  HQ -. professional standards .-> J[Judgment]
  HQ -. professional standards .-> O[Orientation]
  C -->|evidence with provenance| J
  J -->|human-authored judgments + dissent| O
  O -->|reoriented questions / requirements| C
  JAG[Junction Advisory Group] -. field observation / reach-back .-> C
  JAG -. human context transfer .-> J
  EDU[Education] -. learning / pedagogy .-> O
  O -. enterprise learning needs .-> EDU
```

Solid arrows are work-product flows, not reporting lines. Dotted edges are doctrine, collection, reach-back, cross-cutting-arm, or learning relationships. HQ is not a giant command tower.

Contact collection is directed broadly by Orientation's enterprise priorities and specifically by Judgment Officers' collection requirements/RFIs. HQ arbitrates conflicts/scarcity. Contact chooses lawful source, method, timing, and provenance. Judgment Watch belongs to Judgment but works at Contact intake; it triages and correlates signals, routes them to live problems, or proposes a new problem. Once assigned, the Judgment Officer owns the problem.

J2 outputs connect to governance: material findings may trigger rapid adjudication; board and executive Orientation officers protect epistemic integrity; JAG may surge as a fact witness/ground-truth collector; Education converts important learning into instruction. None of these relationships creates line command.
