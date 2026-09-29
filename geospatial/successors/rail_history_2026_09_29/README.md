# Separate fictional early-rail history case

**Record:** `SH-GEO-BST-HISTORY-CASE-20260929-001`
**State:** `PROVISIONAL_DERIVED_SYNTHETIC_HISTORY_CASE`
**Authored:** September 29, 2026 UTC

This successor selects the previously reviewed southwest **fictional
alternative** for a separate history-case map. It gives readers a concrete
illustration of a possible 1954 survivor and mine-only abandoned line while
keeping the accepted source-evidence history unchanged. The owner authorized
work on #107B/#108B, but did not select these particular coordinates. They are
newly authored scenario anchors, never a recovered 1898/1954 survey or a real
property right. First repository availability and acceptance remain null in
the source pending a reviewed merge.

The selected case has 15.084858 miles of illustrated survivor and 7.047398
miles of illustrated abandoned mine-only line. The total 22.132255 miles is a
case-compatible pre-failure hypothesis, **not** the accepted 1898 extent.
Accepted 1898 mileage and geometry remain unknown; the accepted 1954 source
remains a 14–16-mile survivor range with unlocated geometry. Exact abandonment
and survivor-retirement dates remain unknown. The July 1, 1954 date labels the
accepted synthetic rescue event and a case snapshot, not a demonstrated
continuous operating interval.

[`case.geojson`](case.geojson) carries only the two scenario features, with no
current asset ID, operating interval, title or right-of-way. [`case.svg`](case.svg)
is an offline plate that labels the case/evidence boundary on the image.
[`report.json`](report.json) gives the snapshot dispositions and source hashes.
The existing accepted chronology viewer still shows the early **source-evidence
view as unlocated**; this case is not substituted for it. The modern
40-mile operating-source successor, 31-track/26-structure population and all
180 planning months remain untouched. No rail service, mine spur, uranium
custody, asset, tax, cash or finance amount changes.

## Reproduce and inspect

Run from a checkout with the pinned source files and the supported geospatial
dependencies:

```bash
uv run --no-project --with pyproj==3.7.2 \
  python -m geospatial.successors.rail_history_2026_09_29.build --check
uv run --no-project --with pyproj==3.7.2 --with pytest \
  python -m pytest geospatial/tests/test_rail_history_case_successor.py -q
```

The builder rejects changed pinned history/operations/planning sources,
invented recovered geometry, an exact unsupported abandonment day, an
out-of-range 1954 survivor, or a new right/economic/current asset claim. It
does not establish constructibility, survey authority, parcel access, or an
external customer's exact footprint. Those issue criteria need their own
source and engineering work; this case alone does not close #107 or #108.
