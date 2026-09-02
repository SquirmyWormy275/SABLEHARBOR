# BLACKRIDGE COMPLETE ONE-FILE CODEX EXECUTION PACKAGE
# VERSION 1.1.0 — SUPERSEDES ALL EARLIER BLACKRIDGE CODEX HANDOFFS

## THIS FILE IS THE ONLY INPUT REQUIRED

This is a single, self-contained execution package. It contains:

1. the complete Blackridge Enterprise Data Foundation execution mandate;
2. the complete Blackridge Ultimate Sandbox closeout-governance plan;
3. the complete machine-readable Blackridge acceptance register.

Do not pause to request missing governance attachments. They are embedded in this file.

Do not rely on an earlier partial prompt, prior chat summary, previous status message, or the failed/interrupted Codex attempt. This file supersedes those handoffs for the current run while preserving any valid repository work that can be inspected and tested.

## REQUIRED STARTUP ACTIONS

Before substantive implementation:

1. Inspect the repository and any local state left by the failed/interrupted attempt.
2. Save this complete handoff in the repository at:

   `docs/handoffs/BLACKRIDGE_COMPLETE_ONE_FILE_CODEX_EXECUTION_PACKAGE_v1.1.0.md`

3. Extract **Part II** of this file verbatim into:

   `blackridge/docs/governance/BLACKRIDGE_ULTIMATE_SANDBOX_CLOSEOUT_MASTER_PLAN_v1.0.md`

4. Extract the JSON object in **Part III** into a valid JSON file at:

   `blackridge/config/acceptance/BLACKRIDGE_CLOSEOUT_ACCEPTANCE_REGISTER_v1.0.json`

5. Validate the extracted JSON with a parser.
6. Commit those governance artifacts with the initial repository-recovery/canon commit.
7. Update acceptance-gate states only from concrete evidence. Architecture, placeholders, plans, or green tests that do not exercise the requirement do not justify `ACCEPTED`.
8. Execute **Part I** completely. Do not stop after materializing the governance files.

## CURRENT RUN SCOPE

The current Codex run must fully execute **Part I: Blackridge Enterprise Data Foundation**.

Part II defines the complete long-term path to Blackridge v1.0. It is binding governance and must be committed, but it does not require the current run to prematurely build every later facilitator, publication, expert-review, or educational package unless Part I explicitly requires it.

The current run must, however:

- build every data-foundation deliverable in Part I;
- satisfy every Part I completion gate;
- update all acceptance-register gates materially addressed by the work;
- leave later gates honestly marked `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, or `REVIEW_READY`;
- create no fake placeholders to make the register look complete.

## FAILURE-RECOVERY RULE

If work from the failed attempt exists, do not wipe it reflexively.

- Preserve valid commits.
- Quarantine uncertain generated artifacts.
- Re-run migrations, generators, reconciliations, and tests.
- Replace incoherent work rather than layering more code over it.
- Record the recovery decision in the repository audit.
- Never claim recovered work was accepted merely because it existed.

## COMPLETION LANGUAGE

Do not say “complete,” “integration-ready,” “production-ready,” “independently auditable,” or “Blackridge v1.0” unless the corresponding acceptance gates are actually satisfied and evidenced.

Begin with repository forensics and governance materialization, then continue without stopping through the full Part I mandate.

---

# PART I — BLACKRIDGE ENTERPRISE DATA FOUNDATION EXECUTION MANDATE

# CODEX AUTONOMOUS BUILD MANDATE
# BLACKRIDGE ENTERPRISE DATA FOUNDATION v0.1.0
# SQL DATABASE + EXCEL MASTER WORKBOOK + FULL-YEAR SYNTHETIC ENTERPRISE BACK END

You are operating as the principal data architect, mining-systems engineer, financial-systems engineer, simulation architect, accounting-systems engineer, and repository delivery owner for the Blackridge case universe inside Sable Harbor.

This is an execution mandate, not a request for a plan, outline, feasibility memo, or partial prototype.

Your job is to inspect the current repository, reconcile the existing canon and branches, recover any valid Blackridge work that actually exists, and then build the complete first production-grade Blackridge enterprise data foundation. The deliverable must include:

1. a normalized, searchable SQL database;
2. a comprehensive Excel master workbook generated from that same database;
3. deterministic generators and migrations;
4. full financial statements and accounting subledgers;
5. inventory, assets, facilities, employees, maintenance, operations, geology, processing, commercial, procurement, governance, systems, shadow-IT, and provenance data;
6. validations proving that the data reconcile;
7. documentation sufficient for another engineer, auditor, accountant, analyst, or agent to understand and extend the system;
8. GitHub commits, CI, release artifacts, and a pull request;
9. a private treatment for hidden benchmark truth so that the public Sable Harbor repository does not disclose the case answer key.

Do not stop after creating schemas. Do not stop after creating a workbook shell. Do not stop after a few sample rows. Do not stop after reporting progress. Continue until the completion gates at the end of this mandate are satisfied or until a genuine external blocker makes a specific gate impossible. If a noncritical approach fails, choose a sound fallback and continue.

---

# 0. REPOSITORY AND AUTHORITY CONTEXT

## 0.1 Repository

Canonical repository:

`https://github.com/SquirmyWormy275/SABLEHARBOR`

Repository-state rules for this run:

- the repository is intentionally PUBLIC;
- accepted Sable Harbor corporate lore v0.2 and the official organization package have been merged to `main`;
- the exact remote `main` SHA may have advanced after this handoff was assembled, so fetch and inspect the current remote before editing;
- the enterprise-finance platform in PR #9 is review-blocked and must not be silently merged, treated as accepted canon, or used as an unexamined dependency;
- the enterprise-portal work in PR #13 is a separate open workstream and must not be treated as proof that Blackridge has already been materialized;
- several historical `blackridge/m00-*` branches exist, but their visible state has not established a complete accepted Blackridge implementation;
- a prior narrative completion report is not repository evidence;
- the private `SABLEHARBOR-ORACLE` companion repository was not confirmed to exist when this package was assembled.

Treat the live repository, branch graph, commit graph, pull requests, release assets, workflow evidence, and testable files as the source of truth.

If the interrupted or failed Codex attempt left local changes, commits, a feature branch, generated data, or worktree state:

1. inspect it before resetting or deleting anything;
2. preserve coherent work with commits, a recovery branch, or a clearly labeled stash;
3. compare it against this complete mandate;
4. reuse it only after validation;
5. document what was preserved, replaced, or discarded and why.

Do not repeat unsupported claims about a complete Blackridge implementation.
## 0.2 Canon precedence

Use this precedence order:

1. any complete and internally consistent detailed Blackridge canon that is actually present in repository history and can be traced to the approved decisions;
2. `docs/canon/SABLE_HARBOR_CANONICAL_ARCHITECTURE_HANDOVER.md`;
3. `docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`;
4. `docs/canon/DECISION_REGISTER.md`;
5. `docs/canon/SABLE_HARBOR_CONTINUITY_AUDIT_v0.2.md`;
6. this execution mandate for Blackridge implementation details;
7. recoverable prior Blackridge code, but only after tests prove it is coherent;
8. `architecture/corporate-operating-model-v0.1` as noncontrolling background where useful;
9. prior chat summaries or status claims only when corroborated by files and repository history.

Never silently override a LOCKED decision.

When a needed quantitative or technical detail remains OPEN, choose the narrowest reasonable, reversible, internally coherent PROVISIONAL assumption. Record it in the Blackridge decision register, identify its consequences, and continue. Do not halt merely because every parameter was not previously hand-approved.

## 0.3 No license change

Do not add an MIT license or any other open-source license. Preserve the repository’s current no-license/proprietary posture unless an existing controlling repository document says otherwise.

## 0.4 Public repository and hidden truth

The public repository must never expose:

- the hidden causal oracle;
- benchmark answer keys;
- private evaluator rubrics;
- unreleased intervention answers;
- credentials or secrets;
- real personal information;
- licensed third-party material that cannot legally be redistributed.

You are authorized to create a separate PRIVATE companion repository named:

`SquirmyWormy275/SABLEHARBOR-ORACLE`

if it does not already exist and if GitHub authentication permits repository creation.

The public repository should contain:

- schemas;
- generators;
- public participant-visible data;
- public workbooks;
- public SQL database;
- documentation;
- test harnesses that do not reveal hidden answers;
- manifests and hashes for restricted packages;
- interfaces for loading private oracle data.

The private oracle repository should contain:

- hidden canonical ground truth;
- answer keys;
- evaluator-only tables;
- hidden causal states;
- private benchmark packages;
- oracle database;
- oracle workbook or evaluator extracts if useful;
- private validation reports that would reveal the intended diagnosis.

If private repository creation is technically impossible, do not leak the oracle into the public repository. Generate it locally under a gitignored path, create a detailed `ORACLE_PUBLICATION_BLOCKER.md`, preserve hashes and reproducible generation instructions, and finish every other deliverable.

---

# 1. AUTONOMY AND OPERATING RULES

You are authorized to:

- inspect all branches, commits, tags, pull requests, workflows, and repository objects;
- create and switch branches;
- install normal development dependencies in the project environment;
- add Python packages to `pyproject.toml`;
- create migrations;
- create SQLite databases;
- create PostgreSQL-compatible DDL and tests;
- create Excel workbooks;
- generate synthetic data;
- add GitHub Actions;
- create release assets;
- create a private companion repository for the oracle;
- commit frequently;
- push branches;
- open pull requests;
- merge the Blackridge pull request into `main` after all required checks pass, the acceptance evidence is complete, and no unresolved conflicts remain;
- create a tagged prerelease containing generated public artifacts.

Do not ask for confirmation for normal implementation choices.

Only stop for a true external blocker such as:

- invalid GitHub authentication that prevents all pushes;
- an unavailable required credential that cannot be replaced by a local fallback;
- repository corruption that prevents any safe recovery;
- a destructive conflict that would require discarding unrelated user work.

Even then, push all safe completed work, document the blocker precisely, and leave the repository in a resumable state.

Do not:

- spend the session writing only plans;
- create empty directories and call them a build;
- create placeholder CSV files;
- create empty workbook tabs;
- create a database containing only a few demo rows;
- hardcode financial statements independently from the general ledger;
- hardcode the $52 million write-down directly into the statements;
- create contradictory Excel and SQL sources of truth;
- invent people who were supposedly at Blackridge when canon says they were not;
- turn ordinary operational variation into cartoonish incompetence;
- insert fraud unless a future explicitly approved scenario requires it;
- expose hidden oracle data publicly;
- overwrite or delete unrelated Sable Harbor work;
- merge old provisional corporate numbers into canon without review;
- add a framework sample-size table or audit opinion engine to this build;
- use real-world employee personal information;
- copy real mining-company data and represent it as synthetic canon;
- claim checks passed without preserving machine-readable results.

---

# 2. REQUIRED INITIAL REPOSITORY FORENSICS

Before implementation, perform and document a repository audit.

Run at minimum:

```bash
git status
git remote -v
git fetch --all --tags --prune
git branch -a -vv
git log --all --graph --decorate --oneline --date-order
git tag -n
git fsck --full --no-reflogs --unreachable
gh repo view SquirmyWormy275/SABLEHARBOR
gh pr list --state all --limit 100
gh run list --limit 100
```

Inspect all branches matching:

- `blackridge/*`
- `canon/*`
- `architecture/*`
- `docs/*`
- `assets/*`

Inspect unreachable commits and dangling trees before concluding that prior Blackridge work is absent. Recover valid code only if:

- it is consistent with canon;
- it has coherent file history;
- it does not overwrite current lore;
- tests can be run;
- data artifacts can be regenerated;
- no hidden oracle is exposed.

Create:

`blackridge/docs/repository/BLACKRIDGE_REPOSITORY_RECOVERY_AUDIT.md`

It must state:

- branches inspected;
- commits inspected;
- unreachable objects inspected;
- what was recovered;
- what was not found;
- what prior claims were not substantiated;
- which branch is the implementation base;
- which files control canon;
- which pre-existing work is being preserved;
- why the selected integration approach is safe.

## Base branch selection

Use the following rule:

1. Fetch and inspect the current remote.
2. Use the latest accepted `origin/main` as the integration base.
3. Do not stack Blackridge on the review-blocked finance branch, the enterprise-portal branch, an obsolete architecture branch, or a stale M00 branch.
4. If the interrupted run already created coherent Blackridge commits, preserve them and rebase or cherry-pick them onto the correct branch only after inspecting the diff and running focused tests.
5. Create or continue:

`blackridge/enterprise-data-foundation-v0.1.0`

6. Target the eventual pull request at `main`.
7. Do not merge unrelated open pull requests as part of this assignment.
---

# 3. LOCKED BLACKRIDGE CANON

Preserve the following.

## 3.1 Enterprise and site

- Operator: **Argent Ridge Mining**
- Site: **Blackridge Mine**
- Location: Nevada
- Mine type: mid-sized open-pit copper-and-gold operation
- Relevant project: **West Wall Phase 4**
- Period of central case: calendar year 2015
- Blackridge must be modeled as a functioning enterprise and mine, not merely an incident evidence folder.

## 3.2 Phase 4 economics and dates

Treat these as calibrated canon targets:

- Phase 4 capital authorization: approximately **$148.2 million**
- June approval base-case NPV: approximately **$184 million**
- Base-case IRR: approximately **22.8%**
- Investment hurdle: approximately **12%**
- Earliest reasonable reassessment date: **May 18, 2015**
- Approval date: **June 26, 2015**
- Cross-functional trigger: approximately **October 6, 2015**
- Revised case falls below hurdle: approximately **October 19, 2015**
- Year-end write-down/impairment effect: approximately **$52 million**

These numbers must emerge from coherent operations, commitments, forecasts, accounting policies, and valuation calculations. Use calibration parameters, not statement-level plugs.

## 3.3 Causal spine

The central failure is correlated operational downside and consumed optionality:

1. aging fleet and component exposure weaken reliability;
2. increasing West Wall haul distances consume effective haul capacity;
3. waste movement and stripping fall behind;
4. ore exposure declines;
5. blend flexibility narrows;
6. more difficult and variable western material enters the plant in less favorable combinations;
7. recovery deteriorates nonlinearly;
8. local mitigations consume remaining operational slack and temporarily mask the system-level problem;
9. post-approval commitments and governance reverse the burden of proof;
10. the Phase 4 case falls below the hurdle.

The failure is not one bad truck, one bad orebody, one arithmetic mistake, one corrupt executive, or one incompetent department.

## 3.4 Epistemic rules

The system must distinguish:

- what was physically true;
- what was recorded;
- what was available;
- what was known by each system;
- what each person encountered;
- what each person noticed;
- what each person understood;
- what each person believed;
- what each person had authority to change;
- what management received;
- what later reconstruction established.

The public dataset must not contain an explicit field such as `true_root_cause = ...`.

## 3.5 People continuity

**Daniel Mercer** is the only future Sable Harbor leader directly exposed to Blackridge.

Do not place Priya Raman, Jon Bell, Elena Torres, Marcus Reed, Maya Okafor, Caleb Hargrove, or Rachel Kim inside the Blackridge decision process. Priya enters later through Daniel’s reconstruction. Jon enters later by challenging them to prove recurrence.

## 3.6 Organizational tone

No villains are required.

The case must remain credible because:

- local competence is real;
- systems answer locally valid questions;
- definitions differ legitimately;
- reporting compresses information;
- no standing owner exists for the interaction;
- authority and information are inverted;
- post-approval burden of proof changes;
- mitigations obscure deteriorating optionality;
- shadow tools preserve useful local knowledge but remain fragile.

The governing line is:

> Competence existed locally. Integration was absent globally.

---

# 4. PRODUCT OBJECTIVE

Build the Blackridge enterprise backend so that it can support future work in:

