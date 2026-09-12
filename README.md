# SABLE HARBOR

<img src="assets/brand/logos/sable-harbor__primary-horizontal.png" alt="Sable Harbor" width="360">

Sable Harbor is a fictional company universe for exploring how businesses operate, keep accounts, make decisions, and produce evidence. Its archive includes company records, organization charts, contracts, financial models, operating records, controls, and facility plans. You can read the documents and workbooks without running code or using AI.

**[Explore the company](docs/wiki/Home.md)** · **[Choose an exercise](docs/reader/USE_CASES.md)** · **[Find a document](docs/wiki/Library.md)** · **[Maps and buildings](geospatial/facilities/README.md)**

## Choose what you want to do

On a narrow screen, scroll the table sideways to see every column.

| Your purpose | Start with | What you can do |
|---|---|---|
| Accounting and audit practice | [Finance exercises](docs/finance/READER_EXERCISES.md) | Follow source records into journals, reconcile balances, examine intercompany eliminations, and document evidence gaps. |
| Finance postmortems and investment decisions | [Industrial case guide](industrial/CASE_GUIDE.md) and [planning release](docs/releases/INDUSTRIAL_CASE_RELEASES.md) | Compare operating assumptions, capital plans, funding shortfalls, and scenario outcomes. |
| Management case studies | [Business directory](docs/wiki/Home.md#businesses) and [exercise guide](docs/reader/USE_CASES.md) | Examine business responsibilities, project decisions, staffing assumptions, and forecasts. |
| SOC-oriented controls and internal audit practice | [Controls guide](docs/reader/USE_CASES.md#controls-and-assurance) | Run a bounded synthetic evidence exercise, or inspect the approved SOC 2/HIPAA reference preparation and its unexecuted test plans. |
| Due diligence and transaction review | [Transaction records](industrial/transaction/01_RW_TRANSACTION_FILE.md) | Read purchase and governance records, then trace the related operating and financial assumptions. |
| Security, incident response, and continuity exercises | [Runtime estate](enterprise/runtime/README.md) and [CCF examples](enterprise/ccf/README.md) | Examine selected recovery dependencies, evidence, failures, and remediation histories. |
| Operations and supply-chain analysis | [Industrial operations](industrial/operations/README.md) | Explore mine throughput, inventory, logistics, capacity, and operating constraints. |
| Organization and governance studies | [Organization charts](docs/organization/README.md) and [department directory](docs/wiki/Home.md#departments-and-institutions) | Follow reporting relationships, officer responsibilities, independent assurance, and board decisions. |
| Facilities and workplace planning | [Facility atlas](geospatial/facilities/README.md) | Inspect individual site/building/floor plans and distinguish modelled capacity from actual occupancy. |
| Data analysis and software exercises | [Database guide](db/README.md) | Query scoped synthetic records or reproduce a documented model, keeping its scenario and release identity. |

The [full use-case guide](docs/reader/USE_CASES.md) gives reading routes, suggested deliverables, and limits for these and related exercises.

## Open something useful now

- **Review financial results:** download the [operating review workbook](enterprise/operations/publications/operating-review-v1.0.0.xlsx). Start with **Results** or **Cash obligations**, then use the [exercise guide](docs/finance/READER_EXERCISES.md) to find the supporting transactions.
- **Understand a business:** open [Foundry Field](docs/wiki/businesses/Foundry-Field.md), [Advisory](docs/wiki/businesses/Advisory.md), or the [full directory](docs/wiki/Home.md#businesses). Each page links its records and organization charts.
- **Inspect a place:** use the [individual plan index](geospatial/maps/facilities/ARTIFACT_INDEX.md) in GitHub or download the [facility atlas PDF](geospatial/maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf). The selected Sacramento visitor map is available as [PNG](geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.png) and [PDF](geospatial/facilities/visitor/v08/artifacts/visitor-map-v08.pdf).
- **Examine controls:** read the [three exercise procedures](enterprise/ccf/PROCEDURES.md). For assessment planning, open the separate [approved reference preparation](enterprise/ccf/assurance/README.md#approved-reference-assessment-preparation); its test plans are not executed assurance evidence.

## Start without installing anything

1. Open a [business or department page](docs/wiki/Home.md). Each page connects its people, work, and supporting documents.
2. Read Markdown directly on GitHub. Open linked PDFs for formatted documents; download XLSX files to work in a spreadsheet application.
3. For a complete exercise corpus, use a [documented release](docs/reader/USE_CASES.md#downloads-and-tools). Keep its guide and manifest with the files. Earlier releases remain separate snapshots.
4. For interactive maps or an offline case browser, download the applicable package and follow its opening instructions. GitHub's file preview does not run HTML applications. The CCF workbench currently requires a local build; the [controls route](docs/reader/USE_CASES.md#controls-and-assurance) names the generated files and prerequisites.

No code is required for document review. Build commands are available in each package's README for readers who want to regenerate or query the data.

## Understand what you are reading

All company records and scenarios are synthetic. A balanced financial model does not establish commercial feasibility; a passing software test does not establish an effective control. Historical reconstruction, conditional forecasts, proposed facilities, external hosts, and current organizational decisions have different meanings.

- **LOCKED:** accepted within this fictional universe.
- **PROVISIONAL / OPEN:** working direction or an unresolved matter.
- **SUPERSEDED:** preserved history; check its successor before using it as current authority.

Use the [source and status guide](docs/reader/SOURCES_AND_FORMATS.md) when records disagree. Current records do not silently rewrite older released exercises. Some exercises support a complete bounded task; others deliberately or explicitly lack evidence for a broader conclusion.

## Explore further

[Business dossiers](docs/business-lines/README.md) · [Controlled documents](docs/CONTROLLED_DOCUMENT_INDEX.md) · [Brand assets](assets/brand/README.md) · [Wiki source and publication status](docs/wiki/README.md) · [Maintainer instructions](MAINTAINERS.md)

The repository is the source of truth. The wiki lives in [versioned Markdown pages](docs/wiki/Home.md) here; a separate live GitHub Wiki is not required to read it. Interactive viewers open locally from a checkout or release package. No separate website or account is needed for the document routes. Public visibility does not grant an open-source license: all rights remain reserved unless a specific file states otherwise.
