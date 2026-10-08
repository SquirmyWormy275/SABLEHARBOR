# Prospective provider contract draft gate

`company_contract_draft_exercise.py` creates a private `CompanyStore` with
Clean and Messy branches for the selected planned Reno and Boise provider
boundaries. The source-pinned sites are selected for procurement, with draft,
unexecuted contracts and no operation. Proposed internal contacts are not
delegated legal or signature authorities. Clause names are checklist
candidates, not negotiated counterparty terms.

Clean drafts both provider checklists and holds them pending actual service,
data, customer, legal and authority facts. Messy initially omits Boise,
records a premature **local** clearance marker, detects and quarantines it,
backfills the draft checklist and proposes a cure. The cure is not completed;
one exception remains open across five later event rows. No event is a signed
agreement, legal approval, external communication, PHI processing, BA role
determination, provider deployment, contractual cure or termination.

The 2027 event and availability times are authored future simulation as of
September 29, 2026. Each immutable native version also has its real insertion
time. This separation prevents a later audit from treating an authored date as
historic operation. The exercise is outside the frozen current audit pair and
grants no task or assurance credit.

Create it only at a new path under an existing 0700 private parent:

```python
from pathlib import Path
from enterprise.audit_suite.company_contract_draft_exercise import create, verify

root = Path('/private/exercises/contract-draft-01')
create(root, repository=Path('/path/to/SABLEHARBOR'),
       clean_branch='DRAFT-CLEAN-01', messy_branch='DRAFT-MESSY-01')
print(verify(root, repository=Path('/path/to/SABLEHARBOR')))
```

The output contains 12 native versions, an exact receipt and a hash manifest.
`verify` rechecks source pins, exact native rows, causal state, three clocks,
private file modes and absence of grants, collections and active SQLite
sidecars. A later auditor must use ordinary source access and collection in a
fresh engagement after the final registry is frozen. The independently
reviewed isolated reference run is under
`enterprise/generated/audit-suite/company-contract-draft-2026-09-29/` and
does not supply an actual contract or a completed audit procedure.

Run `uv run python -m pytest -q
tests/audit_suite/test_company_contract_draft_exercise.py` for focused causal,
availability and tamper checks.
