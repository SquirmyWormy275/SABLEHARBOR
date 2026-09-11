# Repository validation evidence

Local checks use the repository `.venv` Python 3.12.14. These are local results, **not GitHub CI or merge-gate claims**. Initial read-only checks ran in detached temporary checkout `3480665b2d317b3de74e455158f58ed46d09da70`; publication and industrial builds ran separately at `775d657`. All build output remained in temporary worktrees, apart from the deliberately retained logs below. The integration checkout continued developing independently; final committed-source acceptance also ran from clean checkout `e44b3e3`, as recorded in [final gate results](repo-validation/final-gate-results.json).

[Command/exit-code records](repo-validation/results.json), [additional service checks](repo-validation/extra-results.json), [isolated publication/industrial builds](repo-validation/build-results.json), and [geospatial rebuild checks](repo-validation/geo-build-results.json), and [complete financial builds](repo-validation/finance-build-results.json) contain exact invocation evidence. Absolute executable paths identify the actual interpreter; commands below abbreviate it as `.venv/bin/python`.

| Check | Local result |
|---|---|
| `scripts/validate_governance_j2.py` | PASS; governance, J2, source/PDF hashes and organization boundaries |
| `scripts/validate_institutional_catalog.py` | PASS; 118 objects, nine Pinakes portals |
| `scripts/validate_organization_maps.py` | PASS; source, card copy, logos, publication coverage and preserved history |
| `scripts/validate_business_records.py` | PASS; seven lines, 12 interfaces, ten existing-CCF implementations |
| `scripts/validate_repository_hygiene.py` | Initial workline defects found and corrected in `775d657`; live rerun passed |
| `python -m pytest -q` | PASS, 166 passed and three skipped; 217.39 seconds. Root configuration collects `tests/`, so additional suites ran separately |
| `python -m pytest geospatial/tests -q` | PASS, 20 tests |
| `geospatial/scripts/validate_geospatial.py` | PASS |
| `geospatial/scripts/sync_industrial.py` | PASS |
| `geospatial/scripts/build_geopackage.py --output /tmp/sable-facility-validation.gpkg --database-only` | PASS; fresh 39,821,312-byte GeoPackage |
| Geo catalog, GeoJSON and QGIS source `git diff --exit-code` after rebuild | PASS; no source drift |
| Native `/usr/bin/python3 geospatial/scripts/validate_qgis.py` | Environment unavailable: `qgis` Python module is not installed. Existing `native-qgis` GitHub job remains the required native-reader evidence |
| `python -m unittest discover -s enterprise/services/tests -v` | PASS, 43 tests |
| `python -m enterprise.services.model validate --repository-root .` | PASS |
| Service model build with `--database` into `/tmp/sable-services-validation` | PASS; `comparison.csv` and `REPORT.md` byte-match committed derivatives |
| `python -m pytest enterprise/operations/tests enterprise/business/tests industrial/planning/tests -q` | PASS, 295 tests |
| `python -m unittest discover -s industrial/tests -v` | PASS, 39 tests |
| `python -m unittest discover -s red_wash/tests -v` | PASS, 27 tests |
| `red_wash/tools/validate_red_wash_record.py` | PASS, 514 checks |
| `industrial/tools/validate_industrial_case.py --generate` | PASS, 4,245 checks and 199 selected artifacts |
| `python -m enterprise.business.build` | PASS; complete financial successor built in isolated clean `775d657`, 149.28 seconds |
| `python -m enterprise.operations.build` | PASS; 47,060 events, 98 tables, scoped CSV/SQLite packages and final artifact public-safety scan, 273.07 seconds |
| `tools/documents/build_controlled_publications.py` | PASS; retained 118 hash-verified publications, rendered zero, qpdf normalizer |
| `tools/documents/build_institutional_catalog.py` | PASS; catalog JSON unchanged; SQLite storage bytes differ with identical SQL contents |
| Focused facility, coverage and population tests in final clean integration | PASS, 29 tests, including disconnected-floor and stale-atlas mutations |
| `geospatial/facilities/validate.py --check --require-atlas` on clean `e44b3e3` | PASS; 16 sites, 19 buildings, 27 floors; graph reachability, source hashes, independent formats, HTML and internal PDF destinations |
| Ruff lint for all `geospatial/` | PASS |
| Ruff format for all `geospatial/` | PASS on final `e44b3e3`; initial atlas.py formatting failure was corrected and digest-dependent atlas outputs regenerated |

## Findings and dispositions

1. The first hygiene run exposed two incorrectly relative research-campus canon links and superseded identity labels copied from the organization's historical exclusion register. Commit `775d657` fixes both. The bridges retain original stable IDs, exclusion statuses and source path/line references without republishing superseded labels or quotations. No historical source was rewritten and no validator was weakened. A later hygiene run also caught a stale atlas graph that still contained the earlier labels; atlas regeneration resolved it. The corrected live hygiene log records PASS across 1,775 tracked paths.
2. The first detached checkout intentionally captured a coherent commit before Sacramento source and render assets were staged. Eight focused mutation tests failed because that incomplete snapshot lacked `source/campus.json`; the same 25-test suite passed in the integrated working source. This records an incomplete integration boundary rather than concealing it as a pass. Final acceptance and the enlarged 29-test suite pass from clean `e44b3e3`, which contains every source and derivative.
3. Running the industrial validator without `--generate` in a clean checkout fails because ignored finance journals have not been built. The workflow's required `--generate` invocation succeeds. No facility change caused that prerequisite.
4. Native QGIS is absent on this machine. The Python geographic validator, geometry suite and fresh GeoPackage build pass; they do not substitute for native QGIS. No local native-reader success is claimed.
5. The institutional catalog rebuild changes the tracked SQLite binary's physical representation only. [Comparison evidence](repo-validation/catalog-sqlite-comparison.json) shows identical 970-line SQL dumps and identical 2,097,152-byte file sizes; catalog JSON and all publication bytes remain unchanged. The different binary hashes are recorded, not edited to simulate deterministic bytes. Rebuilt SQLite bytes were confined to the isolated checkout and the original was restored there before financial builds.
6. Root tests emit an existing Python 3.12 SQLite datetime-adapter deprecation warning. The test run succeeds with three skips; no new skips or warning suppression were introduced.

Raw historical failure logs are retained so a reviewer can distinguish observed defects, corrected defects, prerequisites and local environment limits. Only repository-generated public synthetic data and test diagnostics are included.

The root financial/runtime source paths (`tests`, `src`, `pyproject.toml`, `config`, `db`, `enterprise`, `industrial`, `red_wash`) have no differences between the original full-suite test revision and `e44b3e3`. The retained [empty drift log](repo-validation/root-tested-source-drift.log) records that check. Root tests were not redundantly rerun after unrelated atlas edits; final affected geometry, facility and governance/publication gates were rerun.

## Final spatial-register acceptance addition

The final audit adds `program.py --check` to the read-only acceptance chain. It recomputes both SPACE_REGISTER.json and PROGRAM.md, rejecting stale area/seat/population derivatives. All site, building and floor rows explicitly distinguish unknown observed workforce categories and future proposed positions from modelled seats and attendance. Two additional mutation tests reject desk corruption and unknown authorized positions silently changed to zero; the final focused suite has **31 passing tests**. Source geometry, area/seat totals and all 189 plan artifact bytes remain unchanged. Final PR-head CI includes this addition.
