# ISO extension implementation plan

This is proposed engineering work for SABLEHARBOR. Atlas remains a read-only reference guide. No certification scope, actual AI use, deployed settings or reviewer appointments are asserted.

## Management systems and applicability

For each selected system, establish context, interested parties, scope and accountable management. Reconcile the actual service or AI use-case inventory to that scope. Adopt risk criteria that allow comparable repeated assessments, record risk owners and determine treatment. For 27001, incorporate the climate amendment's context determination and interested-party note without treating the note as an independent mandatory climate-control programme.

Create a Statement of Applicability from risk treatment, external obligations and the Annex A comparison. Record necessary controls, inclusion/exclusion rationale, implementation state and remaining measures; include necessary controls outside Annex A. Selection of the reference catalogue in the planner means the controls are considered, not automatically required. Obtain the appropriate treatment and residual-risk decisions. Management review, internal audit and corrective action remain explicit activities even where SOC 2/HIPAA control execution can be reused.

Candidate additions: SH-ASS-003, SH-GOV-002, SH-GOV-005, SH-OPS-004 and SH-PPL-005. Establish an independent audit programme, regular management review with required inputs and recorded outputs, documented operational processes and resource/competence coverage. A management certification is not an independent audit. Evidence: approved scope, criteria, risk/treatment register, Statement of Applicability, audit programme/workpapers, review minutes and validated corrective actions.

## Technical security additions

Use the existing baseline authentication, cryptography/transfer, physical, capacity and environmental supplements. Extend them for the actual ISO clauses rather than assuming those supplements cover all requirements.

- SH-CFG-003: reconcile assets to patch/support status, identify unsupported technology, schedule changes and verify remediation or expiring risk acceptance.
- SH-CFG-004: inventory credential/key/certificate ownership and custody, approved storage, expiry/rotation and revocation; test a failed rotation and a recovery path without exporting secrets.
- SH-OPS-002: record actual load, peak/recovery demand and dependency capacity; set approved thresholds, monitor breaches and verify capacity action.
- SH-SEC-004: apply risk-based vulnerability remediation targets and verify fixes; link overdue exposure to authorized escalation.
- SH-PPL-001/003: document security obligations in workforce arrangements and preserve relevant responsibilities during/after role changes.

Additional local measures still need design for labelling, asset return, physical cabling/maintenance, clock synchronization, masking, leakage protection, web filtering, safe testing and externally developed systems. A broad native mapping must not conceal these conditions. For each, identify the actual system/provider, operator, trigger, configuration criterion, failure response and evidence before design acceptance.

## AI inventory, roles and purpose

SH-AIM-001 and SH-AIM-005 need a system/use-case register identifying developer/provider/deployer/customer roles, intended and prohibited uses, affected populations, locations, components, dependencies, owners and lifecycle state. Establish human decision authority, escalation and stop conditions. A model inventory alone misses the surrounding AI system and non-model processes.

SH-PRD-002/003/004 and SH-ETH-003 need audience-appropriate user information, change notices, external adverse-impact reporting and internal concern channels. Assign triage and response duties; preserve reports, decisions, communications and remedies. Do not infer customer commitments from a product capability.

## AI impact assessment and treatment

Extend SH-AIM-002 beyond model performance validation: define the impact-assessment method, affected individuals/groups and societal effects, foreseeable misuse, technical/social context, jurisdictions and intended deployment. Include discipline-specific safety, privacy or security assessment where relevant. Record consequences, uncertainty, stakeholder input and limitations; feed results into risk assessment and treatment. Reassess at planned intervals and material changes, retain results, and determine appropriate disclosure. Independent model validation alone does not satisfy this workflow.

Evidence: versioned impact assessment, population/context analysis, risk linkage, treatment decisions, limitations and independent challenge. Actual systems and affected groups are required inputs; do not fabricate them for the reference scenario.

## AI data, tooling and lineage

SH-AIM-003, SH-DAT-005 and SH-FND-003 need separate identification of datasets, acquisition/usage rights, provenance, quality criteria, preparation transformations, tooling and external model dependencies. Version raw/derived data and transformation logic; trace training/evaluation partitions and contamination risks; retain rights and source restrictions. Assess suitability for the intended use and affected populations, not only format validity.

Evidence: data/dependency inventory, rights decisions, lineage graph, version hashes, quality checks and transformation reconciliation. Respect source-specific rights; a reference document's presence in Atlas is not a license for unrelated redistribution.

## AI lifecycle and operating monitoring

For each use case, define responsible-development objectives and requirements before design; document design decisions, validation criteria, deployment prerequisites, technical documentation and event-recording requirements. Bind evaluation results and approvals to the exact system version. Use SH-AIM-002 for independent validation, SH-ENG-004 for release authority and SH-AIM-004 for monitoring, maintenance and feedback.

Define monitoring measures, review cadence, limits and stop/escalation thresholds from the actual risk assessment. Include performance degradation, harmful outcomes, misuse, overrides, incidents and supplier changes. Preserve failures and retest evidence across versions and periods; do not replace a failed history with a later passing result.

## Third parties and accountable interfaces

Reconcile responsibilities across the AI lifecycle with suppliers, partners and customers, including data/model/tool providers. Use SH-TPR-002/003/004 to inspect scope, terms, assurance limitations, change/incident reporting and exit obligations. Capture unperformed responsibilities and residual risk explicitly. A provider report or baseline mapping does not transfer our accountability.

## Acceptance and operating inputs

The generated delta workpapers identify candidate baseline reuse, additional native controls, unmapped attributes, owner-role labels and evidence work. Each selected objective requires source interpretation, a sufficiently detailed local design, justified applicability, scoped implementation and independently reviewed evidence. The populated source catalogue still has independent-review gates; it is not a completed certification assessment.

Required actual inputs: service and AI-system inventory, intended uses and roles, affected parties, contracts, system instances, resource/owner appointments, risk criteria and treatment decisions. Independent review and examiner scope acceptance follow those facts. Publisher originals and OCR derivatives remain outside committed implementation data and generated customer outputs.
