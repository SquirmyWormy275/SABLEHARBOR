# SABLE HARBOR

<img src="assets/brand/logos/sable-harbor__primary-horizontal.png" alt="Sable Harbor" width="360">

Sable Harbor is a fictional company universe for exploring how businesses operate, keep accounts, make decisions, and produce evidence. Its archive includes company records, organization charts, contracts, financial models, operating records, controls, and facility plans. You can read the documents and workbooks without running code or using AI.

**[Explore the company](docs/wiki/Home.md)** · **[Choose an exercise](docs/reader/USE_CASES.md)** · **[Find a document](docs/wiki/Library.md)** · **[Maps and buildings](geospatial/facilities/README.md)**

## Choose what you want to do

| Your purpose | Start with | What you can do |
|---|---|---|
| Accounting and audit practice | [Finance exercises](docs/finance/READER_EXERCISES.md) | Follow source records into journals, reconcile balances, examine intercompany eliminations, and document evidence gaps. |
| Finance postmortems and investment decisions | [Industrial case guide](industrial/CASE_GUIDE.md) and [planning release](docs/releases/INDUSTRIAL_CASE_RELEASES.md) | Compare operating assumptions, capital plans, funding shortfalls, and scenario outcomes. |
| Management case studies | [Business directory](docs/wiki/Home.md#businesses) and [exercise guide](docs/reader/USE_CASES.md) | Examine business responsibilities, project decisions, staffing assumptions, and forecasts. |
| SOC-oriented controls and internal audit practice | [Controls guide](docs/reader/USE_CASES.md#controls-and-assurance) | Inspect control designs and bounded synthetic evidence, test exceptions, and assess what evidence is missing. This is not a complete SOC engagement or report. |
| Due diligence and transaction review | [Transaction records](industrial/transaction/01_RW_TRANSACTION_FILE.md) | Read purchase and governance records, then trace the related operating and financial assumptions. |
| Security, incident response, and continuity exercises | [Runtime estate](enterprise/runtime/README.md) and [CCF examples](enterprise/ccf/README.md) | Examine selected recovery dependencies, evidence, failures, and remediation histories. |
| Operations and supply-chain analysis | [Industrial operations](industrial/operations/README.md) | Explore mine throughput, inventory, logistics, capacity, and operating constraints. |
| Organization and governance studies | [Organization charts](docs/organization/README.md) and [department directory](docs/wiki/Home.md#departments-and-institutions) | Follow reporting relationships, officer responsibilities, independent assurance, and board decisions. |
| Facilities and workplace planning | [Facility atlas](geospatial/facilities/README.md) | Inspect individual site/building/floor plans and distinguish modelled capacity from actual occupancy. |
| Data analysis and software exercises | [Database guide](db/README.md) | Query scoped synthetic records or reproduce a documented model, keeping its scenario and release identity. |

The [full use-case guide](docs/reader/USE_CASES.md) gives reading routes, suggested deliverables, and limits for these and related exercises.

## Start without installing anything

1. Open a [business or department page](docs/wiki/Home.md). Each page connects its people, work, and supporting documents.
2. Read Markdown directly on GitHub. Open linked PDFs for formatted documents; download XLSX files to work in a spreadsheet application.
3. For a complete exercise corpus, use a [documented release](docs/reader/USE_CASES.md#downloads-and-tools). Keep its guide and manifest with the files. Earlier releases remain separate snapshots.
4. For interactive maps or an offline case browser, download the applicable package and follow its opening instructions. GitHub's file preview does not run HTML applications.

No code is required for document review. Build commands are available in each package's README for readers who want to regenerate or query the data.

## Understand what you are reading

All company records and scenarios are synthetic. A balanced financial model does not establish commercial feasibility; a passing software test does not establish an effective control. Historical reconstruction, conditional forecasts, proposed facilities, external hosts, and current organizational decisions have different meanings.

- **LOCKED:** accepted within this fictional universe.
- **PROVISIONAL / OPEN:** working direction or an unresolved matter.
- **SUPERSEDED:** preserved history; check its successor before using it as current authority.

Use the [source and status guide](docs/reader/SOURCES_AND_FORMATS.md) when records disagree. Current records do not silently rewrite older released exercises. Some exercises support a complete bounded task; others deliberately or explicitly lack evidence for a broader conclusion.

## Explore further

[Business dossiers](docs/business-lines/README.md) · [Controlled documents](docs/CONTROLLED_DOCUMENT_INDEX.md) · [Brand assets](assets/brand/README.md) · [Wiki source and publication status](docs/wiki/README.md) · [Maintainer instructions](MAINTAINERS.md)

The repository is the source of truth. The wiki is a reading and navigation layer. Public visibility does not grant an open-source license: all rights remain reserved unless a specific file states otherwise.
