# Decision Register Addendum - Canon Closeout Decisions

**Document ID:** `SH-CANON-CLOSEOUT-20260906-001`  
**Version:** 1.0.0  
**Decision date:** September 6, 2026  
**Owner:** Repository owner
**State:** LOCKED decisions; expressly reserved implementation remains OPEN
**Decision authority:** Repository owner's explicit approvals in the canon-closeout conversation  
**Repository promotion:** Controlling when PR #97 is accepted into `main`; branch copies alone are not canonical promotion
**Structured companion:** [Closeout decision record](../structured/canon_closeout_decisions_2026-09-06.json)

## Status and authority

The owner explicitly approved the decisions below. Their approval is preserved here so the
record does not depend on access to a conversation or attachment. The accepted repository
record is the source of truth. Approval, repository integration, canonical promotion,
publication, and issue closure are distinct events. PR #97 supplies the integration history;
the [validation record](../internal/validation/CANON_CLOSEOUT_2026-09-06.md) supplies execution
evidence. A draft branch, generated PDF, checksum, or passing test alone does not create approval.

Once reconciled and accepted into the repository's controlling canon, this dated addendum
supersedes conflicting earlier statements within its exact scope. Unrelated OPEN matters
remain open. Historical board records, original design-session ledgers, released financial
snapshots, and prior artifact bytes retain their original dates and provenance. This editorial
record does not invent a new in-universe board meeting or backdate these approvals.

## CLOSE-001 - Daniel Mercer

**Canon state:** LOCKED

The founder and chief executive's full name is **Daniel Mercer**. This preserves the name
already used in the founding narrative and decision BR-002. Current-facing statements that
his surname was not supplied are superseded by this decision.

This naming decision does not establish any family relationship with Evan Mercer. It does
not change either person's identity, role, board membership, or history, and it does not
resolve other characters' surnames by implication.

The current [board doctrine v1.0.1](../governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md),
structured director record, and finance collision COL-013 agree with this name. This
addendum supersedes conflicting current-governance statements in the earlier corporate
lore and decision register within this scope. The collision retains its prior statements
and dated resolution. The finance-pinned corporate lore v0.3, original decision register,
and board doctrine v1.0.0 retain their exact source bytes; they are historical baselines,
not competing current answers. Existing finance source locks and released packages retain
their original snapshots; they must not be silently rewritten.

## CLOSE-002 - Semaphore precedence

**Canon state:** LOCKED vocabulary; runtime implementation remains separate
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

**Canon state:** LOCKED ARCHITECTURAL DIRECTION; delivery details OPEN
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

**Canon state:** LOCKED repository policy
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

## Repository implementation and historical checkpoint

**Base reviewed:** `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`

The initial source-only checkpoint was preserved in commit
`26644c3bb51625fde8e5f866cb561cf729f3357e`. It accurately recorded the then-missing qpdf
dependency and denied package-installation attempt. The owner subsequently authorized a
narrow publication-builder compatibility update, reconciliation, validation, and merge.
That permission does not grant new in-world authority to an AI or change Daedalus doctrine.

The compatible build keeps office rendering and Ghostscript page sizing, adds an explicit
pypdf normalization backend, and records the selected backend on newly built publications.
It does not promise byte identity across different toolchains. Historical PDFs and package
bytes are retained with their original identity; the current manifest identifies replacements.

The [delivery policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) records the
repository-wide artifact disposition, including named historical ZIP exceptions and the
existing finance release. The [validation record](../internal/validation/CANON_CLOSEOUT_2026-09-06.md)
records checks actually executed, limitations, and the publication/merge evidence. GitHub
issue state records actual closure: #23 and #25 cover these decision scopes, and #35 covers
the adopted packaging policy and documented disposition. AR/VR runtime completion is not
claimed by closing its architectural-direction issue.

Issues #11, #12, #18, #19, #21, #22, #24, #33, #34, #37, #38, #44, and #88 are not
resolved by this addendum. No claim is made that the separate geospatial or ARU draft PRs
have been integrated.
