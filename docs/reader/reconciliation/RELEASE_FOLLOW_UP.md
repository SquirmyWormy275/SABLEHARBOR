# Operating-release counterpart follow-up

**Reviewed:** September 12, 2026. This is a supplemental search; the [448-row baseline audit](README.md) remains pinned to its original source revision and queue.

The existing `sable-harbor-business-operations-v1.0.0.zip` was read without extraction or modification. Its SHA-256 was independently checked as `b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817`. The [release index](../../releases/BUSINESS_OPERATIONS_RELEASES.md) provides its distribution context. The archive contains 566 members; all 26 JSON manifests were searched for each baseline source path and source hash.

[The search record](release-member-review.json) retains the release source revision, manifest member hashes and all 32 candidate records. Source-input provenance and a nearby financial workbook or PDF do not establish that the workbook/PDF renders that Markdown document. Inspection of the root source-input/artifact inventories and unit manifests did not establish an explicit document counterpart mapping for these candidates. No row was promoted to verified and no new artifact was produced.

This bounded search does not claim that every release or every possible counterpart has been examined. Historical snapshot matches remain subject to their own version and source-hash requirements. Native accounting schedules may support a document without being an equivalent publication of it.

To reproduce using a downloaded copy of the exact archive:

```bash
python docs/reader/reconciliation/review_release.py /path/to/sable-harbor-business-operations-v1.0.0.zip --check
```

The script verifies the archive checksum before reading its manifests. It neither downloads nor extracts release files and does not rewrite the baseline audit.
