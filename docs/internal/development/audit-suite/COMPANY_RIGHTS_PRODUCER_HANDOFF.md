# Portal company-rights producer handoff

`enterprise.audit_suite.company_rights_producer` supplies the trusted snapshot
and independent revocation checkpoint expected by the private Daedalus gateway.
It does not enroll the audit portal as a company identity provider or create
record grants. The existing `CompanyStore` system/engagement grants remain
separate from individual record disclosure.

The portal owner must provision two distinct private 0700 roots, keeping the
checkpoint root outside rights-store backup and restore. Instantiate the
producer with the accepted policy file SHA-256, exact public source commit,
`information_policy.validate_record` and `information_policy.decide` from the
accepted public main, a trusted pinned source reader, and the independently
verified company person ID population. The audit branch at `6996c8cb` predates
the accepted policy module, so the focused tests use an explicitly labeled
stand-in validator/decider. `pinned_git_source_reader` handles repository
sources; retained private derivatives need their own exact source reader and
stable record/path/hash pins.

An authorized operator must explicitly call `bind_person` for each audit
principal and engagement, supplying company person ID, tenant and purpose.
The browser session ID is derived from the portal's authenticated server-side
session; bearer credentials and old sessions without an authentication time
cannot issue an assertion. The operator must also register each policy record
with `put_record`; rows retain explicit grants and transitive `sources` IDs.
No rank, role, shared operator token or system-level grant creates a record
grant. Rights changes increment the revision and checkpoint epoch. Person
revocation, deletion, hold changes and restore attempts also advance the
checkpoint epoch; tombstones survive older-copy restores. A restored rights
database whose revision falls behind the independent checkpoint fails closed.

For each disclosure, `authorize_disclosure` checks current session/membership,
policy and exact source bytes, then calls the accepted policy's `decide` for
the named action. `visible_population` requires a complete candidate set and
filters it before ranking, paging, snippets or counts. The private gateway can
consume `snapshot` and `checkpoint` as fresh server-side callables. Both
processes must use the same authenticated session ID and policy/source pins;
no HTTP or model argument may supply person, tenant, purpose or grants.

**Integration owner work:** wire this authority to the audit portal's direct
company reads and every private Alexandria/Daedalus direct library route,
search/snippet/count and graph population, model context/tool result, citation,
memory, derivative, export and restore path listed in the private
`DAEDALUS_COMPANY_RIGHTS_HANDOFF.md`. Supply a real, independently reviewed
company person mapping and per-record grants before enabling any disclosure.
Unclassified retained outputs and incomplete populations must remain
unavailable. Run positive and denied live HTTP/model paths, prompt probes and
older-backup restore tests after wiring. This producer is not a claim that
those service paths are already gated.

Focused validation: `PYTHONPATH=.:src python -m pytest -q
tests/audit_suite/test_company_rights_producer.py tests/audit_suite/test_store.py`
and `ruff check` on changed Python files. See the branch commit receipt for
the exact outcome and cross-repo gateway smoke pins.

## Opt-in portal HTTP boundary

The follow-on `company_rights_http.py` adapter is mounted by
`service.create_app(company_rights_factory=...)`. The trusted factory receives
that app's `Engine` and must return a producer using the identical portal
`Store`; there is no CLI or default factory. The new `/company/rights/` route
family requires this portal's authenticated browser cookie. Bearer credentials,
request parameters and model arguments cannot supply a company person,
tenant, purpose or decision time. Missing configuration, mapping, record,
grant, policy pin or source bytes stops disclosure.

| New route suffix | Required policy action | Response |
| --- | --- | --- |
| `records/{record_id}` | `read` | Exact pinned bytes |
| `records/{record_id}/snippet` | `snippet` | First 160 UTF-8 characters |
| `records/{record_id}/export` | `export` | Exact pinned download |
| `search?q=...` | `search` | Record IDs after rights filtering and paging |
| `count?q=...` | `count` | Count after rights filtering |

Search and count enumerate all registered policy records, verify each exact
path/hash, filter the complete bounded population, then apply text matching
and paging. The boundary caps that population at 512 records and 25 MiB; an
over-limit population fails closed. It does not silently convert a native
CompanyStore `source_reference` into a repository path: many such references
are activity IDs. Explicit policy rows are the only source catalog here.

This route family is an isolated disclosure slice, not a replacement for
existing audit-training workflows. The legacy `/company/systems`, native
record discovery and `company.collect` routes retain their distinct audit
engagement authority. They must not be exposed as Daedalus record entitlements.
The integration owner must add an exact native-record-to-policy-ID closure
before using this boundary for those routes, retained company artifacts,
source impact/disposition, packages or exports. The private Alexandria Library
and Daedalus model, tool, memory and conversation paths remain separate
integration work; the private gateway's route inventory remains controlling.

Concrete integration points for that owner:

1. `enterprise/audit_suite/__main__.py` `serve` must load a private, reviewed
   producer configuration and pass a trusted `company_rights_factory` to
   `service.create_app`. The launch path must pin the accepted policy bytes,
   public source revision, company person census, explicit principal mapping,
   per-record grants and independent checkpoint root. No HTTP field can fill
   one of those inputs.
2. `enterprise/audit_suite/company_collection.py` must map each native
   `(company, branch, system, record, version, sha256)` to a stable policy
   record ID, exact source bytes and transitive source IDs. There is no such
   reviewed mapping in this branch. Reject missing mappings; do not infer one
   from `provenance.source_reference` or a system grant.
