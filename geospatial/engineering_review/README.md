# Railway engineering source review — 28 September 2026

This is a reproducible screen of the **accepted synthetic Taylor A case**, not a
new alignment or construction design. Run `python -m geospatial.engineering_review.build`
and inspect [`PROFILE_AND_HISTORY_REVIEW.json`](PROFILE_AND_HISTORY_REVIEW.json).
The output pins four source files by SHA-256, retains their stable route/history
IDs and is regenerated from source; the accepted industrial files are unchanged.

The current network is 33.348476763611 mainline route-miles, 4 East branch
miles and 2.651523236389 Mineral branch miles, totalling 40 unique route-miles.
The 1954 source gives **14–16 surviving miles without a georeferenced
alignment**. Subtracting that range from the 1968 mainline gives 17.348476763611
to 19.348476763611 **net** route growth. It says nothing about gross new
construction or the location of abandoned/relocated track. In particular, the
current `IND-BST-MAIN-1` feature measures about 15 miles but is dated to the
accepted 1968 geometry; numerical similarity cannot identify it as the 1954
survivor. The 1898 origin likewise has no mapped line. Historical maps must
show those states as unlocated.

The source profiles are screening inputs. The selected mainline has a
constrained preliminary L1 formation profile; East, Mineral and the Red Wash
truck road have **grade-only** L1 profiles. Recomputed maximum absolute sampled
grade is at most 1.8% for the railway routes and 3.799% for the road. The
largest adjacent sampled-grade changes are approximately **0.699, 3.448,
1.010 and 6.076 percentage points**, respectively. The particularly sharp
East branch and road breaks expose missing vertical transitions, even though
their maximum grades meet source constraints. The report records the exact
source-derived stations, cut/fill extrema and each route's modeling state.
It does not turn a grade-break measurement into a designed vertical curve.

## Preliminary branch-transition successor

Regenerate [`VERTICAL_TRANSITION_SCREEN.json`](VERTICAL_TRANSITION_SCREEN.json) with:

```bash
uv run --with-requirements geospatial/requirements.txt python -m geospatial.engineering_review.build_transitions
```

The accepted East profile starts **3.667 m above** the selected mainline formation
at its physical junction. Mineral starts **0.004 m above**. The successor fixes
both starts to the interpolated mainline formation, leaves their remote ends
at source ground, and minimizes absolute cut/fill. It uses the accepted
mainline's 1.8% sampled grade and 10,000 m discrete curvature-screen radius,
with at most 12 m absolute cut/fill, as explicit **proposed** branch screening
constraints. Its unequal-station grade-change bound is a discrete radius
proxy, not a surveyed or constructible vertical curve.

The resulting modeled junction gaps are zero. The East branch's maximum
adjacent sampled-grade change falls from **3.448** to **0.807 percentage
points**; Mineral falls from **1.010** to **0.537**. Both pass the declared
preliminary constraints. The pinned industrial source profiles remain visible
for comparison. The proposed station elevations are a reproducible derivative,
not an amendment to the existing operational route, turnout or profile canon.
Derived output values are rounded to 0.001 in their displayed units for
cross-platform review; constraints are checked at full precision first.
In particular, turnout tangent matching at each switch still requires a
track-design package; elevation continuity alone is insufficient.

## Track, site and rights interface

Regenerate [`TRACK_SITE_INTERFACE_SCREEN.json`](TRACK_SITE_INTERFACE_SCREEN.json) with:

```bash
uv run --with-requirements geospatial/requirements.txt python -m geospatial.engineering_review.build_interfaces
```

It reconciles the **12** accepted facilities, **31** track-register segments
(11 route segments and 20 yard tracks), **26** structures, 40 unique route-miles
and **4.18** separate yard-track miles. Its twelve facility rows carry source
owner labels, synthetic footprint precision, yard track IDs, nearest route
and an explicit real-instrument state. The empty accepted trackage-rights
layer is preserved as zero, not treated as an implied external agreement.

Four of six rail-served site envelopes have yard geometry touching an accepted
route. Taylor Terminal and Taylor Warehouse have no mapped lead joining their
yard tracks to the modeled mainline: nearest separations are **386.6 m** and
**624.2 m**. These are lower-bound geometric gaps, not proposed lead lengths.
The source still models them as operating sites; this screen marks the missing
physical interface without inserting an unowned line across unknown land.
Real title, lease, easement, interchange and access instruments are absent
from this synthetic source population and are not supplied by an owner label.

