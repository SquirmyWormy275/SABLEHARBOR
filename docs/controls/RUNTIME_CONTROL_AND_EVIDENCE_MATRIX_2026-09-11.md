# Runtime Control and Evidence Matrix — Reno / Boise / Northern Nevada

**Purpose:** implementation specification for the Common Controls Framework. This file defines design/evidence requirements; it does not assert operating effectiveness.

| Domain | Reno primary | Boise recovery | Owned Northern Nevada | Evidence / test |
|---|---|---|---|---|
| Asset ownership | Sable-owned equipment | Sable-owned equipment | Sable-owned facility + equipment | asset register, serials, custody, finance reconciliation |
| Physical perimeter | provider building + Sable cage | provider building + Sable cage | Sable-operated perimeter | access design, CCTV, visitor logs, alarm tests |
| Cage/data-hall access | named least privilege | separate named least privilege | named least privilege | quarterly access review; terminated-user population reconciliation |
| Provider master access | restricted/logged | restricted/logged | N/A except contractors | provider-access log review |
| Power | dual A/B, UPS/generator | dual A/B, UPS/generator | engineered redundant paths | SLA reports; load/maintenance tests; excursion population |
| Cooling | high-density/liquid-ready | recovery-density capable | mixed air + liquid-first AI zone | environmental trends, alarms, maintenance |
| Carrier diversity | two physical routes | independent Boise routes | dual property entrances | route diagrams, LOAs, failure tests |
| Network boundary | Sable-controlled edge | independent recovery edge | Sable-controlled edge | config baselines, change logs, scans |
| Identity/PAM | Sable controlled | independent break-glass | Sable controlled | JML population, PAM logs, quarterly certification |
| Keys/HSM | Sable controlled | independent recoverable copy | dedicated key boundary | key inventory, ceremonies, recovery test |
| Data classification | resource-level | same classification | same | entitlement decision logs |
| Backup | immutable protected copies | recovery copy | primary + immutable | backup jobs, restore tests, completeness reconciliation |
| Recovery | fail to Boise | operate/failback | eventually primary; Boise remains independent | timed RTO/RPO exercise |
| Logging | security/admin/application | independent availability | full owned-site telemetry | log source inventory, gap detection, retention tests |
| Vulnerability/configuration | Sable systems | Sable systems | systems + facility controllers | scan/config evidence; remediation |
| Incident response | provider + Sable coordination | provider + Sable coordination | Sable site + vendors | exercises, tickets, notification timestamps |
| Change management | facility changes notified; Sable changes approved | same | Sable facility/IT change control | sampled changes and emergency changes |
| Supplier assurance | annual provider review | independent provider review | critical maintenance/carrier/vendor review | SOC reports, contracts, CUECs, vendor risk review |
| Environmental/fire | provider evidence | provider evidence | Sable inspection/testing | inspection certificates, alarms, maintenance |
| Media handling | Sable custody | Sable custody | Sable custody | chain of custody, destruction certificates |
| Capacity | monthly kW/rack/network | recovery capacity | installed vs ultimate capacity | 95th percentile trends, forecast, expansion gates |
| Finance | colo OPEX + assets | colo OPEX + recovery assets | land/CIP/PP&E + OPEX | GL reconciliation, asset register, approvals |

## Control-state taxonomy

Every implementation record must carry one of: `DESIGN_ONLY`, `IMPLEMENTATION_IN_PROGRESS`, `IMPLEMENTED_NOT_TESTED`, `TESTED_DESIGN_EFFECTIVE`, `OPERATING_TEST_IN_PROGRESS`, `OPERATING_EFFECTIVE`, `EXCEPTION`, or `NOT_APPLICABLE`. Synthetic tests may use `SYNTHETIC_TEST_ONLY` and may never satisfy `OPERATING_EFFECTIVE`.

## Evidence population integrity

For access logs, incidents, changes, maintenance, backups, alerts, and provider tickets, evidence extraction records must preserve source system, period, timezone, query/filter, pagination/export limits, record count, transformations, reconciliation, hash/provenance, and reviewer. Targeted high-risk selections remain nonprojectable unless a separate representative method is defined.

## Runtime-specific acceptance tests

1. Pull power feed A under controlled test; protected load remains available.
2. Pull power feed B under controlled test.
3. Demonstrate generator/UPS transfer evidence at provider/owned layer as applicable.
4. Fail primary carrier and demonstrate alternate route.
5. Recover keys without Reno identity/KMS dependency.
6. Restore protected data in Boise and reconcile integrity/completeness.
7. Start minimum Alexandria/identity/DNS/logging stack in Boise.
8. Demonstrate failback with transaction/data reconciliation.
9. Test cage/owned-site emergency access and access revocation.
10. Test provider/contractor remote-hands authorization and chain of custody.
11. Validate logging continues during primary service disruption.
12. Exercise provider exit/equipment removal procedure at tabletop level before production and physically during migration where feasible.

## SOC readiness

SOC 1/SOC 2 readiness requires the provider assurance report, CUEC mapping, Sable Harbor implementation evidence, complete populations, documented test procedures, exceptions/remediation, reviewer sign-off, and explicit period coverage. Provider reports do not establish Sable Harbor operating effectiveness. The CCF remains the native control architecture; external-framework mappings are overlays.
