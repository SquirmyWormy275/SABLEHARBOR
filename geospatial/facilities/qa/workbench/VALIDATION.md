# Facility workbench acceptance evidence

Implementation base: accepted PR #121 merge `7bc9879fb94dbf999066b8072cc66ec8e05fda0a`. Final code snapshot: `09ef4f1`; UI review binds actual output hashes in [browser-results.json](browser-results.json). Generated reports and interface are source-derived experiments, not canon promotion.

[Exact commands and results](VALIDATION.json): 108 focused facility/population/coverage/workbench tests pass (52 new workbench tests plus 56 existing); Node browser arithmetic/import tests pass; workbench freshness, complete facility/atlas, governance, catalog, organization, hygiene and Ruff checks pass. The [clean root suite](root-tests.log) at `ca3c199` passed 166 tests with three existing skips. Later changes affect only this workbench, atlas navigation, documentation and its tests; root/finance source is unchanged. Final PR-head CI independently rechecks the accepted merge candidate.

Two complete workbench builds reproduce all eight outputs byte for byte. The pre-existing 150-page atlas PDF and artifact index are byte-identical; the atlas HTML adds the workbench link and its source-hash graph updates. All original floor, site and runtime SVG/PNG/PDF assets remain unchanged and pass the existing manifest validator. Approved R01 original hashes remain unchanged.

The browser and Python engines agree for the real 25-floor baseline and five attendance/sharing perturbations. Tests reject stale source locks, duplicate/missing IDs, nonfinite or fractional people, invalid resident subsets and unsafe output destinations. Evidence tests exercise valid temporary-repository acceptance bindings and rejection of unsupported promotions, changed evidence, invalid dates/geometry, malformed types and nonphysical facility demands.

Readiness reports 160 narrow checks: 34 PASS, six REVIEW, zero FAIL and 120 NOT_ASSESSED. Indirect room access needs coordination review; missing engineering evidence is not certification. The queue retains 586 addressable records and marks physical fields not applicable for 437 nonphysical records.

[Visual review](REVIEW.md) covers all four tabs at desktop/mobile widths, source-impact details, forms, scenario imports/exports and atlas navigation. Corrections fixed mobile text/select overflow and completed day-peak and strict import checks. Final merge/CI/retrieval events are recorded in the PR and controlled release evidence.
