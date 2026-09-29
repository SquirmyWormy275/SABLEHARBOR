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