- accounting software;
- finance and FP&A;
- mine operations;
- maintenance and reliability;
- inventory and warehousing;
- procurement;
- capital projects;
- commercial settlement;
- geology and metallurgy;
- workforce planning;
- asset management;
- HSE and environmental compliance;
- IT and data lineage;
- shadow-IT analysis;
- management reporting;
- internal control;
- SOC and IS-audit benchmark generation;
- case-study instruction;
- forensic reconstruction;
- counterfactual analysis;
- management consulting;
- causal analytics;
- future Sable Harbor product testing.

The database must be the canonical queryable enterprise representation.

The Excel workbook must be a professional human-facing management, finance, and master-data interface generated from SQL views.

The database and workbook must never be separately hand-maintained.

---

# 5. TECHNICAL ARCHITECTURE

## 5.1 Language and packaging

Use Python 3.12 as the primary runtime, with compatibility tests for Python 3.11–3.13 where practical.

Use:

- `SQLAlchemy 2.x` for relational models and database access;
- `Alembic` for migrations;
- `Pydantic 2.x` or dataclasses for typed configuration and generation contracts;
- `sqlite3`/SQLAlchemy SQLite as the zero-configuration committed and released database;
- PostgreSQL-compatible types and migrations where practical;
- `pytest`;
- `ruff`;
- `mypy` or `pyright`;
- `openpyxl` and/or `XlsxWriter` for Excel generation;
- `Faker` only with a fixed seed and synthetic-safe profiles;
- Python `Decimal` for money and precision-sensitive calculations;
- deterministic PRNG streams separated by domain;
- SHA-256 manifests.

Do not create a microservice architecture. This is a repository-local, deterministic enterprise data platform.

## 5.2 Database products

Mandatory public artifacts:

- `blackridge_public_v0.1.0.sqlite3`
- `blackridge_schema_v0.1.0.sql`
- `blackridge_postgresql_v0.1.0.sql`
- `blackridge_data_dictionary_v0.1.0.csv`
- `blackridge_data_dictionary_v0.1.0.md`
- `blackridge_query_cookbook_v0.1.0.sql`
- `BLACKRIDGE_MASTER_TRACKER_v0.1.0.xlsx`
- domain CSV extracts;
- checksums and manifest.

Mandatory private artifacts:

- `blackridge_oracle_v0.1.0.sqlite3`
- `blackridge_oracle_manifest_v0.1.0.json`
- evaluator-only reconciliation and answer-key package.

## 5.3 Dataset profiles

Implement at least:

### `smoke`

Small dataset used by CI. It proves schema, generator, finance, workbook, and validation paths without heavy runtime.

### `m00`

The 72-hour golden physical-conservation fixture beginning around January 12, 2015 at 06:00 local time. It must exercise trucks, operators, routes, stockpiles, plant flow, fuel, maintenance, serialized components, and accounting capture.

### `full_2015`

The complete enterprise year:

- opening state at December 31, 2014;
- January 1 through December 31, 2015 transactions;
- 12 monthly closes;
- 2014 comparative/opening balances;
- 2015 budget and rolling forecast versions;
- Phase 4 WBS, commitments, actuals, and impairment analysis;
- all required masters and subledgers;
- public artifacts and private oracle.

### `case_cutoff_<date>`

Public snapshots that enforce what could be known at selected dates, including:

- 2015-04-30;
- 2015-05-18;
- 2015-06-26;
- 2015-09-30;
- 2015-10-06;
- 2015-10-19;
- 2015-12-31.

Snapshot generation must exclude records not available by the cutoff, even when the underlying physical event occurred earlier.

## 5.4 Canonical time fields

Do not collapse time.

Use, where applicable:

- `event_at`
- `recorded_at`
- `available_at`
- `effective_from`
- `effective_to`
- `posted_at`
- `approved_at`
- `observed_at`
- `received_at`
- `decision_at`
- `superseded_at`

Store timezone-aware timestamps. Nevada local business time should be handled explicitly. Preserve UTC and local-business-date views.

## 5.5 Units and precision

Use canonical SI/metric storage where practical:

- tonnes;
- dry metric tonnes;
- kilograms;
- grams;
- meters;
- kilometers;
- liters;
- kilowatt-hours.

Support display conversions for:

- short tons;
- pounds of copper;
- troy ounces of gold;
- gallons;
- miles.

Never mix units silently. Create a `unit_of_measure` table and conversion registry.

Use integer minor currency units or `Decimal`, never binary float for ledger amounts.

## 5.6 Stable identity

Every major entity requires:

- human-readable canonical ID;
- immutable UUID;
- source-system identifier mappings;
- valid-from/valid-to;
- status;
- provenance;
- created/updated metadata.

Identity mapping must be first-class data. Example:

- canonical truck: `BRG-HT-017`
- MineTrack: `T17`
- ForgeWorks: a numeric EAM ID
- ERP: a fixed-asset ID
- vendor portal: an OEM serial reference

Mappings may be incomplete, dated, or disputed. Do not create a magical perfect crosswalk in the public 2015 environment.

---

# 6. REQUIRED REPOSITORY STRUCTURE

Adapt to existing conventions, but the final structure must be comparably explicit:

```text
blackridge/
├── README.md
├── pyproject.toml
├── alembic.ini
├── config/
│   ├── dataset_profiles/
│   ├── accounting/
│   ├── operations/
│   ├── workbook/
│   └── canon/
├── migrations/
├── schemas/
│   ├── sql/
│   ├── jsonschema/
│   └── exports/
├── src/blackridge/
│   ├── cli.py
│   ├── config.py
│   ├── ids.py
│   ├── units.py
│   ├── time.py
│   ├── db/
│   ├── domain/
│   ├── generation/
│   ├── simulation/
│   ├── accounting/
│   ├── validation/
│   ├── export/
│   ├── workbook/
│   ├── snapshots/
│   └── search/
├── data/
│   ├── public/
│   │   ├── databases/
│   │   ├── workbooks/
│   │   ├── extracts/
│   │   ├── manifests/
│   │   └── samples/
│   └── restricted/
│       └── .gitkeep-or-readme-only
├── docs/
│   ├── canon/
│   ├── repository/
│   ├── architecture/
│   ├── data_dictionary/
│   ├── accounting/
│   ├── operations/
│   ├── workforce/
│   ├── assets/
│   ├── inventory/
│   ├── systems/
│   ├── shadow_it/
│   ├── workbook/
│   ├── sql/
│   ├── case/
│   └── decisions/
├── queries/
│   ├── finance/
│   ├── operations/
│   ├── maintenance/
│   ├── inventory/
│   ├── workforce/
│   ├── governance/
│   └── case/
├── scripts/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   ├── regression/
│   ├── corruption/
│   └── workbook/
└── reports/
```

Do not commit Python cache, local virtual environments, temporary workbook files, or the public repository’s hidden oracle.

---

# 7. RELATIONAL DATA MODEL

Create a normalized transactional schema plus analytical views. Do not implement everything as one giant denormalized table.

Every table must have:

- documented purpose;
- primary key;
- foreign keys;
- uniqueness constraints;
- status fields where applicable;
- effective dating where applicable;
- indexes for common queries;
- row-count expectations;
- source/provenance fields;
- data dictionary entries.

## 7.1 Metadata, provenance, and dataset control

Mandatory tables or equivalent:

- `dataset_version`
- `generation_run`
- `generation_seed`
- `schema_version`
- `source_system`
- `source_extract`
- `source_record_reference`
- `identifier_namespace`
- `identifier_map`
- `unit_of_measure`
- `currency`
- `exchange_rate`
- `calendar_date`
- `fiscal_period`
- `assumption`
- `decision_record`
- `canon_reference`
- `lineage_edge`
- `transformation_run`
- `data_quality_rule`
- `data_quality_result`
- `validation_run`
- `validation_result`
- `artifact_manifest`
- `artifact_hash`
- `snapshot_cutoff`
- `release_manifest`

## 7.2 Organization and legal structure

Model enough enterprise structure to produce valid financials while keeping uncertain legal details marked PROVISIONAL.

Mandatory:

- `organization`
- `legal_entity`
- `operating_unit`
- `business_segment`
- `department`
- `cost_center`
- `profit_center`
- `responsibility_center`
- `reporting_hierarchy`
- `delegation_of_authority`
- `approval_limit`
- `location`
- `facility`
- `building`
- `building_level`
- `room`
- `operating_area`
- `security_zone`
- `spatial_relationship`

Use a configurable provisional reporting entity for Argent Ridge Mining and Blackridge. Do not silently create an elaborate portfolio of unrelated mines.

## 7.3 Workforce and HR

The January 2015 Blackridge site population should be approximately 550 employees and embedded contractors, consistent with prior design. Preserve named high-resolution characters where canon exists, but generate the rest deterministically.

Mandatory:

- `person`
- `employee`
- `contractor`
- `employment_relationship`
- `position`
- `position_assignment`
- `reporting_line`
- `department_assignment`
- `crew`
- `crew_membership`
- `shift_pattern`
- `scheduled_shift`
- `actual_shift`
- `attendance_event`
- `leave_request`
- `absence`
- `overtime_authorization`
- `timesheet`
- `time_entry`
- `labor_class`
- `trade_skill`
- `qualification`
- `employee_qualification`
- `training_course`
- `training_completion`
- `license_or_certification`
- `compensation_rate`
- `payroll_profile`
- `benefit_plan`
- `benefit_enrollment`
- `payroll_run`
- `payroll_entry`
- `labor_distribution`
- `system_account`
- `access_role`
- `access_assignment`

Requirements:

- no real PII;
- synthetic names and synthetic non-deliverable email domains;
- no unnecessary sensitive medical or protected-class attributes;
- full effective-dated assignment history;
- no person scheduled in two places simultaneously;
- qualifications constrain maintenance and operating assignments;
- payroll reconciles to time and GL;
- embedded contractors remain distinguishable from employees;
- construction-project contractors remain distinct from routine embedded contractors.

## 7.4 Site, facilities, and buildings

Build the tangible mine.

Mandatory facility classes include:

- administration building;
- mine operations/dispatch building;
- technical services/geology building;
- assay laboratory;
- metallurgical laboratory;
- heavy mobile-equipment workshop;
- fixed-plant maintenance shop;
- component rebuild area;
- warehouse;
- receiving yard;
- quarantine area;
- dirty-core staging;
- tire shop;
- wash bay;
- fueling station/fuel farm;
- explosives magazine and secure blast-material storage;
- primary crusher;
- coarse-ore stockpile;
- grinding building;
- flotation plant;
- concentrate storage and loadout;
- tailings and water-management infrastructure;
- electrical substations;
- communications rooms;
- water treatment/dewatering assets;
- HSE/clinic space;
- security gates;
- laydown yards;
- road-maintenance facilities;
- parking and employee muster areas.

Each facility must link to:

- location hierarchy;
- owner/custodian;
- cost center;
- maintainable assets;
- inspection requirements;
- capacity constraints;
- security zone;
- active dates.

## 7.5 Mine topology, geology, and planning

Mandatory:

- `pit`
- `phase`
- `bench`
- `mining_block`
- `block_model_version`
- `geological_domain`
- `ore_block_estimate`
- `drill_hole`
- `drill_interval`
- `geological_assay`
- `survey`
- `blast_pattern`
- `blast`
- `muckpile`
- `material_class`
- `material_parcel`
- `mine_plan_version`
- `monthly_mine_plan`
- `weekly_mine_plan`
- `shift_mine_plan`
- `precedence_constraint`
- `ore_exposure_state`
- `stripping_state`
- `haul_route_node`
- `haul_route_edge`
- `road_segment`
- `road_condition`
- `road_restriction`
- `dump_point`
- `waste_dump`
- `stockpile`
- `stockpile_layer`
- `stockpile_survey`
- `stockpile_movement`
- `stockpile_provenance_estimate`
- `blend_option`
- `blend_constraint`

Model:

- Central Pit as mature and declining;
- East Wall as the workhorse and flexibility buffer;
- West Wall/Phase 4 as development/ramp exposure;
- North, Central, and South Phase 4 access corridors;
- actual road lengths, grades, rolling resistance, speed limits, and conditions;
- stripping dependencies;
- ore-exposure days;
- blend optionality as a hidden computed state and imperfect public estimates.

The hidden physical oracle may know precise parcel provenance. Public operational records should lose precision as material is blasted, loaded, stockpiled, mixed, reclaimed, and processed.

## 7.6 Mobile and fixed assets

Scale to a real mine:

- 27 haul trucks;
- multiple shovels/loaders;
- drills;
- dozers;
- graders;
- water trucks;
- fuel/lube trucks;
- cranes;
- forklifts;
- light vehicles;
- dewatering equipment;
- process plant fixed assets;
- electrical and instrumentation assets;
- laboratory assets;
- facility assets.

Target:

- approximately 130–160 mobile units;
- approximately 2,500–4,000 fixed maintainable assets;
- at least 1,500 serialized major components and repairables where realistic.

Mandatory:

- `asset_class`
- `asset_model`
- `asset`
- `asset_hierarchy`
- `asset_location_history`
- `asset_status_history`
- `component_class`
- `serialized_component`
- `component_installation_history`
- `meter`
- `meter_reading`
- `asset_criticality_assessment`
- `declared_critical_equipment`
- `criticality_factor`
- `failure_mode`
- `failure_effect`
- `maintenance_strategy`
- `warranty`
- `asset_document`
- `inspection_requirement`

Criticality must be calculated from consequence, redundancy, safety, environmental effect, production effect, lead time, detectability, and replacement complexity. Also create a management-maintained “declared critical equipment list” that is useful but somewhat stale. Do not equate the two.

## 7.7 Maintenance and reliability

Mandatory:

- `maintenance_notification`
- `work_request`
- `work_order`
- `work_order_task`
- `work_order_status_history`
- `priority_code`
- `failure_code`
- `cause_code`
- `remedy_code`
- `downtime_event`
- `equipment_delay_event`
- `planned_maintenance_plan`
- `maintenance_schedule`
- `inspection`
- `condition_monitoring_reading`
- `oil_sample`
- `vibration_reading`
- `temperature_alarm`
- `labor_booking`
- `material_requirement`
- `material_issue`
- `tool_requirement`
- `bay_requirement`
- `crane_requirement`
- `resource_reservation`
- `maintenance_deferral`
- `backlog_snapshot`
- `bad_actor_assessment`
- `repairable_pool_status`
- `vendor_repair_order`
- `component_rebuild_history`

The maintenance workflow must model:

detection → notification → triage → priority → planning → materials → scheduling → resource reservation → execution → testing → release → close.

Constraints:

- bays are finite;
- cranes and lifting fixtures are finite;
- labor skills matter;
- parts may be physically on site but unavailable;
- inspections observe condition; they do not automatically repair it;
- deferred maintenance modestly increases future hazard;
- component health is hidden;
- maintenance sees observable evidence such as alarms and samples;
- similar components fail at different times;
- cohort exposure emerges rather than all failing simultaneously.

Preserve a complete trace for at least one serialized component replacement such as the previously discussed HT-004 wheel-motor chain.

## 7.8 Warehouse, inventory, and materials management

Target:

- at least 12,000 MRO SKUs;
- 25–40 serialized repairable families modeled deeply;
- several hundred nonserialized critical spares;
- bulk consumables generated at realistic scale;
- hundreds of bins and locations;
- hundreds of vendors.

Mandatory:

- `item_category`
- `item_master`
- `sku`
- `vendor_item`
- `warehouse`
- `storage_location`
- `bin`
- `inventory_lot`
- `inventory_serial`
- `inventory_status`
- `inventory_balance`
- `inventory_transaction`
- `inventory_reservation`
- `inventory_issue`
- `inventory_return`
- `inventory_transfer`
- `goods_receipt`
- `receipt_inspection`
- `quarantine_record`
- `cycle_count`
- `inventory_adjustment`
- `reorder_policy`
- `safety_stock_policy`
- `lead_time_history`
- `price_history`
- `stockout_event`
- `expedite_event`
- `obsolete_inventory_assessment`
- `repairable_core`
- `repairable_exchange`

