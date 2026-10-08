# Company legal intake and response exercise

This source family adds company-owned legal operations to the approved fictional
2027 reference scope. Four declared intake channels have twelve monthly ledgers,
monthly operating screening, quarterly Legal review, two contractual inquiry
classifications, a legal-response tabletop and a separate Internal Audit intake
review. The source exists independently of audit workrooms. The private native
store contains 93 Clean and 98 Messy immutable versions across eleven systems.

The operating differences emerge from records. Messy's September screening
references three of four registered channels while the provider ledger contains
a contractual inquiry. Later classification and a second screening version
preserve the earlier review and an open historical exception. The tabletop also
records an initial wait for an unavailable provider copy and a subsequent urgent
access retest. Every tabletop item identifies itself as an exercise; it does not
manufacture an outside agency notice, hearing, penalty or executed settlement.

The declared channel census is a basis for auditor reconciliation, not proof of
all-company completeness. Unregistered personal channels, other legal entities,
real-world matters remain outside the reviewed source boundary. Each monthly
ledger discloses its extraction cutoff. Preliminary screens never attest future
activity; a next-day tail reconciliation closes each declared monthly window.
Quarterly successors reference exact completed tail versions. January 2028 Legal
and Internal Audit successors reconcile all twelve completed 2027 windows while
retaining the earlier December 31 limited snapshots. Annual company records
remain attributed company judgments; their existence does not accept an audit
N/A determination. The receipt explicitly preserves `source_complete=false`,
`nonoccurrence_acceptance=false` and `audit_task_credit=false`.

The V17 snapshot has 48 untargeted SH-LEG-001 routes per side. This source gives
them discovery context: the regulator action can inspect the tabletop, the
reserved entry can inspect the inventory/playbook, and the conditional
enforcement/hearing routes can inspect the intake population and counsel's
trigger classification. The receipt's exact task-ID list is an integration aid
outside company content. No existing route, PBC group, audit task or frozen P1
state is modified by source creation.

The response playbook keeps customer disclosure permission separate from lawful
regulator access, preserves inaccessible-provider correspondence and requires
counsel to verify authority and case-specific timing. The reference basis is
[HHS's enforcement process](https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/enforcement-process/index.html)
and the official [penalty context](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-160/subpart-D)
and [hearing context](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-160/subpart-E).
Those references were researched on October 1, 2026; they do not verify future
2027 law. The playbook requires a new primary-authority check when a trigger
arises and leaves penalty amounts and actual case records unpopulated.

Create and verify a new private destination with:

```sh
PYTHONPATH=src:. python -m enterprise.audit_suite.company_leg001_trigger_screening_2027 create \
  --repository . --private-repository /home/kingoftheeast/Projects/SABLEHARBOR-audit-suite \
  --destination enterprise/generated/audit-suite/company-leg001-trigger-screening-2027-2026-10-01/isolated-run-v3
```

Use the same arguments with `verify` for a separate read-only check. The
destination parent must already be a private 0700 directory; existing outputs
are never replaced. The verifier re-performs the exact native population,
branch-specific predecessor joins, content hashes, clocks, source/receipt pins,
registered owners and empty audit journals, then rechecks the frozen P1 inventory.
Ten focused regressions reject resealed missing-channel data, false accepted
nonoccurrence, changed fictional provenance and a disabled immutable trigger.
A resealed undeclared receipt branch is also rejected. They verify monthly cutoff/tail chronology and preserved correction history.
The first candidate remains preserved and rejected: independent review found
future-window attestation and an unchecked provenance/trigger mutation. The
second candidate corrected both defects but independent review rejected an
extra receipt branch. The third candidate enforces the exact branch map and
requires a fresh independent review.
