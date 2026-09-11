# Facility programme and atlas — R02 / v0.2.0

[Planning workbench: scenarios, readiness and evidence](workbench/README.md).

[Controlled release and checksums](../../docs/releases/FACILITY_ATLAS_RELEASES.md).

Open the [drill-down atlas](../maps/index.html), [portable atlas PDF](../maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf), or [individual artifact index](../maps/facilities/ARTIFACT_INDEX.md). Download the repository to open HTML locally; GitHub displays HTML source rather than serving the interface. The Markdown index provides direct repository links.

The September 11, 2026 owner handover authorized recovery, an integrated Sacramento campus model, explicit population/space reconciliation, facility coverage, saved plans, atlas navigation and repository closeout. This implementation is a **modelled planning package**, with explicitly separated proposed facilities, accepted fictional runtime-land acquisition, construction status, unknown occupied floors and proposed staffing. Accepted canon continues to control institutional facts. [Maintainer authority](../../MAINTAINERS.md) and [delivery policy](../../docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) apply.

[Dated decision and closeout record](CLOSEOUT_2026-09-11.md) preserves the owner direction, acceptance scope, delivered totals and external dependencies.

## Authoritative inputs and derived records

- [Population policy and evidence bridge](population/BRIDGE.md): 44 named employees and seven nonemployee directors; J2 237 billets, six named occupants, 231 unnamed-status billets, unknown vacancies. Enterprise actual population remains unknown.
- [Coverage matrix](coverage/COVERAGE_MATRIX.md): every source appearance has a stable disposition; functions, reference geography and repeated appearances are not separate properties.
- [Sacramento source](source/campus.json), [Fort and Bedford source](source/research_campuses.json), [industrial source](source/industrial_facilities.json): editable local geometry, rooms, seats, floor stacks, access, assumptions and status. Existing industrial/geographic inputs remain authoritative for their original facts.
- [Headcount/space and financial bridge](PROGRAM.md) and [derived area/seat register](SPACE_REGISTER.json): original facility subpackage of 16 sites, 17 buildings and 24 floors; conflicting attendance scenarios are not added together. The [runtime bridge](RUNTIME_BRIDGE.json) adds three accepted site records, one proposed building and one floor, reusing twelve existing runtime plates.
- [Recovery ledger](recovery/README.md): current-main and stale-branch dispositions, exact source hashes, recovered approved R01 references and the separate older exterior-image boundary.
- [Map ID allocation](../registers/MAP_ID_REGISTER.json): stable successor IDs within the established SH-MAP system. [Map manifest](../maps/MAP_MANIFEST.json) extends the rc4 manifest without replacing prior map bytes.

R02 retains 58 original facility sheets in 174 separate SVG, PNG and PDF assets. Combined with twelve reused runtime plates, the atlas covers 19 location packages, 18 buildings, 25 floors and 70 plates / 210 assets; eleven preserved rc4 map records bring the total to 81. Sacramento preserves four buildings, ten floors, 175,392 sf, 362 workplaces and 60 single rooms from the [approved R01 baseline](../../docs/facilities/references/sacramento-hq/r01-approved/README.md). The [ten-floor Sacramento QA](qa/R01_TEN_FLOOR_FINAL_REVIEW.md) and [non-Sacramento review](qa/R02_NON_SAC_FINAL_REVIEW.md) record scoped passes. Integrated runtime/atlas QA, repeat build and all nine final-head checks passed in PR #121; final acceptance and retrieval evidence accompany the published v0.2.0 release. Each floor has its own SVG, PNG and PDF. SVG is editable vector output; room coordinates and programmes remain in JSON for reproducible changes. The atlas consumes manifests, coverage and programme sources. It links location to site to building to floor and visibly labels external, historical, proposed and unresolved records. [GeoPackage and QGIS context](../README.md) remain the geographic framework; local concept plans do not insert a false parcel into GIS.

Sacramento's modelled Education and residence share the campus. This does not establish the actual location or occupancy of the previously unlocated J2 Education record. The production/Alexandria data-center estate remains outside Sacramento. PR #119 merged into accepted main `b83e4be2182a5e4143808a3dab5f8d929a133caf` and was integrated locally through `5d7e5a0`. The [accepted runtime source](../../enterprise/services/source/runtime_sites_2026-09-11.json) selects Switch Reno and IDACORE Boise and records the synthetic acquired Northern Nevada parcel in preconstruction. Provider contracts, assigned interiors and operation remain unestablished. The runtime proposal has 20 technology positions plus two facilities and six guard positions; these are not current employees or additions to the 44 named employees. Its conditional sixteen-seat HQ allocation uses eight existing A-Level03 shared seats and eight existing A-Level01 touchdown seats, with no new Sacramento capacity.

## Rebuild and validate

Use Python 3.12 and the repository's geography/organization/document dependencies, plus CairoSVG. The SVG/PNG/PDF renderer uses Cairo and DejaVu Sans; different library/font environments can change raster/PDF bytes. Exact regeneration is checked within the recorded build environment, and source hashes, content, dimensions and navigation are checked independently.

```sh
python geospatial/facilities/population/build.py
python geospatial/facilities/coverage/build_coverage.py
python geospatial/facilities/render.py
python geospatial/facilities/program.py
python geospatial/facilities/runtime_bridge.py
python geospatial/facilities/integrate_manifest.py
python geospatial/facilities/atlas.py
python geospatial/facilities/validate.py --check --require-atlas
python -m pytest -q geospatial/facilities/test_facilities.py geospatial/facilities/coverage/test_coverage.py geospatial/facilities/population/test_population.py
```

The pre-R01 six-building implementation and its release/QA evidence are superseded. They do not certify R02. Read the [initial](qa/SACRAMENTO_INITIAL_REVIEW.md) and [second-pass](qa/SECOND_PASS_REVIEW.md) visual findings as dated review history, not current acceptance. Final R02 QA and repository-validation evidence must identify the exact reviewed hashes before acceptance. New distributable bundles belong in GitHub Releases; individual controlled plans and useful review evidence are deliberately retained in Git.
