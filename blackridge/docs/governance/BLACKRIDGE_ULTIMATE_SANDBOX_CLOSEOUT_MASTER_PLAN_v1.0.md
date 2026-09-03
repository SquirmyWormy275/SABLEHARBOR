# PART II — BLACKRIDGE ULTIMATE SANDBOX CLOSEOUT GOVERNANCE PLAN

# BLACKRIDGE ULTIMATE SANDBOX — CLOSEOUT MASTER PLAN

**Document version:** 1.0  
**Prepared:** September 1, 2026  
**Project:** Sable Harbor / Blackridge  
**Purpose:** Define the work required to move Blackridge from a detailed concept and enterprise-data build into a durable, independently reviewable, multi-disciplinary synthetic case universe.

---

## 1. Executive conclusion

The existing **Blackridge Enterprise Data Foundation** Codex mandate is the correct first execution package. It is deliberately large: it requires the SQL database, Excel master workbook, deterministic full-year generation, operational subledgers, financial statements, inventory, assets, workforce, maintenance, processing, commercial settlement, governance, systems, shadow IT, provenance, tests, CI, releases, and a private-Alexandria Control boundary.

That build is necessary, but it does not by itself make Blackridge the “ultimate sandbox.”

A complete Blackridge v1.0 requires five additional layers:

1. **Canonical world closure** — a single controlling account of what exists, what happened, what remained unknown, and which details are provisional.
2. **Period-authentic evidence closure** — the files, reports, messages, screens, trackers, physical records, and management representations through which people actually encountered the world.
3. **Scenario and counterfactual closure** — alternate operating paths and intervention windows that remain physically, financially, and temporally coherent.
4. **Evaluation and instructional closure** — participant editions, private Alexandria Control, benchmark questions, scoring, facilitator material, and discipline-specific case packs.
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
- The proposed private companion repository `SABLEHARBOR-ALEXANDRIA-CONTROL` is not yet part of the accepted Blackridge package.

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
- interface definitions for private Alexandria Control data.

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
  - Alexandria Control releases;
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

## 12. Workstream 8 — private Alexandria Control and epistemic model

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
- Git history contains no removed control-plane data;
- participant snapshots cannot query later availability;
- benchmark prompts do not leak expected conclusions.

### Private repository

Create and govern a private `SABLEHARBOR-ALEXANDRIA-CONTROL` repository or an equivalently controlled private storage boundary.

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
- answer key in private Alexandria Control;
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
- Can the public package reach a private Alexandria Control table?
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
- private Alexandria Control build instructions.

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
- private Alexandria Control boundary exists;
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
- private Alexandria Control release;
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

### Stage 5 — Create the private Alexandria Control and evaluator

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
9. `BRG-EPIC-08 Private Alexandria Control evaluator`
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
5. a private Alexandria Control repository and evaluator;
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

