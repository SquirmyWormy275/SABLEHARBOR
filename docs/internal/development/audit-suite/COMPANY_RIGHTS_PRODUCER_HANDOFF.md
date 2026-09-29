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
