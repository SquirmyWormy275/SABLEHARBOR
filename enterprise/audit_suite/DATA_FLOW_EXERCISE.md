# Prospective company-native data and record flow exercise

`company_data_flow_exercise.py` creates a separate private `CompanyStore` with Clean and Messy branches for one nonpersonal, metadata-only restricted-data **candidate marker**. It is a proposed shared-control exercise for SH-DAT-001/002/003 and SH-REC-001/004, not an audit evidence cache or accepted operation. It does not ingest personal data or PHI. Its candidate intake and Reno-to-Boise path are design questions, not deployed flows.

The module checks the current proposed data custodian and Privacy/Legal contacts through the source-pinned organization snapshot and hashes the approved reference scope, draft service-description workpaper, proposed control procedures, and runtime geography decision. These sources support the exercise boundary. They do not establish actual contracts, PHI processing, business-associate status, approved retention, or operating site deployment.

Clean registers the marker, blocks an intake lacking authority, denies a replication request, reconciles the decision record, and defers retention action. Messy admits a local eligibility marker before authority review, queues a *local route marker* before the gate, then quarantines it; the destination acknowledgement remains unverified and the exception stays open. Neither branch actually transfers data or deletes records. The retained event bodies include actor, causal before/after state, prior-record hash, definition hash, data class, authority gaps, source-specific UTC event/availability, and separate actual import time. The 2027 dates are authored prospective exercise time, not historical 2027 operation.

Use a new absolute destination under an existing 0700 private parent. For example:

```python
from pathlib import Path
from enterprise.audit_suite.company_data_flow_exercise import create, verify

root = Path('/private/exercises/flow-01')
create(root, repository=Path('/path/to/SABLEHARBOR'), clean_branch='FLOW-CLEAN-01', messy_branch='FLOW-MESSY-01')
print(verify(root))
```

The output has 13 immutable native versions in `company.sqlite3`, a receipt with every exact native identity/version/SHA/timestamp, and a hash manifest. No grants or collections are made. A later auditor must get an explicit current grant and use ordinary source discovery, exact reads, and collection; this package by itself gives no task credit or conclusion. `verify` checks privacy, hashes, no active SQLite sidecars, native rows, provenance, timestamps, and the causal sequence. It is local integrity verification, not independent professional assessment.

Run `pytest tests/audit_suite/test_company_data_flow_exercise.py`. The focused tests cover both causal branches, source timestamp separation, actual ordinary collection visibility with a grant in a disposable clone, unavailable-before-event behavior, scope collision, and tamper rejection.