3. `enterprise/audit_suite/service.py` must apply the same decision to the
   legacy company discovery routes, collection command output, source impact
   and disposition inputs, artifact downloads and any derived work that can
   disclose a company source. Pagination and counts must follow a complete
   authorized population. `enterprise/audit_suite/recovery.py` must keep the
   independent checkpoint outside the restored rights database and test an
   older-backup restore.
4. The private Alexandria owner must bind the gateway across every route in
   `docs/DAEDALUS_COMPANY_RIGHTS_HANDOFF.md` in the private repository, then
   run positive and denied live HTTP/model, prompt, derivative, export and
   private Control exclusion tests. Passing this portal adapter's HTTP tests
   does not establish that those paths are gated.

The portal's A/B engagements simulate 2027 activity, sometimes viewed in
2028, while the real server clock is September 2026. Snapshot, checkpoint and
browser-session freshness always use wall time. Without a configured case
resolver, policy availability also uses wall time, so a future scenario record
remains denied. Do not pass a fictional 2028 wall `now` to make a five-minute
2026 authority snapshot appear valid.

The optional `CompanyRightsProducer(case_as_of=...)` receives an immutable
`VerifiedCaseContext` built from the same live portal session and engagement
as the rights snapshot. There is **no default resolver** and no resolver that
reads `Store.simulated_at` directly. A missing or malformed approved timestamp
fails closed. The producer re-reads case time, then authority, and re-evaluates
policy before direct disclosure and complete-population results. Candidate
path/bytes are frozen before filtering; mutated caller candidates fail closed.
The HTTP adapter repeats the case-time check before its response. With no
resolver, wall time remains the policy time. No HTTP parameter, model argument,
global process clock or CompanyStore system grant supplies case time or record
rights.

The private gateway's merged two-clock increment is
`fb207339` (private PR #9). To bind its constructor-only `case_as_of` callback,
the service owner must create a closure for the **same already-authenticated
session token and engagement ID** used by the gateway snapshot callback, for
example a closure that calls
`producer.case_time(session_token=token, engagement_id=engagement_id)`.
The gateway still checks its own snapshot/checkpoint freshness against wall
time and rechecks case time before return. The producer's own portal read
uses no request-supplied decision time.

In this branch, an authorized `learn` or `instruct` member can issue
`clock.advance` for an active engagement. Its resulting `simulated_at` is
learner-influenced and cannot silently unlock company records. Before enabling
case-time disclosure, the owner must define an administrator/instructor
approved progression signal with explicit authority, engagement binding,
provenance, revision and freshness, separate from ordinary learner clock
advancement. The resolver must read that reviewed signal and reject missing,
stale or changed approval. The case date controls policy eligibility only; it
does not establish that a forecast is a completed real company fact. Neither
this resolver nor the private gateway is wired into live portal/Daedalus
service launch paths by this isolated commit.

## Protected portal service boundary (September 29 successor)

When `service.create_app` receives `company_rights_factory`, that service is a
dedicated protected disclosure instance. Its HTTP allowlist is deliberately
small: browser session create/logout, the five `/company/rights/` operations,
and exact retained company-source downloads when
`company_native_rights_factory` is also configured. All ordinary portal
commands, native company discovery/collection, source impact, derived audit
routes, uploads, instructor routes, and other downloads return 403 on that
instance. Run the ordinary audit workroom without either rights factory; its
existing training behavior is unchanged. Do not expose ordinary workroom
routes as Daedalus company-record entitlements.

`NativeRecordClosure` requires a separately reviewed exact JSON manifest,
provided from trusted server code with an expected SHA-256. Its schema is
`{version: 1, source_commit, policy_sha256, records: [...]}`. Each record has
`company`, `branch`, `system`, `record`, positive integer `version`, native
`sha256`, `policy_record_id`, and `repository_path`. A retained artifact's
native source tuple and bytes must match one entry and the current producer
policy row. The download also re-reads the native version under the current
portal principal's system grant and approved case time, then requires a current
per-record `export` decision. Unknown, denied, tombstoned, altered, and
unmapped artifact IDs have the same protected 403 response. The manifest is
an explicit bounded closure, not an assertion that every historical native
version in a workroom has been classified.

There is still no operator-reviewed live person/engagement binding, record
grant schedule, accepted 2027 case-clock approval ledger, or protected launch
configuration. The factories are opt-in server hooks; a test fixture or system
grant cannot supply those missing authorities. Private Operational must be
launched against this producer with reviewed inputs and separately exercise
model prompts, person isolation, revocation and older restore before #34 can
claim live company access. Private gateway acceptance is at
`131e60bf7b73bf8b6d3cafae0c61d30ba3917c46`; the public integration remains
pending until its own source branch is accepted.

Isolated validation: focused producer, HTTP, company service and service tests
passed (37 tests). A separate cross-repo smoke with public accepted policy
`fbbdff203c03871fee1a3db876b4b91517903462`, this portal tree based on
`a433b5a9`, and private merged gateway `fb2073397e28e0269c2166526b19c60f67986720`
passed a future-case positive direct read plus a missing-approved-clock denial
through both producer and gateway. The approved clock in that smoke was a
test-only private callback; it does not establish a live approval ledger.
That smoke exercises the accepted
`information_policy.decide`, not the local test stand-in.
