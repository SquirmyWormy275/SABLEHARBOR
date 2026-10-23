# September 11 staged facility workline — historical recovery

**Status:** HISTORICAL / UNACCEPTED STAGED WORKLINE. **Source date:** September 11, 2026. **Imported:** October 23, 2026. **Current authority:** the [accepted R02 facility atlas](../../README.md), its [v0.2.0 release](../../../../docs/releases/FACILITY_ATLAS_RELEASES.md), and later canon.

The original handover captured a 90-sheet facility workline, 91 reachable drawings and a 93-page review atlas. Its 483-path staged repository overlay was never accepted as main at the reported local commit `c991d7868fe7269733e66494fa07dc2506adee8a` or staged tree `10c01c14385cba5636714c6aa32391c9bd2c4d4a`. The current R02 implementation made further source and visual corrections and accepted a **58-sheet** facility program, with twelve reused runtime plates. Do not import the older overlay on top of R02 or use its counts as current occupancy, engineering or audit evidence.

The handover also carries the four separately [approved Sacramento R01 source images](../../../../docs/facilities/references/sacramento-hq/r01-approved/README.md). Those originals are already in accepted Git and remain the visual reference. Approval of those four images does not approve the entire 90-sheet staged overlay. The [dated recovery ledger](../../recovery/README.md) and [R02 closeout](../../CLOSEOUT_2026-09-11.md) explain the later authority decisions.

## Exact historical sources

The [historical release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/facility-workline-staged-history-2026-09-11) holds both original ZIPs. The inner ZIP is also a byte-exact member of the outer ZIP; the separate asset makes direct retrieval easier. Neither ZIP is an ordinary Git object or a current build input.

| Original asset | Bytes | SHA-256 | Contents and role |
|---|---:|---|---|
| `SABLE_HARBOR_COMPLETE_CODEX_HANDOVER_AND_RECOVERY_2026-09-11.zip` | 88,672,423 | `ece5f7183c1bc54f460830bf6ed7d72c9b178ef21dcf51664dc545895a1c90f7` | Eleven entries: handover, checksums, four approved R01 PNGs, original R01 ZIP and the inner recovery ZIP. |
| `SABLE_HARBOR_FACILITIES_RECOVERY_2026-09-11.zip` | 85,188,887 | `029a2c83240b53e2f54f7cfe43d833a8def935c806ff0f00b6f828e85e288354` | 492 entries: 483 declared staged overlay files and nine recovery/publication-history records. |

[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) identifies each member, its size, SHA-256, CRC and Git blob ID; it records whether that blob is reachable from accepted main and whether a current path has the same bytes. Fourteen inner members are exact Git objects in the compared accepted history; 478 are not. This byte comparison does not make any old draft controlling. The source's own `RECOVERY_MANIFEST.json` verifies all 483 staged overlay members against their original hashes and Git IDs. The outer `MANIFEST.sha256` verifies ten companion entries.

To verify downloaded assets without extraction:

```sh
python geospatial/facilities/history/staged-workline-2026-09-11/verify.py /path/to/downloaded-assets
```

The verifier requires the exact two ZIPs, streams every member, checks their CRC/SHA-256/Git ID, checks both internal manifests and proves that the nested ZIP matches the standalone asset. The archive's site and workforce assumptions remain historical planning context. Current [facility coverage](../../coverage/COVERAGE_MATRIX.md), [population bridge](../../population/BRIDGE.md) and [source program](../../PROGRAM.md) govern use of the corrected plans. Actual occupancy, title, provider contracts, installed capacity and audit performance require their own evidence.

Other Seagate, Download and worktree sources are still being reconciled under [archive issue #202](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/202) and [local-source issue #203](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/203). This historical delivery clears no local path for deletion.
