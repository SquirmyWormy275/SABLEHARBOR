# REPOSITORY DELIVERY AND PACKAGING POLICY

**Document ID:** `SH-GOV-DELIVERY-001`
**Version:** 1.0.0
**Decision date:** September 6, 2026
**State:** LOCKED on acceptance into controlling repository canon
**Owner:** Repository owner
**Stewardship:** Repository maintainers
**Authority:** [CLOSE-004](../canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md#close-004---repository-delivery-and-packaging)
**Structured companion:** [Repository delivery and packaging policy](../structured/repository_delivery_and_packaging_policy.json)

## 1. Completion and canonical acceptance

Nothing is delivered or closed merely because it exists in a conversation, attachment, local
scratch directory, or completion statement. A checksum without retrievable artifact bytes is
not delivery. An approved decision must be recorded, reconciled, and accepted into the
repository's controlling canon before it becomes the source of truth. A pending branch or PR
is a preserved proposal or implementation checkpoint and must be described as pending.

Conversation approval is originating authority and provenance for a change. Preserve its
substance in a dated repository decision record; the reader must not need access to the
conversation to determine current canon. Once accepted, that record and its stated
supersession scope control. A commit alone does not create approval, and an approved draft
alone does not establish completed repository integration.

Closeout evidence identifies the accepted commit or PR, controlling records, delivered artifact
paths or release URLs, applicable validation results, and any remaining limits. Closing a
decision issue does not claim that separately deferred implementation has been delivered.
This repository policy records the owner's approval; it does not invent an in-universe Board
meeting, consent, or ratification.

## 2. Repository-wide artifact disposition

| Material | Location and treatment |
|---|---|
| Canonical documents, code, schemas, configuration, generators | Versioned in Git. Preserve source identifiers, status, and lineage. |
| Approved source artwork and canonical visual references | Versioned in Git with provenance and rights information. An approved source-artwork exception, including the controlling J2 PNGs, remains explicit. |
| Controlled corporate PDFs and publications | Versioned in Git alongside their source lineage. Regenerate from accepted source; reconcile versions, manifests, and hashes. A publication does not independently create canon. |
| Complete distributable ZIP packages and other packaged bundles | New versions belong in indexed GitHub Releases, with version identifiers, manifests, and SHA-256 checksums. Do not add duplicate current package bytes to the Git tree by default. |
| Convenience renders and previews | Temporary by default. Retain a useful review or evidence render deliberately, with its purpose and source identified; it acquires no independent authority. |
| Temporary previews, intermediate renders, caches, build debris | Exclude from Git unless deliberately retained as evidence. Local generation is a working step, not delivery. |
| Generated institutional JSON/SQLite catalogs | Keep their current in-tree placement and existing regeneration rules while issue #37 remains OPEN. This policy does not decide their complete lifecycle. |

The narrow historical ZIP exceptions in section 4 justify retaining the existing bytes in-tree.
They do not make the default for new distributable versions ambiguous. Controlled individual
publications remain in-tree even when a release bundle also includes them.

## 3. Release identity, discovery, and corrections

Every controlled release package must be discoverable from the repository's
[controlled-document index](../CONTROLLED_DOCUMENT_INDEX.md), directly or through an indexed
release record, and retrievable from its recorded release location. That record identifies the
version/tag, source commit and relevant canon snapshot, package asset names, manifests,
SHA-256 checksums, limitations, and supersession or historical status where applicable.
GitHub's automatically generated source-code archive is not a substitute for a deliberately
assembled controlled package.

Preserve published package identity and bytes. Corrections receive a new version and changelog;
they do not silently replace an old ZIP under its existing name. Any later relocation must
verify destination bytes against the recorded hash, update navigation, and retain provenance
and disposition flags. A move is complete only after destination retrieval and checksum
verification. This policy does not claim that such a migration has occurred or authorize bulk
deletion of historical artifacts.

The [finance release process](../commercialization/RELEASE_PROCESS.md) continues to govern
finance-specific builds, source locks, safety checks, and package manifests. Its published
snapshots are not rewritten to incorporate a later canon decision. A successor release must
record its own source scope and boundaries.

## 4. Existing package disposition and release index

This inventory records the two tracked ZIPs found in the September 6, 2026 closeout checkout
and the existing published finance release. Local ZIP hashes and sizes were calculated from
their bytes. Finance asset metadata was read from the GitHub release API on September 6,
2026; the API digest and release record are provenance for this inventory, not a claim of a
new local download or revalidation of their internal manifests.

### 4.1 Brand archive: preserved, not distributable

- **Path:** `assets/brand/packages/sable-harbor-logo-system-v0.1.0.zip`
- **Version / size:** `0.1.0` / 2,635,913 bytes.
- **SHA-256:** `8c5d9c6c0de8163896a6ddc9c318f90a4927f5b2e54eba081c829aac20301ecd`
- **Disposition:** explicit historical exception; retain the original in-tree bytes.
- **Existing controlling flags:** `SUPERSEDED`, `HISTORICAL_SNAPSHOT`, `DO_NOT_DISTRIBUTE`.
- **Source of flags:** [Brand package manifest](../../assets/brand/packages/manifest.json).

The archive is effective through September 2 and was superseded September 5. It predates the
approved Pale Sun/Red Wash raster-source overrides and contains noncurrent J2 stationery.
The manifest records no current replacement. This policy neither removes those flags nor
promotes the archive into a current release. A future distribution must be a separately built,
reviewed, versioned package with the current approved assets.

### 4.2 Organization briefing: retained prior package

- **Path:** `docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.zip`
- **Version / size:** `1.0.0` / 1,437,035 bytes.
- **SHA-256:** `6a058ac51d686ef24987fa4a46e3299f79a2e22891569aa676621b6d88a84b6e`
- **Disposition:** explicit historical placement exception; retain unchanged in-tree.
- **Source records:** [Briefing index](../organization/briefing/README.md) and
  [briefing manifest](../organization/briefing/manifest.json), canonical date August 31, 2026.

Keeping this previously delivered package preserves existing links and audit/training history
without rewriting its bytes. Its source manifest supplies no separate distribution-state
flag; this policy does not invent one or certify the package against later canon. Its exact
ZIP hash is newly inventoried here because the briefing manifest inventories individual
outputs rather than the enclosing ZIP. A future revised distributable version belongs in a
GitHub Release. The old package is not silently regenerated in place.

### 4.3 Published finance release: retained at its release location

**Release:** [Sable Harbor finance v0.1.0](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/sable-harbor-finance-v0.1.0)
**Tag:** `sable-harbor-finance-v0.1.0`
**Published:** September 5, 2026
**Source commit:** `4f837ebb229c68baa3655312726febb31cd0d2ba`
**Pinned canon source:** `712076751a31534cd9e6e41458336cdc7b6585b5`

| Published asset | Bytes | Recorded SHA-256 |
|---|---:|---|
| [Public demo ZIP](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-finance-v0.1.0/sable-harbor-finance-public-demo-v0.1.0.zip) | 364,064 | `9eee33de25040a784abe82c12252011a98c129a94637268ba1fd8598f8cbbb8d` |
| [Business-unit evidence ZIP](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-finance-v0.1.0/sable-harbor-finance-business-unit-evidence-v0.1.0.zip) | 216,637 | `ee2253e4ca340aa38f08bc6a1b9d4bd0b045ceccdb58139e6204be9f51e52f36` |
| [Package checksum inventory](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-finance-v0.1.0/sable-harbor-finance-v0.1.0-SHA256SUMS.txt) | 231 | `0b252f7c54d724bd9cbc0ee790d03d770d571e7c998bf2b67d356eb70ba5e515` |

The release record identifies nested manifests/checksum inventories in both ZIPs. Preserve
the release's `PUBLIC_SAFE_SYNTHETIC` classification, `RETROSPECTIVE_CURRENT_CANON` mode,
canon effective through September 3, and September 5 preparation date. August 31 is its
synthetic calibration boundary. It remains a published snapshot; this inventory does not
assert that its modeled or OPEN facets became canon or that the seven evidence packages
satisfy the broader unfinished audit-package requirements in issue #12.

### 4.4 Historical audit and future inventory changes

The [September 3 size audit](../internal/REPOSITORY_SIZE_AND_GENERATED_ARTIFACT_AUDIT_2026-09-03.md)
remains unchanged as a dated observation. Its possible future placement choices are superseded
by this policy within this policy's scope. Its recorded repository size is not a current
measurement. Existing convenience renders remain unless deliberately reviewed; no deletion or
mass reclassification is implied. Record future package additions, replacements, or moves in
the indexed release record with their actual evidence.

## 5. Thorough, organized documentation

Maintain one controlling source for each decision, with stable identifiers, dates, owners
where applicable, explicit status, cross-references, and supersession links. Keep the README
and controlled-document index navigable. Synchronize structured records, controlled PDFs,
publication manifests, and derived catalogs to their controlling sources; distinguish a
canonical structured input from a generated representation. Additional documentation should
add evidence and traceability without creating competing current answers.

Preserve history with its original context. Current-facing summaries must point to the
controlling resolution when an older record conflicts. Organization is part of delivery:
an unindexed package or an undocumented dependency on a chat attachment is unfinished.

## 6. Explicit boundaries

- Issue #35's packaging decision can close after this policy and its disposition inventory
  are accepted and indexed. The retained ZIPs satisfy its allowance for justified in-tree
  packages; their migration is not a prerequisite or a claimed accomplishment.
- Issue #37 remains OPEN for the specific generated-catalog/SQLite lifecycle. Current
  catalogs remain generated, non-authoritative representations under existing rules.
- Retention/deletion, collection access, and other unresolved institutional policies are
  not settled by a packaging location rule.
- Existing public/private and rights boundaries remain in force. Delivery to the appropriate
  controlled repository does not authorize publishing private evaluator material or widening
  access. Preserve the separation from `SABLEHARBOR-ALEXANDRIA-CONTROL`.
- Use the applicable [maintainer validation gates](../../MAINTAINERS.md). Completion must cite
  actual results and accepted repository state rather than an anticipated successful build.