Profile chainage is measured in projected meters; source route miles are
geodesic. The report does not force those two measurements to match exactly.
No historical survey, transition geometry, structure design, earthwork volume,
geotechnical/drainage design, parcel/title/access instrument or exact external
client footprint was recovered here. Issue #107's detailed engineering
acceptance remains open. The report is a bounded, checkable input to that work,
and preserves the no-mine-spur and uranium custody gates.

## Subsequent synthetic worldbuilding design candidate

The later [`WORLD_BUILDING_DESIGN.json`](WORLD_BUILDING_DESIGN.json) and
[`WORLD_BUILDING_DESIGN.geojson`](WORLD_BUILDING_DESIGN.geojson) form a **proposed
case**, separate from the operating source above. Regenerate them with:

```bash
uv run --with-requirements geospatial/requirements.txt python -m geospatial.engineering_review.build_worldbuilding_design
uv run --with-requirements geospatial/requirements.txt python -m pytest -q geospatial/tests/test_worldbuilding_design.py
```

The generator pins eight exact source files, including the accepted track and
facility populations, screening DEM, local roads and waterbody polygons. It
solves a continuous-grade (C1 piecewise-quadratic) profile for the 769-station
mainline and for each proposed curve. Formation grade is at most 1.8%; a
10,000 m vertical curvature proxy applies to the main/branches, 2,000 m to the
two local leads and 1,000 m to the four terminal ladder connections. These are
authored preliminary design assumptions, not a cited railroad standard or
construction certification. The main candidate changes the accepted source
formation by at most **0.615 m** and has maximum screened cut/fill of
**6.683/5.738 m**. The candidate holds the mainline endpoints, so it does not
silently change the accepted 40-mile source.

The East and Mineral branch curves enter tangent to the source mainline and
rejoin their source branches at 1,200 m and 800 m. Their sampled minimum plan
radii are **153.054 m** and **162.210 m**. The accepted waterbody polygon
intersection stays zero, and the six East and three Mineral local-road
crossing IDs are preserved. Reconciliation of the **26** source structures
finds no source-coordinate displacement; the five on affected branches need
new milepost assignments if those curves are adopted. This is a plan/profile
screen only: switch hardware, clearances, earthwork, drainage, load rating,
utilities and field survey remain unproved.

Two additional curves connect the source mainline to one existing track each
at Taylor Terminal and Warehouse. The terminal lead is **506.186 m**, of
which **467.299 m** is outside the synthetic terminal envelope. The warehouse
lead is **717.268 m**, with **711.047 m** outside its envelope. Four separate
yard-ladder curves join the other terminal tracks to the proposed terminal
lead without mutually crossing. Their outside-envelope lengths are retained
per feature in the JSON; they are not summed as a unique property footprint.
The five terminal and one warehouse tracks thus have a **candidate physical
topology**, while the accepted 31-track source remains unchanged. No rail spur
to Red Wash is introduced.

### Exact source choices exposed by the candidate

| Treatment | Consequence before adoption |
| --- | --- |
| Preserve the accepted **40.000000** geodesic route-miles | Redesign the curves and route geometry to remove **0.193028** geodesic route-mile (about **310.775 projected metres**) while repeating grade, curvature, water/road, structure, route-mile and site checks. The two source branches have only **46.568 projected metres** of total slack above their endpoint chords; even perfectly straightening both would leave **264.206 m** of this candidate increase. The present endpoints/junctions or another substantive geometry assumption therefore need reconsideration. A bookkeeping relabeling cannot shorten a physical line. |
| Adopt the curves' **40.193028** geodesic route-miles | Amend the controlling industrial route/segment source, rechain branch mileposts and five structure placements, and reperform dispatch/capacity, maintenance, capital and downstream finance or geographic exports that consume exact mileage. Do not silently add the curves to a frozen release. |

Neither treatment is selected by this derivative. The two new leads plus four
yard ladder curves also need an explicit track-register, asset, operating and
capital treatment before a source successor could represent them as in use.
The existing site envelopes are acreage-based synthetic rectangles, not
property lines. The outside-envelope route, interentity ARU/BS&T connection,
UP interface where applicable, and any real title/easement/road crossing
rights still have no instrument in this package. The terrain and waterbody
screen cannot establish those rights or a finished site plan.

The 1898 coal-era line, the 14–16-mile 1954 survivor and abandoned/relocated
segments retain null geometry with explicit source/derived classifications.
There is no recovered contemporary linework that could locate them. The
proposed modern curves do not backdate the line. Exact external customer
footprints likewise remain governed by their accepted restricted/unknown
precision rather than being invented to fill a map.
