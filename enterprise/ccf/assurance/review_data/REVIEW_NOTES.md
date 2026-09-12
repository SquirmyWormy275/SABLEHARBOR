# Review basis, findings and remaining decisions

This delivery advances beyond the earlier blank coverage workpapers: it records source-condition comparisons, observed gaps, corrective procedures and tests. It does not assert that every paragraph has been exhaustively interpreted or independently accepted.

## What was compared

The review used retained AICPA TSC/description-criteria PDFs, the pinned Title 45 XML, the supplied ISO27001 PDF and amendment, the supplied ISO42001 scan/OCR, and the publisher C5 YAML/PDF source inventory. All original source hashes are verified during the build. Atlas was read-only; its remote reference tree was checked for the supporting standards, without uploading or editing content.

- Fifty targeted findings compare specific duties with existing draft procedures. They include HIPAA environmental decisions, documentation retention, discovery/notice handling, subcontractor and privacy processes; SOC2 accountability/communications/description; ISO management-system and AI work; and C5 service capabilities, fixed intervals and permitted exceptions.
- The 193 ISO objective checks state concrete conditions to compare with the actual candidate procedures. These checks do not replace whole-clause interpretation or ISO42001 Annex B guidance review. The scan/OCR still needs qualified semantic and authenticity review.
- All 17 C5 domains have an authored comparison against candidate native procedures, with distinct corrective design work. Child-level acceptance remains open. All 623 children preserve their publisher kind, linked information blocks and separate corresponding customer responsibilities across 168 parents. Line segmentation is a source navigation aid, not proof that each line is exactly one duty.
- The 22 HIPAA addressable specifications are reconciled one-to-one with the retained source paragraphs. Their environmental decisions remain unresolved. Standards, required specifications, definitions and legal exceptions still apply; this register is not the whole Security Rule.
- Prior SOC2/HIPAA section analyses are retained and explicitly labelled where this pass has not added a targeted duty comparison. An absence of a new finding is not a passing coverage conclusion.

## Decisions now made concrete

1. C5 selection and architecture: the approved two-site Reno/Boise reference cannot demonstrate the sharpened PS-02 requirement for more than two locations and resilience after two simultaneous location failures. Keep that as a gap until the owner and assessor decide selected criteria and actual architecture. No third site is approved or assumed.
2. Product capabilities: identify whether confidential computing/attestation, containers, customer-managed keys, regional partitions, customer security logs, customer IAM and export interfaces actually exist. Conditional criteria need facts; generic corporate procedures cannot provide missing product functionality.
3. Operating facts: identify actual ePHI flows, agreements, subcontractors, AI systems/uses/affected parties, service levels and identity/evidence populations. The approved reference scenario does not assert these facts.
4. Authority: appoint the security official, executors, risk owners, management reviewers and qualified independent reviewers. Record ISMS risk-owner and AIMS designated-management treatment approvals separately.
5. Review judgments: resolve exact source conditions, allowed alternatives, legal-status questions, normative dependencies and reporting period with appropriate reviewers. Risk acceptance does not erase a C5 criterion deviation. No evidence or assurance approvals were generated.

## Current legal-status and source dependency checks

On September 12, 2026, the [HHS direct-liability guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/factsheet/index.html) was checked for the distinction between direct BA duties and delegated customer work. The [HHS court-status notice](https://www.hhs.gov/hipaa/for-professionals/special-topics/reproductive-health/final-rule-fact-sheet/index.html) continues to identify vacated reproductive-health provisions and remaining notice modifications. The historical XML must not be used alone to determine enforceability. Findings rely on the retained regulatory paragraphs for detailed duties; qualified current-law review remains necessary.

ISO27001 cites ISO/IEC 27000 without a date, while the supplied ISO42001 cites ISO/IEC 22989:2022. Their full normative reference reconciliation is still open. The [ISO publisher record](https://www.iso.org/standard/27000) now lists ISO/IEC 27000:2026, published in July 2026, replacing the 2018 edition and changing its focus. Do not silently use the older vocabulary or treat a publisher overview as the full referenced standard. C5 BCM-01 also requires reconciliation with ISO22301 and/or BSI200-4; a recovery drill alone is insufficient. Supporting ISO27002 and AI guidance may improve implementation detail, but their absence must not be hidden by a broad mapping. No standard was purchased and no new independent source acceptance is asserted.

## Re-performance and change control

Authored findings are bound to the source catalogue, requirement definitions, draft designs and analysis inputs reviewed. If those change, the build fails as stale. Rebinding requires reconsidering the analysis; there is no automatic approval or rebinding command. Generated files are immutable review deliveries; make tracked authoring changes and produce a new bundle. Re-performance checks all members and rejects even checksum-resealed edits. Original source text stays outside the committed analysis and customer exports.
