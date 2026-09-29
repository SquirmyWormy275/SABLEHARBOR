# Adjacent declared-subject access review

`company_access_review_successor.generate` creates three native review originals for exactly one quarter after an existing, verified local review continuation. It does not relax the original continuation's adjacent-period rule or replace the original Q2/Q3 records.

The typed `AccessReviewSuccessorRecipe` contains:

- `prior_recipe`: the exact `AccessReviewContinuationRecipe` that produced the previous review.
- `prior_review`: a `ReviewContinuationSourceGroup` with id `prior_review`, an explicit source-store label, three exact native references and selected metadata digest.
- `company_id`, new `branch_id`, new `campaign_id`.
- `period_start`, `period_end_exclusive`, `population_at`, `decision_at`, `reconciliation_at`.
- Explicit `local_requirement_basis`.

`generate(destination, repository=..., source_roots=..., recipe=...)` requires the original `identity`, `remediation_initial`, `remediation_final` roots and a separate `prior_review` root. It validates the original 16 records through the unchanged continuation validator using the original recipe. It then reconstructs all three previous review bodies from those exact rights, decisions, missing subjects, actors and links. Canonical encoded equality preserves primitive types; an integer zero cannot substitute for `whole_review_closed: false`. Exact original identities, availability, recipe attribution and local source qualification are checked.

The new period must immediately follow the prior period, span one UTC calendar quarter and have three strictly ordered post-period review events within seven days of its end. Previous review originals must already be available before the new period cutoff. They may have been published just after the previous quarter's end; the producer does not claim they existed at the beginning of the new quarter.

The new originals preserve the original 16 source pins plus the three predecessor pins and selected metadata digest. Current scoped owner/reviewer assignments are separately resolved for the new review; the prior review is verified against its own event date. Local rights are carried forward explicitly because no intervening activity is supplied. This is not a workforce census, a claim of continuous employment/access operation, new removal execution, professional review or whole-review closure. Missing P014 and other unsupported cohort members remain unresolved. Missing authorized rights remain an unresolved decision, not an invented restoration.

This first bounded successor accepts an original local continuation as predecessor; it is not an arbitrary recursive review chain. Supporting subsequent successor types requires another explicit contract. Prospective fictional review events are authorized simulation work; actual corporate appointments, employment facts and accepted criteria cannot be inferred.

Publication uses a new private staged company store. All 19 selected source bodies are retained separately as upstream originals. Original metadata and implementation/scoped-document pins are rechecked before publication. Existing company stores, source grants and audit states are not mutated. There is no model call, automatic control pass or professional acceptance.

Focused tests cover a real identity → removal → Q3 → Q4 local chain, exact source preservation, missed cohort continuity, adjacent quarter enforcement, repinned forged rights/closure, selected metadata changes and final publication races. Private operator/plan integration is separate from this module API.
