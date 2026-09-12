# Integrated CCF delivery workflow

Owner-authorized implementation follows PR146 and the approved corporate/Reno-primary/Boise-recovery reference scope. SOC 2 Security, Availability and Confidentiality Type 2 readiness and a HIPAA BA/subcontractor scenario remain the baseline. ISO 27001, ISO 42001 and C5 are selectable extensions. Atlas is a read-only reference; code and private populated records belong in SABLEHARBOR.

## One delivery, parallel implementation

| Stream | Owner | Deliverables | Acceptance |
|---|---|---|---|
| Protected service and identity | `service_identity` subagent | Runnable API, verified issuer/audience/signature/expiry, exact subject mapping, deployment configuration | Forged/wrong-issuer/expired identities and unauthorized scope rejected; signed subjects complete permitted actions |
| Evidence collection | `connectors_collection` subagent | JSON/CSV and authenticated HTTPS connectors, pagination/provenance, separate population packet, durable scheduled jobs | Missing/duplicate/wrong-scope pages cannot pass; no secret disclosure; retries/idempotency demonstrated |
| Control testing | `control_testing` subagent | Expanded bounded assertions, typed record contracts, authored-procedure references, substantive negative fixtures | Every new adapter has independent negative evidence; all base/added human criteria retained |
| Integration, history and assessment handoff | Root | Authenticated store boundary, verified migration, private readiness/export package, integrated rehearsal, CI/PR closeout | Preserve original failures and permissions; replay retained history; source and operating gaps remain explicit |

Agents work on separate files. Root owns shared store interfaces, dependency lockfiles, workflow integration, reader/catalog regeneration and GitHub publication. No agent writes Atlas or deploys an external service. Existing private assessments are never overwritten.

## Execution sequence

1. Pin the verified reference, current repository baseline and approved scope.
2. Implement the three parallel streams and adversarial tests.
3. Integrate verified identities with current, scoped local authority; retain host-controlled event times and optimistic revisions.
4. Acquire source records through configured connectors. Retain raw hashes, extraction details, complete pages and source counts. Independent reviewers register the distinct source population; collection never fabricates this approval.
5. Select optional frameworks with repeatable `--framework ISO27001`, `--framework ISO42001` and `--framework C5` arguments. The selected union becomes executable manual duties in the retained plans, with shared controls/actions deduplicated and unmapped assessment prerequisites kept explicit. Create a scoped case with actual facts or an explicitly synthetic fixture. Reconcile the population before automated and manual testing.
6. Independently review results, retain findings, record remediation and validate correction. A competing or historical failure cannot be erased by a passing retest or different timestamp spelling.
7. Generate the scoped assessment handoff and unresolved-input register. Framework source/mapping acceptance remains a separate qualified decision.
8. Exercise the integrated system with signed fixture identities and controlled source endpoints, migrate prior history only when verified reproduction is identical, run regression and repository checks, and merge the concrete result.

## Completion boundaries

Engineering completion means runnable components, integrated tests, operational configuration examples, durable evidence and review mechanics, reproducible private artifacts, and merged code. It does not mean SABLEHARBOR has deployed the service, processed PHI, operated controls through an examination period, obtained certification or received an assessor opinion.

Live activation requires concrete values and authority for the identity issuer/audience/JWKS and subject mapping; deployment host/domain/TLS and service operator; source endpoints, credentials and approved read scopes; named control owners/reviewers; actual service/PHI/vendor responsibilities and commitments; assessment period and complete source populations; qualified source and mapping acceptance. These are external inputs, not development tasks to mark complete with invented values.

## Reviewable final package

The final closeout will link the implementation PR, verified integration report, history-migration receipt, expanded test-contract inventory, private assessment handoff and operational input register. Each unmet gate must identify the precise missing input and the activity it blocks. Preparation records remain explicit about synthetic origins and unresolved assurance acceptance.

## Implemented selection and verification

The default baseline contains 70 controls and 210 boundary plans. Selecting all three extensions produces 86 controls and 258 plans, preserving the baseline and adding only selected candidate duties. Twenty-four controls have bounded automated assertions; all controls retain mandatory human tests. The private delivery exercises 49 synthetic cases, signed HTTP authorization, scheduled collection, independent review and verified migration of prior history. Delivery verification replays retained events and regenerates the selected plans and assessment handoff. Actual deployment and qualified assurance acceptance remain the explicit operational gates above.

For an owner who has not selected an identity tenant or host, the [concrete pilot design](CCF_PILOT_SYSTEM_DESIGN_2026-09-12.md) supplies a local Keycloak, private API and GitHub acquisition path. It turns missing technical choices into testable defaults while retaining actual operating appointments and production rollout as explicit decisions.
