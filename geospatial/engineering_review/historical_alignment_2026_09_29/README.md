# Early BS&T alignment: fictional alternative, September 29, 2026

**Record ID:** SH-GEO-BST-HIST-CANDIDATE-20260929-001

**Status:** PROPOSED_NEWLY_AUTHORED_FICTIONAL_HYPOTHESIS_NOT_RECOVERED_HISTORY

This is a bounded #107B review alternative, not controlling historical geometry. The accepted case still has an unknown 1898 original extent, an unlocated 14–16-mile 1954 survivor, and no located abandoned linework. No survey, map, land instrument, government rail record, or real-world construction is represented by the proposed coordinates. The September 29 authored date is the knowledge date of this alternative, not an 1898 or 1954 evidence date.

The accepted industrial chronology fixes the 1898 predecessor event, 1953 failure at year precision, July 1, 1954 rescue, October 14, 1968 Taylor main completion, and later 1972/1986 branches. A lower-authority September 5 reconciliation describes roughly 22 pre-failure miles, abandonment of mine-only trackage, and 14–16 survivor miles. Those words bound a possible narrative but provide **no historical coordinates**. [`source.json`](source.json) pins each source and marks every new station as authored fiction.

The proposed southwest alternative starts at the later Wamsutter junction, uses newly invented waypoints and an invented west service point, and treats a separate invented mine-only branch as abandoned during the 1953–1954 transition. WGS84 ellipsoid lengths are 15.084858 survivor miles plus 7.047398 mine-only miles, or 22.132255 possible pre-failure miles. These values satisfy the narrative ranges but **do not select an exact accepted 1954 length or establish the 1898 mileage**. The proposed line shares only about 0.050 m of buffered overlap with the modern northbound three-route candidate at Wamsutter; it does not back-project the current route. This is a geometry screen, not historical terrain, engineering, or title proof.

`candidate.geojson` has two proposed lines and no current asset IDs. `report.json` records exact lengths and the accepted unknown fields. The generator rejects changed pinned sources, a survivor outside 14–16 miles, a candidate inconsistent with roughly 22 pre-failure miles, linework that overlaps the modern route, or a claim of current rights/survey authority.

```bash
uv run --no-project --with pyproj==3.7.2 --with shapely==2.1.2 \
  python geospatial/engineering_review/historical_alignment_2026_09_29/build.py
uv run --no-project --with pyproj==3.7.2 --with shapely==2.1.2 --with pytest \
  python -m pytest geospatial/tests/test_historical_alignment_candidate.py -q
```

## Exact remaining evidence boundary

No recovered coal-era survey, property chain, contemporary milepost register, dated abandonment instrument, or external client-site footprint locates an original line. There is no accepted basis to distinguish this invented southwest hypothesis from other possible 14–16-mile locations. Accordingly, adopting it as an inspected historical fact, identifying a real parcel/ROW, or closing the full #107 engineering criterion would overstate the evidence. The supported alternatives are to keep the historical locations explicitly unknown; select a clearly synthetic company-history realization through a separate reviewed adoption; or add genuine located evidence if it later exists. The modern 40-mile operating-source successor and its financial reconciliation do not depend on which historical alternative is chosen.
