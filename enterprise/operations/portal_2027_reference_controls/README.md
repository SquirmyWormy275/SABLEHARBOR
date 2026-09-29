# Q1 2027 local reference-controls case (provisional)

This is one **newly authored fictional future company case** for a nonpersonal
local reference fixture. Its modeled events have 2027 `event_at` and later
`fictional_available_at` values; the source has no repository availability or
acceptance date until it is included in an accepted commit. It does not assert
that the lab, production hosting, provider contracts, or 2027 work actually
operated as of the September 2026 authoring date.

The complete declared population is one SHI local fixture, one modeled
nonhuman account with one local privileged grant, two fixture copies, two
August-roster-linked ESS people in prospective case roles, and **nine selected
due windows**. The three backup windows are specifically January 10, 12,
and 14; this is not a continuous Q1 backup schedule or an approved corporate
RPO. The five CCF control IDs map the case to existing procedure topics, but
this case does not establish corporate policy effectiveness or independent
assurance. Company-wide 2027 denominators remain unknown.

The local plan is modeled approved at 2026-12-31 23:50 UTC, before its
2027-01-01 effective grant. Its fictional record becomes available at
2027-01-01 00:15 UTC. Two separately identified local exercise briefings and
the fixture inventory become fictionally available before the first job.
Those briefings are limited to this case and do not establish enterprise
qualification or actual 2027 employment continuity.

| Local procedure topic | Due | Timely success | Timely failure | Missed window |
|---|---:|---:|---:|---:|
| IAM-006 nonhuman identity | 2 | 2 | 0 | 0 |
| BCM-002 selected backup jobs | 3 | 2 | 0 | 1 |
| BCM-003 restore | 1 | 0 | 1 | 0 |
| IAM-005 local privileged review | 1 | 0 | 0 | 1 |
| REC-004 fixture-copy disposal | 2 | 1 | 1 | 0 |
| **Selected case total** | **9** | **5** | **2** | **2** |

Four exception tickets and five later responses are separately retained.
The late backup, restore retest, backup-copy deletion retry, local grant
revocation, and late privilege review do not turn the original miss or failure
into a timely success. One privilege-review ticket and its two responses occur
after the Q1 cutoff. The output keeps those facts visible and identifies the
ticket that was not yet open at cutoff.

## Source and reproduction

The controlling case source is
`enterprise/operations/source/portal_2027_reference_controls_case_2026_09_29.json`.
The generated ledger is `q1_v0.1.json` in this directory. Both A and B portal
paths may read this **same provisional company case**; no private A/B exercise
declaration, outcome, or hidden answer is imported. The source pins the
accepted August company release's `records.json` and `RELEASE_RECEIPT.json`
by SHA-256 and pins its three local repository inputs by SHA-256.

Obtain `RELEASE_RECEIPT.json` and
`sable-harbor-company-edition-v1.2.0.zip` from the published
`sable-harbor-company-edition-v1.2.0` release. Verify their checksums against
the source pins and the release checksum file, then extract the ZIP. Its
`content/enterprise/generated/company-closeout-v1/records.json` is the records
input. Run from this repository root, substituting the extracted paths:

```bash
python -m tools.company_closeout.portal_2027_reference_controls \
  --records /path/to/content/enterprise/generated/company-closeout-v1/records.json \
  --receipt /path/to/RELEASE_RECEIPT.json \
  --source-root . \
  --output enterprise/operations/portal_2027_reference_controls/q1_v0.1.json \
  --check
python -m pytest -q tests/company_closeout/test_portal_2027_reference_controls.py
```

The CLI rejects changed accepted-release bytes, changed pinned local inputs,
duplicate/missing selected dues, wrong entity/person/role, premature fictional
availability, erased failures, and stale generated output. A preview API
requires `allow_provisional=True`; its result cannot be used as accepted
company evidence. A later accepted edition must bind this source's first
repository availability to its actual containing commit and must retain the
future-event classification.
