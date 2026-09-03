# ALEXANDRIA INFORMATION ACCESS AND DISCLOSURE

**Document ID:** `SH-J2-ALX-DISCLOSE-001` | **Version:** 1.0.0 | **Effective:** September 2, 2026 | **State:** LOCKED ARCHITECTURAL DIRECTION

Alexandria implements Sable Harbor's doctrine of maximum useful visibility and minimum necessary restriction. The default is open. Restriction follows the nature of information—not rank—and may include personal information, legal privilege, active M&A, narrowly compartmented regulated/federal material, and other genuinely protected classes.

Questions are common property. The question remains visible whenever lawful even if evidence or an answer is restricted. Questions propagate wider than answers. Where appropriate, a user may see “Relevant material exists but is restricted” without receiving content, identity, quantity, or inference that defeats the restriction.

Restriction creates work: named owner, reason/class, scope, review/challenge route, start/effective time, reconsideration trigger or duration, and lawful disposition. Security and IAM implement these decisions; they do not redefine the information doctrine as generic least privilege.

Collection is Pinakes' most heavily provisioned portal because raw material may expose personal, privileged, regulated, commercially sensitive, or source-protection concerns. Other portals separate broad visibility of questions/current judgments from entitlement to underlying evidence.

Daedalus has universal institutional read authority and bounded disclosure authority. It can know restricted material exists and is relevant but cannot quote, summarize, confirm, deny, aggregate, compare, visualize, or infer restricted content for an unauthorized user. The policy layer evaluates direct and inferential disclosure in the requesting user's context. Model/tool access never substitutes for user entitlement.

Exact runtime roles, policy engine, redaction mechanism, audit events, inference-leakage tests, and raw Collection entitlements remain OPEN implementation. The architecture must demonstrate them before claiming operational enforcement. An access failure that prevented knowledge from reaching an entitled person is studied as an intelligence-system failure, not merely an IT ticket.
