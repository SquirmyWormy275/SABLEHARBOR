# TECHNOLOGY SERVICES DOCTRINE

**Document ID:** `SH-HQ-TECH-001` | **Version:** 1.0.0 | **Effective:** September 3, 2026 | **State:** LOCKED DIRECTION
**Owner:** Technology Services | **Related:** ESS, CISO/security, business engineering, CCF, Alexandria

## Purpose

Sable Harbor Technology Services is an internal technology and engineering organization, not a glorified help desk. Its products are employee computing, enterprise platforms, developer environments, infrastructure, AI capability, reliability, and the technology supply chain.

The operating standard is **restore capability, not close tickets**. If five hundred people repeatedly need the same support action, that is treated as a product defect rather than successful ticket volume.

## Customer-zero and internal-product model

Technology Services treats employees and internal engineering teams as customers. It runs and improves enterprise platforms with the same seriousness expected of customer-facing technology. Product engineering for Sable Harbor businesses remains with those businesses; corporate Technology Services owns the paved road beneath them.

The practical product lines include:

- employee technology and experience;
- enterprise platforms;
- developer platform and engineering systems;
- cloud and compute infrastructure;
- enterprise AI and automation;
- technology architecture and supply-chain stewardship;
- reliability and service engineering.

## Standards and freedom

Standardize the foundation hard and keep the edges soft. Secure baselines, identity, source-control ownership, cloud foundations, CI/CD interfaces, backups, and critical architecture may be standardized. Tool choice at the edge should remain flexible where consequence is low.

Approved software means supported, not merely allowed. The paved road should be excellent enough that most people choose it voluntarily. Shadow IT is treated first as signal that the paved road may be missing capability, not as evidence of employee disobedience.

The burden of proof sits with restrictions on autonomy. IT may restrict tools, permissions, or architectures when it can articulate a material institutional reason. Friction scales with consequence, not with the existence of a policy.

Technical staff may receive elevated workstation authority where appropriate to the role and threat model; security is engineered around that reality rather than assuming every employee device must be equally constrained.

## Procurement and third parties

Technology Services manages third-party dependencies, enterprise SaaS, major infrastructure vendors, and technology supply-chain risk. Low-risk, low-dollar purchases should follow team judgment. Material spend, sensitive data, significant integration, or hard-to-reverse commitments receive proportionate review. Procurement must not make the low-risk path so painful that rational employees route around it.

## Security

Security is strong and low-theater. The CISO has independent standing and is not reduced to IT operations. The default security answer is **yes, securely**. When Security must say no, it also owes a viable path where one exists.

Controls are engineered into architecture instead of depending on humans being perfect. Monitoring focuses on systems and threats rather than employee surveillance. Blameless incident learning is the default; malice or clear recklessness remain accountable. Red teams exist to break attack chains and improve architecture, not to catch employees in tricks.

The better the environment is engineered, the fewer human-facing controls should remain. Accumulating employee-visible security rituals is treated as a signal of architecture debt.

## Resilience

Resilience is an operating capability rather than a binder. Technology Services designs for failure, identifies what must continue, defines meaningful recovery objectives, performs restoration tests, and exercises real response. Backup success is not restoration evidence.

Third-party dependency resilience includes credible exit, replacement, and recovery thinking for consequential vendors. Critical systems cannot depend on a single human holding the only usable knowledge or keys. Crisis authority can temporarily narrow and accelerate; it remains temporary and is reviewed afterward.

## AI and data

Sable Harbor uses a tiered AI capability rather than forcing one model class everywhere. Small/local models can handle bounded private or predictable tasks; hosted enterprise models can serve controlled internal workloads; frontier models may be used where capability materially matters. Employees should encounter a coherent Sable Harbor AI environment rather than having to personally reason about routing, sandboxing, and data boundaries every time.

AI governance follows **data, capability, authority, and consequence**, not the presence of the AI label. A read-only summarizer can be low consequence; a conventional script with production write authority can be high consequence. Business stewards retain context for their data. Central technology supplies infrastructure and controls.

Every actor has a distinct identity: people, services, devices, and agents. AI agents receive their own identity and explicit delegation. They never silently inherit the full authority of the human using them. Delegation narrows; it does not expand. Break-glass access is time-bounded and conspicuously reviewed.

Evidence is generated to prove consequential controls and authorities without retaining every employee interaction merely because storage is cheap. The Common Controls Framework defines what must be evidenced; Technology Services makes the evidence reliable by design. Detailed ITGC and CCF implementation remains a separate downstream workstream.

## IT talent

Because Technology Services is an engineering organization, its technical careers are not second-class corporate-support roles. It supports apprenticeships, deep technical ladders, principal/fellow-level careers, rotations, and professional development without forcing technical excellence into management.
