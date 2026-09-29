# Corrected 40-mile rail/site interface register

This register reperforms the accepted synthetic three-route successor against
all **12** facility envelopes and **31** source tracks, while protecting all
**26** structure identities. It computes corrected-route geometric separation
in EPSG:26913 from pinned inputs, instead of carrying forward distances from
the original route. The route split is 33.155448786 mainline, 4.136588436 East
and 2.707962778 Mineral miles, totalling exactly 40 in the source selector.
Yard track remains a separate 4.18-mile population.

Four rail-served yard envelopes geometrically touch the corrected route.
Taylor Terminal and Taylor Warehouse still require a local physical lead: the
closest registered yard-track gaps are **387.457 m** and **624.202 m**. The
accepted design candidate depicts proposed leads, but they remain out of
service, outside the 40 route-mile and 31-track operating population, and
outside capital/finance books. Their candidate lengths outside the synthetic
site envelopes are **467.848 m** and **711.040 m**. Four additional terminal
ladders are likewise only proposed. Six of the twelve sites have no rail track
in their source record; Red Wash retains the truck-only nine-mile access and
no mine spur.

[`register.json`](register.json) includes every site owner label and yard ID,
the corrected geometric joins, eight proposed curve/profile screens, eight
turnout-interface screens, all 26 structure design-boundary rows and the two
external-branch endpoint coordinates. Each proposed turnout row checks the
branch's physical start against its parent centerline, its projected junction
chainage, a five-metre sampled plan-tangent angle, and its yard-track end
where one exists. All eight junction gaps are at most 0.00002 m in the
synthetic geometry and all six proposed yard connections touch their selected
track. The builder checks the complete sampled profile station population,
strict chainage order, terminal elevations and plan/profile length for each
curve. These are centerline and profile consistency checks, not a specified
switch number, frog, flangeway or vehicle swept-envelope clearance.

The structure rows retain all **20** accepted culverts, **four** rail bridges
and **two** highway overbridges with fixed coordinates, corrected chainage,
source span, condition, inspection/restriction where present, and source
catch-up amount. The two highway overbridge clearances remain **source
assumptions with a survey gate**. The source has no hydrologic catchment or
design flow for any water crossing and no verified hydraulic capacity or
field load/clearance rating. Inventing a flow value to turn those fields green
would not be a supported engineering conclusion.

External client parcel/footprint IDs remain null. The accepted rights layer
contains zero trackage-rights features. An operating owner label, synthetic
acreage rectangle or designed line outside that rectangle is **not** a deed,
lease, easement, interchange agreement or construction permission. Finished
uranium custody remains gated.

The source candidate supplies continuous-grade profiles with at most 1.8%
sampled grade and 12 m screened cut/fill. The register checks those bounds
and retains the actual sampled radii and station counts. A fictional detailed
turnout/formation specification can be authored later against this bounded
geometry, but it must separately resolve actual vehicle envelope, load,
drainage, soil and earthwork inputs. No construction or real-access claim
follows from a visually connected lead.

```bash
uv run --with-requirements geospatial/requirements.txt \
  python -m geospatial.engineering_review.interface_successor_20260929.build --check
uv run --with-requirements geospatial/requirements.txt --with pytest \
  python -m pytest -q geospatial/tests/test_rail_site_interface_successor.py
```

The source pins every controlling input. The tests reject changed geometry,
an invented in-service lead, an asserted right or parcel footprint, a mine
spur and a false custody permission.
