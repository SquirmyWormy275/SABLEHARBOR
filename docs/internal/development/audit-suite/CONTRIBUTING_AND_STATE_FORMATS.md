# Audit-suite contribution and state formats

This suite is synthetic audit training. The repository license remains unchanged.
The engine, public configuration labels and neutral tests may be reviewed in Git.
Authored case solutions, reviewer keys, local credentials, selected-world files and
licensed source originals remain in protected storage outside the public tree.
Atlas is a reference source, not the destination for this implementation.

## Editable contracts

- `enterprise/audit_suite/resources/selectors.json` holds the approved eighteen
  selectors and 110 option labels. MM08 has no visible submenu.
- Private `definitions/<variant-id>.json` files use case schema `1.0`.
  `corpus.validate_variant` checks identities, facts, native artifact recipes,
  event references, actor knowledge and playable endpoints. The full finite
  inventory contains ten variants per option plus ten internal MM08 variants.
- Private `clean/<control-id>.json` files use clean schema `1`. Control contracts
  bind to the native register, assigned operating authority and explicit scope.
  `clean.build_control` retains source field meanings, dates and original-source
  hashes. Assurance reviewers do not become operating approvers.
- `parameter_contract` defines discrete, authored intensity/severity anchors.
  `parameters.apply` accepts bounded event gates or a complete causal record set.
  A slider cannot silently become a descriptive adjective. Actual approval,
  irreversible loss and privacy projections need records that support those facts.
- MM10 `CHANGE_EVENT_PREFIX_V1` uses stable original change episodes and their
  linked before/after and retest records. A requested count selects a prefix;
  changing the count does not renumber earlier episodes.
- Incomplete-evidence transformations require exact native field/kind predicates.
  Missing alternate documents are inapplicable, not permission to relabel a
  different business process's case as the requested source.

Keep JSON as data. Do not place executable callbacks, shell commands, external
fetch instructions, secrets or unapproved source text in a case. The validators
are executable contracts; private corpus-generation scripts must also preserve
their version and quality receipts. Structural validation alone is not semantic
or professional acceptance.

## Changes, versions and recovery

The local store uses SQLite with immutable, hash-linked engagement events,
revision checks and idempotent command receipts. App commands receive the current
authenticated actor; a payload cannot select its actor or real authorization time.
Simulation dates affect exercise events, not credential expiration.

An explicit scope revision keeps old work and creates a new generation epoch.
Original PBC requests still resolve to their original frozen plan. New tasks start
unconcluded; old samples and failures are not promoted into new-period assurance.
Versioned plan integrity hashes cover the bound recipes and prepared artifacts.
Never edit a frozen run's world or delivery plan in place to repair an authoring
mistake. Correct the source definition and create a new run or explicit successor.

Temporal procedure records keep coverage dates, performance dates, receipt dates,
methodology, evidence and disposition separate. Implementation changes retain old
records and flag work that now requires reassessment. Remaining-work proposals do
not send requests until the learner confirms them. Date arithmetic reports gaps;
it supplies neither a universal roll-forward window nor an audit opinion.

Private backup format `1` stores a consistent database snapshot, original event
history, referenced immutable files, frozen world files and a checksum manifest.
Restoration imports data into application-owned schema `1`, into a new directory
only. It revokes every previous credential and omits sessions, including credentials
that might have been revoked after the snapshot. Provision a new local principal
and explicitly grant the necessary engagement membership after restoration.
Repository content, licensed-source access and optional model/voice installations
are separate prerequisites. A state backup is not their redistribution package.

For a future schema change, implement a numbered migration into a new store,
retain the original backup, verify every event chain and native-file hash, and
exercise revoked-access, failed-job and scope-history recovery. An unrecognized
backup or database schema must fail explicitly. Do not silently rewrite prior
events to make an old record fit a new shape.

## Verification and review

