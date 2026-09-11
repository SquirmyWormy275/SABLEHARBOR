# Industrial facility planning source

The editable [industrial_facilities.json](source/industrial_facilities.json) supplies thirteen packages: all twelve accepted `SH-IND-FAC-*` facility envelopes and the separately proposed `SH-SITE-0006` Red Wash study envelope. Existing industrial operations, geographic geometry and temporal records retain authority. These floor layouts are explicit illustrative interpretations of established functions, not surveyed or completed buildings.

Six buildings each have a separate ground-floor source. Actual floor count is unknown; a single-storey concept is modelled. The warehouse gross areas come from accepted operations: Taylor **210,000 square feet / 19,509.6384 m²**, Rawlins **75,000 square feet / 6,967.728 m²**. Their rectangular footprint proportions and handling/support bands are assumptions. Pallet slots remain **11,000 / 4,000** reserved capacity; no new rack, stacking height, throughput, fire loading or installed equipment is inferred. Storage, receiving/quarantine, dispatch, staff support and protected service reservations replace an office-grid treatment.

| Stable facility ID | Package | Buildings / floors | Assigned FTE | Disposition |
|---|---|---:|---:|---|
| SH-IND-FAC-WAM-INT | Wamsutter interchange | 0 / 0 | 6 | Site/context; three accepted tracks, no occupied building established |
| SH-IND-FAC-TAY-YARD | Taylor Yard and Shops | 2 / 2 | 46 | Running-repair shop and dispatch/crew house concepts; seven original track references |
| SH-IND-FAC-TAY-TERMINAL | Taylor Industrial Transload Complex | 0 / 0 | 19 | Site/context; general/liquid segregation, no fabricated plant or buildings |
| SH-IND-FAC-TAY-WAREHOUSE | Taylor warehouse | 1 / 1 | 8 | Accepted area, illustrative single-storey material-flow layout |
| SH-IND-FAC-TAY-TRUCK | Taylor trucking depot | 1 / 1 | 20 | Inspection/dispatch/welfare concept; staging and road-workforce distinction |
| SH-IND-FAC-EAST-MATERIALS | East Materials team track | 0 / 0 | 3 | Site/context; two tracks, no occupied building established |
| SH-IND-FAC-MINERAL-TEAM | Mineral Transfer team track | 0 / 0 | 3 | Site/context; two tracks; no local trona mine inferred |
| SH-IND-FAC-RAW-TERMINAL | Rawlins satellite terminal | 0 / 0 | 8 | Truck-served site/context, no BS&T connection or evidenced building envelope |
| SH-IND-FAC-RAW-WAREHOUSE | Rawlins warehouse | 1 / 1 | 4 | Accepted area, illustrative single-storey storage/order-pick layout |
| SH-IND-FAC-RAW-TRUCK | Rawlins trucking satellite | 0 / 0 | 4 | Heavy-haul staging; mechanic allocation does not establish a workshop |
| SH-IND-FAC-ARU-OFFICE | Taylor ARU office | 1 / 1 | 10 | Customer desk, finance/admin, operating leadership, shared meeting/welfare |
| SH-IND-FAC-RW-RECEIVING | Red Wash receiving/reagent storage | 0 / 0 | 6 | Source receiving function retained; technical building/tank/containment layer unresolved |
| SH-SITE-0006 | Red Wash surface study envelope | 0 / 0 | 128 site total | Proposed surface envelope; mine floor/underground/process inventory unresolved |

The twelve facility allocations total **137 FTE = 131 ARU/BS&T + 6 Red Wash receiving**. Those six are a subset of the **128 Red Wash site employees**, not additional employees. Pale Sun's **12 platform employees** remain separate. Therefore neither the last row nor its receiving subset may be added to the facility table as though every row were an independent population. Assigned workforce includes drivers, crews, field and outdoor activity; it does not equal indoor attendance or desks.

Indoor planning peaks are Taylor shop 10, dispatch/crew house 20, Taylor warehouse 8, trucking building 8, Rawlins warehouse 4 and ARU office 14. These **64 hypothetical indoor places** are not a simultaneous enterprise census, hiring authority or shift schedule. Room seats and activity capacities may serve the same people in different activities. The Red Wash stress-test scenario separately considers 48 site workers plus four visitors/contractors; it does not establish actual attendance, installed capacity or statutory egress. Future 2031/2036 positions remain unresolved, with no assumed growth approved.

Every site points to its original georeferenced polygon and original geometry/precision/date fields. Local metric diagram frames reuse source acreage/aspect solely to size an illustrative working envelope; they have no survey transform. Proposed building placements do not replace original geometry or establish rail/road crossing permission. The Red Wash overall 1,000 × 800 m envelope remains a **preliminary engineering proposal**, not owned land or historical disturbance. Its accepted operating anchor remains −108.18, 42.22. The rejected mine rail spur is excluded.

The source preserves references to all **20 facility tracks, 11 route segments and 26 network structures**. The latter comprise bridges, culverts and external highway overbridges and receive context plus their existing engineering record, with a justified floor-plan exemption. Route structures are not assigned arbitrarily to an adjacent building. Existing tracks must be rendered from their accepted geographic geometry; local functional zones are not track alignments. The Taylor shop must be reconciled to the original shop track before engineering acceptance. Heavy locomotive overhaul remains outsourced.

The parent facility generator renders these records using the campus schema with `layout_style: industrial`, preventing automatic office corridor/core overlays. Each source building has its own rooms, gross/net/support areas, explicit perimeter egress concept and floor peak. `map_prefix` uses the existing `SH-MAP-ARU` / `SH-MAP-RWM` families with successor allocations from 020 onward. The shared manifest and atlas own output paths and navigation; this source creates no competing geographic portal.

All building dimensions other than the stated warehouse areas, room use subdivisions, clear heights, structural spans, access reservations, egress assumptions and interior capacities are planning assumptions. Source opening dates describe the established synthetic facilities; they are not dates of the illustrated fitout, ownership transfer or construction completion. Detailed field/as-built evidence, fire engineering, accessibility, structural/loading checks, utility/containment design and operator-approved access are the next actions for technical layers explicitly left unresolved.
