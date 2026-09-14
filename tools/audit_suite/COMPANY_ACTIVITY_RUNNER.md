# Independent company activity runner

Run explicit local exercise recipes before creating an audit:

```bash
PYTHONPATH=. .venv/bin/python -m tools.audit_suite.generate_company_activity incident \
  --recipe /private/incident-recipe.json \
  --destination /private/new-incident-run
```

The maintained runner currently accepts `mover`, `identity-period`, `incident`, `backup` and `training`.
Recipe fields follow `TransferRecipe`, `PeriodRecipe`, `IncidentRecipe`, `BackupRecipe` and `TrainingRecipe` in the
corresponding company activity modules. For an identity period, `movers` is a JSON
array of transfer recipes. Training uses arrays of `TrainingMember` objects in
`cohort` and `TrainingCourse` objects in `courses`, with `role_ids` as an array. All assumptions, people, branch identities and dates are
explicit; the runner supplies no default corporate policy or invented appointments.
The existing generator validates the recipe against its pinned repository sources.

Keep the recipe private (0600), and use a new destination under an existing private
0700 parent. Symlinked or hard-linked recipes and existing destinations are rejected.
Generation uses a temporary private directory. Invalid recipes and failed generation
leave no final company store. Successful runs retain `company/company.sqlite3`, the
original recipe bytes, the generator receipt and a manifest of counts and hashes.
A failed final-directory write is rolled back using the private-directory helper.
This does not provide a globally atomic capture of other running company stores.

The runner verifies every new native source hash and confirms zero grants and zero
collections. It creates no engagement, evidence request, prepared audit world, model
call or service process. Source stores can subsequently be connected by the explicit
local company operator and ordinary scoped audit collection. That later collection
must retain its own receipts; generation is not proof that a control operated
successfully, that a population is complete, or that an auditor tested it.

The focused operator tests exercise a real paired source generation, exact recipe
retention, private files, rejection of existing/public/aliased inputs, and cleanup
following an injected partial-generation failure. Generator-specific chronology,
causality and canonical-boundary checks remain in their own test suites.
