# Finance and accounting: human evidence completion handoff

**Workline:** `SH-FIN-HUMAN-001`  
**Prepared:** September 11, 2026  
**Status:** implementation handoff; remaining work below is not represented as complete  
**Scope:** make existing synthetic accounting evidence usable by people reading documents and spreadsheets, while preserving financial models, release history and canon distinctions.

## Assignment and boundaries

Implement a separately versioned human evidence layer over the accepted operating and industrial finance sources. Do not build another financial engine. The immediate delivery is one complete, reconciled Foundry Field customer evidence packet plus its reader index and catalog integration. Broader transaction families follow only after the actual wording and rendered packet are reviewed and accepted.

The user requires Markdown representation, a suitable corporate-letterhead document or Excel artifact for financial/accounting material, and a database slot. Implement a linked record identity, not three independent copies of the facts. A database catalog record with paths, provenance and hashes supplies discoverability; it does not make the catalog a replacement ledger. Preserve native accounting records in their existing database/export system and link them by existing source IDs.

The user separately requires small visible review batches, fixed approved visual references, explicit correction tracking and approval attached to the exact presented commit/files. Keep new visual work isolated. Do not merge or mass-produce changed publication designs on the strength of broad project approval. Prepare browser/PDF previews of the actual package; preserve the accepted version and show changes after corrections.

## Read these controlling sources first

- [Maintainer rules](../../MAINTAINERS.md).
- [Delivery and packaging](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md), [generated-record lifecycle](../governance/GENERATED_RECORDS_LIFECYCLE.md), and [publication build instructions](../../tools/documents/README.md).
- [Finance source lock](../finance/CANON_SOURCE_LOCK.md), [source-lock JSON](../finance/CANON_SOURCE_LOCK.json), [accounting policies](../finance/ACCOUNTING_POLICIES.md), [limitations](../finance/KNOWN_LIMITATIONS.md), and [data-room readiness index](../finance/TRANSACTION_DATA_ROOM_INDEX.md).
- [Business successor](../../enterprise/business/README.md), [operating successor](../../enterprise/operations/README.md), all seven operating guides linked there, and [strict export contract](../audit/OPERATING_DEPTH_EXPORT_SPECIFICATION.md).
- [Industrial finance](../../industrial/finance/README.md) and its transaction, driver, funding and temporal guides; [runtime finance reconciliation](../finance/RUNTIME_INFRASTRUCTURE_FINANCE_RECONCILIATION_2026-09-11.md) for later runtime adjustment boundaries.
- Current publication/brand manifests, institutional catalog schema/generator, and current accepted successor records discovered during refresh. Read source-lock inputs without rewriting them.

## Verified starting evidence

The public [business operations v1.0.0 release](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/business-operations-v1.0.0) was downloaded and inspected on September 11, 2026. Source `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`; publication `2026-09-11T04:43:14Z`; ZIP 73,713,427 bytes; SHA-256 `b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817` matched the actual downloaded bytes. It contains 566 files, 98 parent `tables/` files, seven unit exports, an enterprise SQLite database and a six-sheet reviewed workbook. Its unit packages contain CSV/SQLite and brief README files, not individual invoice/credit/approval PDFs. The archive's recorded control outcomes are 5,136 PASS, 181 FAIL and 2,243 NOT_RUN across 7,560 occurrences. These are historical release results, not newly executed tests or production effectiveness.

The [operations release index](../releases/BUSINESS_OPERATIONS_RELEASES.md) was still phrased as undergoing acceptance at initial inspection; the reader-experience branch corrects it using the verified download. Refresh source and release status before continuing. Do not overwrite the existing release. The [reader exercises](../finance/READER_EXERCISES.md) provide exact available archive paths and honest readiness boundaries.

## Implement in bounded stages

### Stage 1: inventory and choose an evidenced transaction

Refresh main, open PRs and source revisions. Create an isolated successor branch. Inventory the current schemas, source events, existing controlled documents, workbook sheets and catalog tables. Produce a machine-readable coverage register keyed by existing record IDs, with MD, PDF/XLSX, accounting source and catalog targets, status, effective period and explicit exemption/missing dispositions. Distinguish individual transaction documents from summary schedules: a schedule row is not automatically a signed contract or an invoice original.

Select one existing Foundry Field invoice and its actual source-supported contract/version, collection, credit and accounting events. Do not invent missing events to create an attractive narrative. Where the record lacks address, payment instructions, signature, tax details or executed terms, state that omission; do not fabricate it. Identify proposed defaults separately and keep them out of booked amounts.

**Acceptance:** the selected event set exists in one pinned scenario/release; every proposed packet fact has a source field or an explicit absence; no unsupported signatory, real-world execution claim or new financial assumption.

### Stage 2: one readable evidence packet