Run focused tests for the affected mechanism, then actual command-path exercises
with retained native files and immutable IDs. Check substantive source values and
chronology, not merely filenames or successful serialization. Record the exact
code/definition version used by long-running workers; concurrent development can
otherwise create a mixed-version receipt.

Before final delivery, run the complete audit-suite tests and required repository
governance, catalog, organization, hygiene and regression checks. Regenerate
controlled publications and the institutional catalog through their builders.
Preserve approved artwork and finance source locks; never edit their generated
derivatives manually to pass a check.

Human-review exports include original files and interaction/workpaper history.
The separately authorized reviewer edition also includes this run's private case
definitions and causal context. It must not include unrelated engagements or the
entire answer bank. Experimental model feedback is optional, source-bounded and
correctable; a passing model critique is not professional acceptance or an
objective whole-audit grade.

Frozen worlds now record hashes of the application modules used to construct them. New worlds carry an integrity digest, and each generation state pins the complete world digest in its immutable event history. Scope successors retain the prior epoch's pin. Resumed generation checks both that pin and each frozen company-source hash; reviewer exports validate the same frozen inputs. Older checkpoints without this metadata remain identifiable as legacy inputs, rather than acquiring retrospective provenance.

Native JSON object projections require an explicit `object_rows_path` and `object_fields` contract. Field removal preserves the original object envelope and rejects residual disclosure in other fields or metadata. Follow-up delivery retains the exact original recipe. Alternate source projections require independently authored identity, semantic predicates and actual availability dates. A scheduled demonstration is a dated observation packet; it does not establish historical operation or imply that a learner request created a live action.

Backup manifests retain the exact `parent-support/source.sha256` pin alongside `source.json`, including versioned scope directories. Missing, mismatched and orphan pins fail closed before a complete backup or restored destination is published. Arbitrary sidecar paths are not accepted.

MM08 and MM09 allocation uses a frozen encounter pool. Each entry identifies the actual planned initial source request, bound implementation, source definition and initial artifact identities. Follow-ups remain within that encounter. Owner interactions require two distinct scoped responsibility holders; missing or identical participants are excluded. Provider requests name an authored external counterparty and retain the internal source custodian as a relay. Instructor-only allocation counts are omitted from learner state and historical learner exports. Frequency changes the allocated encounters; severity continues to govern the separately authored response mechanics.

### Independent primary packets and instructor Custom composition

Multiple primary cases may coexist only through an explicit private
`binding_contract.causal_composition` contract. `source_catalog(clean_plan)` exposes
stable source addresses to trusted authoring code. Choose every artifact belonging
to each affected request packet; each source must retain distinct stable row IDs.
Declare `mode: INDEPENDENT_SOURCE_PACKETS`, `source_ids`, and one `fact_claims`
entry per private fact (`fact_id`, `subject`, `predicate`, JSON `value`, inclusive
`valid_from` / `valid_to`). Set `semantic_status` to
`AUTHOR_DECLARED_REQUIRES_COMBINED_REVIEW`. Custom structured editing pins selected
source descriptors, performs normal bounded validation and a fresh local critic,
and still requires explicit instructor acceptance. A changed source rejects
acceptance. Model prose cannot silently supply an authoritative binding contract.

Composition retains separate source packets, request event progress and authoring
provenance. Overlapping source or record identities and contradictory typed claims
fail with `COMPOSITION_CONFLICT`. Existing behavior overlays remain a separate,
typed operation. Same-record sequential transformations are not implemented;
unstructured sources without stable record IDs and multiboundary Custom packet
contracts remain blocked. Typed checks do not prove arbitrary natural-language
truth compatibility or professional sufficiency. Unscoped clean actor summaries
are withheld when independent primaries are composed to avoid blanket clean claims.

Explicit instructor-edited MM08 encounter contracts identify both operating
responsibility roles and require distinct scoped people. MM09 contracts carry an
explicit provider object (`id`, `name`, `relationship`,
`origin: AUTHORED_TRAINING_COUNTERPARTY`); provider identity is never inferred from
an internal custodian. Both require a purpose and an actual initial source event.
They undergo the same fresh critic and acceptance process.

