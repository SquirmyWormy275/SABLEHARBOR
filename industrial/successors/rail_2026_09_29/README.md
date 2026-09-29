# September 29 railway operating-source successor

This is a newly authored **synthetic** geometry and milepost correction for the represented BS&T network. The owner selected the full #107B/#108B rail closeout. Accepted PR #178 supplied the fixed-control candidate; this separate source selector applies its three route centerlines to the bounded industrial planning case. The original September 5 operating case and September 6 forecast remain source-locked historical releases. Nothing here is a recovered survey, legal right-of-way, operating authorization, or real infrastructure construction.

## Scope and authority

- Source selector: [`source.json`](source.json), with exact hashes for the locked original operations/network and accepted PR #178 candidate JSON/GeoJSON.
- Effective physical-case scope: retrospective geometry correction to the existing 40.000000000 route-miles. The correction became available September 29, 2026 UTC. Earlier operational facts retain their own dates and known-on boundaries.
- Legal operator and owner, site endpoints, 9-mile truck-only mine access, 31 registered tracks, 26 structure IDs, and all financial rates and opening balances are unchanged. The original unknown 1898 extent and unlocated 14–16-mile 1954 survivor range remain unknown/unlocated.
- Three corrected routes: main 33.155448786 mi, East 4.136588436 mi, Mineral 2.707962778 mi. Actual serialized GeoJSON measures 39.999999880 mi on the WGS84 ellipsoid; 0.000000120 mi is coordinate-rounding difference, below the source's 0.000001-mi validation tolerance.
- Six local leads/ladders in PR #178 remain *proposed*. None enters the operating network, asset/collateral census, capex, funding, service, or customer book. Direct finished-uranium custody remains gated.

The 11 old route-segment IDs are stable asset crosswalk keys. Their suffixes are historical labels, not current mileposts. New physical maintenance-district boundaries were authored at declared stations on the corrected centerlines. The old boundary points could miss the new alignment by 69.403 m, so this successor does not project old boundaries into service. All 26 structure coordinates stay fixed and receive newly calculated mileposts; the crosswalk records both values.

## Reproduction and result

Use the repository's supported geospatial dependencies. The builder creates only separate `industrial/generated/successors/rail_2026_09_29/` outputs and never overwrites `industrial/source` or the preserved default release.

```bash
uv run --no-project --with pyproj==3.7.2 --with shapely==2.1.2 \
  python industrial/successors/rail_2026_09_29/build.py
python industrial/successors/rail_2026_09_29/reconcile.py --write
uv run --no-project --with pyproj==3.7.2 --with shapely==2.1.2 --with pytest \
  python -m pytest industrial/successors/rail_2026_09_29/test_successor.py -q
```

The committed [`reperform-result.json`](reperform-result.json) pins 180 complete three-route planning months, all 13 financial datasets, exact export hashes, and the `$0` modeled journal/cash/tax delta. Only `available_at` and daily train hours change in the operating rows. Base January 2027 train hours become 15.0723716995 from 15.1045430291. Downside March 2027 conditional capacity remains **1,008 cars**, because four failure-speed round trips still exceed the 24-hour roster envelope. A mainline-only sensitivity would give 1,344 cars, but it omits the longer branch duty and is not the adopted full-network case. No 2027 forecast is promoted to 2026 actual.

The builder exports `source/operations.json`, `source/geography/network.geojson`, recomputed spatial screen, `asset_crosswalk.json`, 31 operating artifacts, 180 planning rows, 13 forecast datasets, and `successor_manifest.json`. `reconcile.py` independently recalculates the operating rows and forecast, rejects stale exports, and compares every financial row after removing only the successor availability metadata. Sorted JSON map keys would change a seven-month commodity tie break; the selector writer intentionally retains source insertion order and tests this contract.

## Source locks and unresolved boundary

`industrial/planning/source/preservation.json` and `geospatial/sources/catalog.json` continue pinning the original operations/network bytes. The default `industrial/tools/build_operations.py` build was independently run before and after the source-dir selector change: all **32 output files were byte-identical**. The new selector has a separate output guard and 155 operating reconciliation checks. The historical 1898/1954 centerline candidate remains a separate #107B scope and must never be described as a recovered survey or a real land right.
