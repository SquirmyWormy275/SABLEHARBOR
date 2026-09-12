# Operating decisions needed to complete the CCF

Status: prepared questions, no answers or appointments inferred. The approved Reno primary / Boise recovery / corporate shared-control reference scenario remains the starting point. These questions refine actual operation; they do not reopen that approval. Atlas remains the reference guide.

| ID | Decision or factual input | Suggested evidence | Work unlocked |
|---|---|---|---|
| FACT-01 | Identify actual legal entities, services, systems, locations and providers; distinguish planned from operating components. | Service/asset inventory and architecture/data-flow records | Scope, populations and corporate/site inheritance |
| FACT-02 | Identify actual data categories and contractual roles, including whether and where PHI is processed and which duties are delegated. | Data-flow inventory, executed agreements and responsibility schedules | HIPAA applicability and service description |
| FACT-03 | Identify actual AI systems, intended/prohibited uses, developer/provider/deployer roles and affected people. If no systems operate, record that fact rather than inventing a use case. | AI use-case and dependency inventory | AIMS scope, impact assessment and lifecycle controls |
| AUTH-01 | Appoint executors, accountable owners and qualified independent reviewers; record conflicts and escalation rights. Existing role labels are proposals, not appointments. | Authorized responsibility and independence records | Control execution and substantive review |
| RISK-01 | Approve risk criteria, service/recovery objectives, operational thresholds and treatment authority after reviewing proposed designs. | Risk criteria, BIA and treatment decisions | Local configuration, test criteria and residual-risk decisions |
| SCOPE-01 | Confirm actual assessment boundaries, reporting period and customer/provider responsibility splits with the intended assessor. | Agreed scope, period and responsibility matrix | Period coverage and external assessment preparation |
| SOA-01 | Decide necessary ISO controls and justified exclusions from actual risks and obligations, including necessary controls outside Annex A. | Risk treatment and Statements of Applicability | Accepted applicability; selecting a framework alone does not decide necessity |
| DISC-01 | Identify permitted customer claims, recipients and disclosure restrictions. | Approved assurance claims and disclosure rules | Customer assurance package |

## Review work the implementation team should finish first

Every inventoried attribute has a source-linked coverage workpaper. Reviewers should decompose exact source conditions and record actors, triggers, exceptions, outputs and assessment context. Compare each candidate procedure and supplement against those conditions. A source hash proves which bytes were used, not authenticity, currency, normative completeness or semantic agreement.

For SOC 2, examine the criteria and description criteria in context; points of focus are not automatically mandatory control rows. For HIPAA, paragraph-level duties, definitions, exceptions, contractual roles and current legal status remain review gates. For ISO, include management-system clauses, context and applicable annex guidance; Annex A consideration is not automatic mandatory applicability. For C5, inspect basic, sharpened and complementary criteria and the customer/provider interface.

The generated packet reports inventory routing and draft-design availability only. It does not enter source, mapping or evidence approvals into the assessment engine. Record qualified review through that engine's existing version-bound review workflow after factual decisions are available. Preserve failed and unresolved outcomes.
