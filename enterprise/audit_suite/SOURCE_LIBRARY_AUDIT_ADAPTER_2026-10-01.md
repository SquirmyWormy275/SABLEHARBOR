# Normal source-library audit adapter

Current main integration: the corrected module passed independent review and
actual main reperformance, including held-open WAL, Engine clock, ordinary
typed collection and unchanged accepted-library custody. Independent gate SHA:
`ba1f02d6c35d4ff8f4a029ab7e10315193c71cb9aeb23f729d74828266082350`.
Main reproduction SHA:
`c73ddb35bcc80a2d637bfe10ff3f255dd677468a0aa5f558d41ec2669f333235`.
This accepts only bound adapter/ordinary Engine entrypoints against the exact
selected V2.1 library. Direct in-process CompanyStore cutoffs remain trusted
caller input. The candidate checkpoint wording below predates that separate gate;
neither the gate nor fixture collection supplies actual procedure credit or
validation of evolving company correction journeys.

`source_library_audit.py` reuses the reviewed SEC003 discovery mechanics for a normal CompanyStore library. It preserves the actual projected company/branch/system/record/version, bytes, hashes and event/availability/import clocks. Logical family and system aliases are separate business routing metadata. They cannot replace native identifiers in a collection receipt or satisfy an exact business-reference join.

An operator supplies the independently accepted main library's database, manifest and review pins plus its fixed version boundary. Acceptance requires the exact root review schema `SH_ROOT_COMPANY_LIBRARY_INDEPENDENT_REVIEW_V1`, verdict `PASS_COMPANY_FACING_LIBRARY_SELECTED_BOUNDARY`, explicit `source_quality_accepted_for_final_learner_audit=true`, exact database/manifest pins and strict native-version count. The explicitly supported manifest schema is `SH_COMPANY_OPERATIONAL_PROJECTION_V2_1` and must directly bind `files.company.sqlite3`. A bounded raw-source PASS or false source-quality gate cannot authorize an audit. Pending review, changed pins, source-side SQLite sidecars, symlink ancestors, inherited grants/collections/access journals and changed version boundaries prevent source-workroom staging. The adapter reads only these accepted custody records and the ordinary company database; it never opens a transformation map, authoring recipe, Key, old observation or prepared evidence set.

The company library is staged as a new ordinary-byte, single-link 0600 database in a new 0700 source-workroom directory **before Engine construction and `Engine.create`**. The original remains unchanged. The adapter pins both the business history and complete SQLite schema, including triggers and schema version metadata. Later grants and collection journals are allowed; changing company originals or the schema is not. A new audit workroom starts with zero artifacts, workpapers, populations, selections, reviews, findings and requests, and all tasks not started/not run. Supported provisioning and membership mechanics create distinct company operator, auditor and reserved independent reviewer identities.

The staged source must remain quiescent. Before and after immutable business/schema reads and every normal CompanyStore connection, the adapter rejects any `-wal`, `-shm` or `-journal` file, including dangling symlinks. Engine's ordinary collection uses this same guarded CompanyStore instance. Ordinary grant and collection transactions may create their normal transient DELETE-mode journal inside a connection; it must be gone after that connection closes. The adapter never deletes or checkpoints an unexpected sidecar. This prevents immutable pin checks from observing the base database while normal source reads observe a held-open WAL replacement.

The auditor receives only the declared native-system grants for the explicitly bound company branch. `discover(engine, auditor, engagement, as_of=...)` requires the actual Engine/engagement created by this source workroom, the provisioned audit performer and the activated frozen company binding. It derives the company branch from that binding and rejects a requested cutoff after the engagement's current simulated clock **before any source read**. Older historical cutoffs remain valid. Future evidence becomes discoverable only after an explicit supported `clock.advance` command. Discovery uses ordinary `list_systems`, paginated `list_records`, and exact predecessor `read_version` calls. Every version up to the latest visible version must actually be available; a missing or unavailable predecessor fails incomplete. A later correction does not hide an earlier version. The population claim remains limited to the selected granted systems and cutoff.

Collection uses the existing `company.collect` command and an issued evidence request. The retained artifact must reproduce the exact discovered native version, immutable receipt/provenance and bytes. It uses the source's existing `provenance.name` and `content_type`: `application/json` remains `.json`; `text/plain` or the V2 declaration `text/plain; charset=utf-8` remains `.txt`, with strict UTF-8 decoding. Unsupported types, malformed content and filename/type disagreement fail closed. No private system-name list or rewritten provenance is needed.

Business pointers can be joined with `exact_projected_reference`. That function requires the actual projected native tuple, exact version/hash, event/availability clocks and an independently discovered or collected counterpart. V2 business pointers do not carry a new real import clock; the target's actual import clock is checked separately through accepted custody and discovery. If a pointer additionally includes an import clock, it must match too. No pointer clock is invented. The function does not use a producer pointer list as an audit population or infer completeness, operation or sufficiency.

The adapter does not create a population, sample, observation, workpaper, finding or task disposition automatically. Each selected audit method must author those through supported commands, retain its scope/exclusions and limitations, and await separate reviewer acceptance. A corpus count or successful collection does not perform a clause, establish a full enterprise/year population or grant task credit. The selected V2.1 company library has separate independent acceptance and main pins, while this corrected adapter still awaits independent review; **no actual source-library fieldwork has run** in this candidate. The prior `e9f30331` adapter is preserved as a rejected checkpoint: independent held-open WAL and future-discovery probes demonstrated the two defects corrected here.

Verification uses neutral disposable CompanyStore fixtures, including supported zero-evidence creation and ordinary text collection without persistent sidecars. Tests challenge an actual held-open WAL replacement, staged regular/dangling journal sidecars, a journal appearing after a normal connection closes, future discovery before explicit clock advancement, arbitrary Engine/engagement/actor substitution, pending acceptance, changed original sources, immutable-trigger removal, branch isolation, reviewer separation, unavailable predecessor versions, exact projected joins and unsupported or mismatched evidence types.

```bash
PYTHONPATH=src:. /tmp/sableharbor-audit-merge-venv-20261001/bin/python -m pytest -q \
  tests/audit_suite/test_source_library_audit.py \
  tests/audit_suite/test_fresh_sec003_procedure.py \
  tests/audit_suite/test_company_collection.py
```

This is a reusable code candidate. It does not change the frozen SEC003/identity workrooms, earlier source candidates, source portfolios, routes or the main checkout. The next selected methods will separately examine SEC003 vulnerability history, SEC005 monitoring/baseline history and selected continuity marker/restore history against accepted company sources, preserving broader corporate/ePHI recovery limitations.
