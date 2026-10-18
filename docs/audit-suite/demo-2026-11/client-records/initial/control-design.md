# Selected control design and local implementation context

The catalogue is version 0.1.0, dated 2 September 2026. It names general control expectations; the local scope page and retained operating records specify the procedures examinable here. Broader enterprise requirements remain outside this edition.

| Control | Statement | Objective | Default role | Frequency | Natural evidence |
|---|---|---|---|---|---|
| SH-IAM-007 | Periodic user-access reviews identify stale, excessive, conflicting, or inappropriate access. | IAM-004 | System/data owner | quarterly/semiannual based on risk | review population, decisions, remediation |
| SH-CFG-002 | Baseline configurations are defined for critical technologies and material drift is detected. | CFG-002 | IT/Security/Platform | continuous | baseline-as-code, drift reports |
| SH-BCM-003 | Restore tests demonstrate recoverability of critical data/systems at defined cadence. | BCM-002 | IT/Service owner | quarterly/annual risk-based | restore test evidence |

## SH-BCM-003
Select critical datasets and recovery paths using documented risk; restore into an isolated environment; measure recovery time and recovered data age; validate integrity and usability against the BIA; record failures and retest.

Proposed system of record: Restore test environment

## SH-CFG-002
Version the intended configuration for each technology; compare deployed settings to the approved baseline; investigate drift and link correction or an expiring exception.

Proposed system of record: Configuration baseline repository

## SH-IAM-007
Quarterly for privileged access and at a risk-approved cadence for other rights, reconcile HR/contractor records to actual entitlements; require owner decisions per account; independently confirm removals and overdue escalation.

Proposed system of record: Access review campaign

For these local records, the restore enquiry includes application usability. The original copy plan does not supply approved BIA/RPO/RTO acceptance or a historical application-use contract. The selected enquiry does not turn this local dataset into an enterprise critical-data inventory.
