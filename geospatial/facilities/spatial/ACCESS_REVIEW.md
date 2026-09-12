# Sacramento indirect-access coordination review

This bounded review resolves the six concept-readiness findings by tracing **21 rooms across six floors** through their actual source doors and adjoining working rooms to explicit circulation. It does not modify the approved R01 four-building composition, ten floors, staffing/seat model or room geometry. Original R01 references remain immutable; current R02 JSON supplies the route coordinates. Authority remains with [MAINTAINERS.md](../../../MAINTAINERS.md) and the [approved R01 addendum](../../../docs/facilities/references/sacramento-hq/r01-approved/CODEX_ADDENDUM_APPROVED_SACRAMENTO_VISUAL_BASELINE_R01.md).

The owner authorized the spatial-quality tools and substantive coordination review. The individually listed operational restrictions in [ACCESS_POLICY.json](ACCESS_POLICY.json) are **modelled planning assumptions**, not a statement of actual occupancy, installed access control or completed construction. There is no blanket permission to traverse rooms merely because their access labels match.

## Reviewed attached-room relationships

Every row uses two existing source doors. The route runs from the origin room centre to its door, through the named intermediate room to that room's corridor door, and into the source circulation rectangle. Each straight segment is contained in one convex source rectangle. Source room rectangles, access classes, door definitions and circulation geometry are locked by per-route hashes and rechecked during every build.

| Origin room ID | Origin | Intermediate working room | Route class |
| --- | --- | --- | --- |
| SH-SITE-0001-A-L01-R01 | Focus west | Advisory common bench | staff |
| SH-SITE-0001-A-L01-R02 | Calls west | Advisory common bench | staff |
| SH-SITE-0001-A-L01-R03 | Focus east | Corporate commons / 80 dining seats | staff |
| SH-SITE-0001-A-L01-R04 | Calls east | Corporate commons / 80 dining seats | staff |
| SH-SITE-0001-A-L02-R01 | Focus west | Foundry Field west studio | staff |
| SH-SITE-0001-A-L02-R02 | Calls west | Foundry Field west studio | staff |
| SH-SITE-0001-A-L02-R03 | Focus east | Atlas Meridian product development | staff |
| SH-SITE-0001-A-L02-R04 | Calls east | Atlas Meridian product development | staff |
| SH-SITE-0001-A-L03-R01 | Focus west | Finance | staff |
| SH-SITE-0001-A-L03-R02 | Calls west | Finance | staff |
| SH-SITE-0001-A-L03-R03 | Focus east | Technology / Security / Resilience | staff |
| SH-SITE-0001-A-L03-R04 | Calls east | Technology / Security / Resilience | staff |
| SH-SITE-0001-B-L01-R05 | Head of Contact / Mara Hammer | Contact west studio | J2 |
| SH-SITE-0001-B-L01-R06 | Deputy Head of Contact | Contact west studio | J2 |
| SH-SITE-0001-B-L01-R09 | Methods room | Contact east studio | J2 |
| SH-SITE-0001-B-L01-R10 | Kit preparation / store | Contact east studio | J2 |
| SH-SITE-0001-B-L02-R05 | Head of Judgment / Anika Trish | Judgment studio | J2 |
| SH-SITE-0001-B-L02-R06 | Deputy Head of Judgment | Judgment studio | J2 |
| SH-SITE-0001-B-L02-R09 | Orientation case room | Orientation studio / Grant Kohrs | J2 |
| SH-SITE-0001-B-L02-R10 | Controlled records | Orientation studio / Grant Kohrs | J2 |
| SH-SITE-0001-C-L01-R06 | Shared production kitchen | Campus dining | service |

## Operational separation

- Corporate Levels 01–02: the west focus/call rooms serve the adjoining Advisory or Foundry Field working area. East focus/call rooms serve the adjoining commons or Atlas Meridian area. Preserve an unobstructed route inside the working area; these routes confer no public access to staff rooms.
- Corporate Level 03: west focus/call rooms are attached to the Finance suite; east rooms are attached to Technology/Security/Resilience. Only users authorized in that suite may use those attached rooms. Neither suite is a shortcut for unrelated staff. Internal Audit is never an intermediate route, preserving its independent secure boundary.
- J2 Levels 01–02: leadership, methods, kit and records rooms connect through the corresponding controlled Contact, Judgment or Orientation studio. Routes are for J2-authorized personnel within that working suite. The source's `staff` label on kit/records rooms does not authorize ordinary corporate staff to enter a restricted studio. Visitors remain in their reception/interview zone and no reviewed visitor route crosses a studio.
- Education Level 01: the kitchen's existing dining-service door leads through campus dining to teaching circulation. This is a service-staff connection; coordinate movements with dining use and control kitchen entry. It is not permission for diners to enter the kitchen and does not replace the separate exterior delivery route.

Rooms with private, residential or independent-audit access cannot be an intermediate passage. Restricted intermediates require the J2 route class. A public route cannot cross a nonpublic intermediate. Exact source locks make a changed access tag, missing door, moved room or altered circulation invalidate the prior review rather than silently inherit it.

## Overlay and validation interface

`access.build_access(root: Path) -> dict` returns reproducible, source-hashed overlay data without writing or changing authoritative sources. `routes` contains stable IDs, floor/site IDs, room and synthetic door locator IDs, classification, waypoints, individually verified segments, exact operational assumptions and PASS/FAIL outcomes. Door locator IDs use `<room ID>:door`, referring to the room's source `door` and matching floor-door entry; they do not allocate a new physical asset ID. All interior coordinates are floor-local metres.

`campus_routes` preserves the eight source polylines for public arrival, Education entry, shared pedestrian spine, east/west walk, J2 entry, residential arrival, service arrival and the fire/service loop. Their public/staff/J2/residential/service classifications describe the modelled approach. Campus coordinates are site-local metres. These routes are checked against the source envelope, not certified for width, grade, vehicle swept paths or crossing operations. The workbench model and renderer consume these arrays to save derivative overlays; this module does not create a competing plan source.

Readiness retains the original list of rooms lacking a direct corridor door, adds validated indirect-route IDs and returns PASS for that narrow access test only when its exact route review succeeds. Failed source locks make the affected floor FAIL. Absence of a reviewed indirect route remains REVIEW. Unassessed accessibility and egress engineering remain NOT_ASSESSED.

These polylines establish topological and geometric continuity within the concept rectangles. They do not establish furniture clearance, secured-door hardware, travel-distance limits, exit capacity, barrier-free access or code compliance. Internal route clearance and the stated operational restrictions must be preserved in later fit-out; engineering assessment is still required.

```sh
python -m pytest -q geospatial/facilities/spatial/test_access.py geospatial/facilities/workbench/test_readiness.py
```

The 15 focused tests pass: changed/missing doors, moved intermediate geometry, audit/private access transition and absent floor-door evidence all invalidate routes. The suite verifies readiness cannot turn a failed route into a waiver. Current review returns 21 verified room routes across six floors and eight campus context routes, with zero route failures.
