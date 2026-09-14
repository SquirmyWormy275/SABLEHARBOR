# Repository company documents: first bounded ingestion

Eight repository originals were copied byte-for-byte into a new private company
source store: four non-finance committee charters, the corporate document standard,
the objectives/risk universe, the native common-control catalog, and the enterprise
authority/executive rhythm document. Each has an explicit documentary control link,
pinned Git/blob/SHA identity, and the actual proposed scoped collection custodian.
This is company design documentation, not enterprise operating history or evidence
that controls have operated. No audit, grant, collection, or company conclusion was
created. Finance-pinned records and ambiguous successor records were skipped.

Private operator artifacts are under
`enterprise/generated/audit-suite/repository-documents-2026-09-14/first-v1/`:
MANIFEST.json, PLAN.json, RECEIPT.json, REVIEWED_SOURCE_METADATA.json,
EXCEPTIONS.json, VALIDATION.json and CURRENT_STACK_VALIDATION.json. Source-owned
header text preserves authority/owners and distinctions between approval, document,
and effective dates. Unknown business event dates stay null. Availability begins at
real ingestion, not the document's historical effective date. Original files remain
unchanged; the exact retry creates no duplicate versions.

The reviewed private recipe `../sync-reviewed.py` is retained in the parent artifact
directory. From the repository root, reproduce into a NEW directory under that
existing private parent with:

```sh
PYTHONPATH=. .venv/bin/python enterprise/generated/audit-suite/repository-documents-2026-09-14/sync-reviewed.py enterprise/generated/audit-suite/repository-documents-2026-09-14/next-reviewed-run
```

Re-review accepted source authority and the current finance lock before a later run;
a new Git commit is not itself approval. This recipe is operator-authored, not an
automatic discovery or publication mechanism. Private files are ignored, and no
private source payload is added to this public note.

Native Markdown is now inspected and extracted through the bounded sandbox as
inert UTF-8 plain text, retaining original names and control/custody/authority
qualifiers. It is not interpreted as HTML or executed code. An isolated Engine test
verifies authorized company-persona context and exact collection, then revocation;
the actual eight-document store has no grants. See
`enterprise/audit_suite/REPOSITORY_DOCUMENT_SYNC.md` for API and retry boundaries.
