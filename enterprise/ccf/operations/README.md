# Baseline testing, evidence intake and assessment workflow

This local application imports the verified reference assessment's 210 plans: 70 baseline controls across corporate, Reno and Boise. Each plan preserves the base procedure, added duties, proposed sources, population reconciliation and boundary test. A result belongs to one plan, implementation version and explicit period. It does not accept framework mappings or establish operating effectiveness.

Twenty-four controls have bounded automated assertions **in addition to mandatory manual tests**. The [full test contracts](CONTROL_TEST_CONTRACTS.md) anchor all 24 to authored procedures. The original eight are summarized here:

| Control | Structured record kind | Computed checks |
|---|---|---|
| SH-IAM-004 | `termination` | Disablement deadline, enabled state and remaining entitlement count |
| SH-IAM-007 | `access_review` | Reviewer independence, review deadline and enforcement of retain/remove decisions |
| SH-BCM-002 | `backup_job` | Scheduled job completion, deadline and expected/observed artifact hashes |
| SH-BCM-003 | `restore` | RTO/RPO arithmetic, content hashes, reported dependencies and suppression outcome |
| SH-CFG-002 | `configuration_drift` | Approved/observed baseline and unresolved drift count |
| SH-INC-001 | `incident_escalation` | Escalation deadline and required recipient coverage |
| SH-SEC-003 | `vulnerability` | Verified remediation, deadline and verifier/remediator separation |
| SH-TRN-002 | `training` | Required course version, completion deadline and assessment result |

These checks compare exported fields; for example a reported dependency flag still needs corroboration during human testing. They are not full vendor adapters or complete tests of every duty. The other 46 controls have explicit manual tests. `BASE` and every additional criterion must have an observation, result, rationale and retained record IDs. A missing test stays NOT_RUN. Thresholds and role authorities come from the operator's declared criteria and independent scope review; the application invents no operational SLA.

## Run the complete synthetic exercise

```sh
uv run python -m enterprise.ccf.operations demo \
  --reference /private/reference-assessment-run \
  --source-root /authorized/source-documents \
  --output /new/private/evidence-workflow-demo
```

The command independently verifies the reference bundle against its originals before importing plans. It creates a private SQLite database, 210 test plans, 48 positive/negative cases, one prospective validation, full assessment history, and separately named synthetic credential files. All dates, actors, outcomes and deadlines in this example are invented. Open `START_HERE.md` in the output directory.

## Initialize a separate working store

```sh
uv run python -m enterprise.ccf.operations init \
  --reference /private/reference-assessment-run \
  --source-root /authorized/source-documents \
  --principals /private/authorized-local-principals.json \
  --output /new/private/workflow
```

The principals file is an array with `id`, `permissions` (`prepare`, `review`, `admin`), `boundaries`, `valid_from` and `expires_at`. IDs use letters, digits, hyphens or underscores. Configure immutable subject IDs corresponding to authorized users. Local permission grants confer no corporate appointment. Initialization returns no credentials to the terminal: it writes random 256-bit credentials into mode-0600 files. The database stores only their SHA256 hashes. Keep these files private and deliver each only to its intended holder.

The command interface authenticates the credential, derives the actor, checks scoped permissions and expiry, and uses the host clock. Requests cannot set the actor, event time or computed result. A subject with both prepare and review permissions still cannot review their own case. Reviewers may reassign cases to another currently authorized preparer; earlier preparers remain excluded from review.

The CLI is a **trusted local operator application**. The [protected API and enterprise identity verifier](SERVICE.md) provide a separate service boundary with scoped authorization; deployment still requires approved issuer/subject mappings, TLS/network configuration and protected storage. Database/filesystem administrators remain trusted. The [collection subsystem](COLLECTION.md) implements JSON/CSV and authenticated HTTPS intake with scheduled retries and retained originals. No live deployment or vendor access is implied.

## Command sequence and payloads

Every mutation uses the current case revision to reject stale updates. SQLite serializes writes, retains raw export bytes as JSON text, and appends a hash-linked event. Updates/deletes are blocked by database triggers. Reopening or reporting replays events, rechecks scope and permissions at their event dates, and recomputes tests. The evaluator implementation is pinned when the store is created; changing it requires an explicit history migration rather than silent reinterpretation.

```sh
uv run python -m enterprise.ccf.operations command \
  --db /private/workflow/workflow.sqlite3 \
  --credential-file /private/preparer.credential \
  --case ASSESSMENT-001 --action create --revision 0 \
  --payload /private/create.json
```

