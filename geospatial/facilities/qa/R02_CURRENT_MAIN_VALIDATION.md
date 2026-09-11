# R02 validation against accepted runtime main

Accepted runtime main is `b83e4be2182a5e4143808a3dab5f8d929a133caf`. The new read-only validator batch began at live-worktree HEAD `d02920ce7684ed8f92c22eec87a05519d59316e7`; source development continued independently. These local results are not final-head CI, merge or publication acceptance. [Exact commands, exits and durations](repo-validation/r02-current-main/current-validator-results.json) identify this batch.

| Read-only check | Observed result |
|---|---|
| Governance/J2 validator | PASS |
| Institutional catalog validator | PASS |
| Organization maps validator | PASS |
| Repository hygiene validator | PASS |
| Business records validator | PASS |
| Geospatial `validate(write=False)` | PASS; report-writing deliberately disabled |
| Ruff check and format check, geospatial workflow configuration | PASS |
| All tracked JSON/GeoJSON parse | PASS, 279 files; syntax is separate from semantic schema |
| Services model validate | PASS; 57 services, 49 components, 49 dependencies |
| Runtime site/capital source schema and crosswalk validate | PASS |

## Clean test and domain evidence

Existing [clean-test results](repo-validation/r02-current-main/clean-test-results.json) bind the root suite to `237778db5156ab301804e565397312e96dbcb7a8` in `/tmp/sable-r02-main-validation-237778d`. Root tests passed with three existing skips and a SQLite datetime-adapter deprecation warning. The initial combined domain collection failed because independently named test modules collided; this was a collection namespace issue, not a concealed successful run.

The subsequent [separate domain results](repo-validation/r02-current-main/domain-test-results.json) at that source revision all passed: enterprise operations/business/industrial planning; runtime/services; industrial (39 tests); Red Wash (27 tests); geospatial (23 tests). Separate processes preserve each repository suite's module namespace. These source-bound results do not claim that later changes were tested at that earlier revision.

The [Sacramento ten-floor review](R01_TEN_FLOOR_FINAL_REVIEW.md), [master/stack review](R02_MASTER_STACK_FINAL_REVIEW.json), [non-Sacramento review](R02_NON_SAC_FINAL_REVIEW.md), and [R02 atlas review](R02_ATLAS_VISUAL_QA.md) retain their exact artifact scopes and hashes. The [final integrated review](R02_RUNTIME_ATLAS_QA.md) passes all 81 map imports and the 150-page atlas. [Two full generator rebuilds](R02_DETERMINISM.md) reproduce all 222 checked outputs byte for byte. The final focused suite passes 56 tests and the full facility validator passes 19 sites / 18 buildings / 25 floors.

## Clean finance and publication builds

The [runtime gate results](repo-validation/r02-current-main/runtime-gates-results.json) at clean source `237778d` record successful runtime model/database build, report verification, runtime verification, workbook verification and two complete `enterprise.runtime.build_finance` builds. Their manifests match, SHA-256 `858b80a03fd08772caebf51a8df33fe29d51657df9d4ef31e4ff034b7950c24c`. This is observed deterministic runtime-finance evidence at the stated source revision, not a claim about untested later bytes.

The [publication build results](repo-validation/r02-current-main/publication-build-results.json) at the same source record successful controlled-publication generation, institutional catalog generation and industrial validation with `--generate`. Rebuilt catalog SQL dumps are logically identical, SHA-256 `8a847460c2cf32830a79f3fa25f868bb7abb609330ab562a5c4dc2080b82adc3`; SQLite physical storage bytes differ. The clean build's only tracked drift was that SQLite physical representation. This difference is recorded, not hidden by changing a checksum or represented as byte determinism.

## Remaining final acceptance evidence

- Financial source compatibility: `git diff 237778d 9fb1e3a -- enterprise/runtime enterprise/services enterprise/operations enterprise/business industrial/planning src tests tools/documents` is empty. Subsequent changes are facility integration, QA and documentation; clean financial results remain applicable.
- Final distributable package checksums and retrieval: pending final source snapshot and release evidence. Controlled publication regeneration at `237778d` passed as recorded above.
- Final integrated facility/runtime/atlas verification: PASS; exact output hashes are bound by the current manifests and R02 determinism report.
- Native QGIS: no native-reader success is asserted by this batch; required native-QGIS CI evidence remains pending.
- Required final-head GitHub CI, review, merge SHA/current main and publication: pending actual remote results.

The [earlier repository validation report](REPOSITORY_VALIDATION.md) is explicitly pre-R01 history. Its six-building campus, 63-sheet/189-asset counts, old clean snapshots and original financial runs do not certify this R02/current-main package. Final evidence belongs in this report or a clearly linked successor, preserving historical results rather than relabelling old bytes.