Create an MD packet with contents, period/scenario banner, document identities, exact transaction details, a chronology and accounting cross-references. Produce a letterhead PDF for document-style evidence and an XLSX for the reconciliation schedule where appropriate. Use approved corporate identity and existing publication tools. Clearly label generated reconstructions of synthetic records so professional appearance does not imply an executed original.

The workbook should expose the complete selected population, source IDs, amounts, formulas, units, dates and reconciliation checks. Use readable widths, sensible number formats, print settings and frozen headers. Include an explicit no-record state. No unexplained totals, decorative charts, hidden answer key or untraceable manual adjustments. The document should explain the transaction in concrete wording; do not fill gaps with generic business-language paragraphs.

**Acceptance:** render every changed page/sheet; inspect at ordinary reading size, including print preview. Present the actual packet alongside approved reference styling. Record findings and corrections. Obtain acceptance of this exact small batch before expanding its design.

### Stage 3: database and manifest integration

Extend the existing institutional catalog and approved export schemas deliberately. Prefer existing schema support; add a migration only where necessary. Catalog metadata must resolve stable document ID, source record ID, scenario/run and source revision, effective period, fact/fictionality state, MD path, PDF/XLSX path, source and artifact hashes, version and supersession. Use repository-relative paths or immutable release asset/member identities for released files. Do not import uncontrolled execution databases into Git.

Accounting data continues to reside in its established model and scoped export. Add deterministic links between evidence documents and accounting IDs; verify that both ends exist and share the intended scenario/unit/period. Do not give a link the status of independent corroboration when both sides derive from the same source.

**Acceptance:** no duplicate IDs, orphan catalog entries, absent human artifacts or cross-scenario evidence joins. Changed source bytes make an artifact stale. Catalog inclusion never promotes a planning assumption to canon.

### Stage 4: expand by material reader need

After the first packet is accepted, prioritize:

1. Customer invoice/receipt/credit and deferred-revenue packets for existing commercial histories.
2. Vendor/payable and Treasury request packets, retaining the distinction between requested and funded cash; no bank statement imitation without a separately defined synthetic bank evidence case.
3. Close, allowance and consolidation working papers with full populations and unit/legal reconciliation.
4. Industrial contracts, bills-of-sale/acquisition-support and throughput schedules only where the controlling source supports the instrument or measure. Flag absent underlying legal documents.
5. Selected control-evidence and exception packets linked to the original population and retest; retain FAIL and NOT_RUN.

SOC/CCF completion is owned by a separate active Codex workline per the user. Do not implement, reprioritize or duplicate its backlog here. Link its accepted [CCF surfaces](../../enterprise/ccf/README.md) and refresh accepted status at integration; do not assume the parallel work is complete. A separate, explicit design is needed for daily liquidity simulation, a broader valuation case or new financial assumptions. Such additions must not be smuggled into document formatting. Present pending evidence gaps in the coverage register instead of claiming comprehensive diligence readiness.

### Stage 5: validate and release

Use the current repository test commands; refresh them against actual workflows before execution:

```bash
uv sync --frozen --all-extras
uv run python -m pytest enterprise/operations/tests enterprise/business/tests industrial/planning/tests
uv run python -m enterprise.operations.build
python -m unittest discover -s tests/publications
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
python scripts/validate_repository_hygiene.py
git diff --check
```

The normal operating build requires a clean checkout. `--allow-working-tree` is investigation only and must not certify a release. Do not use schema-draft or review-preparation modes to publish. Preserve the reviewed operating workbook's authoring contract; do not swap writers just to avoid its validator. Extend focused tests for the new source-to-document joins, canonical ID consistency, missing/empty evidence, stale input rejection, sums, Excel formula safety, external-link absence, MD/PDF/XLSX/catalog coverage and both SQLite/PostgreSQL where migrations affect them. Existing controlled-publication tooling documents supported normalization and same-toolchain reproducibility boundaries.

Produce a complete successor distribution under the delivery policy with manifests, hashes and a linked reader index. Keep temporary renders outside current assets; retain selected review evidence deliberately. Required CI and exact-version user visual approval must precede merge/publication of the new visual package. Never replace prior tags, source locks, PDFs or ZIP bytes.

## Definition of done for the first implementation PR

- One accepted, fully readable customer evidence packet and working paper exist as MD plus appropriate PDF/XLSX derivatives.
- Each packet item has a stable database/catalog record and resolves to its existing financial source identity.
- Financial amounts reconcile without changes to historical models; unsupported fields are visible.
- All applicable artifacts are listed, linked and validated; complete pages/sheets passed recorded visual review.
- The reader guide can take a person from repository navigation to the packet without SQL, parsers or AI assistance.
- The PR records exact source/release identity, review commit, artifact hashes, tests and retained gaps. Broader coverage is enumerated as remaining work, not implied by a single example.

No outcome should be described as an audited statement, executed instrument, production control or complete SOC assessment merely because its calculations, formatting and exports pass validation.
