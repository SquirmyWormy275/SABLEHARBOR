# Private companion recovery

These local operator APIs supplement, and do not change, engagement, company-source,
and personal-draft backup semantics. No HTTP backup or restore route is provided.
Keep the bundle private. It contains original personal questions and job commands.

```python
from pathlib import Path
from enterprise.audit_suite.companion_recovery import backup, restore
from enterprise.audit_suite.workspace_context import WorkspaceContexts

manifest = backup(
    Path('/private/operator/new-companion-backup'),
    contexts=contexts,                 # Existing WorkspaceContexts object, optional
    jobs=jobs,                         # Existing BackgroundJobs object, optional
    instructor_access_root=log_root,   # Existing initialized access log, optional
)
receipt = restore(
    Path('/private/operator/new-companion-backup'),
    Path('/private/operator/new-companion-restore'),
    engine=restored_engine,             # Required when contexts are included
    principal_map={'OLD_ID': 'NEW_ID'}, # Explicit, exact, distinct owner mapping
)
contexts = WorkspaceContexts(
    Path('/private/operator/new-companion-restore/contexts'), restored_engine
)
```

Parents must already exist with mode 0700. Destinations must not exist. Files are
0600, symlinks are rejected, and each retained member has an exact byte hash/size.
Context table data is imported into the application-owned schema; supplied SQL is
never executed. Original context text, version history, and content hashes are
preserved. Ownership changes are recorded separately in RESTORE_RECEIPT.json.
Provision replacement principals and grant current engagement membership explicitly
in the independently restored main store first. No credentials or grants are copied.
Current permission must match the historical context permission, or the mapped actor
must have current instructor membership to recover broader or unrecorded authority.
The workspace still flags changed scope/source/permission context and stale links.
Restoring contexts does not restore the referenced artifact bytes or engagements.

Jobs restore only to `jobs-ARCHIVE-ONLY.json`. Original actors, envelopes, status and
transition histories remain unchanged, including RUNNING at capture. This is not an
operational queue, and no job starts or resumes. Any later operational reconstruction
requires separate explicit authorization and reconciliation against main-store command
receipts; this API does not offer it. Do not rename the archive into a service database.

Instructor access data restores to `instructor-access-archive/access.jsonl` and
`head.json`, with exact original bytes and verified hash chain/head. It is a separate
operator archive, not an automatically activated service log. It can be checked with
`InstructorAccessLog(archive_path).verify()`.

Every SQLite read transaction and locked log capture has its own timestamp. The
bundle is **not globally atomic** across components or the main engagement store.
Hashes detect corruption against retained pins, not an attacker rewriting the entire
bundle and manifest. Keep a separate trusted copy of the manifest. Model runtimes,
licensed references, instructor key archives and company-source databases require
their own existing delivery/recovery procedures. An interrupted filesystem publication
must be treated as incomplete; never activate a partial directory manually.
