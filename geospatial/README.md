# Sable Harbor master geospatial package

**v0.1.0-rc3 - operating-decision reconciliation; full program incomplete.**

Start with [the eleven-sheet atlas](maps/SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc3.pdf), [GeoPackage](master/sable_harbor_master_v0.1.gpkg), and [portable QGIS project](qgis/sable_harbor_master.qgz).

Current main was inspected at `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`. Existing geospatial commits were recovered into an isolated branch without touching the unfinished merge in the original worktree. The 673-file discovery inventory and 89 curated objects are inherited controlled inputs; semantic census reconciliation is incomplete.

## Governing current decisions

Red Wash anchor: 42.22 N, 108.18 W, Sweetwater County. Taylor replaces Bloodstone. The latest approved operating model uses **Taylor transload and truck last mile, no mine spur**. The previous 4.23-mile connector is preserved as a superseded, never-built proposal in `history/`. Current rail geometry contains only the 38.81-mile Wamsutter-Taylor preliminary corridor. No truck route is fabricated.

Sable Harbor acquisition of ARU closes **2026-01-07**. The pre-acquisition map is explicitly a **2026-01-06 scenario with proposed geometry**, not recovered historical track. The closing date is corroborated by the separately pinned, unmerged ARU baseline branch; branch-derived allocations are not promoted to main canon.

The operating overlay records 225 recurring annual rail loads, a 300-load design allowance, 10-14 days of storage, two weekly windows, $8.5M Phase I and $6.5M gated remainder, with $11M catch-up capital separate. See `sources/APPROVED_OPERATING_DECISIONS_20260906.json` for retrieval provenance.

## Rebuild

```sh
python -m pip install -r geospatial/requirements.txt
python geospatial/scripts/build_geopackage.py
python geospatial/scripts/render_maps.py
python geospatial/scripts/validate_geospatial.py
python -m pytest geospatial/tests -q
QT_QPA_PLATFORM=offscreen /usr/bin/python3 geospatial/scripts/validate_qgis.py
```

Normal builds use committed inputs offline. Candidate-engineering outputs are comparative research: the mine-connector alternative must never be copied back into the current network. `history/` is superseded evidence, not a current map source.

## Remaining work

Exact HQ, Hazelwood and Cradle footprints; Taylor yard/town engineering; final interchange, structures, roads and land screening; mine engineering; complete semantic census; and Evalon historical occupancy remain incomplete. The historical outside-Pittsburgh Evalon shop versus Hazelwood is the remaining material location decision. See `reports/OPEN_CONFLICTS.md`.

All geometries preserve fictional/real distinctions and feature-level provenance. Current validation evidence is in `reports/`. No main merge or public publication is claimed.
