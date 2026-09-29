# August 2026 period population handoff to the audit portal

**Record:** SH-PORTAL-PERIOD-SOURCE-HANDOFF-2026-08-v1

**Version:** 1.0.0 · **Prepared:** September 28, 2026, America/Los_Angeles

**State:** Reviewable company-source input; not an audit conclusion or portal acceptance

The [machine-readable handoff](PORTAL_PERIOD_SOURCE_HANDOFF_2026-09-28.json) describes only the accepted [company edition 1.2.0](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/sable-harbor-company-edition-v1.2.0) at source commit `ddca0d93b16c743e90ce5ac3f9cc74fb74ec6d1f`. Its release receipt says `ACCEPTED_SCOPED_EDITION`; its SHA-256 is `bc0b66500d682c1ea1705601bc1b45e1c6e166d3d28b308df9c729c53767e`. The release ZIP SHA-256 is `8136d8cae07dd4f9fc1f488a7d1034275f5c4149f8606774c6370bbaff7c597c`. The source's old `PENDING_REPOSITORY_ACCEPTANCE` row labels are preserved historical metadata; the later release receipt establishes this edition's scoped acceptance. It does not backdate any row's availability.

## Exact declared August populations

| Population and unit | Declared/due | Observed in source | Missing or excluded | Limit |
|---|---:|---:|---|---|
| Employee × August pay date | 1,404 | 1,404 payroll, 1,404 modeled settlements, ten approved employer/date batches | Zero within the declared schedule; seven nonemployee directors excluded as people, not payroll events | 702 employees × August 14 and 31; modeled clearing is not independent bank confirmation. |
| August contract deliverable | 92 | 92 authorities, deliveries, delivery evidence and invoices | Zero within the declared contract set | Receipt dispositions: 59 modeled paid; 33 explicitly unpaid. No invoice due date supports an arrears conclusion. |
| Selected operating case | Ten | Ten quantity chains, 52 stage events | Zero within the **selected** cases; the full-month physical transaction denominator is unknown | Five exception cases, four normal and one assay-passed case with external transport authority open. |
| Current research/materials project | No duty cadence declared | Five (three Willow, two Cradle) | Due/missing statutory occurrences unknown | Bench failures and noncommercial work remain; these are not five sales. |
| August BST rail event review | One represented event | `BST-EVT-014` event facts | One review-performance evidence gap; 13 other historical events excluded by date | The 2026 event-year authority and reporting determination remain open. No filed report is inferred. |
| Red Wash permit condition set | Due cadence unknown | Fourteen permit register records | Fourteen missing-performance-evidence sets; **missing occurrence count unknown** | `ACTIVE_SYNTHETIC` permit status does not establish condition performance or a monthly frequency. |

The August period is `[2026-08-01, 2026-09-01)` in each source's declared timezone; the payroll and company commercial rows use `America/Los_Angeles`, while the permit and rail registers use `America/Denver`. Their event dates are retained, not recast into a universal local day. The September HR exit `SH-HR-2026-09-01` is one separate change event and is excluded from every August denominator. The 2027–2031 conditional forecast populations and CCF's 7,560 forecast control occurrences are also excluded.

All regenerated August rows have repository-source availability `2026-09-22T23:26:06Z`; the public edition was published `2026-09-22T23:50:07Z`. An August effective date is **not** an August known-on date. A portal query for public release evidence must use the later publication time or an explicitly justified earlier source-access boundary. The release's September operating-event cutoff is September 14 America/Los_Angeles, separate from this August completed-month handoff and September 22 personnel/policy successors.

## Portal intake contract

Use the existing company-source/version/collection schema. For each selected row retain its original stable ID, exact source path and SHA-256, legal entity, unit, effective event time, source/release availability, fact/scenario state, and access scope. The JSON's `id_set_sha256` is SHA-256 of compact UTF-8 JSON for the sorted unique IDs; it detects a changed member set without publishing a second row database. `null` due or full-month denominator means **unestablished**, never zero. The portal owner should map one declared population to one evidence request/period ledger boundary and retain source rows separately from collected audit artifacts. Do not import a 2027 forecast row into the August actual boundary or count a source document version as a business occurrence.

The [read-only verifier](../../../tools/company_closeout/period_source_handoff.py) checks exact accepted release and regenerated-source hashes, then rejects missing/duplicate payroll events, broken contract joins, unpaid invoices represented as cash, changed selected stages, and invented permit cadence. Generate records from a clean checkout of the accepted `ddca0d93` commit. Run the remaining commands from this review branch, pointing `--source-root` at that accepted checkout:

```sh
cd /path/to/accepted-ddca-checkout
python -m enterprise.operations.completed_period --output /new/private/completed-period-ddca
cd /path/to/review-branch-checkout
gh release download sable-harbor-company-edition-v1.2.0 --repo SquirmyWormy275/SABLEHARBOR --pattern RELEASE_RECEIPT.json --dir /new/private/release-v1.2.0
python -m tools.company_closeout.period_source_handoff \
  --records /new/private/completed-period-ddca/records.json \
  --receipt /new/private/release-v1.2.0/RELEASE_RECEIPT.json \
  --source-root /path/to/accepted-ddca-checkout \
  --output docs/internal/company-closeout/PORTAL_PERIOD_SOURCE_HANDOFF_2026-09-28.json --check
PYTHONPATH=src:. python -m pytest -q tests/company_closeout/test_period_source_handoff.py enterprise/operations/tests/test_completed_period.py
```

The isolated run passed the exact handoff check and 28 focused tests. A first system-Python test invocation without `PYTHONPATH=src:.` failed at `tests/conftest.py` because it could not import `sable_harbor`; the supported invocation above passed. No active audit-suite branch, A/B workroom, private company store, audit command or shared portal manifest was changed.

The portal owner still must determine actual due/event populations for each relevant permit condition, perform the BST event-year review, and reconcile the full physical transaction month before claiming those scopes complete. This handoff does not authorize fictional activity solely to satisfy an audit test.
