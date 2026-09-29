# Rail source-consumer and geometry-only sensitivity receipt

**Record ID:** SH-RAIL-SOURCE-CONSUMER-2026-09-29

**Basis:** accepted `main` `64513f27446a34ffc710138a05639173822f1075` and proposed PR #178 candidate `e4fd1ea0`

**State:** independent read-only review; no operating-source adoption, asset commissioning, survey, land right or historical-original claim

## Exact input and result

The proposed fixed-control candidate is pinned here by SHA-256: `COMPENSATED_40_MILE_CANDIDATE.json` `7592f356a9d13878a61960d735fba61924119c8efac226544c133f85d59b4750`, GeoJSON `2d3358d9dd7d117954b7d36879626659117cb9387b1350b4541abccb726228ad`. Its route split is main **33.155448786**, East **4.136588436**, Mineral **2.707962778** geodesic miles, summing to **40.000000000**. The accepted source split is 33.34847676361104 / 4.000000000 / 2.651523236389135. The proposed junction mileposts rechain from East 15 to about **14.848837** and Mineral 26 to about **25.840193**.

`crosswalk-result.json` inventories all **11** route-segment IDs and **26** fixed-coordinate structure IDs. The proposed segment-boundary mileposts are projections of old physical points onto the new route and **are not adopted asset boundaries**. Some old segment endpoint points lie as much as **69.403 m** from the new line; a successor must decide and document the corresponding physical boundary. All 26 structure coordinates project onto the candidate centerline at the recorded 0.001 m precision. Their mileposts still change; examples are `BR-01` 5.2→5.141138, `BR-02` 18.1→17.948837, `BR-03` 28.4→28.240193, and `BR-04` 2.8→2.936588. `CUL-17/18` shift +0.136588 and `CUL-19/20` +0.056440 mile. Preserve stable asset IDs and add an old/new version crosswalk rather than silently reusing old mileposts.

The **complete three-route** 180-row 2027–2031 planning reperform preserves the source's branch basis: one out-and-back trip on each branch at 15 mph, plus **0.613130235 h** local switching. The longer branches increase daily branch work from **1.500000000 to 1.525737064 h**. With the shorter mainline and revised branch work together, every scenario-month changes only `capacity.rail.train_hours_daily`; **all 180 capacity-car quantities stay unchanged**. A fourth failure-speed round trip in downside March 2027 would consume **24.008643 h**, above the 24-hour combined crew envelope, so conditional capacity stays **1,008 cars**. This is conditional capacity, not observed demand or a new qualified operating authority.

For diagnostic contrast only, changing the mainline while holding branch work artificially at 1.5 h changes **179** months in train-hours alone and raises the downside March 2027 conditional capacity **1,008→1,344 cars**. That is **not the complete-route successor**. `reperform-result.json` records both comparisons; the complete-route calculation is the adoption basis.

Rebuilding the old and **complete-route-adjusted** conditional forecasts in separate temporary directories produced **row-equal outputs in all 13 financial datasets**: 123,716 journal rows, 10,350 trial-balance rows, 360 monthly statements, 360 funding rows and the remaining receipts/asset/debt/tax/intercompany/inventory/revenue/elimination populations. The scenario summaries are equal. Therefore the geometry-only full-route update produces **$0 modeled journal, balance, cash and tax change in this sensitivity**. This does not price, authorize, construct, commission or book the proposed Taylor leads/ladders; doing so would require an independently supported asset/capital and rights treatment.

## Source and consumer boundary

| Layer | Exact accepted source/consumer | Required successor treatment |
| --- | --- | --- |
| Preserved physical source | `industrial/source/operations.json`; `industrial/source/geography/network.geojson`; associated DEM/profile/spatial-screen pins | Do not overwrite their historical bytes. `industrial/planning/source/preservation.json` pins source SHA/bytes, and `geospatial/sources/catalog.json` pins `SRC-CURRENT-OPS` and `SRC-CURRENT-NETWORK` at `d91a22c3`. Add dated source/version and explicit selection. |
| Industrial operating build | `industrial/tools/build_operations.py`, `industrial/tests/test_operations.py` | Reconcile exact 40, three route IDs, 11 route segments, 26 structures, branches/no mine spur, source hashes, facility population, generated CSV/SQLite/GeoJSON/maps/manifests. Keep original default release reproducible. |
| Conditional physical/financial plan | `industrial/planning/source/operating_plan.json`, `industrial/planning/operating_model.py`, `industrial/planning/forecast.py`, `industrial/planning/build.py` | Use a separately versioned plan source for both the new mainline distance and the branch running time at 15 mph while preserving 0.613130235 h switching. Reperform all 180 months and full forecast/enterprise outputs. Regression-test that March 2027 downside conditional capacity stays 1,008 cars and journals remain equal if no costs change. |
| Geographic export | `geospatial/scripts/sync_industrial.py`, `validate_reconciliation.py`, `build_geopackage.py`, `render_maps.py`, `package_release.py`; `geospatial/geojson/rail_network.geojson`, `rail_mileposts.geojson`, `bst_alignment_current.geojson` | Current scripts consume old pinned files and reject hash drift. Select a new source ID/version rather than rewrite `SRC-CURRENT-*` pins; regenerate layers, maps, package and semantic validation. Preserve original snapshots/releases. |
| Company assets and debt | `enterprise/operations/current_balances.py`, `enterprise/closeout/finance_administration.py`, `debt_rights.py`, `aru_tax_workpapers.py`, `docs/organization/source/chartbook.json` | Reconcile the 149-asset source census and 64 ARU-collateral IDs to stable identities. Geometry-only milepost revision adds no asset or pledge. Organization display source contains old segment details; update only a controlled successor/current display after accepted source selection. Historical chartbook snapshot stays frozen. |

## Reperformance

On a checkout containing the final PR #178 candidate:

```bash
python docs/internal/company-closeout/evidence/rail-source-consumer-2026-09-29/reperform.py
uv run --no-project --with pyproj --with shapely python docs/internal/company-closeout/evidence/rail-source-consumer-2026-09-29/crosswalk.py
```

Both scripts print JSON and write no repository files. Compare output with the two pinned `*-result.json` receipts. The scripts reject changed population/schema and a non-40-mile candidate. The crosswalk is a screening mapping, not adopted engineering. For a later source successor, additionally run industrial operation/plan/integrity tests, geospatial reconciliation and native readback, source-lock validation, organization maps, finance/export checks, and the maintainer suite on the exact integration head. This receipt is the pre-adoption comparison only.

## Historical alignment boundary

The accepted chronology fixes the 1898 founding, 1953 failure at year precision, 1954 rescue, 1968 Taylor completion, 1972/1986 branches and 1991 ownership. It supplies no georeferenced 1898 coal line, exact 1954 survivor centerline, or abandoned/relocated segment. An explicitly newly authored fictional alignment candidate can be developed under the #107 closeout instruction if its new anchors, event time, knowledge date, source status and uncertainty are visible. The 1954 **14–16-mile range** must remain a range in accepted history, and modern 15-mile chainage cannot be labeled the historical survivor. No candidate can be called a recovered survey or evidence of real property rights.