Inventory states must include:

- available;
- reserved;
- installed;
- in repair;
- dirty core;
- awaiting inspection;
- quarantined;
- in transit;
- on order;
- consigned;
- obsolete;
- scrapped.

Physical quantity, system quantity, available quantity, reserved quantity, and accounting quantity may differ temporarily. Reconciliations must explain the differences.

Include:

- fuel;
- explosives;
- tires;
- lubricants;
- filters;
- hoses;
- electrical components;
- mill liners;
- grinding media;
- flotation reagents;
- laboratory supplies;
- PPE;
- serialized rotables;
- general MRO.

## 7.9 Procurement, vendors, and AP

Mandatory:

- `vendor`
- `vendor_site`
- `vendor_contact`
- `vendor_category`
- `vendor_qualification`
- `vendor_risk_assessment`
- `contract`
- `contract_line`
- `contract_amendment`
- `service_level`
- `insurance_certificate`
- `purchase_requisition`
- `requisition_line`
- `request_for_quote`
- `supplier_quote`
- `purchase_order`
- `purchase_order_line`
- `change_order`
- `goods_receipt`
- `service_entry`
- `supplier_invoice`
- `supplier_invoice_line`
- `three_way_match_result`
- `payment`
- `credit_memo`
- `vendor_performance`
- `expedite_tracker`
- `open_commitment`

Model ordinary mismatches:

- split receipts;
- partial invoices;
- freight on separate invoices;
- quantity tolerances;
- price variances;
- delayed service entries;
- expedited orders;
- substitutions;
- consignment;
- receipts awaiting inspection.

Do not create fraudulent invoices as the primary story.

## 7.10 Mine operations and dispatch

Mandatory:

- `operating_shift`
- `shift_plan`
- `dispatch_plan`
- `equipment_assignment`
- `operator_assignment`
- `prestart_inspection`
- `haul_cycle`
- `load_event`
- `queue_event`
- `travel_event`
- `dump_event`
- `delay_event`
- `payload_measurement`
- `fuel_consumption`
- `fuel_transfer`
- `road_delay`
- `shovel_event`
- `production_actual`
- `plan_variance`
- `shift_handover`
- `daily_production_summary`

The haul engine must derive cycle time from:

- route;
- distance;
- grade;
- rolling resistance;
- truck state;
- payload;
- queue;
- shovel performance;
- road restrictions;
- fueling;
- operator availability;
- weather where modeled.

Do not simply type “effective haul capacity.” Compute it.

Every truck at every instant must have one state and one location. Every operator must have at most one active assignment.

## 7.11 Processing, metallurgy, laboratory, and material balance

Mandatory:

- `plant_unit`
- `process_stream`
- `process_tag`
- `sensor_reading`
- `feed_campaign`
- `blend_plan`
- `blend_actual_estimate`
- `crusher_run`
- `mill_run`
- `flotation_run`
- `reagent_usage`
- `sampling_event`
- `laboratory_sample`
- `assay_result`
- `assay_rerun`
- `quality_control_sample`
- `metallurgical_trial`
- `feed_characteristic`
- `recovery_calculation`
- `concentrate_lot`
- `tailings_lot`
- `work_in_process_balance`
- `process_mass_balance`
- `contained_metal_balance`
- `plant_downtime`
- `process_variance_explanation`

The hidden response model should include:

- grade;
- hardness;
- mineralogy/sulfide behavior;
- blend interactions;
- throughput;
- grind state;
- reagent conditions.

Recovery must be derived. The western material should not be uniformly “bad.” Penalties should emerge when combinations cross thresholds under constrained blend conditions.

Model sample and assay latency. Event time and available time must differ.

## 7.12 HSE, environmental, and regulatory operations

Mandatory:

- `hse_incident`
- `near_miss`
- `safety_observation`
- `stop_work_event`
- `corrective_action`
- `environmental_permit`
- `permit_obligation`
- `inspection`
- `environmental_sample`
- `water_balance`
- `tailings_inspection`
- `spill_or_release`
- `emergency_drill`
- `regulatory_correspondence`
- `compliance_calendar`

Include ordinary unrelated events so the case world does not revolve solely around Phase 4.

## 7.13 Commercial, concentrate, revenue, and receivables

Mandatory:

- `customer`
- `offtake_counterparty`
- `offtake_contract`
- `pricing_term`
- `payable_term`
- `treatment_charge`
- `refining_charge`
- `freight_term`
- `quotation_period`
- `shipment_lot`
- `concentrate_inventory`
- `weighbridge_ticket`
- `moisture_result`
- `provisional_assay`
- `final_assay`
- `bill_of_lading`
- `freight_invoice`
- `provisional_sales_invoice`
- `final_settlement`
- `pricing_adjustment`
- `cash_receipt`
- `royalty_calculation`
- `revenue_recognition_event`

Use two credible offtake counterparties with differing settlement mechanics.

Production date, shipment date, provisional invoice date, cash date, and final settlement date must differ realistically.

## 7.14 Capital projects and Phase 4 WBS

Mandatory:

- `capital_project`
- `wbs_element`
- `wbs_dependency`
- `project_budget_version`
- `project_forecast_version`
- `project_schedule_version`
- `milestone`
- `physical_progress`
- `financial_progress`
- `capital_authorization`
- `approval_record`
- `commitment`
- `capital_contract`
- `change_order`
- `capital_invoice`
- `capital_accrual`
- `contingency_draw`
- `capitalization_event`
- `asset_under_construction`
- `project_risk`
- `project_assumption`
- `project_status_snapshot`

Phase 4 WBS must include at least:

- North development;
- Central development;
- South development;
- trunk and access roads;
- waste-dump access;
- drainage;
- dewatering wells/pumps/piping;
- power;
- communications;
- engineering;
- environmental work;
- owner’s costs;
- mobile support;
- contingency.

Physical progress and financial progress must be separate. Percent complete must not automatically mean ore access is achieved.

## 7.15 Finance and accounting

Build a real double-entry accounting system.

Mandatory:

- `ledger`
- `chart_of_accounts`
- `account`
- `account_hierarchy`
- `journal_source`
- `journal`
- `journal_line`
- `subledger_reference`
- `opening_balance`
- `trial_balance`
- `budget_version`
- `budget_line`
- `forecast_version`
- `forecast_line`
- `cost_allocation_rule`
- `cost_allocation_run`
- `accrual`
- `prepayment`
- `bank_account`
- `bank_transaction`
- `bank_reconciliation`
- `accounts_payable_open_item`
- `accounts_receivable_open_item`
- `fixed_asset`
- `fixed_asset_component`
- `depreciation_method`
- `depreciation_run`
- `construction_in_progress`
- `inventory_valuation`
- `ore_inventory_valuation`
- `concentrate_valuation`
- `lease`
- `debt_instrument`
- `interest_schedule`
- `royalty`
- `asset_retirement_obligation`
- `closure_cost_estimate`
- `tax_rate`
- `current_tax`
- `deferred_tax`
- `impairment_indicator`
- `impairment_scenario`
- `discounted_cash_flow`
- `impairment_calculation`
- `financial_statement_line`
- `financial_statement_value`
- `management_adjustment`
- `close_task`
- `close_status`

Financial dimensions must include:

- legal entity;
- site;
- department;
- cost center;
- project/WBS;
- asset;
- vendor/customer;
- material;
- location;
- journal source;
- fiscal period.

### Accounting outputs

Produce monthly and annual:

- Income Statement;
- Balance Sheet;
- Statement of Cash Flows;
- Statement of Changes in Equity;
- Trial Balance;
- General Ledger;
- AP aging;
- AR aging;
- fixed-asset rollforward;
- CIP rollforward;
- inventory rollforward;
- debt rollforward;
- ARO rollforward;
- budget versus actual;
- forecast versus actual;
- site cost report;
- unit-cost report;
- capital project report;
- impairment model and sensitivities.

### Accounting policies

Document and configure:

- fiscal calendar;
- functional/reporting currency;
- inventory costing;
- ore/WIP/concentrate valuation;
- MRO valuation;
- depreciation;
- units-of-production where appropriate;
- straight-line where appropriate;
- capitalization thresholds;
- stripping/capital policy;
- revenue and provisional pricing;
- treatment/refining/freight;
- royalties;
- accruals;
- asset retirement/closure obligation;
- impairment;
- taxes;
- materiality/rounding for reports.

Do not claim the synthetic policy is authoritative GAAP guidance. Label it a coherent PROVISIONAL case policy.

### Financial integrity rules

Every journal must balance.

Every month:

- debits equal credits;
- opening plus activity equals closing;
- Balance Sheet balances;
- cash-flow statement reconciles opening to closing cash;
- AP subledger ties to AP control;
- AR subledger ties to AR control;
- payroll ties to labor distribution and GL;
- fixed assets/CIP tie to GL;
- depreciation ties to the fixed-asset register;
- inventory valuations tie to quantity ledgers and GL;
- commercial settlements tie to AR and cash;
- capital commitments tie to WBS;
- impairment ties to the DCF and fixed-asset/CIP carrying values.

The approximately $52 million impairment must be produced by the model. A test must fail if it is merely hardcoded.

## 7.16 Governance, meetings, decisions, and management reporting

Mandatory:

- `meeting_series`
- `meeting`
- `meeting_attendee`
- `agenda_item`
- `pre_read`
- `presentation_deck`
- `deck_version`
- `meeting_note`
- `decision`
- `action_item`
- `action_status_history`
- `escalation`
- `committee`
- `committee_membership`
- `capital_review`
- `board_material`
- `board_approval`
- `kpi_definition`
- `kpi_observation`
- `status_definition`
- `management_status`
- `variance_explanation`
- `forecast_narrative`

Model:

- shift handover;
- daily production meeting;
- weekly maintenance review;
- weekly planning review;
- monthly site business review;
- capital review committee;
- board approval;
- October reconstruction.

Attendance does not imply comprehension.

Management representations must be time-bounded and versioned. Do not overwrite old decks.

## 7.17 Systems, interfaces, data lineage, and shadow IT

Formal systems should include fictionalized platforms such as:

- `GeoCore`
- `StrataPlan`
- `MineTrack`
- `ForgeWorks`
- `AssayLab`
- `ProcessVault`
- `Argent ERP`
- reporting warehouse/BI layer
- document repository
- HR/timekeeping
- procurement/vendor portal

Mandatory:

- `application_system`
- `system_instance`
- `system_owner`
- `system_module`
- `interface`
- `interface_run`
- `integration_error`
- `extract_definition`
- `extract_run`
- `report_definition`
- `report_run`
- `dashboard`
- `data_refresh`
- `system_account`
- `permission`
- `source_identifier`
- `semantic_definition`
- `data_dictionary_term`
- `lineage_edge`
- `crosswalk`
- `crosswalk_version`
- `shadow_artifact`
- `shadow_artifact_version`
- `shadow_artifact_owner`
- `shadow_artifact_dependency`
- `tracker`
- `tracker_status_definition`
- `tracker_snapshot`
- `parallel_work_representation`
- `translation_rule`
- `management_compression`
- `file_drop`
- `email_attachment_exchange`

Shadow artifacts must be categorized as one or more of:

1. gap-filling;
2. translation;
3. roll-up;
4. personal operational;
5. reconciliation.

Preserve “trackers for trackers” and different honest definitions of done.

Examples to instantiate:

- haul-capacity workbook;
- reliability bad-actor workbook;
- executable maintenance-backlog sheet;
- Phase 4 readiness tracker;
- metallurgical blend-sensitivity workbook;
- procurement expedites tracker;
- finance forecast workbook;
- site business review status deck.

Each must have:

- business question;
- creator;
- owner;
- audience;
- source inputs;
- refresh cadence;
- status semantics;
- transformation logic;
- version history;
- limitations;
- lineage.

## 7.18 Documents, communications, and evidence artifacts

Mandatory:

- `document`
- `document_version`
- `document_category`
- `document_owner`
- `document_reference`
- `communication_thread`
- `communication_message`
- `message_recipient`
- `attachment`
- `memo`
- `meeting_minutes`
- `observation_note`
- `artifact_hash`
- `artifact_access`
- `artifact_availability`

Generate selected realistic communications, but do not create millions of meaningless emails.

No period artifact may use hindsight language or reveal the final case answer before it was knowable.

## 7.19 Control and evidence enablement

Create an enabling schema, but do not attempt to encode professional audit opinions or universal sample rules.

Mandatory:

- `policy`
- `procedure`
- `business_process`
- `risk`
- `control`
- `control_version`
- `control_owner`
- `control_execution`
- `evidence_artifact`
- `control_exception`
- `management_issue`
- `remediation_action`

This exists so future NAILEX/SOC exercises can consume the Blackridge world. It must not turn Blackridge into an artificial control checklist.

---

# 8. SCALE AND POPULATION TARGETS

Use mine-scale calculations rather than arbitrary inflation. The full build must nevertheless be substantial.

Target ranges:

- people and embedded contractors: approximately 550 active at opening;
- historical position/assignment records: at least 650;
- facilities/areas/rooms/spatial objects: at least 250;
- haul trucks: exactly 27 unless canon later changes;
- total mobile units: approximately 130–160;
- fixed maintainable assets: approximately 2,500–4,000;
- serialized components/repairables: at least 1,500;
- MRO SKUs: at least 12,000;
- vendors: at least 300;
- active/material contracts: at least 50;
- purchase orders: at least 5,000 annually;
- PO lines: at least 15,000;
- goods receipts: at least 10,000;
- supplier invoice lines: at least 15,000;
- maintenance work orders: at least 6,000;
- maintenance labor bookings: at least 30,000;
- inventory transactions: at least 75,000;
- haul cycles: at least 150,000 for full 2015, calibrated to shifts and fleet;
- canonical event ledger: at least 1,000,000 events when expanded into state changes;
- plant hourly records: all 8,760 hours, plus higher-frequency records for selected tags;
- journal lines: at least 100,000, driven by subledgers;
- documents/communications/artifacts: at least 3,000 metadata records, with a smaller high-quality rendered subset;
- governance/action records: at least 1,000;
- full dataset: enough to expose realistic performance and search behavior without gratuitous duplication.

The exact counts may vary if documented engineering logic supports the variation. Do not reduce the build to toy scale.

Create a row-count manifest with expected and actual counts.

---

# 9. GENERATION AND SIMULATION ORDER

Use dependency-aware generation.

## Phase A — foundation

1. repository recovery audit;
2. canon extraction;
3. configuration and decision register;
4. database schema and migrations;
5. identifier and unit registries;
6. metadata/provenance framework.

## Phase B — master data

1. organization/legal structure;
2. locations/facilities/buildings;
3. workforce/positions/crews;
4. vendors/customers;
5. items/warehouses;
6. assets/components;
7. systems/interfaces;
8. chart of accounts and financial dimensions;
9. projects/WBS;
10. geological/mine topology.

## Phase C — opening state

Create a coherent December 31, 2014 closing/opening state including:

- opening trial balance;
- cash and debt;
- AP/AR open items;
- inventory quantities and values;
- ore/WIP/concentrate inventories;
- fixed assets and accumulated depreciation;
- CIP;
- ARO;
- employees and schedules;
- asset states;
- maintenance backlog;
- critical spares;
- vendor commitments;
- mine plan;
- stockpiles;
- plant WIP;
- contracts;
- project status.

## Phase D — M00

Recover or rebuild the 72-hour M00 vertical slice.

It must prove:

- material conservation;
- contained-metal conservation;
- fuel conservation;
- truck exclusivity;
- operator exclusivity;
- component exclusivity;
- maintenance prerequisites;
- no negative inventory;
- coherent time ordering;
- deterministic replay;
- accounting capture.