### Five-layer experimental review and confidential review channels

`review_layers.resolve` resolves only controls linked to selected workpapers or
referenced delivered artifacts. It reads pinned frozen worlds and validated unit
plans, scoped source-derived authority procedures, exact bound control and
organization records, case facts/events/delivery state, and authored rubrics with
acceptable alternatives. Missing authority access and unlinked control scope are
reported explicitly; retained primary-source pins are rechecked. Source-derived
procedures are not represented as the complete licensed standard text.

The full five-layer input and bounded model projection are stored as immutable,
content-addressed `worlds/<engagement>/review-inputs/<digest>.json` files. State and
learner history retain metadata/digests only. Complete model records are selected
within explicit per-layer budgets; omitted records and full-layer digests are
recorded. Extracted-text truncation is marked with original length and digest.
Consent binds the exact input metadata and sources, including private-layer pins.

The first actual local model call reviews the five layers for an instructor. Its
result, model identity, source inputs and omissions remain private. The second
call receives observable work only, without private facts or first-pass prose;
its suggestions are learner-facing. Both restrict citation identifiers and verify
quoted excerpts against supplied observable sources. Neither grades a whole audit
or penalizes a legitimate sample merely because a planted exception was missed.
Natural-language paraphrase correctness remains subject to human judgment.

Authorized REVIEWER exports include only private appendices referenced by committed
review records, verify their digests, and link them from the export index. Learner
exports and APIs never contain private input layers or private model prose. A
context omission or unavailable licensed source remains a review limitation,
not an assertion that the entire standard/case was evaluated.

New experimental reviewer responses also contain `findings` (up to five). Each
finding has a category (`SUPPORTED`, `CONTRADICTED`, `UNSUPPORTED`,
`NOT_OBSERVABLE`, `REQUIRES_REVIEW`), claim, exact learner excerpt
`{source_ref, text}`, source references, rationale, uncertainty and suggested
follow-up. Excerpts must match decoded values in an actual observable source,
not merely an authorized normative/private reference. The excerpt reference must
also appear in the finding's references. Only the last two categories permit
`{source_ref: null, text: ""}` when no observed passage exists. An empty findings
list is valid; the model is never required to invent a defect. Explicit quotes
inside rationale/claim/uncertainty/follow-up are verified too. Older stored
`observations` remain readable and are not rewritten into invented typed findings.

## Explicit review feedback

`review.resolve` with an explicit `disposition` records feedback: `agree`,
`disagree`, `correct`, `missing_context` or `human_review`. Current learners may
respond, as may reviewers and instructors. A human comment retains its issue
status and appends the response to history with exact current workpaper version
and digest. An experimental suggestion retains its original result, input pins
and `SUGGESTIONS_ONLY` status; feedback is appended to appeals with the response's
workpaper pins. The current feedback status and disposition are separate fields.
Neither agreement nor a claimed correction establishes acceptance or closes an
issue. Prepared input rows cannot receive feedback.

An optional `input_digest` for experimental suggestions or
`response_workpaper_version` for human comments rejects stale explicit pins.
The command's existing expected engagement revision remains required. For
compatibility, a human review command without disposition remains an independent
resolution action restricted to review/instruct permission. Historical entries
are not rewritten. Focused authorization, replay, stale-input and preservation
tests cover both routes.

Independent resolution additionally requires an OPEN human comment and an actor
who neither prepared nor contributed a workpaper version. The server enforces
this even for an instructor. Explicit feedback remains available to contributors;
its correction claim does not resolve the comment. The UI exposes a separate
resolution form only when `review_independent_resolution` is advertised and the
current reviewer qualifies. Its command omits disposition and pins the current
workpaper version. Replaying the original command retains its receipt; a new
second resolution of an already resolved comment is rejected.
