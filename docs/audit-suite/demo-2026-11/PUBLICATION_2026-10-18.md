# November client-record publication decision

**Record ID:** `SH-DEMO-PUBLICATION-20261018`
**Decision date:** 18 October 2026
**Authority:** Repository owner's explicit instruction to put the actual November client data in the public repository.
**Acceptance:** Effective on merge into the controlling repository branch; a pending branch or pull request is not completed public delivery.

## Decision and purpose

The owner authorized publication of the three existing November client submissions so a consumer working from a public repository clone can use the actual evidence. Requiring access to the owner's workstation or an attachment did not satisfy that delivery requirement.

The [client-record directory](client-records/README.md) therefore retains the existing 70 synthetic artifacts and three manifests in Git. This is a narrow owner-approved exception to the default package placement in the [Repository Delivery and Packaging Policy](../../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md). It applies to these individually readable, manifest-verified directories and includes their walkthrough media. It does not create a general rule for other complete packages or duplicate ZIP archives.

## Published identities

| Directory | Edition | Artifacts | Original manifest SHA-256 |
|---|---|---:|---|
| [initial](client-records/initial/) | `SH-NOV2026-0-v1` | 58 | `6a827d65478af38409d5cb8c4960706eeba65a8c647c7e59b543ef41ae88615d` |
| [follow-up](client-records/follow-up/) | `SH-NOV2026-1-v1` | 5 | `a70e1bd7c7928149bd570d1bc98f623fde6401b058235aa24a0fe7ed89d1418a` |
| [correction](client-records/correction/) | `SH-NOV2026-2-v1` | 7 | `3fdaedefb890e1f9cf4ef4ea2e79002578000d3c4537c6dbca6388ef3f12b28a` |

Every artifact keeps its original path within its submission, bytes, version, source digest, availability date and relationship metadata. All three original directories passed the standalone verifier before copying. The repository copies must pass the same checks, and their manifests must match the hashes above, before merge. Current guidance sits outside the preserved submissions so documentation updates do not rewrite evidence.

## Supersession and boundaries

This decision supersedes the November completion guide's local-only delivery restriction for these three submissions. It also authorizes public access to all three stages at once. Their initial, follow-up and correction sequence remains evidence of simulated delivery history; it no longer provides restricted stage disclosure.

This record covers the verified client artifacts. The owner's broader publication of the accepted 5,714-version company source edition is recorded separately in the [data availability decision](../DATA_AVAILABILITY.md). Private operator selection and source maps, evaluator and answer material, credentials, and the separate CLEAN and MESSY auditor workspace databases remain outside the public company-record delivery. The source-delivery tool's validation and credential checks remain in force.

This is a repository publication decision, not a new company event or in-universe approval. It does not extend the [scope](SCOPE.md), change the fictional dates, remove stated evidence limitations or establish an audit conclusion. The [completion guide](COMPLETION.md) retains the earlier implementation and media-validation history; the accepting pull request records this publication's checks and integration.
