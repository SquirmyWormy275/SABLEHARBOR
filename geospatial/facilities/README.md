# Facility programme and atlas

[Controlled release and checksums](../../docs/releases/FACILITY_ATLAS_RELEASES.md).

Open the [drill-down atlas](../maps/index.html), [portable atlas PDF](../maps/SABLE_HARBOR_Facility_Atlas_v0.1.0.pdf), or [individual artifact index](../maps/facilities/ARTIFACT_INDEX.md). Download the repository to open HTML locally; GitHub displays HTML source rather than serving the interface. The Markdown index provides direct repository links.

The September 11, 2026 owner handover authorized recovery, an integrated Sacramento campus model, explicit population/space reconciliation, facility coverage, saved plans, atlas navigation and repository closeout. This implementation is a **modelled planning package**, not a claim of acquired property, construction, occupied floors or new personnel. Accepted canon continues to control institutional facts. [Maintainer authority](../../MAINTAINERS.md) and [delivery policy](../../docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) apply.

[Dated decision and closeout record](CLOSEOUT_2026-09-11.md) preserves the owner direction, acceptance scope, delivered totals and external dependencies.

## Authoritative inputs and derived records

- [Population policy and evidence bridge](population/BRIDGE.md): 44 named employees and seven nonemployee directors; J2 237 billets, six named occupants, 231 unnamed-status billets, unknown vacancies. Enterprise actual population remains unknown.
- [Coverage matrix](coverage/COVERAGE_MATRIX.md): every source appearance has a stable disposition; functions, reference geography and repeated appearances are not separate properties.
- [Sacramento source](source/campus.json), [Fort and Bedford source](source/research_campuses.json), [industrial source](source/industrial_facilities.json): editable local geometry, rooms, seats, floor stacks, access, assumptions and status. Existing industrial/geographic inputs remain authoritative for their original facts.
- [Headcount/space and financial bridge](PROGRAM.md) and [derived area/seat register](SPACE_REGISTER.json): 16 site packages, 19 buildings, 27 floors; conflicting attendance scenarios are not added together.
- [Recovery ledger](recovery/README.md): current-main and stale-branch dispositions, exact source hashes and unrecovered image boundary.
- [Map ID allocation](../registers/MAP_ID_REGISTER.json): stable successor IDs within the established SH-MAP system. [Map manifest](../maps/MAP_MANIFEST.json) extends the rc4 manifest without replacing prior map bytes.

Each floor has its own SVG, PNG and PDF. SVG is editable vector output; room coordinates and programmes remain in JSON for reproducible changes. The atlas consumes manifests, coverage and programme sources. It links location to site to building to floor and visibly labels external, historical, proposed and unresolved records. [GeoPackage and QGIS context](../README.md) remain the geographic framework; local concept plans do not insert a false parcel into GIS.

Sacramento's modelled Education and residence share the campus. This does not establish the actual location or occupancy of the previously unlocated J2 Education record. The production/Alexandria data-center estate is excluded from Sacramento; PR #119 remains its separate pending runtime workline. Primary colocation regional direction follows the owner handover; pending provider/owned-building details are not imported as accepted main.

## Rebuild and validate

Use Python 3.12 and the repository's geography/organization/document dependencies, plus CairoSVG. The SVG/PNG/PDF renderer uses Cairo and DejaVu Sans; different library/font environments can change raster/PDF bytes. Exact regeneration is checked within the recorded build environment, and source hashes, content, dimensions and navigation are checked independently.

```sh
python geospatial/facilities/population/build.py
python geospatial/facilities/coverage/build_coverage.py
python geospatial/facilities/render.py
python geospatial/facilities/program.py
python geospatial/facilities/integrate_manifest.py
python geospatial/facilities/atlas.py
python geospatial/facilities/validate.py --check --require-atlas
python -m pytest -q geospatial/facilities/test_facilities.py geospatial/facilities/coverage/test_coverage.py geospatial/facilities/population/test_population.py
```

Read the [initial](qa/SACRAMENTO_INITIAL_REVIEW.md) and [second-pass](qa/SECOND_PASS_REVIEW.md) visual findings as dated review history, not current acceptance. Final QA and repository-validation evidence identify the exact reviewed hashes. New distributable bundles belong in GitHub Releases; individual controlled plans and useful review evidence are deliberately retained in Git.
