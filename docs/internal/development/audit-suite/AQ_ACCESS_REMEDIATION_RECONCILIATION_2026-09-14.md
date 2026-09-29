# Selected local access-remediation observations

The pure helper `enterprise.audit_suite.access_remediation_reconciliation.analyze(contracts, sources, bodies, scope)` returns a list of observations. The maintained report's optional input key is `access_remediation_contracts`; its output key is `access_remediation_reconciliation`. Existing plans without the optional section retain their existing behavior and shape. The helper reads no files or stores and changes no audit state.

Each contract has exactly these fields:

```json
{
  "parent": {
    "population_ref_id": "selected-population",
    "decisions_ref_id": "selected-decisions",
    "reconciliation_ref_id": "selected-reconciliation",
    "application_ref_id": "selected-application",
    "hr_ref_id": "selected-hr"
  },
  "producer_label_expected": "explicit-native-producer-label",
  "baseline_ref_id": "selected-baseline-state",
  "request_ref_id": "selected-removal-request",
  "attempts": [
    {
      "resolver_ref_id": "selected-resolver",
      "execution_ref_id": "selected-execution",
      "state_ref_id": "selected-resulting-state",
      "verification_ref_id": "selected-operating-probe"
    }
  ],
  "followup_ref_ids": ["selected-followup"]
}
```

There may be at most four contracts, one or two attempts per contract, and zero to two followups, inside the existing 64-source budget. Both attempts plus the full local history require 16 sources for one branch: five parent records and eleven continuation records. Paired branches sharing those five parent records require 27. Source IDs are explicit references to an authorized retained capture; no latest-version discovery or source fallback occurs. A producer label is checked as an explicit native claim, separately from the physical portfolio component identity.

The parent review uses the existing native IAM007 review reconciliation, including original population/member pins, decision/application links, rights comparisons and qualified HR coverage. The continuation checks the exact five upstream native identities on every record, declared campaign and actors, source availability by the continuation input, original unresolved-population claims, local qualification, and the complete set of explicitly associated previous-event links. A link outside the contract's associated source set is `MISSING_SELECTED_SUPPORT`; this does not mean the evidence does not exist. Associated mismatched pins and late predecessor availability are separate observations.

For each explicitly selected attempt, the helper compares the requested rights and owner decision with the selected application baseline. It derives the local state transition from the exact permission-name mapping, then separately compares recorded before/after rights, removals, unresolved names and status text. It compares the designated operating probe's observed/expected rights, excess/missing sets and permission-probe results with that resulting local state. Permission arrays are interpreted as sets; ordering alone is not an exception. Executor/verifier identity differences are observable metadata, not professional independence or qualification approval. Followup records contribute source and lineage checks; this version does not independently judge the adequacy of their response or closure wording.

Times use the existing explicit UTC checks. Source role, scope and malformed typed references fail closed. Factual mismatches produce separate booleans and link observations, without a blanket control result. Continuation timing relative to the audit period is reported separately; later remediation does not rewrite an earlier period conclusion.

The captured projection does not retain the raw `origin` and `provenance` fields needed to recompute the producer's selected metadata digest. Therefore the helper reports consistency of the declared digest and `metadata_verification: NOT_RECOMPUTABLE_FROM_RETAINED_FIELDS`. It never manufactures missing metadata or claims independent verification of that digest. The surrounding maintained report remains responsible for original byte verification and current registry, scope, revision and grant checks before publication.

Every result explicitly preserves `whole_review_closure: NOT_ESTABLISHED`, `population_acceptance: NOT_PERFORMED`, `control_effectiveness: NOT_ASSESSED`, `professional_assurance: NOT_PERFORMED`, and `coherent_operating_year: NOT_ESTABLISHED`. Agreement among these local records does not prove external-system permission execution, erase an omitted person, supersede old quarterly records, or establish a complete control population.

Validation uses actual independently generated native parent/continuation fixtures. Focused tests cover both local branches, exact lineage, retained population limitations, mapping/state/probe contradictions, misleading status text, changed native parent pins, metadata-label differences, delayed state availability, unsupported roles/routes, malformed versions, bounded selection and missing associated support. Professional sufficiency remains outside these mechanical checks.
