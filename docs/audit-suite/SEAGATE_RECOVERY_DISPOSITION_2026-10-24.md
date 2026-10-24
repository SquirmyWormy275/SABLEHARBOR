# Seagate recovery disposition, 24 October 2026

The 133 archive families in the explicitly named Sable Harbor Seagate recovery
folder have recorded GitHub dispositions. The [family index](recovery/SEAGATE_ARCHIVE_DISPOSITIONS_2026-10-24.json)
provides one row per original archive, its exact SHA-256 and compressed byte size,
and its accepted source-catalog commit and PR where recorded. It exports only
approved metadata fields from the preserved private reconciliation ledger.

| Disposition | Families | Meaning |
|---|---:|---|
| Private original preservation | 131 | Original recovery bytes and source context are preserved in the owner-approved private Alexandria repository; the individual delivery and fresh-retrieval receipts control. |
| Verified equivalent cache | 2 | Accepted geospatial history preserves the unique source and evidence, with an explicit [cache equivalence record](../../geospatial/history/v1.5.0-previews-2026-10-03/CACHE_EQUIVALENCE.json); original cache wrappers were retired. |

The original compressed archives total **28,962,562,508 logical bytes**. This is
an archive-byte total, not a measure of unique company records, expanded data,
or physical disk space reclaimed. It includes historical editions and test
material. Preserving such material does not adopt it as current canon or certify
that a scenario event occurred.

The owner explicitly approved the existing private Alexandria repository for
restricted recovery records and later authorized incremental removal of verified
Sable Harbor local copies. Each archive was removed only after its recorded
accepted preservation or equivalence decision and retrieval gate. Twenty loose
recovery originals and one additional restricted control item also received
individual dispositions. Their detailed private records are available through
the [private evidence continuation](https://github.com/SquirmyWormy275/SABLEHARBOR-ALEXANDRIA-CONTROL/releases/tag/sableharbor-recovery-ledgers-provisional-part2-2026-10-24).

At the dated observation in the index, this named Seagate folder contained no
regular files or links. Its root and seven empty descendant directories remained.
This observation applies only to that folder. No unrelated drive directories,
personal files or Steam files were changed or deleted.

## Trace a recovered source

Start with [company data availability](DATA_AVAILABILITY.md) for the accepted
5,714-version company library and the three separate November submission stages.
The original CLEAN and MESSY histories remain distinct; archive preservation does
not combine them or replace their controlling sources.

For an archive-specific check, locate its whole-file SHA-256 in the family index.
The accepted commit links identify its source-catalog decision. Authorized private
readers can then use the exact source-ledger name and digest pinned in the index
to retrieve its original path, archive/member mapping, sensitivity decision,
immutable release assets and per-stage verification/removal receipt. The
`evidence_row_sha256` is the SHA-256 of that private source row serialized with
sorted keys, compact JSON separators, and a trailing newline. Opaque family IDs
retain the source-ledger row order and confer no company authority.

The public index omits private filenames, archive member names, credentials,
hidden evaluation truth and private contact data. A private link requires owner
authorization; it does not make the public company library depend on the author's
computer or a running workroom.

## Remaining boundary

This is a Seagate archive disposition record. The wider laptop reconciliation,
unique Git changes, operating dependencies and remaining historical sources are
still tracked in [recovery issue #203](https://github.com/SquirmyWormy275/SABLEHARBOR/issues/203).
The 1,232-row candidate inventory remains a source-discovery ledger, not a claim
of 1,232 unique projects. No whole-workstation cleanup clearance or branch-pruning
authorization follows from this index. Empty-directory removal and later
completion observations require their own dated records.

Repository delivery follows the [delivery policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md).
Source authority and historical limitations remain those of the accepted domain
records. No professional audit opinion or real external execution is asserted.