## Phase E — full 2015 operations

Generate forward chronologically.

Do not generate December financial statements first and backfill random transactions.

Generate:

- shifts;
- operations;
- maintenance;
- inventory;
- procurement;
- processing;
- commercial;
- payroll;
- accounting;
- governance;
- shadow-IT artifacts;
- forecasts;
- decisions.

The canonical incident trajectory may be calibrated, but individual events should emerge from rules and dependencies.

## Phase F — monthly closes

For each month:

1. close operations;
2. reconcile material;
3. post procurement and AP;
4. post payroll;
5. value inventory;
6. post depreciation;
7. account for sales settlements;
8. accrue missing invoices;
9. update capital/CIP;
10. update ARO/interest/tax as configured;
11. produce trial balance;
12. produce statements;
13. produce management pack;
14. record variance explanations;
15. lock the period snapshot.

## Phase G — case snapshots

Create time-cutoff databases/workbooks that contain only information available by each cutoff date.

---

# 10. EXCEL MASTER WORKBOOK

Create:

`BLACKRIDGE_MASTER_TRACKER_v0.1.0.xlsx`

This is mandatory.

It must be generated from SQL queries/views. It must not contain an independently invented second dataset.

## 10.1 Workbook design principles

- professional, restrained industrial style;
- dark navy/charcoal section headers;
- white header text;
- hardcoded user-adjustable inputs in blue font;
- formulas in black;
- links to other workbook sheets in green;
- external links, if any, in red—but avoid external workbook links;
- yellow fill for assumptions requiring attention;
- zeros displayed as `-`;
- negatives displayed in red parentheses;
- units stated in headers;
- gridlines hidden on presentation sheets;
- freeze panes;
- filters;
- Excel Tables with unique table names;
- no merged cells inside data tables;
- merged cells only for section headings where useful;
- sensible widths and wrapped text;
- no formula errors;
- no circular references;
- calculation mode automatic;
- no macros required;
- no password protection;
- no broken external paths.

Add workbook properties:

- dataset version;
- schema version;
- generation seed;
- build timestamp;
- source database hash;
- canon version;
- public/restricted classification.

## 10.2 Required workbook navigation sheets

1. `START_HERE`
2. `CONTROL_PANEL`
3. `MASTER_INDEX`
4. `ENTITY_SEARCH`
5. `TABLE_CATALOG`
6. `DATA_DICTIONARY`
7. `QUERY_LIBRARY`
8. `BUILD_MANIFEST`
9. `VALIDATION_STATUS`
10. `RECONCILIATIONS`
11. `CANON_REFERENCES`
12. `DECISION_REGISTER`

`START_HERE` must explain:

- purpose;
- public versus oracle data;
- how the workbook was generated;
- how to refresh/regenerate;
- sheet conventions;
- colors;
- IDs;
- limitations;
- link to SQL query cookbook;
- link to repository docs.

`ENTITY_SEARCH` must provide a combined, filterable index for:

- people;
- positions;
- assets;
- components;
- facilities;
- buildings;
- rooms;
- inventory items;
- vendors;
- customers;
- contracts;
- projects;
- WBS elements;
- systems;
- documents;
- controls;
- meetings;
- decisions.

Use a dynamic search area if supported by modern Excel and retain a plain Excel Table fallback.

## 10.3 Required financial sheets

At minimum:

- `FIN_DASHBOARD`
- `INCOME_STATEMENT`
- `BALANCE_SHEET`
- `CASH_FLOW`
- `EQUITY_STATEMENT`
- `TRIAL_BALANCE_MONTHLY`
- `GENERAL_LEDGER_EXTRACT`
- `CHART_OF_ACCOUNTS`
- `BUDGET_VS_ACTUAL`
- `FORECAST_VS_ACTUAL`
- `SITE_COST_REPORT`
- `UNIT_COSTS`
- `WORKING_CAPITAL`
- `AP_AGING`
- `AR_AGING`
- `CASH_RECON`
- `FIXED_ASSET_ROLLFORWARD`
- `CIP_ROLLFORWARD`
- `DEPRECIATION`
- `ARO_ROLLFORWARD`
- `DEBT_ROLLFORWARD`
- `INVENTORY_VALUATION`
- `ORE_WIP_CONC_VALUATION`
- `CAPEX_WBS`
- `PHASE4_DCF`
- `PHASE4_SENSITIVITY`
- `IMPAIRMENT_CALC`
- `MONTHLY_CLOSE`

Financial statements and rollforwards must use formulas or query-linked values, not pasted statement totals.

## 10.4 Workforce sheets

- `EMPLOYEE_MASTER`
- `CONTRACTOR_MASTER`
- `POSITION_MASTER`
- `ORG_ASSIGNMENTS`
- `CREWS_AND_SHIFTS`
- `SCHEDULED_VS_ACTUAL`
- `TIMESHEETS`
- `PAYROLL_SUMMARY`
- `LABOR_DISTRIBUTION`
- `TRAINING_AND_CERTS`
- `SYSTEM_ACCESS`
- `WORKFORCE_METRICS`

## 10.5 Facilities and asset sheets

- `FACILITY_MASTER`
- `BUILDINGS_AND_AREAS`
- `SITE_LOCATION_TREE`
- `MOBILE_FLEET`
- `FIXED_ASSET_MASTER`
- `ASSET_HIERARCHY`
- `SERIALIZED_COMPONENTS`
- `INSTALLATION_HISTORY`
- `CRITICAL_EQUIPMENT`
- `ASSET_CRITICALITY`
- `METERS`
- `ASSET_STATUS`

## 10.6 Maintenance sheets

- `WORK_ORDERS`
- `MAINTENANCE_BACKLOG`
- `DOWNTIME_EVENTS`
- `PM_COMPLIANCE`
- `BAD_ACTORS`
- `CONDITION_MONITORING`
- `REPAIRABLE_POOL`
- `BAY_AND_CRANE_CAPACITY`
- `MAINT_LABOR`
- `MAINT_PARTS_USAGE`
- `HT004_GOLDEN_TRACE`

## 10.7 Inventory/procurement sheets

- `ITEM_MASTER`
- `WAREHOUSES_AND_BINS`
- `INVENTORY_BALANCES`
- `INVENTORY_TRANSACTIONS_EXTRACT`
- `CRITICAL_SPARES`
- `STOCKOUTS`
- `CYCLE_COUNTS`
- `QUARANTINE`
- `VENDOR_MASTER`
- `CONTRACT_MASTER`
- `PURCHASE_ORDERS`
- `OPEN_COMMITMENTS`
- `GOODS_RECEIPTS`
- `SUPPLIER_INVOICES`
- `THREE_WAY_MATCH`
- `EXPEDITES`
- `VENDOR_PERFORMANCE`

## 10.8 Mine and processing sheets

- `MINE_PLAN`
- `PITS_PHASES_BENCHES`
- `ROAD_GRAPH`
- `SHIFT_PLANS`
- `MATERIAL_MOVEMENT`
- `HAUL_CYCLES_EXTRACT`
- `FLEET_AVAILABILITY`
- `ORE_EXPOSURE`
- `STOCKPILES`
- `BLEND_OPTIONALITY`
- `PLANT_DAILY`
- `PLANT_HOURLY_EXTRACT`
- `METALLURGY`
- `LAB_ASSAYS`
- `RECOVERY`
- `CONCENTRATE_LOTS`
- `MASS_BALANCE`
- `CONTAINED_METAL`

## 10.9 Commercial sheets

- `OFFTAKE_CONTRACTS`
- `SHIPMENTS`
- `PROVISIONAL_INVOICES`
- `FINAL_SETTLEMENTS`
- `PRICING_ADJUSTMENTS`
- `ROYALTIES`
- `COMMERCIAL_RECON`

## 10.10 Governance, systems, and shadow-IT sheets

- `MEETING_CALENDAR`
- `MEETING_ATTENDEES`
- `DECISIONS`
- `ACTION_ITEMS`
- `CAPITAL_APPROVALS`
- `KPI_DEFINITIONS`
- `KPI_HISTORY`
- `VARIANCE_EXPLANATIONS`
- `SYSTEM_CATALOG`
- `INTERFACES`
- `IDENTIFIER_MAP`
- `DATA_LINEAGE`
- `SHADOW_IT_REGISTER`
- `TRACKER_CHAIN`
- `STATUS_DEFINITIONS`
- `PARALLEL_REPRESENTATIONS`
- `DATA_QUALITY_ISSUES`
- `CASE_TIMELINE`

## 10.11 Workbook dashboards and charts

Include useful, not decorative, charts:

- monthly ore and waste movement versus plan;
- exposed ore and blend optionality;
- throughput and recovery;
- fleet availability versus effective haul capacity;
- maintenance backlog and repeat failures;
- critical-spares availability;
- inventory value by class;
- budget versus actual;
- cash and working capital;
- Phase 4 commitment curve;
- Phase 4 NPV/IRR sensitivity;
- impairment bridge;
- production-to-revenue timing;
- financial statement trends.

Do not create a dashboard that implies the 2015 organization already had the integrated insight. Clearly label modern “case analytics” separately from period-authentic management views.

## 10.12 High-volume Excel handling

Excel cannot contain unlimited raw telemetry.

Rules:

- include complete master data tables where within limits;
- include complete financial statements and summary views;
- include full GL if under the row limit; otherwise partition by quarter;
- include representative/filtered transaction extracts;
- include SQL row counts and query instructions for full high-volume facts;
- provide domain CSV extracts;
- never silently truncate;
- every truncated sheet must state the source SQL view, total rows, included rows, filters, and export path.

---

# 11. SQL SEARCH AND ANALYTICAL VIEWS

Create indexes and views that make the database immediately useful.

## 11.1 Master search

Create:

- `vw_master_entity_search`
- `entity_search_fts`

Fields should include:

- `entity_type`
- `canonical_id`
- `uuid`
- `display_name`
- `description`
- `status`
- `organization`
- `location`
- `owner`
- `effective_from`
- `effective_to`
- `source_system`
- `search_text`

Support full-text search across all major masters.

## 11.2 Financial views

- `vw_trial_balance_monthly`
- `vw_income_statement_monthly`
- `vw_balance_sheet_monthly`
- `vw_cash_flow_monthly`
- `vw_budget_vs_actual`
- `vw_ap_aging`
- `vw_ar_aging`
- `vw_fixed_asset_rollforward`
- `vw_inventory_valuation`
- `vw_phase4_commitment_curve`
- `vw_phase4_impairment`
- `vw_cost_per_tonne`
- `vw_cash_cost_per_payable_lb`

## 11.3 Operations views

- `vw_shift_performance`
- `vw_material_movement_daily`
- `vw_effective_haul_capacity`
- `vw_fleet_availability`
- `vw_road_constraints`
- `vw_ore_exposure`
- `vw_blend_optionality`
- `vw_plant_performance`
- `vw_mass_balance`
- `vw_recovery_variance`
- `vw_concentrate_production`

## 11.4 Maintenance/inventory views

- `vw_maintenance_backlog`
- `vw_bad_actor_assets`
- `vw_repeat_failure`
- `vw_asset_health_observations`
- `vw_critical_spares`
- `vw_repairable_pool`
- `vw_stockout_risk`
- `vw_open_work_orders`
- `vw_inventory_position`
- `vw_po_receipt_invoice_match`

## 11.5 Workforce/governance/system views

- `vw_active_workforce`
- `vw_shift_coverage`
- `vw_qualification_coverage`
- `vw_labor_cost`
- `vw_open_actions`
- `vw_decision_lineage`
- `vw_kpi_compression_chain`
- `vw_shadow_artifact_lineage`
- `vw_identifier_crosswalk`
- `vw_data_availability_by_cutoff`

## 11.6 Query cookbook

Provide at least 75 documented example queries, including:

- find every record linked to one haul truck;
- trace a serialized component through hosts and repair;
- trace one tonne-equivalent material parcel from mine to concentrate;
- trace one concentrate lot to invoice and cash;
- reconcile AP to GL;
- reconcile inventory to GL;
- compare physical and system inventory;
- list employees qualified for a specific task on a date;
- find all assets dependent on one crane or facility;
- reconstruct Phase 4 commitments at a cutoff date;
- show the different definitions of “availability”;
- compare tracker status definitions;
- find all artifacts available by May 18;
- find information not yet available on June 26;
- trace the October reconstruction;
- calculate current and historical asset criticality;
- identify stale critical-equipment-list entries;
- show items physically present but unavailable;
- produce monthly statements;
- run budget-versus-actual;
- run impairment sensitivity;
- show causal precursors without exposing oracle fields.

---

# 12. CLI AND DEVELOPER EXPERIENCE

Implement a CLI such as:

```bash
python -m blackridge doctor
python -m blackridge db upgrade
python -m blackridge generate --profile smoke --seed 20150112
python -m blackridge generate --profile m00 --seed 20150112
python -m blackridge generate --profile full_2015 --seed 20150112
python -m blackridge validate --profile full_2015
python -m blackridge reconcile --profile full_2015
python -m blackridge export excel --profile full_2015
python -m blackridge export csv --profile full_2015
python -m blackridge snapshot --cutoff 2015-05-18
python -m blackridge query --database <path> --sql-file queries/...
python -m blackridge manifest
```

`doctor` should report:

- Python version;
- package versions;
- database path;
- schema version;
- dataset version;
- profile;
- available disk space;
- Git commit;
- Git dirty state;
- SQLite feature availability including FTS5;
- workbook engine;
- external tools such as LibreOffice if present;
- GitHub authentication status;
- oracle repository accessibility.

Commands must return nonzero on failure and emit machine-readable JSON with `--json`.

---

# 13. VALIDATION AND CONSERVATION

Implement validators that fail hard.

## 13.1 Relational integrity

- `PRAGMA integrity_check` passes;
- `PRAGMA foreign_key_check` returns no errors;
- all required uniqueness constraints pass;
- no orphaned rows;
- effective dates are valid;
- no duplicate immutable canonical IDs.

## 13.2 Physical conservation

- every material movement has a source and destination;
- no negative stockpile or WIP quantity;
- opening + inflow − outflow = closing;
- plant feed = concentrate + tailings + WIP change within configured tolerances;
- contained copper and gold reconcile within configured tolerances;
- fuel opening + receipts − consumption = closing;
- every serialized component has exactly one host, location, or in-transit state at a time;
- every truck has one state and one location at a time;
- every employee/operator has at most one active shift assignment;
- maintenance return-to-service occurs only after prerequisites.

## 13.3 Accounting integrity

- every journal balances;
- every fiscal-period trial balance balances;
- Balance Sheet balances;
- cash flow reconciles;
- subledgers tie to control accounts;
- inventory quantity/value ties to GL;
- fixed assets/CIP/depreciation tie to GL;
- payroll ties to time/labor distribution;
- revenue/settlement ties to AR/cash;
- Phase 4 actuals and commitments tie to WBS;
- impairment ties to DCF and carrying amount;
- no unexplained balance-sheet plug other than documented opening equity.

## 13.4 Epistemic and snapshot integrity

- no record appears in a cutoff snapshot before `available_at`;
- later corrections preserve prior versions;
- no October conclusion appears in May or June artifacts;
- management decks use contemporaneous definitions;
- hidden oracle columns are absent from public DB and workbook;
- public and private packages have separate manifests.

## 13.5 Determinism

Given the same:

- code commit;
- schema version;
- dataset profile;
- seed;
- config;

the generated row counts, keys, hashes, and reconciled outputs must be identical.

Maintain a checked golden fingerprint for `smoke` and `m00`.

## 13.6 Corruption tests

Deliberately mutate copies and prove validators detect:

- unbalanced journal;
- orphaned PO line;
- negative inventory;
- double-installed component;
- duplicate employee assignment;
- missing haul destination;
- impossible timestamp;
- snapshot leakage;
- truncated vendor export;
- workbook/database hash mismatch;
- hardcoded impairment;
- missing GL/subledger link.

