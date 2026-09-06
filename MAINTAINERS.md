# Maintainer Rules

This repository is the Sable Harbor canonical synthetic enterprise archive. Maintainer work must preserve the distinction between canon, generated representations, historical records, and implementation convenience.

## Authority order

Use this order when resolving conflicts among accepted repository records:

1. Current controlling canon under `docs/canon/`, including accepted dated decisions and their explicit supersession scope.
2. In-universe board records where they ratify governance, financing, J2, Alexandria, or publication authority.
3. Repository-stored chat-derived canon ledgers and forensic audit records where they preserve originating design decisions, except where a later accepted controlling decision supersedes them.
4. Canonical Markdown source documents under `docs/`, including governance, organization, controls, J2, and Alexandria doctrine.
5. Structured records, generated PDFs, catalogs, SQLite indexes, rendered images, and distributable packages.

Generated artifacts never create canon by repetition, polish, checksum, or catalog inclusion. If a generated artifact conflicts with a canonical source, correct the source or generator first, then regenerate.

Conversation approval authorizes a change; it must be preserved in a repository decision record,
reconciled, and accepted into controlling canon before the change is treated as canonical.
An external conversation is provenance, not a competing live source of truth. A branch or PR
remains pending until accepted. A commit alone does not create approval. See
[Canon authority and publication boundaries](docs/internal/CANON_AUTHORITY_AND_PUBLICATION_BOUNDARIES.md).

Preserve source files explicitly pinned by an immutable finance release. Record later canon
through a dated superseding addendum and, where needed, a separately versioned successor
source. The September 6 closeout retains the pinned v0.3 lore, base decision register, and
board v1.0.0 source; [board v1.0.1](docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md)
and CLOSE-001 govern the current founder/CEO name. Do not weaken source-lock validation to
make a later canon update appear to belong to an older finance snapshot.

## Delivery and packaging

Follow the [Repository Delivery and Packaging Policy](docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md),
approved under CLOSE-004. Nothing is delivered or closed solely because it exists in chat,
an attachment, scratch storage, or a completion statement. Record the accepted commit/PR,
controlling paths, artifact locations, validation evidence, and remaining limits.

Keep canonical source, code, approved visual sources, and controlled corporate publications
in Git. Publish new complete distributable package versions in indexed GitHub Releases with
manifests and checksums. Preserve the policy's explicitly inventoried historical ZIP exceptions
and all existing disposition flags; do not rewrite prior bytes or imply a migration occurred.
Exclude temporary build outputs unless deliberately retained as evidence. Keep documentation
thorough and indexed, with one controlling source per decision and synchronized derivatives.

Issue #37 remains OPEN: the generated institutional catalog and SQLite index retain their
current placement and regeneration rules pending their specific lifecycle decision.

## Canon states

Use the repository state vocabulary precisely:

- `LOCKED` means accepted canon.
- `LOCKED DIRECTION` means the institutional direction is accepted, but some implementation detail can still mature.
- `LOCKED ARCHITECTURAL DIRECTION` means the architecture is accepted, while runtime implementation remains open.
- `PROVISIONAL` means accepted working direction, not final canon.
- `OPEN` means unresolved and must not be silently invented.
- `SUPERSEDED` means preserved history that no longer controls current canon.
- `SUPERSEDED IN PART` means a document remains historically useful but later records control identified parts.

Do not promote an `OPEN` or `PROVISIONAL` matter to `LOCKED` for symmetry, documentation neatness, or validator convenience.

## Manual edit versus generated artifact boundaries

### Edit manually

- Canonical Markdown source documents.
- Governance, J2, Alexandria, controls, organization, and internal audit-trail Markdown.
- Structured registers when they are the canonical structured source for a decision.
- Validator source code.
- README and navigation documents.

### Regenerate, do not hand-edit

- Controlled PDF publications.
- `institutional_catalog.json`.
- `institutional_catalog.sqlite3`.
- Generated chart PNGs where source SVG/tooling exists.
- Publication manifests and checksum manifests.
- Distributable ZIP packages, unless the package is a preserved external artifact.

### Special case: J2 identity

The approved J2 PNG files are controlling source artwork. SVGs are vector derivatives and must not supersede or reinterpret the approved PNGs. Do not manufacture additional J2 marks or variants without an identity decision.

## Required validation before merge

Run the applicable checks before merging changes that touch canon, governance, J2, Alexandria, organization maps, controlled publications, generated catalogs, or public repository safety:

```bash
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
python scripts/validate_organization_maps.py
python scripts/validate_repository_hygiene.py
python -m pytest -q
git diff --check
```

For publication or catalog changes, also run:

```bash
python tools/documents/build_controlled_publications.py
python tools/documents/build_institutional_catalog.py
git status --short
```

Any generated drift must be explained and committed or the source/generator must be corrected.

## Issue handling

Open-canon issues track unresolved institutional decisions. They are not implementation tasks to be closed by plausible completion.

Repository hygiene issues track source/publication boundaries, generated-artifact lifecycle, release packaging, validation, public-repository safety, and navigation quality.

Do not create many small duplicate administrative issues. Consolidate process issues when possible. Preserve separate issues only when the unresolved canon questions are substantively different.

## Public repository safety

Do not commit:

- credentials, tokens, keys, secrets, or private contact data;
- hidden benchmark truth or evaluation oracles;
- unreleased scenario answer keys;
- NAILEX proprietary implementation material;
- material whose value depends on remaining outside the public Sable Harbor archive.

Fictional public content must remain distinguishable from private assessment material.
Private evaluator material belongs in `SABLEHARBOR-ALEXANDRIA-CONTROL`. Public references may name
that repository and its purpose, version, or checksum, but must not describe its hidden payloads.

## Board records and approvals

Board records under `docs/governance/board-records/` provide in-universe ratification history. They may support audit scenarios, but they do not authorize inventing new structures outside the accepted canon. Later board paper trail should sequence decisions realistically and preserve open boundaries.

## Slop control

Before adding a doctrine, role, process, count, or formal artifact, ask:

> Did Sable Harbor actually decide this, or is it only a plausible completion?

If it is only plausible completion, either omit it, mark it provisional, or place it in an implementation note. Do not let generated prose crowd out the design.
