# Initial CCF assurance scope and source proposal

**Status:** Owner-approved reference design scope; source access remains pending. **Date:** September 11, 2026.

**Approval record:** The owner accepted the proposed boundary, SOC 2 categories/Type 2 readiness and HIPAA business-associate/subcontractor scenario with “Approve proposed reference scope.” This approval governs development planning; it does not attest to deployed services, actual PHI processing or completed assessment reviews.

The owner selected internal management, external assessments and customer assurance, with SOC 2 + HIPAA as the baseline and selectable ISO/IEC 27001, ISO/IEC 42001 and BSI C5 extensions. The first [executable delta workbench](../../../enterprise/ccf/assurance/README.md) is available. It deliberately cannot turn unreviewed reference mappings into complete framework coverage.

## Approved first reference assessment

Use the shared technology/runtime service as the first bounded reference assessment: corporate shared controls supporting Reno primary colocation and Boise recovery. Identify and retain supplier/customer responsibilities, administrative access, development/change paths and information flows within that boundary. The planned Northern Nevada owned data center and the wider operating businesses remain separately scoped; their native controls stay in the enterprise CCF. This is an approved development reference scope, not a claim that the colocation contracts or deployments are complete.

Use SOC 2 Security, Availability and Confidentiality coverage with Type 2 readiness as the eventual assessment destination. Processing Integrity and Privacy remain selectable extensions to the SOC scope and should be included when service commitments require them. The owner has not yet selected an external examiner or an operating period. A synthetic reference period may be used for development, clearly separate from any actual period of operation.

For HIPAA, use a business-associate/subcontractor service scenario for the reference design, with explicit PHI/ePHI flows, customer responsibilities, contractual assurances and applicable Security, Privacy and Breach Notification obligations. This reference scope does not establish that any real Sable Harbor entity is a business associate or actually processes health information. Preserve alternative entity-role scenarios in the scope model for future assessments; the business-associate/subcontractor scenario is selected for this reference design.

**Decision recorded:** The first reference boundary, categories and health-data scenario above are accepted. Actual service data flows and obligations still need documented validation. A production examination period, assessor appointment and spending commitments will be separate concrete decisions when operating readiness warrants them.

## Source access needed for reviewed crosswalks

The [AICPA criteria page](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) currently presents a free-account login for the criteria download. Obtain an authorized copy of the TSC, current applicable description criteria and any needed engagement guidance. A subsequent [publisher-source search](CCF_SOURCE_SEARCH_FOLLOWUP_2026-09-11.md) obtained local copies of the TSC and description criteria editions from publicly indexed AICPA CDN URLs; full inventory/mapping review remains open. User account credentials should not be copied into this repository or chat.

The [ISO 27001](https://www.iso.org/standard/27001) and [ISO 42001](https://www.iso.org/standard/42001) public pages establish the relevant standards, but no licensed full copies were found locally. Use an existing authorized organizational copy, including applicable amendments; otherwise a specific acquisition decision is needed. Do not treat the Adobe crosswalk or public standard abstracts as a substitute for exact-source validation. No purchase is made by this proposal.

**Input still needed:** An existing authorized copy of the full ISO 27001/42001 standards, or a decision on acquiring them. The named AICPA criteria editions are now locally available. Licensed source bytes can stay outside the public repository and workbench exports. The engine supports content-addressed local source storage and verifies each document hash.

HIPAA public-rule decomposition and BSI C5 source/version validation remain engineering/research work; they do not require the owner to supply a crosswalk. The current starter contains discovery entries and candidate HIPAA routes, not a completed mapping population. Exact legal applicability and contractual representations require scoped acceptance rather than inferred regulated status.

## Compliance Atlas source-access check

At the owner’s request, re-inspected [Compliance Atlas at revision `4a6e1e8`](https://github.com/shashankvaidya99/compliance-atlas/tree/4a6e1e8b1bb0e4111d11630e80e888a648d45aed). Its tracked tree contains a README, license and fourteen HTML files. The SOC 2, ISO 27001 and ISO 42001 volumes are editorial references; they contain no publisher document attachments or external source-download links (their external links load fonts). The repository does not supply the requested AICPA TSC/description criteria or ISO standards/amendments. That repository inspection did not resolve source access; the subsequent publisher search obtained both AICPA documents, while full ISO copies remain missing. No Atlas material was imported as an authoritative requirement or accepted mapping.

## What is ready to inspect

- Strict versioned source, framework, requirement, attribute, mapping and assessment inputs bound to the native snapshot.
- Baseline/extension selection and scoped control, implementation, evidence and assessment-gap output.
- Eight fictional acceptance cases, including separate SOC/HIPAA tests reusing an artifact and six extension gaps.
- Internal Excel workbook, evidence request list, CSV/JSON outputs and a local searchable explorer.
- Bound review records, source/evidence hashes, negative validation and complete-package re-performance.

These are implemented preparation capabilities. They do not close authenticated production workflow, all-domain control enrichment, complete framework source population, real operating effectiveness, or external assessment acceptance. The full CCF remains in development.
