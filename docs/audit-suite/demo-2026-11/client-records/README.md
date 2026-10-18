# November company records

[Scope](../SCOPE.md) · [Delivery guide](../SOURCE_DELIVERY.md) · [Publication decision](../PUBLICATION_2026-10-18.md)

These are the actual synthetic company records for the November demonstration. All 70 artifacts and their three manifests are included in this repository. Clone or download the repository to read them locally; no credentials, workspace database or generator run is required.

The exercise covers SH-IAM-007 access reviews, SH-CFG-002 configuration baseline and drift, and SH-BCM-003 restore testing within the declared local scope. It concerns fictional Q1 2027 operations, with simulated client correspondence in January 2028. It does not establish whole-company completeness or an audit conclusion.

## Read the submissions in order

| Submission | What it contains | Edition | Artifacts |
|---|---|---|---:|
| [Initial](initial/) | Scope and control design; identity history and review exports; configuration approvals, observations and application; backup and restore records; walkthrough video, transcript and captions. | `SH-NOV2026-0-v1` | 58 |
| [Follow-up](follow-up/) | Q1 access-review population, decisions, follow-up and account CSV; client response explaining the earlier export and recovery limits. | `SH-NOV2026-1-v1` | 5 |
| [Correction](correction/) | Revised configuration summary and client response; walkthrough addendum with transcript and captions. | `SH-NOV2026-2-v1` | 7 |

Start with the initial [scope](initial/SCOPE.md), [control design](initial/control-design.md), [response](initial/response.md) and [manifest](initial/manifest.json). Read the [follow-up response](follow-up/response.md) and [correction response](correction/response.md) alongside the earlier records. Later submissions add or supersede particular artifacts; they do not replace the entire initial directory. The initial review export covers Q2; the follow-up supplies the requested Q1 records.

All stages are publicly visible. The sequence records when the fictional client supplied each submission; it is not an access restriction. A consumer may inspect all three stages immediately. Keep each manifest and its directory intact rather than merging or rewriting the submissions.

## Verify a clone

Use Python 3.11 or newer. From the repository root:

```bash
python3 tools/audit_suite/demo_source_delivery.py verify docs/audit-suite/demo-2026-11/client-records/initial
python3 tools/audit_suite/demo_source_delivery.py verify docs/audit-suite/demo-2026-11/client-records/follow-up
python3 tools/audit_suite/demo_source_delivery.py verify docs/audit-suite/demo-2026-11/client-records/correction
```

Each command should report `VERIFIED` with its edition and artifact count from the table. The reader checks all listed hashes and byte counts and rejects missing or unexpected files, altered records and path aliases. It uses the Python standard library and does not change the submissions.

The original client instructions inside the initial submission remain unchanged as part of its hashed evidence. This index and the [publication decision](../PUBLICATION_2026-10-18.md) describe the current public access arrangement. Private operator selections, evaluator material, credentials and workspace databases are not part of these submissions.
