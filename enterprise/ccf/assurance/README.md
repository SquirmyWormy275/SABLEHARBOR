# CCF assessment and framework delta workbench

This is the executable assessment/delta layer for the [owner-selected SOC 2 + HIPAA baseline](../../../docs/internal/development/CCF_ASSURANCE_DIRECTION_2026-09-11.md). It supports extension selection, original synthetic examples, internal workbooks, evidence request lists and a searchable local explorer. It is **not a populated, reviewed external-framework crosswalk or a completed CCF**. The owner approved the first reference service/report scope; source access remains pending.

The companion assessment schema is `0.2.0`. It binds to the exact `0.1.0` native register snapshot; it does not silently relax that preparation schema's empty external-mapping fields or promote its draft records. Requirement, mapping and assessment records live in versioned input packages. Existing native controls retain their IDs, risk relationships and history.

## Run the delivered examples

From the repository root:

```bash
uv run python -m enterprise.ccf.assurance demo --output /tmp/ccf-assurance-demo
uv run python -m enterprise.ccf.assurance verify --output /tmp/ccf-assurance-demo
uv run python -m enterprise.ccf.assurance starter --output /tmp/ccf-assurance-starter
uv run python -m enterprise.ccf.assurance verify --output /tmp/ccf-assurance-starter
```

Open `explorer.html` or `workbench.xlsx` inside a package. The HTML works locally without a server or network dependency. Search by control, requirement or finding, and filter baseline/extension and framework. The workbook contains native controls, mappings, source references, evidence requests, evidence metadata, test workpapers and the scoped delta.

`demo` uses eight **fictional** requirements across five named framework adapters; none is publisher criteria. Two baseline requirements are supported within that synthetic exercise, using one shared artifact through two distinct tests. Six extension cases expose missing controls/mappings, unimplemented controls, unreviewed mappings, absent tests, an assessment gap and a failed restore case. These examples do not demonstrate actual SOC 2, HIPAA, ISO or C5 conformity.

`starter` is the real-framework **discovery work queue**: 105 entries comprising 61 candidate SOC criterion identifiers, one internal SOC description/scope gate, 37 HIPAA section entries and six extension source gates. It also provides 55 paragraph-level candidate attributes across HIPAA sections 164.308, 164.310 and 164.312, routed to native controls for review. It is not a complete legal obligation inventory; definitions, parent standards, implementation specifications and internal preparation gates are distinguished by their context. The default proposed categories select 77 entries; every one remains unresolved. Selecting all SOC categories includes all 105 entries. There are no approved real mappings or invented reviewer identities in this starter.

## Select frameworks and build from reviewed inputs

```bash
uv run python -m enterprise.ccf.assurance starter --target ISO42001 --output /tmp/ccf-ai-planning
uv run python -m enterprise.ccf.assurance build \
  --catalog /path/to/catalog.json --assessment /path/to/assessment.json \
  --source-root /private/standards-by-hash --output /private/new-assessment-package
```

`--target` is repeatable and replaces the extension selection; it selects all categories for those frameworks. This is an exploratory change and clears the scope review. Fine-grained category selections live in the assessment input. The original package is never edited. A changed catalog must be explicitly bound by its new digest in a successor assessment.

The generated `catalog.schema.json` and `assessment.schema.json` are the strict import contracts. They include sources, framework inventories, requirements and attributes, native mappings, local implementations, evidence, tests, applicability and disclosure records. Unknown fields, duplicate IDs, dangling references, omitted expected requirements and ambiguous JSON are rejected. Empty categories and missing mandatory categories cannot produce empty successful assessments.

For each source marked `AVAILABLE`, place the authorized original document in `--source-root`, named by its lowercase SHA-256 hash (no extension). Build, verification and customer export read and hash-check the original. Source documents are not copied into the output or repository. Metadata-only and inaccessible sources remain visible as blockers. Source retrieval date, effective interval, edition, publisher, rights note and review stay separate. Source-file access establishes byte identity; it does not establish that an interpretation or mapping is correct.

## Meaning of a delta

The report retains unfinished baseline work as well as extension work. Each selected requirement is assessed independently for every selected native boundary. Its attributes identify:

- candidate native support and reuse from the baseline;
- missing control/mapping or proposed implementation work;
- evidence and test gaps;
- documentation or assessment obligations;
- source, scope, applicability and review blockers;
- relevant source-role labels, without inventing appointments.

Several controls can jointly satisfy different attributes of a requirement. Every required attribute needs support. Reusing an artifact does not reuse another framework's conclusion: each test names a requirement, attributes, implementation version, boundary, assessment mode, period, expected population, method, selection rationale and independent review. A design test does not establish operating effectiveness. Hash, provenance, period, origin, expiry and population mismatches remain gaps. The planner consumes reviewed test results; it does not itself execute every control procedure or authenticate upstream systems.

A failure is not erased by a competing PASS. This version intentionally keeps unresolved failure records blocking support. The existing native workflow separately supports waiver/remediation/re-performance; an authorized integration of those closure records into longitudinal framework assessments is subsequent work. Do not delete a failure from an assessment package to manufacture success.

