# Facility planning workbench releases

## v1.0.0

Owner-authorized companion to the accepted facility atlas v0.2.0. It adds capacity experiments, source-change impact traversal, architectural concept readiness and evidence candidate intake/review. It does not change approved R01 originals, accepted R02 floor geometry, workforce facts or engineering authority.

Entry point: [offline workbench](../../geospatial/maps/workbench.html). [Methods, source and commands](../../geospatial/facilities/workbench/README.md). Accepted facility base: `7bc9879fb94dbf999066b8072cc66ec8e05fda0a`.

Acceptance vehicle: [PR #124](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/124). [Versioned release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-workbench-v1.0.0).

- Package: `SABLE_HARBOR_Facility_Workbench_v1.0.0.zip`.
- Exact packaged source: `474c0ffcfecce49e44976c334e8d113c13c895dd`.
- Size: 201,616,184 bytes; 2,147 payload files.
- SHA-256: `688afd73a1b027c9d247bfc6969afafc8e195cadadd8ab0c0f9e42c0dafba456`.
- Matching `.manifest.json` and `.sha256` assets accompany the ZIP. Embedded file hashes and integrity pass.
- [Local validation and deterministic reproduction](../../geospatial/facilities/qa/workbench/VALIDATION.md); [visual QA](../../geospatial/facilities/qa/workbench/REVIEW.md).
- Final-head CI, merge and download-verification events are preserved in PR #124 and supplemental release closeout evidence. Publication follows successful gates; source-index metadata changes do not alter the packaged snapshot.

 New bundles include public source context and the existing offline atlas; original releases retain their identities and bytes. The approved R01 ZIP remains the same explicit immutable-source exception. Other historical ZIPs are excluded.

```sh
python geospatial/facilities/workbench/package_release.py \
  --revision <COMMITTED_SOURCE> --output /tmp/SABLE_HARBOR_Facility_Workbench_v1.0.0.zip
```

The deterministic builder verifies every embedded checksum and ZIP integrity. Published delivery requires PR gates, merge and retrieved bytes matching the recorded checksum.
