# Intelligent contextual workspace

Execution update, September 14, 2026: **IN_PROGRESS** under the owner’s explicit overnight authorization. The planning status and authorization language retained below describe the earlier queue proposal; current execution is controlled by [QUEUE.json](../../../reader/overnight/QUEUE.json). Partial technical checkpoints do not establish full-stage completion or professional/user acceptance. See [the implementation checkpoint](COMPANY_SOURCE_IMPLEMENTATION.md).

Status: **LOCKED_DIRECTION; QUEUED_NOT_STARTED**. Owner emphatically endorsed contextual navigation: “YES! CONTEXT CONTEXT CONTEXT!!!!! Make this intelligent!!!!!!!!!!!!!” This adopts the preceding navigation proposals and makes context a core design requirement. It records implementation work, not completed features or a started overnight run.

## Context contract

The subsequent owner instruction “add everything else you mentioned too” explicitly includes every final navigation proposal. CX-02 covers stable destinations, unified search, previews, object summaries, saved workspaces and consolidation of duplicate screens; CX-04 covers contextual actions, keyboard efficiency and plain-language progressive forms; CX-05 covers all navigation acceptance checks. Empty search states must explain active filters and offer reset. Important actions cannot depend on hover. New capabilities receive a home in the existing workflow rather than automatically adding sidebar destinations.

Maintain explicit, inspectable context for engagement, company branch, audit scope/period, role and permissions, simulated date, active investigation/question, control/procedure, population/sample, source versions, current workpaper/review point and unresolved dependencies. Distinguish user-declared intent from inferred intent. Let users correct, clear or switch investigation context; never silently carry facts or drafts across engagement boundaries. Stable navigation remains predictable even as contextual content changes.

Use context to surface related authorized records, relevant changes, unresolved questions and available next actions. Explain recommendations with actual source/work references and why they matter now. Show unavailable support and uncertainty. Match suggestions to work state: an unrequested population, received-but-unreconciled export and changed population require different actions. Do not equate completion with effectiveness or recommend a passing conclusion simply because a mode is Clean.

Learner assistance must use only information authorized and available to that learner at that time. Hidden scenario truth, instructor keys, future company events and unrelated engagement data cannot feed suggestions, search, summaries or agent context. Instructor explanations remain in the separate protected key workflow. Respect guided versus unassisted engagement settings; hints/reveals are explicit and recorded, not covert assistance embedded in navigation.

Intelligence does not require a model call on every interaction. Deterministic relationships, permissions, dependencies and source versions provide the foundation. Optional model-generated synthesis cites accessible evidence, labels inference and falls back to usable navigation when unavailable. Suggestions never silently submit requests, modify scope, promote notes, clear review points or make professional judgments. Explicitly authorized actions use ordinary domain commands and audit history.

## Queued work

| ID | Deliverable | Acceptance |
|---|---|---|
| CX-01 | Permission-aware context model and investigation state | Persist and expose the context contract with provenance, staleness and explicit context switching. Keep engagement/branch boundaries and user intent inspectable. Demonstrate no hidden-key, future-record, cross-role or cross-engagement leakage, including inferred context and caches. |
| CX-02 | Stable navigation, unified search and list-preview-workspace flow | Consolidate overlapping destinations; use consistent object summaries, contextual actions, permission-aware grouped search and previews. Preserve filters, position and drafts across deep links/back navigation; support next/previous inspection and saved role/engagement workspaces with reset. Keep navigation stable rather than adaptively moving controls. |
| CX-03 | Evidence-linked contextual guidance | Surface relevant authorized relationships, changes, blockers and suggested next actions with reasons and cited records/work. Distinguish declarations from inference and missing evidence from adverse conclusions. Permit user correction/dismissal. Respect unassisted assessment boundaries and log deliberate hints; never use hidden answers to steer learners. Refresh suggestions when versions, access or scope change. |
| CX-04 | Efficient contextual forms and accessible actions | Reuse known scoped context visibly and allow correction; progressively disclose advanced fields, preserve invalid-form entries, explain disabled actions without leaking restricted facts. Provide discoverable keyboard shortcuts and non-hover alternatives. Preview references without losing work; explicit actions preserve accountability. |
| CX-05 | Contextual journey and isolation validation | Exercise unfamiliar investigation, evidence correction, role/context switch, access revocation, stale suggestion, contradictory support, empty filtered search and model unavailability. Verify deep links/back navigation/draft retention, recommendation provenance, cache isolation and no covert key assistance. Measure navigation/entry burden and obtain actual user feedback; record scripted versus human acceptance separately. |

## Completion and coordination

Success means users can tell what they are investigating, what supports it, what changed and why a next action is relevant, without repeatedly reconstructing context. It does not mean automatic conclusions or dynamic menu rearrangement. Reuse UX/IK/AQ foundations rather than creating competing stores or another dashboard for each feature.

Jobs share the existing `audit_company` lane, worker cap and integrator ownership of shared schemas/dependencies/catalogs. Keep populated contexts, private keys and learner histories in excluded storage. Preserve source/version history and existing permission/publication boundaries. Atlas remains read-only. This queue addition starts no scheduler or execution.


## Implemented recorded-evidence context — September 14

Artifact details now show the recorded request purpose, source-declared and
request-linked controls, related scoped procedure definitions, and exact
workpaper versions citing the original. Links resolve against the current
authorized projection. Control relevance does not establish procedure support;
no filename analysis, hidden Key, model call or automatic conclusion supplies
these relationships. Users can hide the section and return through exact
record links without losing their investigation context.

“Open workpaper draft” restores the existing personal new-workpaper draft.
“Add this original to draft” explicitly appends the selected artifact without
overwriting text, control selection or conclusions. Closing retains the draft
and returns to the original only while its source/context pins remain current.
Scope and permission changes close stale forms; source-binding changes disable
the handoff. Successful formal saves clear the transient handoff.

Validation: 126 frontend unit tests, production TypeScript/Vite build and full
mocked-browser suite passed. Browser regression covers existing-draft retention,
explicit deduplicated attachment, exact return navigation, scope/permission
changes and source-binding changes. Actual A-viewer read-only checks traversed
original → request/control/procedure → original and returned to the private
instructor investigation with focus/search retained. Learner isolation and
unchanged formal history were verified. Private receipts are under
`enterprise/generated/audit-suite/company-portfolio-2026-09-14/reference-a-v1-evidence-context-browser/`.
These are scripted checks, not owner usability or full contextual-journey acceptance.

## Implemented retained-original comparison and review feedback

The PBC workspace now includes a retained side-by-side original inspector. Each
side searches the currently authorized artifact inventory, caps matching options
and preserves an explicitly selected original when the search changes. Text is
loaded only on request through the existing download route, bounded to 1 MiB per
file and verified against exact retained size and hash. Binary files retain their
exact download link. Concise source identity accompanies the content; full hash,
routing and coverage fields remain expandable. Changing authority or source
context clears the pair; stale successes and failures cannot replace current
content. Ordinary panel navigation retains the selected pair. This does not
produce workpaper content or infer equivalence between files.

Review details now show recorded human response history and experimental appeals.
The response form passes the exact current workpaper version or original review
input digest. Prepared inputs and unauthorized viewers cannot respond. The UI
requires the server's explicit `review_feedback` capability: older local servers
cannot accidentally apply their earlier resolution semantics to the new form.
Feedback remains distinct from the issue status and independent reviewer action.
