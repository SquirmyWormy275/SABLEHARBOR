# Instructor-authored assessment history

`InstructorAssessments(private_root, engine, bindings)` records explicit qualitative instructor judgments in a separate protected private sidecar. It does not generate scores, grades, conclusions or rubric criteria; invoke models; change audit/source records; accept work professionally; or release content to learners. Only the original author with current scoped instructor authority can read or correct an assessment. There is no implicit colleague sharing.

The six required dimensions are discovery, evidence, testing, judgment, documentation and follow-through. Each contains authored `assessment`, `rationale` and explicitly selected `reference_ids`. An instructor may state “not assessed” or “insufficient support”; the form does not compel an adverse or positive finding. Distinctions such as not requested, unavailable, uninspected, inadequately tested, misinterpreted, insufficiently documented and out of scope must be authored with reasons. Missing links and file opens do not establish those judgments automatically.

## Selection and pins

`options(actor, engagement, revision)` requires an explicit historical revision. It reuses the protected comparison inventory and its streamed selected history verification. It returns the current engagement revision; exact Key and authored rubric digests; selected shared-state/event/history digests; bound revision and audited actor; issue/expectation selectors; and server-generated evidence references. It never materializes all historical states or downloads original bytes through the comparison report.

References preserve distinct relationships: exact retained metadata link, control association only, explicit source link, recorded population link, exact recorded workpaper version and recorded workpaper-review link. `inventory_sha256` hashes the exact comparison row. `content_sha256` is a recorded original artifact or workpaper-version hash when available and is otherwise null. A metadata association is not proof that the underlying bytes were inspected, that a task implements an expectation, that testing was adequate, or that the audited actor authored shared work. No unsupported inspection record is invented.

The saved document pins Key manifest, complete existing authored rubric, comparison inventory, audited actor, selected learner revision/state/event/history and bound revision. Historical shared state is not a submission or individual performance record. Source existence and retained-copy availability remain distinct. A correction may deliberately select a different historical revision, but must supply freshly resolved exact pins; no latest substitution occurs.

## API

- `listing(actor,eid)` returns owned metadata only: `{engagement_id,current_engagement_revision,assessments}`. No authored narratives are included beyond a current-context title.
- `read(actor,eid,id)` returns metadata and `document` only when current Key/source/scope basis remains valid. It verifies exact selected historical pins before exposing the document.
- `save(actor,eid,payload)` requires exactly the fields below; it returns the saved document DTO.
- `snapshot()` and `validate_archive(value)` support an inert private archive only.

```text
{
 expected_engagement_revision, learner_revision,
 key_pin, rubric_sha256, inventory_sha256,
 title, issue_ids, expectation_ids,
 dimensions:[{dimension,assessment,rationale,reference_ids}],
 alternatives:[{expectation_id,description,rationale,reference_ids}],
 overrides:[{expectation_id,prior_interpretation,replacement,rationale,reference_ids}],
 defects:[{issue_id,description,impact,rationale,reference_ids}],
 predecessor:null|{id,sha256}, command_id
}
```

All six dimensions appear exactly once. Selected expectations must refer only to explicitly selected issues. Annotation targets must belong to the selected issue/expectation set; evidence references must be server-issued and associated with selected expectations. Defensible-alternative acceptance, overrides and scenario defects are attributed instructor statements with explicit reasons, not automatically validated findings or professional acceptance.

The document is `INSTRUCTOR_AUTHORED_ASSESSMENT_V1`: ID/version/author/engagement/time, predecessor, pins, authored payload, whitelisted selected existing issue/expectation definitions, selected references and the explicit unvalidated/no-aggregate-grade/shared-state qualification. Source paths, full Key snapshots and original byte blobs are not copied. Existing rubric definitions are retained exactly as selected, rather than generated from keywords.

Metadata includes ID, document SHA, immutable version/predecessor, saved/current engagement revisions, historical learner revision, context status, personal-content visibility and correction availability. Changed source/scope basis or Key redacts title/document; nonauthors receive not found and noninstructors are denied. Ordinary work can advance while an old explicitly pinned assessment remains inspectable under the same source/scope/Key basis.

Corrections create a new ID and incremented version, preserving the exact predecessor document SHA. Only the same author/engagement may correct the current leaf. Branching from a superseded predecessor is rejected. Exact command retry returns the existing immutable document with current authorization and correction eligibility; changed payload under the same command is rejected. Current engagement revision is checked before new publication, and final Key/source/context/authority checks occur inside the private transaction.

## Bounds and recovery

Title is at most 200 characters; dimension assessment and annotation descriptions/interpretations/impacts at most 2,000; rationale at most 4,000. There are at most 10 selected issues/expectations, 8 alternatives, 8 overrides, 8 defect flags and 32 distinct selected evidence references. Options permit at most 4,096 references, a bounded rubric and an 8 MiB inventory. Each document is at most 256 KiB; storage has at most 256 immutable documents and 16 MiB event bodies. The canonical inert archive is at most 32 MiB. Limits reject rather than truncate.

Storage is an owned nonaliased 0700 directory and 0600 regular database, with immutable append-only rows and validated hash/sequence/correction/ownership chains. `PRIVATE_INSTRUCTOR_ASSESSMENTS_V1` explicitly states `INERT_ONLY_NO_ACTIVE_REHYDRATION`. There is no active archive restore, principal remapping, credential/grant restoration or automatic learner release. Supported inert backup does not assert an actual backup occurred.

Disposable tests cover six explicitly unassessed dimensions, exact historical workpaper versions, metadata-only/control-only distinctions, streaming history, same-author corrections across explicit revisions, reasoned alternatives/overrides/defects, command idempotence/conflict, scope/role/Key races, private storage and archive corruption, quotas and unchanged audit state. This is engineering capability for IK-04, not IK-06 qualified calibration or issued professional acceptance.

## Exact recorded work inventory

The comparison now retains explicit authored-task-linked workpaper versions even
when their source-artifact intersection is empty. These use
`EXACT_AUTHORED_TASK_WORKPAPER_VERSION`, distinct from the original
`EXACT_RECORDED_WORKPAPER_VERSION` source association. Both retain the exact
historical workpaper digest; a task link does not invent source support.

`instructor_work_links` adds bounded `recorded_sample_executions`,
`recorded_findings` and `recorded_remediations` metadata to each comparison
expectation. Sample records match exact retained evidence ID **and SHA**, or an
explicit authored task whose recorded digest matches that task in the selected
historical state. Original and corrected traces remain separate, with exact
record hashes, revisions, predecessor hashes, selected-history leaf status,
recorded workpaper/population/selection pins and matching item locators.
Locators remain author-supplied; these links confer no automatic testing credit.

Findings and remediation records match their actual `evidence_ids` fields to
exact retained originals. These are direct recorded ID associations; they are
not content inspection, approval or inferred causal conclusions. Remediation
support is not retroactively attributed to the original finding. Their full
historical record digests are retained; they have no invented version number.
No title, shared control or narrative keyword creates any of these links.

Assessment options add `sample_execution`, `finding` and `remediation` reference
kinds with, respectively, `EXACT_RECORDED_ITEM_OR_AUTHORED_TASK_LINK`,
`DIRECT_RECORDED_FINDING_EVIDENCE_ID` and
`DIRECT_RECORDED_REMEDIATION_EVIDENCE_ID` relations. `content_sha256` is the exact
historical record digest, while `inventory_sha256` remains the digest of its
qualified metadata row. Explicit historical selection never substitutes later
work. Inspection remains `NOT_OBSERVABLE_NO_DOWNLOAD_EVENT_LOG`; recorded links
or file opens do not establish understanding or adequate testing.
