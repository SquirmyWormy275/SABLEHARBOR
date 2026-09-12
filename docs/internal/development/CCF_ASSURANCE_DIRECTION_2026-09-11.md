# CCF operating and assurance direction

**Recorded:** September 11, 2026. **Status:** User-selected product direction; implementation requirements, not an assessment conclusion or an executed assurance engagement.

## Accepted direction

The owner selected all three uses: internal management, external assessment readiness, and customer assurance supported by assessment results. SOC 2 and HIPAA are the initial coverage baseline. The product must support selecting additional frameworks, including ISO/IEC 27001, ISO/IEC 42001 and BSI C5, and generating the remaining work needed for the selected scope.

This replaces the suggested internal-management-first-only direction and advances external mapping and assessment development alongside the native operating register. Existing native control identities, business-risk coverage and management/independent-assessment responsibilities remain the foundation. HIPAA is now an explicit baseline development target, rather than only a suggested research entry in the Atlas comparison.

## Product contract

One native control can support several versioned external requirements through reviewed mappings. Each scoped implementation, test and conclusion remains separately addressable. A framework selection must produce a delta against actual implementation and evidence status, not simply subtract the labels in two framework catalogs.

Inputs are the target framework and edition, service/entity/system boundary, assessment date or period, selected categories or profile, legal/applicability assumptions, and the versioned implementation/evidence baseline. Unresolved inputs remain visible and produce a provisional delta. They must not silently become exclusions or covered requirements.

For every applicable target requirement, the output must distinguish:

| Disposition | Required output |
|---|---|
| Supported by existing controls | Native control and local implementation references, reviewed mapping rationale, evidence/test references and their scope/period limitations. |
| Existing control needs enhancement | The uncovered requirement attributes and proposed changes to the existing design or procedure. |
| New control required | A proposed native control or local implementation, objective/risk rationale and acceptance criteria; no automatic approved ID or duplicate control merely because a framework was selected. |
| Evidence or testing gap | Missing, stale, failed, insufficient or out-of-scope evidence; population and period requirements; necessary re-performance. |
| Assessment or management-system gap | Missing scope documents, governance activities, workpapers or external assessment steps, separately from operating controls. |
| Unresolved or excluded | Missing source/access/review/applicability information, or a justified reviewed exclusion. These are distinct states. |

Every action should include accountable-role references, dependencies, priority rationale, evidence expectations and review state. Exports must show source versions, baseline identity and assumptions. Changing the scope, edition or evidence period must invalidate affected conclusions and regenerate the delta. A passed baseline assessment is not transitive proof for another framework.

Customer assurance outputs should trace statements to approved scoped conclusions and supporting records, with audience-specific disclosure permissions. Internal evidence, private assessment material and unsupported claims must not be published through a generic framework export.

## Initial assessment coverage

- **SOC 2:** Develop category-selectable criteria, system description, customer/provider responsibilities, and separate design/operating-effectiveness records. Propose Type 2 readiness as the planning destination; the owner has not yet selected report type, categories, service boundary, assessor or period.
- **HIPAA:** Develop a role- and data-flow-scoped assessment covering applicable Security, Privacy and Breach Notification obligations. Selecting it for preparation does not establish that an entity is a covered entity or business associate or that actual PHI is processed. HHS describes those scope relationships in its [Privacy Rule summary](https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html) and [business associate guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html). HHS does not recognize private Security Rule certifications; the output should be described as an assessment and evidence package, not an HHS-approved certification. [HHS certification FAQ](https://www.hhs.gov/hipaa/for-professionals/faq/2003/are-we-required-to-certify-our-organizations-compliance-with-the-standards/index.html).
- **Additional frameworks:** Make ISO/IEC 27001, ISO/IEC 42001 and BSI C5 selectable extension targets. Validate authoritative editions, source access and requirement-level mappings before producing reviewed coverage. Do not infer exact source coverage from the Atlas or reuse an older edition merely because it is already listed in the repository.

## Implementation sequence and acceptance

1. Add versioned source/requirement, assessment-scope and reviewed mapping records to a successor schema; the preparation schema currently disallows populated mapping arrays.
2. Populate and review SOC 2/HIPAA baseline requirements using authorized primary sources, linked to native controls and local implementation gaps.
3. Implement the scope-aware delta generator and separate control, evidence, assessment and unresolved outputs.
4. Add ISO/IEC 27001, ISO/IEC 42001 and C5 extensions after source validation, then expose framework selection and customer assurance views.

Meaningful acceptance cases include partial coverage, several controls jointly supporting one requirement, one control supporting several frameworks, a fully mapped but unimplemented control, failed or expired evidence, mismatched periods/boundaries, missing licensed source text, changed editions, and an unresolved applicability decision. None may be reported as demonstrated coverage merely because a mapping exists. Synthetic examples must remain distinguishable from operating evidence.

The owner need not supply control crosswalks or choose implementation mechanics. The owner has [approved the first reference scope](CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md): corporate shared controls supporting Reno primary and Boise recovery, SOC 2 Security/Availability/Confidentiality with Type 2 readiness, and a HIPAA business-associate/subcontractor design scenario. Actual service data flows, an examination period, examiner appointment and any commercial deadline remain to be established. Existing six material-decision packets remain separate. This direction authorizes preparation toward external assessment, not a claim of passing one.
