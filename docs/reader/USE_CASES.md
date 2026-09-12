# Using the Sable Harbor universe

**Reviewed:** September 11, 2026 · **Role:** reader guide; does not create company facts or professional conclusions.

Choose a bounded question, a business, and a period before collecting evidence. Keep one release's records together. A 2027 conditional forecast cannot stand in for a 2026 transaction record. The exercises below suggest work for the reader; they do not publish assessment answer keys.

## Pick a first task

These entry points are files you can open now. Where a task needs a release download or local build, that requirement is explicit.

| Task | Open first | Working evidence | Produce |
|---|---|---|---|
| Explain a cash shortfall | [Operating review XLSX](../../enterprise/operations/publications/operating-review-v1.0.0.xlsx), **Cash obligations** | [Finance exercise 3](../finance/READER_EXERCISES.md#3-investigate-a-cash-shortfall) identifies the release tables | Arrears reconciliation and a short decision memo |
| Trace an invoice | [Finance exercise 1](../finance/READER_EXERCISES.md#1-follow-a-customer-invoice-through-collection-and-credit-loss) | Foundry Field invoice, credit and journal extracts in the named release | Dated movement schedule with source IDs |
| Review a control exception | [CCF procedures](../../enterprise/ccf/PROCEDURES.md) | Locally built native example package; see the controls route below | Test worksheet preserving the original failure and retest history |
| Prepare an assurance evidence request | [Approved reference preparation](../../enterprise/ccf/assurance/README.md#approved-reference-assessment-preparation) | Proposed workpapers and unexecuted plans; source originals required for the build | Scoped request list and review queue, with no assurance conclusion |
| Understand accountability | [Business and department directory](../wiki/Home.md) | Linked current charts, charters and decision records | A source-linked account of who decides, operates and reviews |
| Review a facility programme | [Independent plan index](../../geospatial/maps/facilities/ARTIFACT_INDEX.md) | [Population bridge](../../geospatial/facilities/population/BRIDGE.md), site and floor plans | Annotated plan and capacity review |

On a narrow screen, scroll tables sideways to see every column.

## Accounting and financial audit practice

Start with the [finance exercise guide](../finance/READER_EXERCISES.md), [industrial finance](../../industrial/finance/README.md), and [accounting policies](../finance/ACCOUNTING_POLICIES.md). Select one entity and period; trace a supported transaction from its source register to the journal and reporting output. Reconcile a selected balance and record unexplained differences or missing support.

Produce a reconciliation workbook and a short evidence memo. Use the native released workbooks and scoped SQLite/CSV exports when supplied. A summary journal is not automatically an invoice, bank confirmation, or payroll record. The finance guide identifies which exercises have that depth and which need further development.

## Financial postmortems and capital allocation

Read the [industrial participant guide](../../industrial/CASE_GUIDE.md), [planning package](../../industrial/planning/README.md), and [business operations](../../enterprise/operations/README.md). Compare an operating scenario's throughput, costs, capital needs, requested cash, and funding constraints. Explain why an apparently profitable plan may remain unfunded or infeasible.

Produce a decision memo supported by a scenario comparison. Distinguish a retrospective analysis of a synthetic reconstruction from a postmortem of conditional future scenarios. Do not describe forecast outcomes as observed company history.

## Controls and assurance

Choose one of three distinct routes. The approved reference scope and the executed synthetic examples answer different questions.

| Route | Start and access | What you inspect | What it supports |
|---|---|---|---|
| Native control exercises | [Preparation README](../../enterprise/ccf/README.md) and [procedures](../../enterprise/ccf/PROCEDURES.md); build locally | Finance-close, identity-lifecycle and recovery examples, including FAIL/NOT_RUN cases and independent re-performance | Practice testing a bounded population and following an exception |
| Assessment mechanics | [Workbench instructions](../../enterprise/ccf/assurance/README.md#run-the-delivered-examples); run `demo` locally | Eight fictional requirements, evidence reuse, missing support and a failed restore case | Learn the assessment interface and why separate requirements need separate conclusions |
| Approved reference preparation | [Reference instructions](../../enterprise/ccf/assurance/README.md#approved-reference-assessment-preparation) and [source inventory](../../enterprise/ccf/assurance/reference_data/README.md); build locally with the required source originals | Corporate/Reno/Boise SOC 2 Security/Availability/Confidentiality and HIPAA scenario, proposed implementation workpapers and unexecuted tests; optional C5 extension | Prepare evidence requests, scope review and mapping work; no completed assurance result |

For the native exercise, the documented build produces `exercises.json`, `COVERAGE.md` and `registry.sqlite3` in your chosen output folder. The assessment `demo` produces `workbench.xlsx` and `explorer.html`; the reference bundle puts those files under `assessment/` and adds `WORKPAPERS.json`, implementation/test-plan CSVs and readiness notes. Open the workbook in Excel or another spreadsheet application, or open the explorer in a browser. The explorer runs locally without a server. These outputs are generated by the linked commands; this guide does not imply they are a prebuilt public download.

Produce a scoped test worksheet and findings memo for an exercise, or an evidence-request list for reference preparation. Name the objective, population, procedure, original result and review history. The reference scope approval does not approve individual mappings or perform tests. Neither route supplies a SOC report or an enterprise-wide operating-effectiveness conclusion. Passing package validation checks the synthetic data and build, not the enterprise's controls.

## Management, organization, and professional practice

Use the [business directory](../wiki/Home.md#businesses), [current charts](../organization/README.md), and [Advisory manual](../advisory/SABLE_HARBOR_ADVISORY_FIRM_MANUAL_2026-09-09.md). Select a documented project or matter, identify the responsible roles and decision authority, and compare the recorded work with the applicable policy. Follow the operations package for synthetic project, staffing, customer, and forecast histories.

Produce a short case analysis: the decision, available evidence, constraints, alternatives supported by the records, and remaining questions. Keep Advisory matter work separate from Atlas product responsibilities. Organizational display records are not an employee census.

## Transaction due diligence and legal-record review

Begin with the [Red Wash transaction file](../../industrial/transaction/01_RW_TRANSACTION_FILE.md), [ARU purchase record](../../industrial/transaction/04_ARU_APPROVAL_AND_PURCHASE_AGREEMENT.md), and [data-room scope](../finance/TRANSACTION_DATA_ROOM_INDEX.md). Follow consideration, approval, asset/liability treatment, operating dependencies, and closing conditions into the financial records.

Produce a source-linked diligence request list and a transaction-to-books bridge. Distinguish a synthetic agreement from real legal execution. A data-room category list is not evidence that every listed document exists; tax and external filing limits remain explicit.

## Operations, logistics, and resource planning

Open [industrial operations](../../industrial/operations/README.md), [mine records](../../red_wash/README.md), and the [planning case](../../industrial/planning/README.md). Examine a selected throughput, inventory, logistics, or capacity question. Connect operating units and periods to the corresponding costs and revenues.

Produce an operating reconciliation or capacity assessment, naming assumptions and missing engineering detail. Do not infer installed track, plant, custody rights, or permitted capacity from a conceptual map. Retain the accepted prohibition on a Red Wash mine rail spur.

## Security, resilience, and vendor review

Read the [runtime estate](../../enterprise/runtime/README.md), [services register](../../enterprise/services/README.md), and [CCF recovery example](../../enterprise/ccf/PROCEDURES.md). Follow one dependency from a selected provider or service through the design and supporting evidence. Review the disclosed recovery example and what it does and does not demonstrate.

Produce a dependency assessment, recovery evidence review, or vendor-question list. Selected vendors, synthetic contracts, planned equipment, and executed deployments are distinct states. These are tabletop and evidence-review resources, not a live cyber range.

## Facilities and workplace planning

Use the [facility atlas](../../geospatial/facilities/README.md), [planning workbench](../../geospatial/facilities/workbench/README.md), and [spatial review](../../geospatial/facilities/spatial/README.md). Select a site, inspect its status, then follow building and floor links. Compare the area, population, attendance, and seat assumptions. In GitHub, the [individual artifact index](../../geospatial/maps/facilities/ARTIFACT_INDEX.md) links straight to saved SVG, PNG and PDF plans. For a visit-oriented illustration, use the locked V08 [PNG](../../geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.png) or [PDF](../../geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.pdf); it is not to scale.

Produce a planning review with annotated plans. Proposed geometry and modelled seats do not establish property ownership, code compliance, construction, or actual attendance. Each saved plan remains available independently of the interactive viewer.

## Research, commercial, and data-analysis exercises

Use the [Willow](../business-lines/WILLOW.md), [Cradle](../business-lines/PROJECT_CRADLE.md), [Foundry Field](../business-lines/FOUNDRY_FIELD.md), and [Atlas Meridian](../business-lines/ATLAS_MERIDIAN.md) dossiers to find relevant projects, recovery streams, contracts, and commercial assumptions. The [operations guides](../../enterprise/operations/README.md) explain which detailed synthetic histories exist.

Possible bounded tasks include contract-to-revenue review, customer retention analysis, research gate review, recovery-lot reconciliation, and forecast comparison. Choose a task only after confirming the required fields in its released dataset. Use the [database guide](../../db/README.md) for SQL work; it is optional for document and spreadsheet readers.

## Downloads and tools

| Package | Human-facing entry | Scope |
|---|---|---|
| Industrial planning case | [Release, workbook and participant ZIP](../releases/INDUSTRIAL_CASE_RELEASES.md) | Mine/logistics/transaction records and conditional enterprise planning; offline browser and database included. |
| Business finance | [Release index](../releases/BUSINESS_FINANCE_RELEASES.md) | Business-driven conditional forecast and seven scoped unit exports. |
| Business operations | [Release index](../releases/BUSINESS_OPERATIONS_RELEASES.md) | More detailed operating histories, control exercises, and reviewed workbook. |
| Facility atlas | [Release index](../releases/FACILITY_ATLAS_RELEASES.md) | Independent maps and plans, source status and navigation. |
| Spatial review | [Release index](../releases/FACILITY_SPATIAL_RELEASES.md) | Sections, elevations, roofs, schedules and offline viewer. |
| Native CCF and assessment workbench | [Local build instructions](../../enterprise/ccf/README.md#run), [assessment examples](../../enterprise/ccf/assurance/README.md#run-the-delivered-examples) and [reference preparation](../../enterprise/ccf/assurance/README.md#approved-reference-assessment-preparation) | No prebuilt download claimed. Generated JSON/SQLite examples and XLSX/HTML assessment views; reference builds require source originals. |

Open Markdown in GitHub, PDFs in a PDF reader, and downloaded XLSX workbooks in a spreadsheet application. For HTML, extract the complete package before following its opening instructions. SQLite is optional for querying large tables; the [document library](../wiki/Library.md) provides ordinary file links.

## Where the reading routes live

The README, this guide and [wiki pages](../wiki/Home.md) are ordinary Markdown in this repository. The [library](../wiki/Library.md) links the underlying files without relocating them. A separate GitHub Wiki or hosted application is not needed for these reading routes.

The facility atlas and packaged case browsers open from a downloaded checkout or extracted release. Keep their directory structure so links continue to work. CCF assessment explorers are local workbench outputs; they are not a public evidence portal. The [source and format guide](SOURCES_AND_FORMATS.md) explains document authority, publication pairings and the distinction between a library entry and transaction evidence.

A classroom or professional exercise should specify its own question and deliverable. The public archive does not expose private scoring material. Repository visibility does not override the repository's rights notice.
