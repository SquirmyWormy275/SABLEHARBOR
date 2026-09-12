# ISO extension planning delivery

The ISO source-access gap is resolved for the owner's supplied ISO/IEC 27001:2022 PDF and BS ISO/IEC 42001:2023 scan. The exact 27001:2022/Amd 1:2024 distributor original is available in local holdings. Atlas was consulted read-only at its user-provided-source revision; no implementation files were uploaded there.

## Implementation

The source-bound adapter is `enterprise/ccf/assurance/iso.py`. Its CLI accepts ISO27001, ISO42001 or C5 extension selections while retaining the approved SOC 2/HIPAA corporate/Reno/Boise baseline. Original PDFs are content-addressed outside Git. Short original work objectives, candidate native mappings and source locators are versioned in `iso_data/`.

- ISO27001: 30 ISMS leaf clauses, 93 Annex A reference controls, a document-context gate and a distinct climate-amendment record.
- ISO42001: 32 AIMS leaf clauses, 38 Annex A reference controls linked to normative Annex B guidance and a document-context gate for terms, parent text and annex objectives. Annexes C/D remain informative context.
- Independent expected identifier sets reject omissions, substitutions and category mistakes; AI guidance links are checked separately.
- Delta work distinguishes candidate baseline reuse, additional native-control candidates and unmapped assessment/source attributes. Across both ISO extensions, 22 native controls are additional candidates relative to the current baseline routes; that is not a claim that 22 controls are necessarily sufficient.
- Statement of Applicability rows remain unresolved pending risk-treatment and external-obligation decisions. Considering all Annex A controls does not make every control mandatory.

The generated original implementation plan covers management-system operation, audit/review, technical security additions, AI inventory/roles, impact assessment, data rights/lineage, development/validation/monitoring, reporting and supplier responsibilities. It explicitly identifies where a broad model-validation or security-architecture mapping needs more detailed measures.

## Limits and source provenance

The 42001 scan was rendered and OCR-processed locally without changing the original. The Annex A table identifiers were visually checked on PDF pages 25–28. The watermark degrades OCR, so extracted wording is not independently accepted normative text. Full paragraph semantics, source authenticity, inventory acceptance and mapping sufficiency remain review work.

The 27001 climate amendment adds a context determination and an interested-party note. The adapter preserves those distinctions; it does not invent a mandatory climate programme. Actual ISMS/AIMS scope, AI use cases, lifecycle roles, affected parties, contracts, owners, risk criteria and operating evidence remain inputs for final assessment.

Original hashes: 27001 `843a6728009540947b2c5531f94b4cf1fb698d5bf3b51b324c8801e3e01c5b78`; 42001 `d50103cc0af6d2322c60753ab4a6d9cc54594bc78163481322bf80ee2f75a896`; amendment `43c8e4bbc525b247579b133334f2f52ee306ec26007007f9f99f64f95b72e05c`.

Historical baseline packages and their hashes remain unchanged. Their recorded implementation revisions are required for re-performance. The historical starter still represents its earlier access queue; the ISO adapter provides the new source-bound path.

## Validation

All 155 CCF tests passed, including eight ISO-specific checks for source identifier omissions/substitutions, independent selection, mandatory management-system scope, unresolved applicability, candidate reuse, guidance links and resealed bundle tampering. The combined source-backed ISO27001/ISO42001/C5 package built and re-performed exactly. Separate ISO27001 and ISO42001 packages were also built. Chromium verified all 4,083 attribute rows, ISO filtering, AI guidance workpapers and climate-amendment rows without JavaScript errors. Governance, hygiene and reader regeneration passed (1,004 indexed files and 2,227 local links).
