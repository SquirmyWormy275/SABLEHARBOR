# Facility planning workbench

Open [the offline workbench](../../maps/workbench.html) from an extracted repository or release. It connects the accepted [atlas](../../maps/index.html) to scenario testing, source-change impacts, architectural concept readiness and evidence intake. No server, account or network access is required. [Delivery index](../../../docs/releases/FACILITY_WORKBENCH_RELEASES.md).

The owner authorized all three extensions on September 11, 2026, following acceptance of PR #121 (`7bc9879fb94dbf999066b8072cc66ec8e05fda0a`). This implementation adds tools, not personnel, property, construction, geometry or engineering decisions. Accepted R01 originals and R02 plans retain their authority and bytes. Proposed changes still follow [maintainer authority](../../../MAINTAINERS.md) and [delivery policy](../../../docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md).

## Scenario testing

Select a location and edit anonymous planning demand per floor. Assigned desks remain reserved; shared desks must accommodate both the planned sharing ratio and everyone simultaneously attending. Required shared desks are the larger of `ceil(shared workers / sharing ratio)` and `ceil(shared workers × attendance fraction)`. A sharing ratio cannot make attending people disappear. Touchdown users have their own capacity. Floor peaks are source model comparisons, not licensed occupancy limits.

The baseline reproduces Sacramento's 504-person day scenario and separate 60-room night capacity. The 48 resident trainees are inside the single 120-person day cohort. Training and meeting seats are alternative activities, not additional people. The cohort is assigned to the source event's Education L01; the tool does not invent a second concurrent class. Other floors use anonymous capacity comparisons; unknown runtime desks remain unknown. Site/building sums disclose unknown floors instead of reporting an enterprise population. The 2031/2036 choices introduce no automatic growth.

Export and re-import experiments as JSON. A source hash mismatch, missing/duplicate floor, invalid number or inconsistent resident subset blocks evaluation. Downloaded experiments do not edit sources. CLI result files must be new files outside the repository.

```sh
python geospatial/facilities/workbench/build.py scenario \
  geospatial/facilities/workbench/BASELINE_SCENARIO.json --output /tmp/scenario-result.json
```

## Source-change impacts

The source panel traverses a conservative dependency graph from current manifests and generator inputs to registers, independent plans, the atlas and workbench. It reports regeneration candidates and responsible commands; commands are a set, not an execution sequence. Shared generators can invalidate more sheets than ultimately change pixels. Unmapped files require review and are never silently declared harmless.

```sh
python geospatial/facilities/workbench/build.py impact \
  --changed geospatial/facilities/source/campus.json --output /tmp/campus-impact.json
```

The CLI also detects changed or deleted sources against the saved graph. Preserve a pre-change graph until impact review is complete; rebuilding replaces its baseline. Readiness/evidence views are explicitly dated by source hashes. `build --check` detects stale derived files without rewriting them.

## Readiness and evidence

[Readiness method and limits](README_READINESS.md) describe geometry-supported concept checks and unassessed engineering. [Evidence intake and review](README_EVIDENCE.md) describes hashed documents, effective intervals, stable IDs and exact accepted-decision bindings. The UI downloads pending submissions only. The CLI can validate and export reviewed candidates; neither interface promotes canon. External facts still need evidence and normal repository reconciliation.

## Reproduction and validation

Python 3.12, Shapely and the existing facility/geography dependencies; Node for browser-math tests. Committed JSON and HTML are derivatives of code and accepted sources.

```sh
python geospatial/facilities/workbench/build.py
python geospatial/facilities/workbench/build.py build --check
python -m pytest -q geospatial/facilities/workbench
node geospatial/facilities/workbench/test_app.cjs
python geospatial/facilities/validate.py --check --require-atlas
```

`BASELINE.json`, `DEPENDENCIES.json`, `READINESS.json`, `EVIDENCE_QUEUE.json`, baseline experiment/result and `MANIFEST.json` identify the exact inputs and outputs. The workbench is linked from the existing atlas and repository navigation; it is a companion to the same stable-ID model, not a competing floor-plan register.
