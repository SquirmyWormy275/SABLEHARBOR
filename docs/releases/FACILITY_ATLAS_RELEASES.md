# Facility atlas controlled releases

## v0.2.0 / R02 — pending acceptance

Acceptance vehicle: [PR #121](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/121). Scoped R02 facility visual QA is recorded; final runtime/atlas integration QA, deterministic regeneration, final-head CI, merge and release publication remain pending. This index does not claim a published delivery.

The successor preserves the [approved R01 references](../facilities/references/sacramento-hq/r01-approved/README.md), ingested in `ebe7e9e`, and replaces the pre-recovery six-building Sacramento design. Its source program has four Sacramento buildings, ten floors, 175,392 sf gross, 362 workplaces and 60 single rooms. The original facility subpackage is 16 sites, 17 buildings, 24 floors and 58 sheets in 174 independent SVG/PNG/PDF assets. The [accepted runtime bridge](../../geospatial/facilities/RUNTIME_BRIDGE.json) reuses twelve plates and adds three sites, one proposed owned building and one floor. Combined inventory is 19 location packages, 18 buildings, 25 floors and 70 plates in 210 SVG/PNG/PDF assets, alongside eleven preserved rc4 context records (81 maps total). Actual personnel, occupancy, property and construction boundaries remain explicit.

| Required release evidence | Current state |
|---|---|
| Version/tag | `facility-atlas-v0.2.0` reserved for the successor |
| Package | `SABLE_HARBOR_Facility_Atlas_v0.2.0.zip`; final bytes and SHA-256 pending |
| File manifest and checksum | Same basename with `.manifest.json` and `.sha256`; pending final build |
| Exact packaged source commit | Pending final validated committed snapshot |
| Canon bases | Initial `786fc9a5311a04dde92ee6dbb08ac3b77a380200`; R01 ingestion `ebe7e9e`; accepted runtime main `b83e4be2182a5e4143808a3dab5f8d929a133caf`, integrated through `5d7e5a0` |
| PDF pages, bookmarks and link totals | Pending final atlas manifest |
| QA / CI / merge | Pending exact final-head evidence |
| Published download and retrieval verification | Pending gated publication; no delivery asserted |

Build only from the final committed snapshot:

```sh
python geospatial/facilities/package_release.py \
  --revision <FINAL_VALIDATED_COMMIT> \
  --output /tmp/SABLE_HARBOR_Facility_Atlas_v0.2.0.zip
```

The builder validates ZIP integrity and every embedded checksum, with fixed member timestamps, ordering and permissions. It includes the public repository source context so provenance links resolve offline. One release-navigation file is generated to avoid a circular archive checksum. Historical source statuses retain their original scope.

The two historical distribution ZIPs remain excluded. The immutable owner-supplied approved source archive, `docs/facilities/references/sacramento-hq/r01-approved/SABLE_HARBOR_Sacramento_HQ_Drafts_R01.zip`, is an explicit inclusion exception: SHA-256 `eb10588f6cc6e214d8541b96b1bd044f52f0df85e384fc53a316b55b5d026fe0`. The builder rejects changed or missing reference bytes. This is preserved source artwork, not a duplicate generated delivery ZIP. The original PNGs, handover, addendum and reference manifest are also included unchanged.

Start at `geospatial/maps/index.html`, the separate `geospatial/maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf`, or the individual artifact index. The [closeout record](../../geospatial/facilities/CLOSEOUT_2026-09-11.md) tracks remaining evidence. Publication requires retrievable download bytes matching the final checksum; published identities must never be silently overwritten.

## v0.1.0 — superseded unpublished draft

The pre-R01 draft was **not published**. Its earlier package and QA evidence are historical build records, not accepted delivery or current campus authority. Do not use its six-building plans, capacities, atlas totals or checks as R02 acceptance evidence. The reserved draft tag/name is superseded by v0.2.0.

For archaeology only: source commit `dcb827cf296ee5a2e1eb31874d7997c320b1aa6b`; draft ZIP size 148,862,665 bytes; SHA-256 `8fb51b8b42eb09b3446977d1c6dc1c4f8faf13dc5887b49bb4a2dc1b26110168`. Its 63-sheet/189-asset, 19-building/27-floor inventory predates recovery of approved R01. These recorded draft bytes are not linked as a published release. The existing published finance releases and rc4 geographic atlas are unaffected.
