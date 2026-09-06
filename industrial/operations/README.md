# ARU / BS&T operating evidence

This directory explains the controlled operating model in `../source/operations.json`. It is a synthetic industrial case in real Wyoming geography. Exact customer, employee and financial records are maintained by the companion finance corpus; this slice supplies the physical assets, assigned responsibilities, service rules and cost-to-serve basis those records must use.

The selected railway has 40 unique route-miles, four owned locomotives, three generally available and two normally required. Its 2025 external baseline is 9,000 revenue carloads and 58 employees inside ARU's 131 employees. Red Wash contributed no 2025 ARU revenue. Ordinary inbound mine service begins July 7, 2026; direct uranium-product custody remains gated.

Run the offline build from the repository root:

```bash
python industrial/tools/build_operations.py
python -m unittest discover -s industrial/tests -p test_operations.py
```

The build produces CSV registers, a SQLite evidence database, GeoJSON facility envelopes and structure points, node registers, service-calendar cases, financial reconciliation, SVG maps and a SHA-256 manifest under `industrial/generated/operations`. It calculates the railway length on the WGS84 ellipsoid rather than accepting a displayed “40 miles” label. Every default build uses pinned local sources and writes no wall-clock timestamps into generated artifacts.

The maps `bst_network.svg`, `red_wash_site.svg` and `red_wash_underground.svg` are deterministic code-rendered replacements for current publications. Existing approved brand masters and old Red Wash raster maps are not edited by this build. The old map bytes remain historical evidence under the parent publication manifest.

The source includes 12 operating facilities, the complete main/branch segment register and yard tracks, four railway bridges, 20 culverts, two synthetic I-80 highway overpasses at reference-road intersections, locomotive/service-car/leased-car/road-equipment/handling-equipment registers, craft allocations, property agreement summaries, dated safety events and separate claim/environmental balances. These are populated records, not assertions that actual government registries contain a fictional railroad.

Read the geography memorandum for the selected alignment and source limitations; the service plan for capacity, materials and the elapsed-time SLA; the rate memorandum for external versus intercompany charges; and the labor/safety memorandum for preserved obligations and imperfect operating history.

The publication cutoff is September 5, 2026 at 23:59:59 America/Los_Angeles. Reference retrieval on September 6 UTC occurred on September 5 local time. Source retrieval dates do not establish what was known during an earlier transaction. July and August service entries are synthetic historical case data; full September through December rows remain forecast at this cutoff.

An optional independent check resamples the pinned DEM, checks published formation grades and repeats line/waterbody intersections. It requires numerical GIS packages, but does not fetch new source data:

```bash
uv run --no-project --with numpy --with rasterio --with pyproj --with scipy --with shapely python industrial/tools/build_operations.py --verify-geography
```

The full track export includes every route segment and yard track. Yard lines represent declared lengths in conceptual parallel orientations inside synthetic site envelopes; switches, curves and property rights require separate engineering. The physical-to-finance bridge validates every external contract quantity, both terminal and warehouse site capacities, staff references, vehicle/driver hours, car spots and common capital timing.

The historical map `bst_historical_routes.svg` separately shows the 1898 coal origin, the unlocated 14–16-mile surviving estate rescued in 1954, the 1968 Taylor mainline, the 1972 East Materials branch and the 1986 Mineral Transfer branch. Early geometry is explicitly schematic and unlocated. The surviving 1954 mileage is not backdated as a measured 1898 system; the 1991 ownership change adds no route mileage. The current three map outputs retain their separate geographic and mine operating roles.
