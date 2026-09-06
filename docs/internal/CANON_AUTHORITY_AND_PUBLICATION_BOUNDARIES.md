# CANON AUTHORITY AND PUBLICATION BOUNDARIES

**Document ID:** `SH-INT-AUTH-BDY-001`  
**Version:** 1.1.0
**Updated:** September 6, 2026
**Status:** LOCKED INTERPRETIVE CONTROL  
**Owner:** Corporate Governance / J2 Headquarters  
**Related:** [Design-session ledger](CHAT_CANON_LEDGER_J2_ALEXANDRIA.md); [board records](../governance/board-records/README.md); [controlled-document index](../CONTROLLED_DOCUMENT_INDEX.md); [delivery and packaging policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md)

## Purpose

This record prevents generated artifacts from laundering unsupported authority into Sable Harbor canon.

A repository commit, controlled PDF, publication manifest, validation pass, SQLite catalog entry, or repeated cross-reference does not independently prove that a proposition was approved. Those artifacts are evidence of implementation and reconciliation. They do not create approval by themselves.

## Current source hierarchy

1. Current accepted controlling canon under `docs/canon/`, including dated decisions and their explicit supersession scope.
2. The in-universe board approval records where they ratify governance, financing, J2, Alexandria, and controlled-publication authority.
3. Repository-stored design-session ledgers and forensic audit records preserving originating decisions, except where a later accepted controlling record supersedes them.
4. Canonical Markdown source doctrine.
5. Generated publications, structured records, catalogs, validators, and indexes.

If a generated publication or structured record conflicts with the source doctrine, the source doctrine controls until corrected.

If source doctrine conflicts with an applicable ledger or board record, resolve and record the
conflict rather than hiding it through regeneration. Preserve historical statements with their
original dates; identify the later controlling resolution in current-facing records. This order
aligns with [MAINTAINERS.md](../../MAINTAINERS.md) and does not retroactively rewrite the
September design sessions or invent a later in-universe Board approval.

## Repository acceptance and delivery

Conversation approval is authority to make the approved change and provenance for its recorded
decision. It is not a substitute for delivery. Preserve the approval's substantive content in
the repository, reconcile affected sources, and accept the result into controlling canon.
Only then does the accepted record become the source of truth within its stated scope.
No reader should need a private conversation or attachment to discover current canon.

A pending branch or PR is a preserved checkpoint, not completed canonical integration. Neither
a commit without approval nor a completion statement without delivered bytes establishes canon
or closes work. The accepted source record controls its structured/publication representations;
those representations preserve and expose its meaning rather than independently approving it.

The [September 6 closeout addendum](../canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md)
records the owner's approved decisions and their integration boundary. The
[delivery policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md) defines actual
artifact locations, indexed releases, historical exceptions, and closeout evidence. It leaves
issue #37's specific catalog/SQLite lifecycle unresolved and preserves public/private boundaries.

The finance-pinned v0.3 lore, base decision register, and board v1.0.0 source are preserved
byte-for-byte for the older finance snapshot. CLOSE-001 supersedes their conflicting surname
statements; the [current board doctrine is v1.0.1](../governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md).
The dated addendum and separately versioned successor provide current authority while the
unchanged earlier sources preserve historical reproducibility. A later canon decision does
not silently alter the source perimeter or bytes of an already published finance release.

## Board approval versus document generation

The Board may approve a doctrine, charter, or system by meeting minutes or written consent. A generator may then publish the approved source into a PDF or catalog entry.

The generator is not the approver.

A polished letterhead, checksum, or validation pass never turns an unapproved idea into canon.

## Version and state discipline

A document may be publication version `1.0.0` while its underlying implementation remains `LOCKED DIRECTION`, `LOCKED ARCHITECTURAL DIRECTION`, `PROVISIONAL`, or `OPEN` in specific areas.

The state field describes substantive authority, not visual polish.

## Validation discipline

Validators may enforce actually approved canon, required files, source/publication reconciliation, and safety boundaries. They must not convert a one-time implementation snapshot into permanent canon merely because a previous phase happened to produce a specific number of topics, PDFs, rows, or files.

Counts that are true canon, such as nine current directors, five standing committees, and the nine accepted Pinakes doors, may be enforced. Counts that are historical execution metadata should be treated as minimum sanity checks or audit facts rather than governing design.

## Slop control

Future additions should be tested against one question before being elevated into doctrine:

> Did Sable Harbor actually decide this, or is this a plausible completion added because the structure looked incomplete?

If the answer is plausible completion, the content should be deleted, demoted to an implementation note, or marked provisional rather than allowed to crowd the signal.