| Action | Required payload / behavior |
|---|---|
| `create` | `plan_id`; `scope` with explicit `origin` (`SYNTHETIC` or `OPERATOR_SUPPLIED`), timezone-aware `period_start`/`period_end`, `service`, `implementation_version`, `criteria_authority`. Creator becomes assignee. |
| `assign` | Reviewer supplies `assignee`; the assignee must have current prepare permission for this boundary and must not be a prior reviewer. |
| `population` | Independent reviewer registers `expected_ids`, `excluded_ids`, `source_count`, `source_system`, `query`, `reconciliation`, `criteria_review`, `captured_at`, `census_json` and its `source_export_sha256`. The retained census is a JSON array of all included/excluded IDs. Exclusions require `exclusion_rationale`. Counts, IDs and digest must reconcile. |
| `intake` | Assigned preparer supplies `raw_json`, `captured_at`, `expires_at`, `source_system`, `extraction_query`, `transformation_version` and `manual_tests`. Source system must match the registered population. |
| `review` | Independent reviewer supplies current `submission_id`, `decision` (`ACCEPT` or `REJECT`) and `rationale`. Expired evidence can be rejected but cannot be accepted. Acceptance preserves the computed result. |
| `remediate` | Assigned preparer supplies `change_reference`, `action`, future `due_at`. Later submissions retain the original scope and population. |
| `close_prospectively` | Independent reviewer supplies `validation_case_id` and `rationale`. The new case must independently pass the same plan, service, origin and criteria authority, cover a period after the original and remediation, and retain fresh evidence. Historical failures remain visible. |

Population registration is a separate authenticated action before intake. This enforces separation and reconciliation; it does not prove that a declared source query is authoritative. Independent reviewers must check the actual source and exclusions. Zero populations are not automatically passed: use the separate applicability process to resolve a no-occurrence claim.

Each record in `raw_json` is an object with `id`, `origin`, `boundary_id`, timezone-aware `occurred_at`, `kind` and `data`. Occurrence time is the scoped event/snapshot time, not a substitute for the event-specific timestamps in `data`. Every ID must match the independent population exactly; duplicates, omissions, mixed origins and wrong scope prevent testing. Raw export size is limited to 10 MB. JSON intake records are supported directly. The collection subsystem can normalize configured JSON, CSV and authenticated HTTPS exports; actual provider field mappings and access scopes require verification.

`manual_tests` maps every plan criterion ID to `{ "result": "PASS|FAIL|NOT_RUN", "rationale": "...", "record_ids": ["..."] }`. Referenced IDs must exist in the retained export. The structured fields for the record kinds are shown in the explicit synthetic [examples](examples.py); [testing.py](testing.py) implements the bounded assertions. Additional record kinds can carry documentary evidence for manual tests.

A missing population or incomplete test cannot pass. A failed assertion remains FAIL even if another manual test is missing. Missing evidence can be corrected and independently retested against the same period/population. Any known substantive failure, including one found during remediation of an earlier NOT_RUN, permanently marks the history. A later same-period pass cannot close that historical failure. Prospective closure validates the correction and retains the failed original period.

## Reporting and credential revocation

```sh
uv run python -m enterprise.ccf.operations report \
  --db /private/workflow/workflow.sqlite3 \
  --credential-file /private/reviewer.credential \
  --output /new/private/report.json

uv run python -m enterprise.ccf.operations revoke \
  --db /private/workflow/workflow.sqlite3 \
  --credential-file /private/admin.credential --subject SUBJECT-ID
```

Reports expose only currently authorized boundaries and include evidence freshness, overdue remediation, raw records, test details and retained findings. Period summaries combine cases for the same plan, service, origin and period: any known historical failure takes precedence over a competing pass, and incomplete/stale cases prevent a current pass. Freshness is evaluated when reporting; an old accepted result is not silently represented as current evidence. Revocation is append-only and blocks subsequent actions while preserving authorized earlier history. Existing stores and reports are never overwritten by these commands.

Actual source access, population/criteria authority, operating facts and named appointments must be supplied before this can represent an actual assessment. The output remains local CCF workflow evidence until a separate qualified framework/source review accepts the relevant mappings. Atlas remains a read-only guide; all populated outputs belong in private SABLEHARBOR holdings.

## Integrated delivery and history migration

One command verifies the reference against authorized sources, builds all control examples, exercises the signed API with scheduled collection, and assembles a private assessment handoff and precise activation-input register:

```sh
uv run --extra ccf-service python -m enterprise.ccf.operations.delivery build \
  --reference /private/reference-assessment-run \
  --source-root /authorized/source-documents \
  --legacy-store /private/pr146/workflow.sqlite3 \
  --legacy-revision 52c37a1415c3d4702375f79c5de59a1861a9b62b \
  --output /new/private/integrated-ccf
uv run --extra ccf-service python -m enterprise.ccf.operations.delivery verify --output /new/private/integrated-ccf
```

Omit both legacy arguments when there is no prior store. Migration loads the exact prior evaluator from the explicitly selected trusted local Git revision, verifies the original snapshot, and accepts a private copy only if the current evaluator reproduces identical history. It retains permissions and revoked credentials without overwriting the original. Stop the old writer before real cutover; later appends are not included. A replay difference requires reviewed migration work, not automatic acceptance.

`START_HERE.md` links control coverage, framework deltas, source dependencies, the signed API rehearsal, and the actual inputs required for live activation. `ASSESSMENT_HANDOFF.json` remains preparation until actual operating evidence and qualified source/mapping reviews support the strict assurance-engine input contract. No source availability, local test result or migration receipt establishes external coverage by itself.
