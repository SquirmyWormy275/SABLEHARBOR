# SABLE HARBOR

<img src="assets/brand/logos/sable-harbor__reverse-horizontal.png" alt="Sable Harbor" width="360">

Sable Harbor is a fictional company built to explore how businesses work: how they make decisions, keep accounts, manage operations, and document what happened. The repository contains its company records, organization charts, contracts, financial models, controls, and facility plans. You can read the documents and workbooks without running code or using AI.

**[Read the Wiki](https://github.com/SquirmyWormy275/SABLEHARBOR/wiki)** · **[Start here](docs/wiki/Start-Here.md)** · **[Choose an exercise](docs/reader/exercises/README.md)** · **[Find a document](docs/wiki/Library.md)** · **[Contribute](CONTRIBUTING.md)**

[Locations and facilities](docs/wiki/Locations.md) · [Records and decisions](docs/wiki/Records-and-Decisions.md)

## Choose what you want to do

On a narrow screen, scroll the table sideways to see every column.

| Your purpose | Start with | What you can do |
|---|---|---|
| Accounting and audit practice | [Finance exercises](docs/finance/READER_EXERCISES.md) | Follow transactions into the journals, reconcile balances, examine intercompany eliminations, and identify missing evidence. |
| Finance postmortems and investment decisions | [Industrial case guide](industrial/CASE_GUIDE.md) and [planning release](docs/releases/INDUSTRIAL_CASE_RELEASES.md) | Compare operating assumptions, capital plans, funding shortfalls, and scenario outcomes. |
| Management case studies | [Business directory](docs/wiki/Home.md#businesses) and [exercise guide](docs/reader/USE_CASES.md) | Examine business responsibilities, project decisions, staffing assumptions, and forecasts. |
| SOC-oriented controls and internal audit practice | [Controls guide](docs/reader/USE_CASES.md#controls-and-assurance) | Test a control against example records, or use the approved SOC 2/HIPAA reference material to plan an assessment. The reference test plans have not been carried out. |
| Due diligence and transaction review | [Legal and transaction records](docs/reader/transactions/README.md) | Read purchase and governance records, then trace the related operating and financial assumptions. |
| Security, incident response, and continuity exercises | [Runtime estate](enterprise/runtime/README.md) and [Common Controls Framework (CCF) examples](enterprise/ccf/README.md) | Examine recovery dependencies, incident evidence, failures, and remediation histories covered by the exercises. |
| Operations and supply-chain analysis | [Industrial operations](industrial/operations/README.md) | Explore mine throughput, inventory, logistics, capacity, and operating constraints. |
| Organization and governance studies | [Organization charts](docs/organization/README.md) and [department directory](docs/wiki/Home.md#departments-and-institutions) | Follow reporting relationships, officer responsibilities, independent assurance, and board decisions. |
| Facilities and workplace planning | [Facility atlas](geospatial/facilities/README.md) | Inspect site, building, and floor plans. Distinguish planned capacity from actual occupancy. |
| Data analysis and software exercises | [Database guide](db/README.md) | Query the example records or reproduce a documented model, keeping track of its scenario and release. |

The [full exercise guide](docs/reader/USE_CASES.md) explains where to start, what to produce, and what each exercise can and cannot establish.

## Open something useful now

- **Complete a first exercise:** choose an [acquisition reconciliation, invoice trace, or contract-obligations review](docs/reader/exercises/README.md). Each guide names the records and worksheet tabs, walks through the steps, and identifies missing evidence.
- **Review financial results:** download the [operating review workbook](enterprise/operations/publications/operating-review-v1.0.0.xlsx). Start with **Results** or **Cash obligations**, then use the [exercise guide](docs/finance/READER_EXERCISES.md) to find the supporting transactions.
- **Trace accounting support:** open the [five accounting evidence packages](docs/finance/evidence/coverage/README.md). Each includes the complete set of records for its stated scope, reconciliation results, and CSV/SQLite access. New PDF/workbook designs remain in review.
- **Read legal records:** use the [instrument directory](docs/reader/transactions/README.md) to find commercial terms, corporate approvals, acquisitions, and host rights. The directory also identifies missing evidence.
- **Understand a business:** open [Foundry Field](docs/wiki/businesses/Foundry-Field.md), [Advisory](docs/wiki/businesses/Advisory.md), or the [full directory](docs/wiki/Home.md#businesses). Each guide introduces the business, its people, its records, and its unanswered questions. The live Wiki includes the supporting text in full.
- **Inspect a place:** use the [individual plan index](geospatial/maps/facilities/ARTIFACT_INDEX.md) in GitHub or download the [facility atlas PDF](geospatial/maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf). The selected Sacramento visitor map is available as [PNG](geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.png) and [PDF](geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.pdf).
- **Review technical and site evidence:** download the [offline review edition](docs/releases/CLOSEOUT_EVIDENCE_RELEASES.md) to browse runtime cases, check which source records are covered, inspect site records and geographic evidence gaps, and save your review notes without a server.
- **Examine controls:** read the [three exercise procedures](enterprise/ccf/PROCEDURES.md). For assessment planning, open the separate [approved reference preparation](enterprise/ccf/assurance/README.md#approved-reference-assessment-preparation). Its test plans describe work to be done, not tests already performed.

## Start without installing anything

1. Open a [business or department page](docs/wiki/Home.md) to learn about its people and work, then follow the links to supporting documents.
2. Read Markdown directly on GitHub. Open linked PDFs for formatted documents; download XLSX files to work in a spreadsheet application.
3. For all the files in an exercise, use a [documented release](docs/reader/USE_CASES.md#downloads-and-tools). Keep its guide and manifest with the files. Do not mix records from different release snapshots.
4. For interactive maps or an offline case browser, download the package and follow its opening instructions. GitHub's file preview does not run HTML applications. The CCF workbench currently requires a local build; the [controls guide](docs/reader/USE_CASES.md#controls-and-assurance) lists the prerequisites and files it produces.

No code is required for document review. Each package's README includes build commands for readers who want to regenerate or query the data.

## Understand what you are reading

All company records and scenarios are synthetic. A balanced financial model does not establish commercial feasibility, and a passing software test does not prove that a control works. Check whether a record describes reconstructed history, a conditional forecast, a proposed facility, an external host, or a current company decision.

- **LOCKED:** accepted within this fictional universe.
- **PROVISIONAL / OPEN:** working direction or an unresolved matter.
- **SUPERSEDED:** preserved history; check its successor before treating it as current.

The [source and status guide](docs/reader/SOURCES_AND_FORMATS.md) explains which record to follow when documents disagree. New records do not rewrite older released exercises. Some exercises include everything needed for the stated task; others identify missing records that prevent a broader conclusion.

## Work with the repository

Use these folders to find the documents, data, and tools behind the Wiki.

| Area | Contents |
|---|---|
| [`docs/wiki/`](docs/wiki/README.md) | Company articles, reading guides, and navigation. |
| [`docs/`](docs/) | Company records, governance, finance, and controlled-document indexes. |
| [`enterprise/`](enterprise/README.md) | Business models, operating records, runtime design, and controls. |
| [`industrial/`](industrial/README.md) | Industrial operating and investment cases. |
| [`geospatial/`](geospatial/README.md) | Geographic evidence, facility plans, and notes on their accuracy. |
| [`blackridge/`](blackridge/README.md) | The separate Blackridge case and its data. |
| [`tools/`](tools/) | Build, publication, and review utilities. |

The [contribution guide](CONTRIBUTING.md) covers setup, checks, and publishing changes. The [open questions register](docs/wiki/Open-Questions.md) separates unanswered questions and missing evidence from presentation work that is already complete.

## Explore further

[Business dossiers](docs/business-lines/README.md) · [Controlled documents](docs/CONTROLLED_DOCUMENT_INDEX.md) · [Brand assets](assets/brand/README.md) · [Wiki source and publication status](docs/wiki/README.md) · [Maintainer instructions](MAINTAINERS.md)

The repository is the source of truth. The [live Wiki](https://github.com/SquirmyWormy275/SABLEHARBOR/wiki) is its reading edition; the [versioned sources](docs/wiki/README.md) remain here. Source links identify the published snapshot, and an automated check flags changed source files or edits made directly to the Wiki.

Interactive viewers open locally from a checkout or release package. No separate website or account is needed to read the documents. Public visibility does not grant an open-source license: all rights remain reserved unless a specific file states otherwise.
