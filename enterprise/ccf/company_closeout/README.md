# Company obligation review and runtime input boundary

Document ID: SH-C05-C06-REVIEW-2026-09-15. Prepared September 15, 2026 UTC.
Acceptance: pending repository acceptance. Implementation of the closeout assignment;
this record does not claim completed C05/C06 or accepted operating effectiveness.

## Reperform the declared population

```sh
python -m enterprise.ccf.company_closeout.validate
python -m unittest enterprise.ccf.company_closeout.test_validate -v
python -m unittest enterprise.runtime.tests.test_security -v
```

`obligation_census.json` preserves all 14 Red Wash permit entries and 14 historical
rail safety events, exact source rows, source hashes, responsible roles, activity,
condition, individual screening route and missing next facts. These are two complete
source populations, not a company-wide obligation population. The register is a
new September 15 review of source facts through August 31; its availability must
never be backdated into August. It changes no permit, historical incident, financial
balance, corrective-action status or filing state.

The validator rejects omitted/duplicate members, changed facts, stale source or
evidence hashes, premature availability and unsupported performance promotion.
MISSING_EVIDENCE does not mean FAILED, NOT_RUN, NO_OCCURRENCE or NOT_APPLICABLE.
Future-due cannot be inferred where the underlying due date is still unknown.

## Primary authority work and precise limitations

Ten annual primary editions of 49 CFR 225.19 (2014, 2016, 2018–2025) were retrieved
from GovInfo and their reporting-group text read on September 15. The register
records exact URLs and SHA-256 hashes. October annual editions are not automatically
the rule effective on an earlier event date; intrayear amendment/Guide/threshold
checks remain open. The original browser fetch for the 2018 PDF failed; direct
HTTPS retrieval succeeded and is hash-recorded. No external account was contacted.

The [2023 primary text](https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol4/pdf/CFR-2023-title49-vol4-sec225-19.pdf)
distinguishes crossing, equipment and injury groups. The two crossing events need
crossing-definition review without a damage-threshold gate for Group I. The four
derailment events need qualifying repair cost, which cannot be substituted with
the source's combined claim/damage amount. Injury records need causation and
case-specific criteria. Environmental releases need separate spill screening.
Rules/timestamp events retain their corrective actions; absence of a recorded
trigger is not a final legal no-report opinion. Filing evidence remains missing
for every event, independent of whether corrective action was recorded.

[NRC's Wyoming record](https://www.nrc.gov/agreement-states/wyoming) confirms the
September 30, 2018 transfer for the identified milling/byproduct scope. It does not
validate fictional license WYSML-094 or its specific conditions. All 14 permits
still need instrument-specific obligations, due populations and evidence joins.
The MW-17/Cell 1 investigation remains unresolved; a trend is not a final liability
finding. No framework has been made universally applicable.

## C06 company-to-existing-runtime input contract

The active `SABLEHARBOR-audit-suite` worktree on `build/audit-training-suite` was read
only. Its `tools/audit_suite/COMPANY_ACTIVITY_LINKED_PLAN.md` describes native
`PRIVATE_COMPANY_ACTIVITY_LINKED_PLAN_V2` inputs and exact-source selection. It is
concurrent work, not accepted main or a new company database. This census is an
upstream review register, **not** a fabricated `PRIVATE_COMPANY_ACTIVITY_RUN_V1`
operator output. Never manufacture wrapper manifests to import it as activity.
The runtime owner must resolve source records into supported native producers and
preserve selected metadata digests, operator/member hashes and source references.
The integration owner's separately exercised capsule adapter may instead import
these public repository documents using the existing `company_store.append_version`
interface and origin `REPOSITORY_SYNTHETIC_DOCUMENT`. Register the system and owner
through `register_system`; supply exact expected version, command ID, event and
available timestamps, content bytes and provenance. Actual `imported_at` is assigned
by the store and cannot be supplied as a historical timestamp. Registration/import
creates no access grant or prior operating history. Do not label this review as
`AUTHORED_TRAINING_SOURCE` performance or use `MIGRATED_SYNTHETIC_HISTORY` to suggest
recovered execution. Fresh-store capsules and linked native activity plans are
different interfaces; preserve each one's declared scope.

For each company-side handoff retain:

- Stable record/source ID, legal entity, unit, effective period and timezone.
- Event and available dates separately from authorship/import/acceptance dates.
- Scenario, fact origin, complete declared population and explicit exclusions.
- Source version/commit/hash, evidence relationships and native access scope.
- Exact selected versions; no newest-version fallback or forecast promotion.
- Preparer and independent reviewer identities, outcome, exceptions and retest state.

Authority and information policy remain in accepted Alexandria doctrine and
`enterprise/runtime/security.py`; this input contract grants no entitlement.
Runtime collection must filter direct and indirect disclosure before retrieval,
including snippets, counts, graph, tool responses and export. Private memory stays
separate; holds preserve protected bytes without restoring ordinary disclosure.
Synthetic source review cannot satisfy ACTUAL_COLLECTED_EVIDENCE.

C09 rejects malformed shared tenant identity and absent/malformed mandatory policy
metadata before any allow path. Its tests cover every disclosure surface, bounded
existence, legitimate OPEN access, mismatched tenants, missing/empty/non-string
identities, malformed purposes and retained revocation/deletion behavior. This is
a reference implementation fix; adoption by the active portal and deployed behavior
need their own integration evidence. Existing readiness gates remain unchanged.

## Residual owners and acceptance boundaries

| Work | Delivered evidence | Exact remaining work / owner |
|---|---|---|
| C05 | 28 source-bound individual dispositions; ten retrieved primary editions | Company compliance lane: instrument terms, complete enterprise activity census, event-date rules, supported performance/filing chains and qualified review |
| C06 | Existing-runtime input boundary and reference disclosure tests | Runtime owner: native company import, actual isolated software backup/restore, independent review, indirect-disclosure integration and external gate evidence |
| C09 | Source regression fix and positive/negative tests | Integration owner: required repository checks, accepted PR and portal integration receipt |

Preserve the CCF denominators: native preparation 166 controls / 1,660 boundaries;
operations 70 baseline or 86 extended / 24 computed assertions; business exercise
7,560 expected occurrences across 42 combinations. This 28-row review is not a
replacement denominator or evidence that the 15 native risk mapping gaps closed.
No IT or regulator acceptance gate is asserted by this source review.