---

# 14. WORKBOOK QA

Automate workbook QA.

Check:

- required sheets exist;
- sheet names are unique and within Excel limits;
- tables have unique names;
- formulas are present where expected;
- no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or unintended `#N/A`;
- no broken external links;
- no sheet silently exceeds row limits;
- financial statements tie to SQL values;
- source database hash is embedded;
- key formats are correct;
- zeros display as `-`;
- negatives display in red parentheses;
- units are present;
- freeze panes and filters are present;
- workbook opens with openpyxl;
- if LibreOffice is available, recalculate and reopen the workbook headlessly;
- selected sheets render legibly or produce screenshots for QA.

Create:

`blackridge/reports/WORKBOOK_QA_REPORT.md`

Include screenshots or rendered previews for:

- START_HERE;
- FIN_DASHBOARD;
- INCOME_STATEMENT;
- BALANCE_SHEET;
- PHASE4_DCF;
- INVENTORY_SUMMARY;
- ASSET_HIERARCHY;
- ENTITY_SEARCH;
- VALIDATION_STATUS.

---

# 15. DOCUMENTATION

Mandatory documentation:

1. `blackridge/README.md`
2. `BLACKRIDGE_REPOSITORY_RECOVERY_AUDIT.md`
3. `BLACKRIDGE_CANON_IMPLEMENTATION_SPEC.md`
4. `BLACKRIDGE_DATA_ARCHITECTURE.md`
5. `BLACKRIDGE_ENTITY_RELATIONSHIP_MODEL.md`
6. `BLACKRIDGE_DATA_DICTIONARY.md`
7. `BLACKRIDGE_GENERATION_GUIDE.md`
8. `BLACKRIDGE_ACCOUNTING_POLICIES.md`
9. `BLACKRIDGE_FINANCIAL_MODEL_GUIDE.md`
10. `BLACKRIDGE_INVENTORY_AND_COSTING_GUIDE.md`
11. `BLACKRIDGE_MAINTENANCE_MODEL.md`
12. `BLACKRIDGE_MINE_AND_PROCESS_MODEL.md`
13. `BLACKRIDGE_WORKFORCE_MODEL.md`
14. `BLACKRIDGE_SYSTEMS_AND_SHADOW_IT_MODEL.md`
15. `BLACKRIDGE_PUBLIC_PRIVATE_DATA_BOUNDARY.md`
16. `BLACKRIDGE_SQL_QUERY_GUIDE.md`
17. `BLACKRIDGE_EXCEL_WORKBOOK_GUIDE.md`
18. `BLACKRIDGE_VALIDATION_AND_RECONCILIATION.md`
19. `BLACKRIDGE_CASE_SNAPSHOT_GUIDE.md`
20. `BLACKRIDGE_LIMITATIONS_AND_OPEN_DECISIONS.md`
21. `BLACKRIDGE_BUILD_REPORT_v0.1.0.md`
22. `BLACKRIDGE_RELEASE_NOTES_v0.1.0.md`

Generate an ERD in Mermaid and rendered SVG where tooling permits.

Every major PROVISIONAL assumption must have:

- ID;
- description;
- reason;
- alternatives considered;
- impact;
- affected tables;
- reversibility;
- approval state.

---

# 16. DATA PROFILING AND MANIFESTS

For every released artifact, record:

- file name;
- SHA-256;
- size;
- dataset version;
- schema version;
- seed;
- generator commit;
- build time;
- public/restricted classification;
- row counts;
- date ranges;
- null counts for required fields;
- validation status.

Create:

- `DATA_MANIFEST.json`
- `DATA_PROFILE.md`
- `DATA_PROFILE.json`
- `CHECKSUMS.sha256`
- `RECONCILIATION_REPORT.md`
- `RECONCILIATION_REPORT.json`
- `VALIDATION_REPORT.md`
- `VALIDATION_REPORT.json`

---

# 17. GITHUB ACTIONS

Add CI workflows.

## Pull-request CI

Run:

- format/lint;
- type checks;
- unit tests;
- schema migration tests;
- `smoke` generation;
- `m00` generation;
- relational integrity;
- financial reconciliation;
- workbook generation and QA;
- deterministic fingerprint check;
- public/oracle leakage scan;
- documentation link check.

Use a Python matrix where practical.

## Full build workflow

Add a manually dispatchable and scheduled workflow that:

- generates `full_2015`;
- validates it;
- exports workbook, DB, CSVs, manifests;
- uploads public artifacts;
- never exposes oracle assets on the public repository;
- optionally publishes oracle artifacts to the private companion repository when credentials permit.

Do not make ordinary PR CI rebuild a huge full-year dataset if it creates excessive runtime. Use smoke/M00 in PR CI and full build in a dedicated workflow.

---

# 18. RELEASE AND ARTIFACT HANDLING

Binary files may exceed comfortable Git storage.

Rules:

- commit code, schemas, migrations, small fixtures, documentation, manifests, and compact samples;
- commit the public M00 fixture if reasonably sized;
- do not commit a generated file larger than GitHub’s hard limit;
- use GitHub Release assets for large public SQLite/Excel/CSV packages;
- use the private oracle repository’s release assets for large restricted packages;
- use Git LFS only if it is already configured or can be configured cleanly without burdening normal clones;
- never silently omit a required artifact because it is large.

Create prerelease/tag:

`blackridge-data-v0.1.0`

Public release assets should include at minimum:

- public SQLite database;
- master Excel workbook;
- data dictionary;
- CSV extract archive;
- SQL query cookbook;
- validation/reconciliation reports;
- manifest and checksums.

Private oracle release assets should include:

- oracle SQLite database;
- evaluator package;
- private manifest/checksums;
- private validation report.

---

# 19. GIT AND DELIVERY WORKFLOW

Make coherent incremental commits, for example:

1. `Audit Blackridge repository state and recover valid scaffolding`
2. `Establish Blackridge schema and migration foundation`
3. `Add canonical master-data generators`
4. `Implement M00 event and conservation model`
5. `Add 2015 mine, processing, maintenance, and inventory generation`
6. `Implement double-entry accounting and subledgers`
7. `Add Phase 4 capital and impairment model`
8. `Add systems, shadow IT, governance, and cutoff snapshots`
9. `Generate SQL search views and query cookbook`
10. `Generate Blackridge Excel master workbook`
11. `Add validation, corruption, and workbook QA tests`
12. `Add CI, release workflows, and complete documentation`
13. `Publish Blackridge enterprise data foundation v0.1.0`

Push after meaningful milestones.

Open a pull request titled:

`Build Blackridge enterprise data foundation v0.1.0`

Target:

- `main`.

The PR body must include:

- repository audit result;
- architecture;
- actual row counts;
- artifact list;
- financial reconciliation results;
- physical conservation results;
- workbook QA results;
- public/private boundary;
- limitations;
- open/provisional decisions;
- commands to reproduce;
- release links.

After CI passes:

- merge the Blackridge PR into `main` only after all required checks, review gates, and public/private-boundary checks pass;
- do not disturb the state of unrelated open PRs;
- do not force-push shared branches;
- retain commit/release traceability.

---

# 20. REQUIRED COMPLETION GATES

Do not declare the task complete until all applicable gates pass.

## Gate 1 — repository truth

- all relevant branches and history inspected;
- recovery audit committed;
- unsupported prior completion claims corrected in documentation;
- safe integration base selected.

## Gate 2 — schema

- migrations run from empty database;
- public and oracle schemas exist;
- PostgreSQL DDL generated;
- data dictionary complete;
- ERD generated.

## Gate 3 — master data

- workforce populated;
- facilities populated;
- assets/components populated;
- inventory populated;
- vendors/contracts populated;
- systems/shadow artifacts populated;
- chart of accounts and dimensions populated.

## Gate 4 — operations

- M00 runs;
- full 2015 runs;
- mine/haul/maintenance/processing/inventory/commercial flows exist;
- event and cutoff timestamps exist;
- no toy-scale shortcuts.

## Gate 5 — financials

- opening trial balance exists;
- 12 monthly closes exist;
- four primary statements exist;
- subledgers reconcile;
- Phase 4 DCF computes;
- impairment computes to approximately the canonical amount through assumptions and carrying values;
- no statement-level plug.

## Gate 6 — SQL usability

- public SQLite DB generated;
- FTS/entity search works;
- analytical views work;
- at least 75 query examples run;
- query cookbook committed.

## Gate 7 — Excel usability

- master workbook generated;
- all required sheets populated or explicitly redirected to full SQL tables;
- formulas and formatting validated;
- key dashboards/charts present;
- workbook hash links to DB;
- no silent truncation.

## Gate 8 — integrity

- SQL integrity passes;
- foreign keys pass;
- physical conservation passes;
- accounting reconciliation passes;
- deterministic replay passes;
- corruption tests pass;
- cutoff leakage tests pass;
- oracle leakage scan passes.

## Gate 9 — documentation

- all mandatory documents present;
- no unresolved placeholder TODOs in required deliverables;
- provisional decisions registered;
- reproduction steps work from a fresh clone.

## Gate 10 — GitHub delivery

- branch pushed;
- PR opened;
- CI green;
- public release assets uploaded;
- private oracle repository/package created or a precise external blocker documented;
- build report contains actual SHAs, run IDs, row counts, hashes, and links.

---

# 21. FINAL RESPONSE REQUIREMENT

At the end of the Codex session, do not merely say “done.”

Provide a concise but complete final report containing:

- base branch used;
- feature branch;
- final commit SHA;
- pull request URL;
- merge status;
- release URL;
- private oracle repository/release URL or blocker;
- database file names and sizes;
- workbook file name and size;
- schema version;
- dataset version;
- seed;
- actual row counts by domain;
- test counts;
- CI run URLs;
- reconciliation totals;
- statement totals;
- impairment result;
- conservation results;
- known limitations;
- exact commands for regeneration.

If any completion gate is not satisfied, state it explicitly and identify the exact blocker. Do not represent partial work as complete.

---

# 22. FINAL ENGINEERING PRINCIPLES

The Blackridge backend must obey these principles:

1. **The enterprise exists before the audit.**
2. **Transactions arise from operations, not from a desired statement total.**
3. **The Excel workbook is an export/interface, not a competing source of truth.**
4. **The SQL database is normalized, searchable, versioned, and reproducible.**
5. **Every important number is traceable.**
6. **Every mutable entity is effective-dated.**
7. **Time of occurrence is not time of knowledge.**
8. **Local systems may be correct within their definitions.**
9. **Shadow IT can contain real intelligence.**
10. **Parallel representations can disagree honestly.**
11. **The public case must not expose the oracle.**
12. **The approximately $52 million impairment must be derived, not typed.**
13. **No free tonnes, no free metal, no free fuel, no ghost labor, no ghost inventory, no unbalanced journals.**
14. **No one person is made stupid so the plot can work.**
15. **The build is complete only when a fresh clone can regenerate, validate, query, and export it.**

Begin now with repository forensics. Continue through implementation, validation, GitHub publication, and release. Do not stop at a milestone.

---

# PART II — BLACKRIDGE ULTIMATE SANDBOX CLOSEOUT GOVERNANCE PLAN

# BLACKRIDGE ULTIMATE SANDBOX — CLOSEOUT MASTER PLAN

**Document version:** 1.0  
**Prepared:** September 1, 2026  
**Project:** Sable Harbor / Blackridge  
**Purpose:** Define the work required to move Blackridge from a detailed concept and enterprise-data build into a durable, independently reviewable, multi-disciplinary synthetic case universe.

---

## 1. Executive conclusion

The existing **Blackridge Enterprise Data Foundation** Codex mandate is the correct first execution package. It is deliberately large: it requires the SQL database, Excel master workbook, deterministic full-year generation, operational subledgers, financial statements, inventory, assets, workforce, maintenance, processing, commercial settlement, governance, systems, shadow IT, provenance, tests, CI, releases, and a private-oracle boundary.

That build is necessary, but it does not by itself make Blackridge the “ultimate sandbox.”

A complete Blackridge v1.0 requires five additional layers:

1. **Canonical world closure** — a single controlling account of what exists, what happened, what remained unknown, and which details are provisional.
2. **Period-authentic evidence closure** — the files, reports, messages, screens, trackers, physical records, and management representations through which people actually encountered the world.
3. **Scenario and counterfactual closure** — alternate operating paths and intervention windows that remain physically, financially, and temporally coherent.
4. **Evaluation and instructional closure** — participant editions, private oracle, benchmark questions, scoring, facilitator material, and discipline-specific case packs.
5. **Institutional closure** — independent validation, release governance, reproducibility, archival controls, documentation, and a final acceptance audit.

The proper definition of “closed” is therefore:

> **A clean environment can be generated from a tagged commit; every released number and artifact can be traced; period users cannot see future or hidden truth; multiple disciplines can work the same world through controlled packages; alternative interventions can be simulated; the public package cannot leak the oracle; and an independent reviewer can reproduce every material validation and reconcile every material statement.**

---

## 2. Current repository reality

At the time of this plan:

- Sable Harbor’s accepted corporate lore and organization materials are on `main`.
- Blackridge is explicitly classified as a **separate executable case universe**, not a Sable Harbor business unit or consolidated operating component.
- The current Blackridge dossier states that the executable case database, asset register, financial package, and release package are not yet materialized in the accepted repository.
- The enterprise-finance platform exists as a separate release candidate and remains review-blocked.
- The enterprise-portal work is open and correctly avoids claiming that Blackridge has already been materialized.
- Several old `blackridge/m00-*` branches exist and require a documented recovery/disposition audit.
- The proposed private companion repository `SABLEHARBOR-ORACLE` is not yet part of the accepted Blackridge package.

### Consequence

Do not stack the Blackridge build blindly on the review-blocked enterprise-finance PR. Build Blackridge from accepted canon, reuse shared financial-engine patterns only after inspecting and validating them, and preserve Blackridge as a separately versioned case package.

---

## 3. Blackridge product model

Blackridge should be treated as six coordinated products, not one folder.

### 3.1 Developer edition

Contains:

- source code;
- schemas;
- migrations;
- generators;
- validation logic;
- scenario configuration;
- build tooling;
- tests;
- public-safe fixtures;
- interface definitions for private oracle data.

### 3.2 Public world edition

Contains:

- public SQLite database;
- PostgreSQL DDL;
- Excel master workbook;
- public extracts;
- data dictionary;
- query library;
- participant-safe documents;
- case metadata;
- manifests and checksums.

It must not reveal hidden truth or evaluator answers.

### 3.3 Period-authentic participant editions

Contains controlled snapshots such as:

- April 30, 2015;
- May 18, 2015;
- June 26, 2015;
- September 30, 2015;
- October 6, 2015;
- October 19, 2015;
- December 31, 2015.

Each edition must expose only data and artifacts actually available to the selected role by the cutoff.

### 3.4 Facilitator edition

Contains:

- session plan;
- learning objectives;
- suggested prompts;
- progressive hints;
- common failure modes;
- discussion guide;
- expected analyses;
- alternative defensible conclusions;
- debrief sequence.

### 3.5 Private oracle/evaluator edition

Contains:

- hidden physical truth;
- hidden component health;
- true material provenance;
- exact causal graph;
- counterfactual outcome tables;
- scoring rules;
- answer keys;
- leakage tests;
- benchmark evaluator;
- private validation detail.

This edition belongs in a private repository or private release boundary.

### 3.6 Research and publication edition

Contains:

- case narrative;
- technical appendices;
- tables and exhibits;
- methodology;
- limitations;
- synthetic-data disclosure;
- instructor notes;
- formal citation and provenance package;
- publication-ready PDF/PowerPoint where useful.

---

## 4. Workstream 0 — repository recovery, branch hygiene, and authority

### Objective

Establish a defensible repository baseline before adding more Blackridge history.

