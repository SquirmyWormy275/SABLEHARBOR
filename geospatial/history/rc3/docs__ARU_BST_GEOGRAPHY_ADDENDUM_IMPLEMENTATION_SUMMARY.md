> **Historical rc2 implementation summary.** The mine-connector proposal and date-open statements below are superseded by [rc3 reconciliation](OPERATING_MODEL_RECONCILIATION_20260906.md). Current design is Taylor hub, truck last mile, no mine spur; ARU close 2026-01-07.

# Governing addendum implementation summary

**Implemented locally in v0.1.0-rc2.** Red Wash's approved Sweetwater anchor and the Taylor rename are applied across the current dataset, maps, registers and affected Red Wash source documents. Superseded imagery and the previous review package retain provenance.

## Preliminary route comparison

| Taylor alternative | Coordinate (lat, lon) | Legacy corridor | Later mine connection | Reason retained |
|---|---|---:|---:|---|
| A | 42.12, -108.10 | 33.35 mi | 8.12 mi | Shorter legacy system, longer integration |
| B | 42.15, -108.205 | 37.06 mi | 5.05 mi | Intermediate alternative |
| C — preferred proposal | 42.17, -108.225 | 38.81 mi | 4.23 mi | Closest to roughly 40 legacy route-miles with the shortest integration connection |

The selected lines form a connected Wamsutter–Taylor–Red Wash network with three declared nodes. The Wamsutter screening node is snapped to a FRA main-network feature with UP as source owner. That does not transfer real track or establish a turnout, service agreement or land right. The later mine segment is distinct and never represented as 2025 infrastructure.

The input DEM is a 70.211 m USGS 3DEP screening grid. Routes use an A* terrain cost and buffered NHD waterbody exclusions, followed by endpoint-constrained cubic smoothing. Plan sampling gives minimum radii around 914 m and 984 m. Neither selected line intersects the fetched NHD waterbody polygons. This does not establish floodplain or wetland avoidance.

A separate constrained formation profile uses a 1.8% grade limit and a 10,000 m minimum equivalent vertical-curvature radius. Legacy centerline cut/fill reaches approximately 7.55/5.50 m; the connector reaches approximately 3.56/4.45 m. Ground gradients are much steeper in places and are not reported as track grades. Cross-sections, soil conditions, actual earthwork volumes and costs are not calculated.

The reference crossing screen finds two highway features, 55 local-road features and six hydrography features intersected by the legacy proposal; the connector intersects two local-road features. These are raw feature counts, not counts of unique bridges or crossings. A highway crossing and real local access require explicit structure and clearance treatment before the alignment can be accepted.

BLM point queries return BLM administrative management at Red Wash and all three Taylor candidate points. The broad-area BLM geometry request failed; no complete land-tenure coverage is claimed. Point results do not establish parcel ownership, mining rights or permission.

## Business scale

The approved working case is approximately 9,000 annual revenue carloads, four locomotives with three generally available, and 58 BS&T staff. At an explicitly assumed 250 service days, 9,000 carloads average 36 revenue loads per service day. Empty-car movements, seasonality, train length, track occupancy and directional balance remain unspecified. The geometry is consistent with a small shortline scale; capacity is not proven by map length alone.

The later connector's limited length supports evaluating targeted integration, but no conclusion is made that the $15 million working integration ceiling is sufficient. Host-interface work, highway/drainage structures, track rehabilitation, yard geometry and earthwork quantities could change that conclusion. The approximately $11 million catch-up capex remains separate from integration.

## Remaining choices and work

Evalon/Willow occupancy timing and the transaction defining pre-acquisition remain open. HQ, Hazelwood and Cradle exact footprints, full mine surface/underground engineering, Taylor town layout, yard tracks, operating capacity, final structures and land rights remain incomplete. The pre-acquisition sheet is explicitly a legacy-scale scenario with an unresolved effective date.

Structural validation and 14 tests pass. Native QGIS 3.44.11 opens all layers and the relocated project. Eleven current map sheets are produced in PDF/SVG/PNG/JSON. The repository push remains blocked pending explicit approval to publish the reviewed package publicly.
