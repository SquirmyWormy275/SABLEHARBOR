# October 1–3 local operations and repository-source predecessors

**Status:** exact historical bytes from unaccepted local branches. The [current completed-period source](../../../../enterprise/operations/docs/completed-period.md), [operations guide](../../../../enterprise/operations/README.md), and current root `.gitignore` retain their accepted status. This record does not complete August payroll, the composite company edition, or any external payment or filing.

The [manifest](MANIFEST.json) records two distinct Git blobs, their original paths, local commit/date, byte size, SHA-256, Git blob OID, accepted-current path relation, and exact Seagate archive-member copies. Both files are retained here at exact bytes:

- [Completed-period document predecessor](../../../../enterprise/operations/docs/history/completed-period-2026-10-03.original.md), from a local October 3 source stage. Its header describes an August 2026 synthetic company period and September 15 authorship but explicitly says repository acceptance was pending; the later local source date and October 23 recovery intake are separate. Relative links inside that original byte snapshot are historical. Use the current source link above for live navigation.
- [October 1 repository ignore-file predecessor](gitignore.original.txt), preserving the 669-byte local `.gitignore` version without using it as the current repository configuration.

Run `python docs/internal/repository-history/local-worktree-2026-10-01-03/verify.py` on a fresh GitHub checkout to confirm the two tracked files against every SHA-256, Git blob OID and byte length. These are direct Git files, not a Release asset or a full Git bundle. Their original commit/ref histories and Seagate archive families remain separately unresolved, so neither workstation nor Seagate cleanup is cleared by this intake alone.