### Required work

- Inspect all branches, tags, PRs, Actions runs, dangling commits, unreachable trees, and release assets.
- Identify whether any prior M00 implementation exists outside visible branch tips.
- Recover valid work only after it passes canon and test review.
- Record unsupported prior completion claims without repeating them as fact.
- Create a branch-disposition register for every `blackridge/*` branch.
- Preserve unique evidence before closing or deleting stale branches.
- Select a clean Blackridge integration branch from accepted `main`.
- Add a Blackridge-specific `AGENTS.md`.
- Add Blackridge CODEOWNERS.
- Define who may approve:
  - canon changes;
  - model changes;
  - public releases;
  - oracle releases;
  - accounting policy changes;
  - scoring changes.
- Add repository labels and issue templates for:
  - canon conflict;
  - model defect;
  - reconciliation defect;
  - period leakage;
  - oracle leakage;
  - documentation gap;
  - calibration question;
  - expert-review finding.

### Closure evidence

- Repository recovery audit
- Branch and PR disposition register
- Controlling-source map
- Clean feature branch
- No unexplained duplicate active Blackridge heads
- No destructive history rewrite
- Documented authority matrix

---

## 5. Workstream 1 — canonical world bible

### Objective

Create one controlling, versioned specification of the Blackridge world.

### Required documents

1. `BLACKRIDGE_CANON_BIBLE.md`
2. `BLACKRIDGE_DECISION_REGISTER.md`
3. `BLACKRIDGE_CHRONOLOGY.md`
4. `BLACKRIDGE_CAUSAL_MODEL.md`
5. `BLACKRIDGE_EPISTEMIC_MODEL.md`
6. `BLACKRIDGE_ORGANIZATION_AND_AUTHORITY.md`
7. `BLACKRIDGE_SYSTEM_LANDSCAPE.md`
8. `BLACKRIDGE_ACCOUNTING_AND_ECONOMIC_CANON.md`
9. `BLACKRIDGE_PHYSICAL_SITE_CANON.md`
10. `BLACKRIDGE_CHARACTER_REGISTER.md`
11. `BLACKRIDGE_OPEN_QUESTIONS.md`
12. `BLACKRIDGE_CANON_CHANGELOG.md`

### Canon must distinguish

- LOCKED
- PROVISIONAL
- OPEN
- SUPERSEDED
- MODEL_PROPOSED
- SCENARIO_INPUT
- SYNTHETIC_INSTANCE
- DERIVED
- ORACLE_ONLY

### Canon subjects

- Argent Ridge corporate perimeter
- Blackridge legal and operating status
- mine location and physical topology
- ownership/mineral rights
- office/site/facility hierarchy
- Central Pit, East Wall, West Wall, Phase 4
- fleet and process plant
- capital approval
- decision dates
- financial targets
- personnel and reporting relationships
- authority limits
- source systems
- shadow tools
- meeting and reporting cadence
- causal chain
- intervention windows
- aftermath
- Sable Harbor continuity

### Required rule

No generator configuration may quietly become canon. Every locked value must have a canon decision ID; every nonlocked value must be labeled and reversible.

---

## 6. Workstream 2 — enterprise data foundation

### Objective

Execute the existing mega-prompt completely.

### Mandatory substrate

- normalized SQL schema;
- SQLite public database;
- PostgreSQL-compatible migrations and DDL;
- Excel master tracker;
- full 2015 operating year;
- 2014 opening and comparative balances;
- all four primary financial statements;
- inventory;
- assets;
- maintenance;
- workforce;
- procurement;
- geology;
- planning;
- dispatch;
- processing;
- laboratory;
- commercial settlement;
- capital projects;
- governance;
- systems;
- shadow IT;
- controls/evidence enablement;
- manifests;
- deterministic generation;
- public/private separation;
- CI and release package.

### Additional closeout rule

The data foundation is not accepted merely because tests are green. The acceptance review must inspect:

- actual tables and row counts;
- representative records;
- complete transaction traces;
- workbook formulas and formatting;
- statement tie-outs;
- cutoff snapshots;
- source-to-report lineage;
- oracle leakage;
- fresh-clone regeneration.

---

## 7. Workstream 3 — calibration and domain fidelity

### Objective

Make the synthetic world plausible enough that specialists do not immediately reject it.

### 7.1 Mining engineering calibration

Document and validate:

- mine scale;
- annual and daily material movement;
- stripping ratios;
- bench and road geometry;
- haul distances;
- grade and rolling resistance;
- truck payload and cycle distributions;
- shovel loading rates;
- queue behavior;
- drilling and blasting rhythm;
- ore exposure;
- stockpile capacities;
- waste-dump capacities;
- fleet composition;
- labor coverage;
- fuel consumption.

### 7.2 Reliability and maintenance calibration

Document and validate:

- asset ages;
- component lifecycles;
- PM intervals;
- condition-monitoring cadence;
- work-order volumes;
- planner ratios;
- bay and crane capacities;
- maintenance labor mix;
- parts lead times;
- repairable pools;
- backlog distributions;
- repeat-failure logic;
- deferred-maintenance effects;
- fleet-availability definitions.

### 7.3 Processing and metallurgy calibration

Document and validate:

- process flowsheet;
- throughput;
- grind/recovery response;
- ore hardness;
- mineralogy;
- feed blend;
- reagent usage;
- sampling;
- assay turnaround;
- mass-balance tolerances;
- concentrate grade;
- moisture;
- payable metal;
- tailings behavior;
- nonlinear western-material interaction.

### 7.4 Finance and accounting calibration

Document and validate:

- chart of accounts;
- cost-center structure;
- inventory-costing methods;
- stripping and development accounting;
- fixed-asset lives;
- depreciation;
- CIP;
- concentrate provisional pricing;
- TC/RC;
- freight;
- royalties;
- ARO;
- debt;
- tax;
- impairment;
- cash flow;
- monthly close;
- statement presentation.

### 7.5 Workforce calibration

Document and validate:

- headcount;
- crew rotations;
- trade mix;
- qualifications;
- overtime;
- absences;
- embedded contractors;
- payroll;
- labor allocation;
- management spans;
- site-services staffing.

### 7.6 Supply-chain calibration

Document and validate:

- vendor count;
- purchase-order volume;
- SKU count;
- critical spares;
- warehouse layout;
- reorder policies;
- lead-time variability;
- expedites;
- inspection/quarantine;
- consignment;
- repairable exchanges.

### 7.7 Legal, regulatory, environmental, and insurance calibration

Add:

- mineral and surface rights;
- permits;
- environmental obligations;
- water rights;
- tailings obligations;
- explosives controls;
- reclamation and closure;
- insurance policies;
- surety/bonding;
- claims;
- material contracts;
- land access;
- royalties;
- regulator correspondence.

### Required source discipline

Create a calibration source register. Distinguish:

- real-world public reference;
- synthetic design choice;
- expert judgment;
- canon requirement;
- scenario assumption;
- derived result.

Do not copy a real mine’s confidential data or make Blackridge a disguised clone.

---

## 8. Workstream 4 — temporal depth and historical continuity

### Objective

Prevent January 1, 2015 from appearing out of nowhere and prevent December 31, 2015 from being the end of the world.

### Required periods

#### 2010–2013 supporting history

Enough history to support:

- long-lived asset ages;
- component replacements;
- mine development;
- contracts;
- employee tenure;
- system implementations;
- debt;
- stockpile practices;
- legacy spreadsheets;
- prior capital decisions.

This can be lower resolution than 2014–2015.

#### 2014 comparative year

High enough resolution to support:

- opening trial balance;
- operating baseline;
- budget formation;
- reliability trends;
- maintenance backlog;
- ore exposure;
- capital model assumptions;
- year-over-year comparisons.

#### Full 2015

Highest-resolution case year.

#### 2016 aftermath

Include:

- impairment disclosure;
- remediation;
- project redesign;
- workforce consequences;
- lender/board response;
- management postmortem;
- technology and governance changes;
- career outcomes;
- Daniel Mercer’s reconstruction;
- the bridge to Sable Harbor’s founding.

### Required temporal properties

- bitemporal facts where material;
- versioned assumptions;
- immutable period snapshots;
- correction and restatement history;
- no future knowledge in earlier artifacts;
- distinct event, recorded, available, approved, posted, and decision times.

---

## 9. Workstream 5 — source-system emulators

### Objective

Allow future products and agents to operate against systems rather than only a perfect warehouse.

### Required emulated systems

- GeoCore
- StrataPlan
- MineTrack
- ForgeWorks
- AssayLab
- ProcessVault
- Argent ERP
- HR/timekeeping
- procurement/vendor portal
- document repository
- reporting warehouse
- email archive
- shared-drive export
- selected vendor portals

### Emulator forms

At least one of:

- local REST API;
- SQLite source database;
- CSV export endpoint;
- HTML report;
- mock login-free web UI;
- CLI export;
- event stream;
- scheduled file drop.

### Required imperfections

- different identifiers;
- different timezones;
- delayed sync;
- stale extracts;
- limited retention;
- pagination;
- missing fields;
- cancelled/voided records;
- duplicate records;
- revised reports;
- data-quality flags;
- permissions;
- source-specific definitions.

### Acceptance criterion

A tool should be able to reconstruct a result from source-system interfaces without direct access to the perfect canonical database.

---

## 10. Workstream 6 — period-authentic evidence factory

### Objective

Create the actual documentary world that humans, auditors, analysts, and AI agents must interpret.

### Required artifact classes

- emails and threads;
- meeting invites;
- agendas;
- minutes;
- handwritten or typed notes;
- shift handovers;
- daily production reports;
- weekly planning reports;
- maintenance trackers;
- bad-actor lists;
- work orders;
- parts requisitions;
- purchase orders;
- invoices;
- receipts;
- goods-receipt records;
- lab certificates;
- assay reports;
- metallurgical trial sheets;
- dispatch exports;
- road-inspection records;
- safety records;
- environmental records;
- board packs;
- capital committee materials;
- forecast workbooks;
- Phase 4 model versions;
- management status trackers;
- photographs;
- diagrams;
- maps;
- screenshots;
- scanned forms;
- telephone call notes;
- vendor correspondence;
- contracts;
- change orders;
- policies and procedures;
- audit/control evidence.

### Artifact controls

Every artifact requires:

- immutable artifact ID;
- creator;
- owner;
- recipient/audience;
- creation time;
- event/effective time;
- availability time;
- system/location;
- version;
- supersession;
- source inputs;
- hashes;
- transformation lineage;
- access classification;
- authenticity limitations;
- case cutoff behavior.

### Period authenticity

- no modern terminology in 2015 artifacts unless deliberately justified;
- no hindsight phrasing;
- no omniscient author voice;
- no filenames that reveal the answer;
- no implausibly perfect meeting minutes;
- no email in which a character summarizes the entire causal model.

### Noise and decoys

Add unrelated but real operational issues:

- minor safety incident;
- vendor dispute;
- training backlog;
- benign data anomaly;
- weather disruption;
- water-management issue;
- successful maintenance campaign;
- routine employee turnover;
- unrelated budget variance.

These must be meaningful enough to require judgment without becoming fake red herrings.

---

## 11. Workstream 7 — role, permission, and information-access model

### Objective

Model what each person and system could actually access.

### Required features

- user accounts;
- security groups;
- system roles;
- report permissions;
- shared-drive access;
- email access;
- physical-access zones;
- data-owner approvals;
- temporary access;
- contractor restrictions;
- privilege changes;
- account disablement;
- delegated authority;
- meeting attendance;
- distribution lists.

### Participant personas

Build role-filtered packages for at least:

- board member;
- CEO/CFO;
- site general manager;
- mine manager;
- maintenance manager;
- technical-services leader;
- processing manager;
- finance manager;
- project director;
- reliability engineer;
- planner;
- metallurgist;
- procurement analyst;
- data contractor;
- internal auditor;
- external consultant.

### Acceptance criterion

A participant edition must not expose information that its persona could not have accessed by the cutoff.

---

## 12. Workstream 8 — private oracle and epistemic model

### Objective

Separate truth, evidence, belief, and decision.

### Private oracle must model

- hidden physical state;
- true component health;
- true material provenance;
- true geology/material properties;
- actual causal edges;
- latent operational slack;
- true intervention outcomes;
- random-number streams;
- selected counterfactual ground truth;
- actor exposure;
- actor awareness;
- actor understanding;
- actor belief;
- actor authority;
- actor action;
- later reconstruction state.

### Required tests

- public database contains no oracle columns;
- public filenames and IDs do not leak answers;
- public workbook formulas do not reference private files;
- release archives exclude private paths;
- Git history contains no removed oracle data;
- participant snapshots cannot query later availability;
- benchmark prompts do not leak expected conclusions.

### Private repository

Create and govern a private `SABLEHARBOR-ORACLE` repository or an equivalently controlled private storage boundary.

---

## 13. Workstream 9 — scenario and counterfactual engine

### Objective

Make Blackridge reusable for decision and causal testing rather than a fixed murder mystery.

### Scenario families

#### Operational

- improved road maintenance;
- higher/lower truck availability;
- different maintenance deferral;
- additional truck rental;
- different fleet allocation;
- altered stripping priority;
- changed stockpile policy;
- altered plant throughput target;
- different blending rules.

#### Capital

- staged Phase 4;
- delayed approval;
- reduced initial scope;
- redesigned corridor;
- added contingency;
- deferred commitment;
- alternate hurdle rate;
- changed commodity-price assumptions.

#### Information and governance

- cross-functional review introduced;
- integrated data product available;
- different meeting cadence;
- different escalation threshold;
- integrated assumption owner;
- early model challenge;
- revised board-pack design.

#### Supply chain

- spare availability;
- vendor delay;
- repairable-pool strategy;
- different contracting;
- expedited logistics;
- consignment.

#### External

- copper/gold prices;
- diesel;
- FX;
- weather;
- labor availability;
- regulatory delay;
- interest rates.

### Intervention dates

At minimum:

- January 1;
- April 30;
- May 18;
- June 26;
- July 31;
- September 30;
- October 6;
- October 19.

### Required outputs

- physical operating result;
- production;
- recovery;
- metal;
- cost;
- cash;
- NPV/IRR;
- impairment;
- covenant headroom;
- workforce impact;
- project status;
- confidence interval;
- assumptions;
- comparison to base case.

### Critical rule

Counterfactuals must rerun the causal model. They may not be spreadsheet overlays that simply add a chosen benefit to the final answer.

---

## 14. Workstream 10 — benchmark and question registry

### Objective

Create reusable tests for people, software, and AI systems.

### Benchmark dimensions

- retrieval;
- entity resolution;
- temporal reasoning;
- reconciliation;
- provenance;
- accounting;
- financial analysis;
- mine operations;
- maintenance;
- inventory;
- sampling/population analysis;
- causal reasoning;
- uncertainty;
- counterfactuals;
- governance;
- judgment;
- communication;
- hallucination resistance.

### Question registry fields

- question ID;
- version;
- discipline;
- persona;
- cutoff;
- allowed sources;
- expected output form;
- difficulty;
- required calculations;
- required evidence;
- prohibited future evidence;
- scoring dimensions;
- alternate acceptable reasoning;
- common errors;
- leakage sensitivity;
- public/private classification.

### Minimum benchmark tiers

1. **Basic retrieval**
2. **Cross-system reconciliation**
3. **Multi-period analysis**
4. **Causal diagnosis**
5. **Decision recommendation**
6. **Counterfactual design**
7. **Adversarial/noisy evidence**
8. **Executive communication**

### Scoring principle

Do not score only whether a participant guessed “the answer.” Score:

- evidence use;
- temporal validity;
- uncertainty calibration;
- traceability;
- economic coherence;
- operational coherence;
- distinction between observation and inference;
- recommendation quality;
- avoidable downside reduction.

---

## 15. Workstream 11 — audit and assurance packages

