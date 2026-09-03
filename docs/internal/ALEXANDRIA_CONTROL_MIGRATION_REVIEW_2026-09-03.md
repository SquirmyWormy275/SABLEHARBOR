# Alexandria Control migration review — 2026-09-03

## Repository migration

- Old repository name: `SABLEHARBOR-ORACLE` (legacy migration reference only)
- New repository name: `SABLEHARBOR-ALEXANDRIA-CONTROL`
- Classification rule: observable in-world surfaces stay public; god-view truth, evaluator
  interpretation, scoring, expected detections, and private leakage controls stay private.

## Files reviewed

The review covered the root README and maintainer rules; governance, document-index, open-issue,
and safety-sweep documents; Blackridge README, generator CLI, foundation tests, query cookbook,
case and supporting documentation; validation, reconciliation, conservation, corruption, profile,
and workbook reports; and acceptance metadata.

## Disposition

Public schemas, deterministic generators, participant-visible records, analytical examples,
physical/financial reconciliation, generator QA, workbook QA, profiles, and non-revealing boundary
assurances stayed public. The existing evaluator seed was migrated to structured private scenario
truth, rubrics, expected-detection data, manifests, and leakage tests. Public generator-integrity
assertions remain public; private evaluator assertions are separately enforced in Alexandria
Control. No new hidden truth or canon was added.

## Safety and validation

Current-facing references use Alexandria Control naming. Historical handoff documents and this
migration record may retain the former name solely to explain provenance. Search and validation
results are recorded in the migration PR and updated here at closeout: repository governance,
catalog, organization, hygiene, root tests, Blackridge smoke/m00/full-year builds, Blackridge tests,
and whitespace validation were run.

## Unresolved boundary questions

Evaluator criteria not present in the v0.1.0 seed remain `TODO_PRIVATE_REVIEW` in the private
repository. No open canon issue was resolved by this migration.