Reviewed exclusions retain their justification and are never counted as support. Addressable HIPAA specifications are not automatically excluded: source/context analysis and scoped decisions remain required. Paragraph labels in the starter are discovery notes, not substitutes for the regulation.

## Reviews, provenance and access boundaries

A review names distinct author and reviewer subjects and the review date. Its `subject_digest` is the canonical digest of the normalized containing record with `review` and `inventory_review` removed. The digest uses the native register's sorted, compact UTF-8 JSON representation. Changing the reviewed record invalidates that binding. Reviewers must record a new approval of the actual changed content; the example helper that binds fictional reviews is not an approval service.

These subject IDs and approval records are caller-supplied. **This local CLI does not authenticate people, validate real appointments, enforce enterprise approval grants, or provide tamper-proof storage against a filesystem administrator.** Hashes detect drift relative to inputs; they are not digital signatures or proof that an underlying manual test was performed. Packages and their review history must be retained in the organization's controlled record system before operational use.

Internal packages contain assessment inputs, including evidence payloads. Directories are created with owner-only access and files with owner read/write permissions. Their source documents remain external. The workbook/explorer omit raw payloads but may still reveal sensitive scope, findings and metadata; they are internal outputs, not public trust-center pages. The HTML has no authentication layer and must not be deployed as a public evidence service.

Customer export is a separate operation:

```bash
uv run python -m enterprise.ccf.assurance customer \
  --catalog /path/to/catalog.json --assessment /path/to/assessment.json \
  --source-root /private/standards-by-hash --output /private/approved-statements.json
```

It requires reviewed operating-record scope and explicit reviewed disclosure statements tied to selected, supported requirements. Synthetic, excluded, unselected or unsupported statements are rejected. It emits only the supplied approved audience/statement and scope period; it does not compose claims from private evidence or leak internal counts and findings. It does not issue an auditor's report, certification, or HIPAA opinion.

`verify` checks all package members and hashes, the exact current native/implementation inputs, source documents when required, and regenerated JSON, schemas, CSV, workbook and HTML. Rehashing an edited result does not make it match re-performance. Byte reproducibility is required within the pinned runtime; different dependency versions can change workbook or schema serialization. Use the package's original repository revision and locked environment.

## Reference decisions and remaining work

Adobe's stable v5 and preview v6 workbooks informed the separation of mapping, implementation guidance, tests and evidence requests. No Adobe workbook content or normative standards text is imported here. Sources: [Adobe downloads](https://www.adobe.com/trust/compliance/common-controls-framework.html), [AICPA criteria access](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022), [eCFR Part 164](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164), [administrative safeguards](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.308), [physical safeguards](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.310), [technical safeguards](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312), [ISO 27001](https://www.iso.org/standard/27001), [ISO 42001](https://www.iso.org/standard/42001).

The next source-population tranche needs authorized AICPA criteria/description criteria and ISO sources, complete public-law/C5 review, scoped applicability, richer control designs and test workpapers. The owner approved corporate shared controls supporting Reno primary and Boise recovery, SOC 2 Security/Availability/Confidentiality with Type 2 readiness, and a HIPAA business-associate/subcontractor reference scenario. The [scope approval and source record](../../../docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md) preserves that decision. Actual data flows, an external assessment period and examiner appointment remain open. Existing generic starter inputs and synthetic packages are unchanged; the planning approval does not supply their missing record-level reviews. Production identity/connector/storage integration, authenticated review and the broader CCF backlog are not completed by this planning layer.

## Approved reference assessment preparation

The reference builder creates the corporate/Reno/Boise design scope with SOC 2 Security/Availability/Confidentiality, a HIPAA business-associate/subcontractor scenario and an optional C5 extension. It includes source inventories, 192 proposed implementation workpapers, unexecuted test plans and a scoped delta. It does not invent operating evidence, personnel appointments or independent reviews.

```bash
uv run python -m enterprise.ccf.assurance.reference build \
  --baseline-only --source-root /path/to/content-addressed-originals \
  --output /tmp/ccf-reference-baseline
uv run python -m enterprise.ccf.assurance.reference build \
  --source-root /path/to/content-addressed-originals \
  --output /tmp/ccf-reference-with-c5
uv run python -m enterprise.ccf.assurance.reference verify \
  --source-root /path/to/content-addressed-originals \
  --output /tmp/ccf-reference-with-c5
```

The new output directory contains `assessment/` (the existing ten-member workbench), `WORKPAPERS.json`, CSV implementation/test plans, source inventories, a mapping review queue, the reference scope, readiness notes and a bundle manifest. Both the inner assessment and the outer bundle can be re-performed; available source originals are hash-checked and the HIPAA paragraph population is reconciled to the pinned XML. These bundles are internal preparation records. The baseline has 447 requirement/boundary rows and 870 attribute test plans; all assessment conclusions remain unresolved pending the relevant reviews and evidence. Counts include context, definitions and review tasks, not only operative controls.

The [reference source notes](reference_data/README.md) distinguish all 61 TSC and nine DC identifiers, the full Part 160/164 section/paragraph extraction, and the eight C5 continuity workpapers from complete obligation/mapping review. The generic `starter` and fictional `demo` retain their existing behavior. ISO extensions stay discoverable but are not selected in this first reference build.