### Objective

Make Blackridge useful to audit and control products without pretending one framework governs everything.

### Potential packages

- financial-statement audit;
- internal control over financial reporting;
- capital-project audit;
- inventory observation and valuation;
- fixed assets/CIP;
- revenue and provisional pricing;
- impairment;
- procurement/AP;
- payroll;
- maintenance controls;
- IT general controls;
- system-generated reports/IPE;
- data reliability;
- internal audit;
- operational audit;
- forensic/postmortem engagement.

### Required discipline

For every audit package, separate:

- governing standard;
- criteria;
- professional methodology;
- firm methodology;
- technical source behavior;
- scenario-specific assumptions.

The existing authority research must govern any later SOC/IS-audit pack. Blackridge should provide populations and evidence; it should not hardcode unsupported sample sizes or audit conclusions.

### Package contents

- engagement brief;
- process narratives;
- risk-control matrix;
- PBC list;
- meeting request list;
- populations;
- sample candidates;
- evidence;
- seeded exceptions;
- incomplete evidence;
- reviewer comments;
- workpapers;
- answer key in private oracle;
- versioned authority references.

---

## 16. Workstream 12 — multi-disciplinary case packs

### Objective

Allow the same world to support multiple professional and educational uses.

### Required first-wave packs

1. **Board and governance**
   - Should Phase 4 proceed?
   - What information should the board demand?
   - When should the burden of proof change?

2. **Finance and valuation**
   - Rebuild the investment case.
   - Challenge sensitivity design.
   - Evaluate impairment and liquidity.

3. **Accounting and audit**
   - Close the year.
   - Reconcile subledgers.
   - Test inventory, CIP, revenue, ARO, and impairment.

4. **Mine operations**
   - Diagnose haulage, stripping, and ore-exposure constraints.
   - Design a revised operating plan.

5. **Maintenance and reliability**
   - Analyze fleet cohort exposure, backlog, parts, and repairable pools.
   - Recommend interventions.

6. **Metallurgy and processing**
   - Analyze feed provenance, blend, throughput, grind, and recovery.

7. **Supply chain and procurement**
   - Evaluate critical spares, vendor performance, expediting, and working capital.

8. **Data engineering and Foundry Field**
   - Resolve identifiers.
   - Reconstruct lineage.
   - Design a relationship-and-meaning layer.

9. **Management and organization**
   - Analyze reporting compression, authority, incentives, and communication.

10. **AI and analytics**
    - Build evidence-bound analysis.
    - Test hallucination, temporal leakage, and explainability.

### Each pack requires

- participant brief;
- role;
- cutoff;
- source package;
- assignment;
- deliverable template;
- facilitator guide;
- private scoring rubric;
- debrief;
- alternate defensible answers;
- expected duration ranges by course design, without binding the software build;
- citation and provenance rules.

---

## 17. Workstream 13 — maps, visualizations, and interfaces

### Objective

Make the world comprehensible without reducing it to dashboards.

### Required visual assets

- mine-site map;
- pit/phase/bench map;
- haul-road graph;
- plant flowsheet;
- facility layout;
- asset hierarchy;
- organizational chart;
- authority graph;
- source-system map;
- data-lineage graph;
- shadow-IT network;
- Phase 4 WBS;
- capital commitment curve;
- case timeline;
- causal graph;
- evidence-availability timeline;
- financial-statement dashboard;
- inventory and critical-spares dashboard.

### Recommended technical formats

- SVG;
- PNG;
- GeoJSON;
- GraphML;
- Mermaid source;
- PDF;
- PowerPoint;
- notebook visualizations.

### Period view versus modern view

Label them distinctly:

- **Period-authentic management view**
- **Modern analytical reconstruction**
- **Oracle-only causal view**

Never make a modern integrated dashboard appear as though Blackridge management possessed it in 2015.

---

## 18. Workstream 14 — APIs, notebooks, and integration surfaces

### Objective

Ensure future tools can use Blackridge without reverse-engineering the repository.

### Required interfaces

- documented Python package;
- CLI;
- SQL query cookbook;
- read-only REST API or local API server;
- Parquet exports;
- DuckDB-compatible analytics package;
- selected graph export;
- data contracts;
- JSON Schemas;
- example Jupyter notebooks;
- example BI connection instructions;
- schema-change guide;
- extension SDK for new scenarios and artifacts.

### Example notebooks

- rock-to-cash trace;
- truck/component trace;
- monthly close;
- inventory reconciliation;
- Phase 4 DCF;
- causal timeline;
- May 18 evidence review;
- counterfactual intervention;
- shadow-IT lineage;
- audit population extraction.

### Acceptance criterion

A new developer or analyst can reproduce a meaningful analysis from a clean environment without reading generator internals.

---

## 19. Workstream 15 — quality engineering and red-team testing

### Objective

Prove the sandbox is coherent, difficult, fair, and nonleaky.

### Test classes

- unit;
- integration;
- migration;
- property-based;
- deterministic replay;
- mutation;
- corruption;
- performance;
- workbook;
- database;
- cutoff;
- access-control;
- oracle leakage;
- benchmark leakage;
- counterfactual;
- scenario isolation;
- reconciliation;
- documentation-link;
- release-manifest;
- fresh-clone;
- cross-platform.

### Red-team questions

- Can a participant infer the answer from filenames?
- Does a management deck contain future-restated values?
- Does a row appear before `available_at`?
- Can one entity exist under two canonical IDs?
- Does Excel disagree with SQL?
- Can an unbalanced journal reach a statement?
- Can an asset be in two locations?
- Can a component be installed twice?
- Can inventory go negative?
- Can a counterfactual change final results without changing causal events?
- Can the public package reach a private oracle table?
- Can one random seed contaminate another?
- Can two scenarios aggregate accidentally?
- Can a user query future evidence through an unrestricted view?
- Can the expected answer be recovered from comments or test names?
- Does one seeded exception look implausibly obvious?
- Are all decoys irrelevant, or are some legitimately important?
- Are alternative recommendations scored fairly?

### Performance targets

Define and measure:

- full-year generation;
- database build;
- workbook build;
- key query latency;
- snapshot build;
- release size;
- memory;
- deterministic hash stability.

Do not claim performance without recorded measurements.

---

## 20. Workstream 16 — independent specialist validation

### Objective

Subject Blackridge to review by people capable of finding domain-specific nonsense.

### Recommended review roles

- open-pit mining engineer;
- mine planner;
- mobile-equipment reliability professional;
- mineral-processing/metallurgy professional;
- mine accountant/controller;
- valuation/FP&A professional;
- inventory/procurement professional;
- environmental/closure specialist;
- data architect;
- internal/external auditor;
- case-method educator;
- security/data-governance reviewer.

### Review method

Each reviewer should receive:

- scope;
- assumptions;
- domain extracts;
- validation questions;
- known provisional decisions;
- issue template;
- severity taxonomy.

### Finding states

- accepted;
- accepted with limitation;
- remediation required;
- disputed;
- deferred;
- canon change required;
- scenario-specific.

### Acceptance rule

“Reviewed” is not a checkbox. Preserve reviewer role, date, files reviewed, findings, resolution, and residual limitations.

---

## 21. Workstream 17 — release, preservation, and long-term governance

### Objective

Make Blackridge durable and maintainable.

### Required release controls

- semantic version;
- immutable tag;
- release notes;
- source commit;
- schema version;
- dataset version;
- scenario version;
- seed;
- artifact manifest;
- checksums;
- SBOM;
- dependency lockfile;
- container image or reproducible environment;
- public/restricted classification;
- deprecation policy;
- migration policy;
- known limitations;
- support status.

### Reproducibility package

Include:

- `Dockerfile`;
- `docker-compose.yml` for PostgreSQL;
- devcontainer or equivalent;
- pinned Python lockfile;
- Makefile/Taskfile;
- one-command smoke build;
- one-command full build;
- one-command validation;
- one-command public release;
- private oracle build instructions.

### Archival controls

- release artifacts stored outside ordinary branch history where large;
- checksums;
- redundant backup;
- machine-readable manifest;
- documented recovery test;
- no reliance on one developer workstation;
- no untracked canonical source.

### Governance cadence

Define:

- canon-review process;
- source-update process;
- schema release process;
- scenario approval;
- oracle change approval;
- benchmark versioning;
- issue triage;
- branch retirement;
- annual rebuild/revalidation.

---

## 22. Workstream 18 — Blackridge aftermath and Sable Harbor bridge

### Objective

Close the narrative and institutional loop.

### Required material

- October reconstruction;
- year-end close;
- impairment;
- board response;
- project redesign or suspension;
- changes in responsibilities;
- system-remediation program;
- reporting changes;
- lessons learned;
- Daniel Mercer’s post-event reconstruction;
- what Daniel did and did not know;
- how Priya Raman entered later;
- Jon Bell’s recurrence challenge;
- why Blackridge alone did not justify founding a company;
- how later 2016–2018 customer incidents proved recurrence.

### Important continuity rule

Do not retroactively insert the Original Eight into the Blackridge event. The bridge must preserve the accepted corporate lore.

---

## 23. Workstream 19 — final publication package

### Objective

Make the case usable without requiring repository expertise.

### Public package

- case overview;
- synthetic-data statement;
- participant guide;
- database;
- workbook;
- selected exhibits;
- data dictionary;
- query guide;
- installation guide;
- release notes;
- limitations;
- manifests/checksums.

### Facilitator package

- instructor guide;
- learning objectives;
- discussion plan;
- question bank;
- hint ladder;
- grading rubric;
- debrief;
- alternative analyses.

### Private evaluator package

- oracle;
- answer keys;
- scoring code;
- hidden datasets;
- intervention truth;
- leakage tests;
- evaluator documentation.

### Publication-quality outputs

- case-study PDF;
- executive briefing deck;
- technical architecture deck;
- data dictionary PDF;
- workbook;
- SQLite database;
- archive ZIPs;
- optional web documentation site.

---

## 24. Final closeout audit

Blackridge may be called **accepted v1.0** only after a formal closeout audit.

### 24.1 Canon

- controlling canon exists;
- every locked fact is indexed;
- every provisional assumption is labeled;
- no unresolved conflict exists among controlling files;
- Sable Harbor continuity passes.

### 24.2 Data

- clean database builds;
- migration path works;
- row-count manifest exists;
- full 2015 exists;
- opening and aftermath periods exist;
- master-data domains are populated;
- no toy placeholder tables remain.

### 24.3 Physical model

- material, metal, fuel, labor, assets, and components conserve;
- mine/plant scale is calibrated;
- causal model produces the intended trajectory without direct output plugs.

### 24.4 Financial model

- 12 closes;
- four statements;
- all subledgers reconcile;
- cash flow reconciles;
- impairment is derived;
- Excel and SQL tie exactly.

### 24.5 Evidence

- material artifact classes exist;
- evidence is period-authentic;
- hashes and lineage exist;
- source-system exports and shadow artifacts are represented;
- no hindsight leakage.

### 24.6 Scenarios

- baseline reruns;
- counterfactuals alter causal events;
- scenario isolation passes;
- intervention results are traceable;
- assumptions are versioned.

### 24.7 Evaluation

- question registry exists;
- scoring is evidence-based;
- alternate defensible answers exist;
- facilitator and oracle packages exist;
- leakage testing passes.

### 24.8 Accessibility

- database is searchable;
- workbook is usable;
- APIs/CLI work;
- notebooks run;
- documentation links work;
- new-user walkthrough succeeds.

### 24.9 Security and separation

- public repository contains no oracle;
- private oracle boundary exists;
- public release is scanned;
- real PII/secrets absent;
- licenses and usage terms documented.

### 24.10 Independent review

- specialist reviews completed;
- findings resolved or carried as explicit limitations;
- acceptance report signed/recorded;
- fresh-clone reproduction independently repeated.

### 24.11 Release

- immutable tag;
- public release;
- private oracle release;
- manifests;
- checksums;
- SBOM;
- release notes;
- known limitations;
- recovery procedure.

---

## 25. Recommended execution sequence

### Stage 1 — Finish the data foundation

Run the existing Blackridge mega-prompt. Do not dilute it.

### Stage 2 — Independent acceptance audit of that build

Do not let the builder grade its own work. Use a separate review session or agent to:

- inspect the PR;
- regenerate from a clean clone;
- open and inspect the workbook;
- run query samples;
- inspect journals and statements;
- run corruption tests;
- compare public/private packages;
- issue a formal acceptance finding register.

### Stage 3 — Freeze `blackridge-data-v0.1.0`

Tag and preserve the accepted substrate before adding narrative/evidence complexity.

### Stage 4 — Build the period-authentic artifact factory

This is the most important missing layer after the database. Create the actual records through which Blackridge personnel experienced 2015.

### Stage 5 — Create the private oracle and evaluator

Do this before publishing benchmark questions.

### Stage 6 — Build counterfactuals and case cutoffs

Prove that the world can answer “what could have been known and what could have been changed?” rather than merely replaying the predetermined outcome.

### Stage 7 — Produce discipline-specific case packs

Begin with:

1. board/governance;
2. finance/valuation;
3. operations/reliability;
4. data engineering/Foundry;
5. accounting/audit.

### Stage 8 — Obtain specialist review

Use findings to revise model parameters and documentation without rewriting accepted history silently.

### Stage 9 — Final Blackridge v1.0 release

Publish public, facilitator, and private evaluator editions with a closeout report.

---

## 26. Recommended GitHub epics

1. `BRG-EPIC-00 Repository recovery and canon authority`
2. `BRG-EPIC-01 Canon bible and decision register`
3. `BRG-EPIC-02 SQL/Excel enterprise data foundation`
4. `BRG-EPIC-03 Domain calibration and expert review`
5. `BRG-EPIC-04 Historical baseline and aftermath`
6. `BRG-EPIC-05 Source-system emulators`
7. `BRG-EPIC-06 Period-authentic evidence factory`
8. `BRG-EPIC-07 Access and persona packages`
9. `BRG-EPIC-08 Private oracle and evaluator`
10. `BRG-EPIC-09 Scenario/counterfactual engine`
11. `BRG-EPIC-10 Benchmark and question registry`
12. `BRG-EPIC-11 Audit and assurance packs`
13. `BRG-EPIC-12 Multi-disciplinary case packs`
14. `BRG-EPIC-13 Maps, BI, and interfaces`
15. `BRG-EPIC-14 APIs, SDK, and notebooks`
16. `BRG-EPIC-15 Quality and red-team validation`
17. `BRG-EPIC-16 Release, archival, and governance`
18. `BRG-EPIC-17 Narrative aftermath and Sable Harbor bridge`
19. `BRG-EPIC-18 Final publication and closeout audit`

---

## 27. Recommended release ladder

- `blackridge-canon-v0.1.0`
- `blackridge-data-v0.1.0`
- `blackridge-evidence-v0.1.0`
- `blackridge-oracle-v0.1.0` — private
- `blackridge-counterfactuals-v0.1.0`
- `blackridge-casepacks-v0.1.0`
- `blackridge-rc1`
- `blackridge-v1.0.0`

Each release must pin:

- source commit;
- schema;
- dataset;
- scenario;
- generator;
- seed;
- artifact hashes;
- limitations.

---

## 28. Highest-priority additions not fully closed by the current mega-prompt

The current mega-prompt is already broad. The most important additional work is not “more tables.” It is:

1. a controlling canon bible;
2. source-system emulators;
3. a period-authentic evidence corpus;
4. role- and cutoff-specific participant packages;
5. a private oracle repository and evaluator;
6. a genuine counterfactual engine;
7. a question/scoring registry;
8. multi-disciplinary participant and facilitator case packs;
9. independent specialist validation;
10. formal v1.0 release governance and archival.

Those ten additions are what turn an excellent synthetic enterprise database into the ultimate reusable sandbox.

---

## 29. Nonnegotiable closeout principles

