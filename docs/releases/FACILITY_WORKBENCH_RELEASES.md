# Facility planning workbench releases

## v1.0.0

Owner-authorized companion to the accepted facility atlas v0.2.0. It adds capacity experiments, source-change impact traversal, architectural concept readiness and evidence candidate intake/review. It does not change approved R01 originals, accepted R02 floor geometry, workforce facts or engineering authority.

Entry point: [offline workbench](../../geospatial/maps/workbench.html). [Methods, source and commands](../../geospatial/facilities/workbench/README.md). Accepted facility base: `7bc9879fb94dbf999066b8072cc66ec8e05fda0a`.

Release tag: `facility-workbench-v1.0.0`. Exact package source, hash and acceptance evidence are recorded here before publication. New bundles include public source context and the existing offline atlas; original releases retain their identities and bytes. The approved R01 ZIP remains the same explicit immutable-source exception. Other historical ZIPs are excluded.

```sh
python geospatial/facilities/workbench/package_release.py \
  --revision <COMMITTED_SOURCE> --output /tmp/SABLE_HARBOR_Facility_Workbench_v1.0.0.zip
```

The deterministic builder verifies every embedded checksum and ZIP integrity. Published delivery requires PR gates, merge and retrieved bytes matching the recorded checksum.
