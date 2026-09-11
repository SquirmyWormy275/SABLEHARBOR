# Architectural concept readiness

`readiness.build_readiness(root: Path) -> dict` reads the repository's current `geospatial/facilities/source/*.json` and, when present, `RUNTIME_BRIDGE.json`. It returns evidence; it neither changes canon nor certifies architecture, accessibility, fire safety or building-code compliance. The source authority and generated-record boundaries in [MAINTAINERS.md](../../../MAINTAINERS.md) continue to apply.

Every check has a stable `SH-READY:<source scope ID>:<rule>` ID, scope, severity, outcome, basis, evidence and next action. Source SHA-256 locks identify the exact assessment inputs. `summary.outcomes` counts PASS, REVIEW, FAIL and NOT_ASSESSED; `engineering_certified` is always false. PASS means only that the specific narrow concept test passed. The overall status is ACTION_REQUIRED for a failed concept check, REVIEW_REQUIRED for coordination findings, and otherwise PARTIAL_EVIDENCE. It never reports a certified or construction-ready state.

The checks cover:

- Explicit adjacency/separation intent: reports the actual source relationships; does not invent maximum distances or claim that qualitative operational relationships have been verified.
- Footprint separation: detects positive-area overlap of building rectangles in a site's common local coordinate frame. No statutory setback or fire-separation requirement is asserted.
- Loading/service coordination: detects intersection, shared segments and touching points between recorded service and public/pedestrian route centre-lines. A crossing triggers review because elevations, widths, swept paths and operating controls are absent. A clear centre-line test does not certify safe vehicle manoeuvres.
- Door access: verifies positive-width door anchors lie on their room boundary and checks whether at least one reaches an explicit circulation rectangle boundary. Missing or indirect access triggers review where circulation geometry exists. Missing geometry is NOT_ASSESSED. Door swing envelopes, complete opening widths and travel routes are not inferred from a point anchor.
- Core stacking: compares explicit floor overrides with the common building core template. A shared template supports concept alignment only; it does not establish structural/service engineering. Renderer-inferred cores without explicit source geometry remain NOT_ASSESSED.
- Accessibility and egress: inventories lift, accessible-room, stair, exterior-door and occupancy evidence while returning NOT_ASSESSED for the engineering assessment. Labels and occupancy numbers alone cannot demonstrate a compliant route or safe exit system.
- Context-only/external locations: retains an explicit interior NOT_ASSESSED disposition instead of inventing provider floor geometry.

Coordinates are metres. The `1e-6` comparison tolerance handles floating-point conversion and is not a clearance requirement. Checks deliberately use no legal/code thresholds. Identical sources produce identical output; no build timestamp or current Git SHA is inserted.

At implementation review the accepted 19-site/18-building/25-floor sources produce 160 checks: 34 PASS, six REVIEW, zero FAIL and 120 NOT_ASSESSED. The six reviews concern direct circulation on Sacramento A Levels 01–03, B Levels 01–02 and C Level 01. Their listed rooms connect indirectly through adjoining working rooms; these are coordination questions, not asserted source defects. These counts describe the reviewed inputs and are not permanent design constraints.

Run the focused mutation tests:

```sh
python -m pytest -q geospatial/facilities/workbench/test_readiness.py
```

Tests move a door into a room interior, disconnect circulation, remove geometry, move a floor core, overlap buildings and change a service crossing. They also ensure that labels cannot certify accessibility/egress and that current repository assessment is deterministic. UI/CLI integration consumes the returned dictionary; this module does not write a competing source register.