1. Blackridge is a functioning world, not an answer key.
2. The physical world precedes the records.
3. The accounting world derives from transactions.
4. The evidence world derives from people and systems.
5. The participant sees only what was available and permitted.
6. The oracle remains private.
7. Alternative conclusions may be defensible.
8. Scoring rewards evidence and reasoning, not only answer matching.
9. Counterfactuals rerun causality.
10. Public and private releases are separately validated.
11. Green CI is evidence, not proof of completeness.
12. Every material claim remains traceable.
13. Every version remains reproducible.
14. No framework or methodology is silently universalized.
15. “Complete” is reserved for the final closeout audit.

---

## 30. Final recommended definition

Blackridge is fully closed when it can simultaneously function as:

- an enterprise database;
- an Excel-based management and accounting environment;
- a mine operations simulator;
- a maintenance and supply-chain simulator;
- a financial and valuation model;
- a period-authentic evidence repository;
- a data-integration challenge;
- an audit and control-testing environment;
- a causal and counterfactual benchmark;
- an AI evaluation suite;
- a business-school case;
- a professional training laboratory;
- a reproducible, versioned software product.

Until all of those surfaces are backed by one coherent world and independently validated, Blackridge should remain a release candidate rather than be described as complete.

---

# PART III — BLACKRIDGE MACHINE-READABLE CLOSEOUT ACCEPTANCE REGISTER

```json
{
  "document": {
    "title": "Blackridge Closeout Acceptance Register",
    "version": "1.0",
    "date": "2026-09-01",
    "status": "proposed_closeout_control"
  },
  "state_values": [
    "NOT_STARTED",
    "IN_PROGRESS",
    "BLOCKED",
    "REVIEW_READY",
    "ACCEPTED_WITH_LIMITATION",
    "ACCEPTED",
    "SUPERSEDED"
  ],
  "completion_rule": "Blackridge v1.0 may be called accepted only when all P0 gates are ACCEPTED, all P1 gates are ACCEPTED or ACCEPTED_WITH_LIMITATION with recorded residual risk, and any deferred P2 gate is explicitly outside the v1.0 release claim.",
  "gates": [
    {
      "gate_id": "BRG-G000",
      "workstream": "repository",
      "requirement": "Inspect all Blackridge branches, PRs, tags, workflows, dangling commits, and unreachable objects.",
      "priority": "P0",
      "evidence": [
        "BLACKRIDGE_REPOSITORY_RECOVERY_AUDIT.md",
        "branch_disposition_register.json"
      ],
      "classification": "public",
      "depends_on": [],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G001",
      "workstream": "repository",
      "requirement": "Select accepted main as the canon base and avoid blind dependency on review-blocked finance work.",
      "priority": "P0",
      "evidence": [
        "base_branch_record.json",
        "controlling_source_map.md"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G000"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G010",
      "workstream": "canon",
      "requirement": "Publish a controlling Blackridge canon bible with LOCKED, PROVISIONAL, OPEN, SUPERSEDED, MODEL_PROPOSED, SCENARIO_INPUT, SYNTHETIC_INSTANCE, DERIVED, and ORACLE_ONLY states.",
      "priority": "P0",
      "evidence": [
        "BLACKRIDGE_CANON_BIBLE.md",
        "BLACKRIDGE_DECISION_REGISTER.md"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G001"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G011",
      "workstream": "canon",
      "requirement": "Reconcile Blackridge people and chronology to the accepted Sable Harbor lore; Daniel Mercer remains the only future Sable Harbor leader directly exposed.",
      "priority": "P0",
      "evidence": [
        "BLACKRIDGE_CONTINUITY_AUDIT.md"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G010"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G020",
      "workstream": "data_foundation",
      "requirement": "Build normalized SQL schema, explicit migrations, SQLite public database, and PostgreSQL-compatible DDL.",
      "priority": "P0",
      "evidence": [
        "migration_test_report.json",
        "schema_fingerprint.json",
        "blackridge_public.sqlite3"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G010"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G021",
      "workstream": "data_foundation",
      "requirement": "Generate BLACKRIDGE_MASTER_TRACKER Excel workbook exclusively from database views and validate it against SQL.",
      "priority": "P0",
      "evidence": [
        "BLACKRIDGE_MASTER_TRACKER_v0.1.0.xlsx",
        "WORKBOOK_QA_REPORT.md"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G020"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G022",
      "workstream": "data_foundation",
      "requirement": "Populate full-scale workforce, facilities, assets, components, inventory, vendors, contracts, systems, and master data.",
      "priority": "P0",
      "evidence": [
        "row_count_manifest.json",
        "data_profile.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G020"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G023",
      "workstream": "operations",
      "requirement": "Generate M00 and full 2015 mine, haul, maintenance, inventory, processing, commercial, and governance activity chronologically.",
      "priority": "P0",
      "evidence": [
        "m00_validation.json",
        "full_2015_validation.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G022"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G024",
      "workstream": "finance",
      "requirement": "Produce 2014 opening balances, 12 monthly closes, four primary financial statements, subledgers, and a derived Phase 4 impairment.",
      "priority": "P0",
      "evidence": [
        "financial_reconciliation.json",
        "impairment_lineage.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G023"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G025",
      "workstream": "integrity",
      "requirement": "Pass physical, metal, fuel, labor, asset, component, inventory, journal, statement, subledger, cutoff, and deterministic-replay checks.",
      "priority": "P0",
      "evidence": [
        "VALIDATION_REPORT.json",
        "RECONCILIATION_REPORT.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G024"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G030",
      "workstream": "calibration",
      "requirement": "Create a calibration source register distinguishing public reference, canon, synthetic design, expert judgment, scenario input, and derived result.",
      "priority": "P1",
      "evidence": [
        "calibration_source_register.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G010"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G031",
      "workstream": "calibration",
      "requirement": "Obtain recorded specialist review of mining, maintenance, metallurgy, accounting, supply chain, workforce, environmental, and data architecture.",
      "priority": "P1",
      "evidence": [
        "expert_review_register.json",
        "expert_review_findings.md"
      ],
      "classification": "public_summary_private_detail",
      "depends_on": [
        "BRG-G025",
        "BRG-G030"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G040",
      "workstream": "history",
      "requirement": "Generate enough 2010–2013 history to support asset, workforce, contract, debt, system, and shadow-artifact opening states.",
      "priority": "P1",
      "evidence": [
        "historical_coverage_report.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G022"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G041",
      "workstream": "history",
      "requirement": "Generate a high-resolution 2014 comparative baseline and a 2016 aftermath package.",
      "priority": "P1",
      "evidence": [
        "2014_comparative_validation.json",
        "2016_aftermath_manifest.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G040",
        "BRG-G024"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G050",
      "workstream": "source_systems",
      "requirement": "Provide emulated source-system interfaces for GeoCore, StrataPlan, MineTrack, ForgeWorks, AssayLab, ProcessVault, Argent ERP, HR, procurement, reporting, and documents.",
      "priority": "P1",
      "evidence": [
        "source_system_emulator_manifest.json",
        "adapter_contracts/"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G023"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G051",
      "workstream": "source_systems",
      "requirement": "Model source-specific IDs, timezones, pagination, delayed sync, limited retention, revisions, permissions, and data-quality limitations.",
      "priority": "P1",
      "evidence": [
        "source_system_behavior_tests.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G050"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G060",
      "workstream": "evidence",
      "requirement": "Generate period-authentic communications, workpapers, reports, system exports, trackers, contracts, invoices, lab records, maps, screenshots, and meeting material.",
      "priority": "P1",
      "evidence": [
        "artifact_manifest.json",
        "artifact_coverage_report.md"
      ],
      "classification": "public_participant",
      "depends_on": [
        "BRG-G023",
        "BRG-G050"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G061",
      "workstream": "evidence",
      "requirement": "Every artifact has ID, creator, audience, timestamps, availability, version, hash, lineage, access, and limitations.",
      "priority": "P0",
      "evidence": [
        "artifact_integrity_validation.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G060"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G062",
      "workstream": "evidence",
      "requirement": "Pass period-authenticity review with no hindsight narration or answer-revealing filenames.",
      "priority": "P0",
      "evidence": [
        "period_authenticity_review.md",
        "leakage_scan.json"
      ],
      "classification": "public_summary_private_detail",
      "depends_on": [
        "BRG-G060"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G070",
      "workstream": "access",
      "requirement": "Implement role-, permission-, and cutoff-aware data packages for at least fifteen personas.",
      "priority": "P1",
      "evidence": [
        "persona_package_manifest.json",
        "access_boundary_tests.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G051",
        "BRG-G060"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G080",
      "workstream": "oracle",
      "requirement": "Create a private oracle repository or equivalently controlled private storage boundary.",
      "priority": "P0",
      "evidence": [
        "oracle_repository_record.json",
        "public_private_boundary.md"
      ],
      "classification": "public_metadata_private_content",
      "depends_on": [
        "BRG-G010"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G081",
      "workstream": "oracle",
      "requirement": "Model hidden physical truth, actor knowledge states, causal graph, intervention outcomes, and scoring data.",
      "priority": "P1",
      "evidence": [
        "oracle_manifest.json",
        "oracle_validation.json"
      ],
      "classification": "private",
      "depends_on": [
        "BRG-G080",
        "BRG-G023"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G082",
      "workstream": "oracle",
      "requirement": "Prove public code, Git history, workbooks, archives, and releases do not leak oracle data.",
      "priority": "P0",
      "evidence": [
        "oracle_leakage_scan.json"
      ],
      "classification": "public_summary_private_detail",
      "depends_on": [
        "BRG-G081"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G090",
      "workstream": "counterfactual",
      "requirement": "Implement intervention scenarios that rerun the physical and financial causal model.",
      "priority": "P1",
      "evidence": [
        "counterfactual_registry.json",
        "counterfactual_validation.json"
      ],
      "classification": "private_or_controlled",
      "depends_on": [
        "BRG-G025",
        "BRG-G081"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G091",
      "workstream": "counterfactual",
      "requirement": "Provide traceable outcomes for operational, capital, information/governance, supply-chain, and external scenarios at key intervention dates.",
      "priority": "P1",
      "evidence": [
        "intervention_outcome_manifest.json"
      ],
      "classification": "private_or_controlled",
      "depends_on": [
        "BRG-G090"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G100",
      "workstream": "benchmark",
      "requirement": "Create a versioned benchmark question registry spanning retrieval through adversarial causal judgment.",
      "priority": "P1",
      "evidence": [
        "benchmark_question_registry.json"
      ],
      "classification": "public_metadata_private_answers",
      "depends_on": [
        "BRG-G060",
        "BRG-G081"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G101",
      "workstream": "benchmark",
      "requirement": "Implement evidence-based scoring with temporal validity, uncertainty, traceability, economic coherence, and alternative acceptable reasoning.",
      "priority": "P1",
      "evidence": [
        "scoring_specification.md",
        "scoring_tests.json"
      ],
      "classification": "private",
      "depends_on": [
        "BRG-G100"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G110",
      "workstream": "audit",
      "requirement": "Create audit-ready process, population, PBC, evidence, workpaper, and exception packages without hardcoding unsupported methodology.",
      "priority": "P2",
      "evidence": [
        "audit_package_manifest.json",
        "authority_mapping.json"
      ],
      "classification": "controlled",
      "depends_on": [
        "BRG-G060",
        "BRG-G100"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G111",
      "workstream": "audit",
      "requirement": "Trace audit rules and methods to governing authority, criteria, professional guidance, firm methodology, or technical behavior.",
      "priority": "P0",
      "evidence": [
        "audit_authority_validation.json"
      ],
      "classification": "controlled",
      "depends_on": [
        "BRG-G110"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G120",
      "workstream": "case_packs",
      "requirement": "Publish participant and facilitator packs for board, finance, accounting/audit, operations, maintenance, metallurgy, supply chain, data engineering, management, and AI.",
      "priority": "P2",
      "evidence": [
        "case_pack_manifest.json"
      ],
      "classification": "public_and_private_facilitator",
      "depends_on": [
        "BRG-G060",
        "BRG-G100"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G130",
      "workstream": "visualization",
      "requirement": "Publish mine, plant, facility, organization, authority, system, lineage, WBS, timeline, and causal visualizations with period/modern/oracle labels.",
      "priority": "P2",
      "evidence": [
        "visual_asset_manifest.json"
      ],
      "classification": "public_and_private",
      "depends_on": [
        "BRG-G023",
        "BRG-G060"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G140",
      "workstream": "developer_experience",
      "requirement": "Provide CLI, API, Parquet/DuckDB exports, JSON schemas, notebooks, containerized environment, and extension SDK.",
      "priority": "P1",
      "evidence": [
        "developer_acceptance_report.md",
        "notebook_test_report.json"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G020",
        "BRG-G025"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G150",
      "workstream": "quality",
      "requirement": "Pass unit, integration, property, mutation, corruption, performance, workbook, cutoff, access, oracle leakage, scenario isolation, and fresh-clone tests.",
      "priority": "P0",
      "evidence": [
        "complete_test_evidence.json",
        "fresh_clone_report.md"
      ],
      "classification": "public_summary_private_detail",
      "depends_on": [
        "BRG-G082",
        "BRG-G091",
        "BRG-G140"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G160",
      "workstream": "release",
      "requirement": "Publish immutable public, facilitator, and private evaluator releases with manifests, checksums, SBOM, lockfiles, limitations, and recovery instructions.",
      "priority": "P0",
      "evidence": [
        "release_manifest.json",
        "CHECKSUMS.sha256",
        "SBOM.json"
      ],
      "classification": "split_public_private",
      "depends_on": [
        "BRG-G150",
        "BRG-G031"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G170",
      "workstream": "narrative",
      "requirement": "Close the October reconstruction, year-end impairment, 2016 aftermath, and continuity bridge into Sable Harbor without retroactive founder insertion.",
      "priority": "P1",
      "evidence": [
        "BLACKRIDGE_AFTERMATH_AND_SABLE_HARBOR_BRIDGE.md"
      ],
      "classification": "public",
      "depends_on": [
        "BRG-G011",
        "BRG-G041"
      ],
      "state": "NOT_STARTED"
    },
    {
      "gate_id": "BRG-G180",
      "workstream": "closeout",
      "requirement": "Complete an independent v1.0 closeout audit covering canon, data, physics, finance, evidence, scenarios, evaluation, accessibility, security, specialist review, and release.",
      "priority": "P0",
      "evidence": [
        "BLACKRIDGE_V1_CLOSEOUT_AUDIT.md",
        "BLACKRIDGE_V1_ACCEPTANCE.json"
      ],
      "classification": "public_summary_private_detail",
      "depends_on": [
        "BRG-G160",
        "BRG-G170"
      ],
      "state": "NOT_STARTED"
    }
  ]
}
```

---

# FINAL EXECUTION DIRECTIVE

This single file contains the complete handoff.

Execute in this order:

1. repository and failed-run recovery audit;
2. commit this handoff and extract/commit Parts II and III to their required repository paths;
3. establish the correct Blackridge branch from current accepted `main`;
4. execute every requirement and gate in Part I;
5. generate and validate the SQL, Excel, financial, inventory, operational, documentary, manifest, CI, and release outputs required by Part I;
6. update the embedded acceptance register’s repository copy from actual evidence;
7. open the Blackridge pull request against `main`;
8. obtain green CI and complete the release-candidate evidence package;
9. report exact SHAs, URLs, row counts, file sizes, statement totals, reconciliation results, validation results, unresolved limitations, and acceptance-gate states.

There are no external governance files to wait for.

Do not stop at a plan.
Do not stop at a schema.
Do not stop at a workbook shell.
Do not stop at sample records.
Do not stop at an intermediate progress report.
Do not mark untested work accepted.
Do not leak the oracle.
Do not discard valid interrupted-run work without documenting the decision.

Start now.
