# Decision Register Addendum - Canon Closeout Decisions

**Document ID:** `SH-CANON-CLOSEOUT-20260906-001`  
**Version:** 1.0.0  
**Decision date:** September 6, 2026  
**Decision authority:** Repository owner's explicit approvals in the canon-closeout conversation  
**Repository promotion:** PENDING - draft source checkpoint, not completed closeout  
**Structured companion:** [Closeout decision record](../structured/canon_closeout_decisions_2026-09-06.json)

## Status and authority

The owner explicitly approved the decisions below. Their approval is preserved here so the
record does not depend on access to a conversation or attachment. This draft does not claim
that current `main`, controlled publications, catalogs, finance exports, or issue state have
already been reconciled. Approval, repository integration, canonical promotion, publication,
and issue closure are distinct events.

Once reconciled and accepted into the repository's controlling canon, this dated addendum
supersedes conflicting earlier statements within its exact scope. Unrelated OPEN matters
remain open. Historical board records, original design-session ledgers, released financial
snapshots, and prior artifact bytes retain their original dates and provenance. This editorial
record does not invent a new in-universe board meeting or backdate these approvals.

## CLOSE-001 - Daniel Mercer

**Approved canon state on promotion:** LOCKED

The founder and chief executive's full name is **Daniel Mercer**. This preserves the name
already used in the founding narrative and decision BR-002. Current-facing statements that
his surname was not supplied are superseded by this decision.

This naming decision does not establish any family relationship with Evan Mercer. It does
not change either person's identity, role, board membership, or history, and it does not
resolve other characters' surnames by implication.

Reconcile the current board doctrine and structured director record, corporate-lore
current-governance section, and finance collision COL-013. Preserve the collision's prior
statements and dated resolution rather than deleting its history. Existing finance source
locks and released packages must not be silently rewritten.

## CLOSE-002 - Semaphore precedence

**Approved canon state on promotion:** LOCKED vocabulary; runtime implementation remains separate  
**Issue:** #23

| Level | Agreed handling meaning |
|---|---|
| Routine | Handle through the normal reading and response cycle. |
| Priority | Expedite; waiting for the normal cycle could materially impair a decision. |
| Immediate | Interrupt normal work for prompt attention; an active situation needs a timely response. |
| Flash | Exceptional, time-critical traffic where delay could cause severe, imminent consequences. |

Precedence conveys handling urgency only. It does not confer truth, confidence, enduring
importance, author seniority, or authority to command. A Routine message can be strategically
profound; a Flash message can contain uncertain information. Foundational doctrine makes no
fixed response-time promise. Operational procedures may define justified handling targets
without changing those meanings.

Semaphore remains durable, searchable, threaded, supersession-aware, and human-authored.
Orientation Officers retain professional judgment over what merits traffic. Adoption does
not rewrite the metadata or vocabulary of historical cables.

## CLOSE-003 - Planned Alexandria AR and VR integration

**Approved canon state on promotion:** LOCKED ARCHITECTURAL DIRECTION; delivery details OPEN  
**Issue:** #25

Alexandria must be fully usable through an ordinary desktop interface. Future augmented
reality **and virtual reality** integration is planned, not merely an unspecified possibility.
The architecture should support those future interfaces without making headsets or spatial
hardware prerequisites for core use.

Spatial interaction serves understanding of relationships, chronology, physical locations,
evidence lineage, and competing interpretations. It does not create another institution or
change Alexandria's authority. Access, disclosure, provenance, uncertainty, and human-authorship
rules apply through every interface; visual prominence cannot imply truth or consensus, and
relationships cannot be exposed to unauthorized viewers.

No current AR/VR implementation, device, vendor, delivery date, or procurement commitment is
asserted. Detailed interface and runtime work remains open. Daedalus synthetic workspace
content remains non-authoritative and cannot automatically enter institutional records.

## CLOSE-004 - Repository delivery and packaging

**Approved canon state on promotion:** LOCKED repository policy  
**Issue:** #35; #37's specific catalog/SQLite lifecycle remains a separate unresolved decision

| Material | Agreed location and treatment |
|---|---|
| Canonical documents, code, schemas, configuration, generators | Versioned in the repository. |
| Approved source artwork and canonical visual references | Versioned in the repository with provenance. |
| Controlled corporate PDFs and publications | In the repository alongside their source lineage. |
| Complete distributable ZIP packages | GitHub Releases, with version identifiers, manifests, and checksums; linked from the repository index. |
| Temporary previews, intermediate renders, build debris | Excluded unless deliberately preserved as evidence. |

Nothing is considered delivered or closed merely because it exists in a conversation,
attachment, local scratch directory, or an assistant's completion statement. Chat approval
authorizes the change; repository integration and canonical acceptance make the controlled
record the source of truth. A branch or PR must be identified honestly as pending while it
has not been accepted into controlling canon. A checksum alone is not delivery of the bytes.

Every controlled release package must be discoverable from the repository and retrievable
from its recorded release location. Existing historical packages are preserved or deliberately
migrated with identity and checksums intact. This policy does not authorize bulk deletion,
reclassification of a quarantined archive as current, or rewriting prior release bytes.

Document thoroughly and keep the archive organized: maintain one controlling source per
decision, stable identifiers, explicit owners/status/dates where applicable, clear indexes,
cross-references, supersession links, and synchronized structured/publication representations.
Additional documentation must add traceability rather than create competing sources of truth.
The existing public/private boundary is unchanged; private evaluator material is not made
public by a repository-delivery requirement.

## Implementation checkpoint - September 6, 2026

**Base reviewed:** `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`  
**Checkpoint state:** SOURCE-ONLY DRAFT; publications and final acceptance pending

The four affected Alexandria doctrine sources and the existing Pinakes Semaphore entry
have been edited to reflect CLOSE-002 and CLOSE-003. This addendum and its structured companion
preserve all four approvals. Remaining current-source, authority-policy, navigation, and
Daniel/COL-013 reconciliation is not claimed complete.

The existing publication builder requires LibreOffice, Ghostscript, and qpdf. This environment
provides a headless office runtime and Ghostscript, but qpdf was absent. Normal package
installation/update failed, including environment permission errors. No installation bypass,
alternative renderer, or successful publication rebuild is claimed. Existing PDF files and
their manifests/catalogs are therefore not current representations of these source edits.

Before canonical promotion and issue closure:

- [ ] Finish current-facing Daniel, decision-register, authority-policy, and navigation reconciliation.
- [ ] Publish the approved packaging policy and index its source/structured/publication representations.
- [ ] Align current-source versions and controlled-publication output versions.
- [ ] Rebuild affected controlled PDFs, publication manifests, JSON catalog, and SQLite catalog using an accepted toolchain.
- [ ] Visually inspect changed publications and verify source/output hashes and links.
- [ ] Run applicable maintainer validators, focused regression tests, the repository test suite, and diff checks.
- [ ] Accept the reconciled commit into controlling canon on `main`; record the actual commit/PR and validation evidence.
- [ ] Close #23 and #25 only for the agreed decision scope; retain AR/VR implementation limits explicitly.
- [ ] Close #35 only after its repository-wide policy and artifact disposition criteria are satisfied.

Issues #11, #12, #18, #19, #21, #22, #24, #33, #34, #37, #38, #44, and #88 are not
resolved by this checkpoint. No claim is made that the separate geospatial or ARU draft PRs
have been integrated.
