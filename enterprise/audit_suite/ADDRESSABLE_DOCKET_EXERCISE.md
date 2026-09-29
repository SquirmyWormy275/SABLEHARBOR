# Prospective HIPAA addressable-specification docket

`company_addressable_docket_exercise.py` creates a private company-native
Clean/Messy source pair for the **22 source-identified addressable
specifications**. It pins the one-to-one inventory in
`enterprise/ccf/assurance/review_data/addressable_specifications.json`, the
separate HIPAA section analysis, finding and control-procedure context, and
proposed consultation contacts. SH-POL-003 is a related general exception
control, not a substitute for the addressable decisions; its active
`OPEN`/`INSUFFICIENT_SOURCE` gap remains unresolved.

Clean reconciles all 22 locator candidates and holds them pending an actual
environmental and authority assessment. Messy initially omits
`164.312(e)(2)(ii)` and records an invalid blanket-waiver marker. Later source
reconciliation quarantines the marker, backfills the missing locator and
leaves one exception open. Neither branch decides HIPAA applicability,
approves an alternative, or claims an implemented safeguard. The output is a
pending intake docket, not a 22-decision register.

The 2027 event and availability times are future authored simulation as of
September 29, 2026. Real insertion time is retained separately. This exercise
is outside the current audit pair's frozen source registry and supplies no
audit task, collection, operating-history or legal credit.

Create only at a new path under an existing 0700 private parent:

```python
from pathlib import Path
from enterprise.audit_suite.company_addressable_docket_exercise import create, verify

root = Path('/private/exercises/addressable-docket-01')
create(root, repository=Path('/path/to/SABLEHARBOR'),
       clean_branch='ADDR-CLEAN-01', messy_branch='ADDR-MESSY-01')
print(verify(root, repository=Path('/path/to/SABLEHARBOR')))
```

The output contains 50 immutable native versions, an exact receipt and hash
manifest. `verify` checks the current pinned source inventory, private modes,
native content and chronology, one continuing exception, and absence of audit
grants or collections. The independently reviewed reference run is under
`enterprise/generated/audit-suite/company-addressable-docket-2026-09-29/`.
The corrected `HANDOFF-V2.json` states that actual HIPAA applicability is
**undetermined**; the ambiguous V1 handoff is preserved as history.

Run `uv run python -m pytest -q
tests/audit_suite/test_company_addressable_docket_exercise.py` for focused
source, chronology, availability and tamper checks. A final audit needs actual
service facts, qualified owner/legal decisions and ordinary source collection
in a fresh bound engagement.
