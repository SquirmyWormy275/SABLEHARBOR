# SABLE HARBOR — FULL-STATE CODEX IMPLEMENTATION HANDOFF

**Package ID:** `SH-ARU-RW-PS-CODEX-HANDOFF-2026-09-05-R2`  
**Revision:** R2 — execution, commit, push, and merge authority corrected; R1 is superseded.  
**Decision cutoff:** September 5, 2026  
**Scope:** Pale Sun, Red Wash, American Resource Utility, Blood, Sweat & Tears Railway, both acquisitions, the post-acquisition operating model, the Taylor interface, all associated geography, models, narrative, evidence, graphics, and the participant-facing M&A case.  
**Purpose:** This is the implementation authority and state transfer for Codex. It is intentionally redundant. It is not a short recap.

---

# 0. READ THIS BEFORE TOUCHING THE REPOSITORY

Read this entire handoff before editing any file. Do not skim it, compress it, or replace it with a self-authored plan. The user spent several hours closing decisions one by one. Your job is to **implement the settled state**, engineer the specifically authorized bounded details, reconcile every conflicting repository artifact, and produce a clean, validated closeout package.

The core operating rule is:

> A decision made in chat is not a deliverable and is not canonical merely because it was said. It becomes the source of truth only after it is correctly implemented in the repository, classified, validated, and incorporated into the controlled canon. Over-document rather than under-document, but keep the result organized.

## Repository execution and delivery authority

This handoff is the user's explicit authorization to **implement and deliver the completed work to GitHub**. Codex is authorized to:

- inspect `main`, relevant branches, draft PR #95, repository history, CI, and existing generated artifacts;
- create or reuse a clean implementation branch;
- add, modify, rename, archive, and generate every file required by this scope;
- run migrations, builds, renderers, tests, validators, reconciliation checks, and deterministic rebuilds;
- commit the completed implementation;
- push the implementation branch to the remote;
- open or update a pull request when that is the practical or repository-required delivery mechanism;
- resolve merge conflicts and CI failures rather than stopping at a review checkpoint;
- merge the fully reconciled and validated implementation into `main`;
- push the resulting `main` revision;
- close, supersede, or replace draft PR #95 after harvesting only the portions that survive reconciliation.

A pull request is optional delivery plumbing, **not a user-approval gate**. Do not stop with work merely local, committed but unpushed, sitting in a draft PR, or described as “ready for review.” The requested end state is a clean repository with the complete package implemented, validated, merged into `main`, and pushed.

Use ordinary non-destructive Git operations. Do not force-push or rewrite published history, and do not delete unrelated branches. If branch protection requires a PR, use it and complete the merge. Only a genuine external blocker—such as missing credentials, unavailable remote access, or an irreconcilable repository failure—may prevent delivery; report exact evidence if that occurs.

Draft PR #95 is not canonical merely because it exists, and it must not be blindly merged. Its earlier creation without authorization is historical context, not a prohibition on the **currently authorized** implementation workflow. Inspect it, reconcile it, reuse only valid material, and then dispose of it cleanly as part of delivery.

Codex must not fabricate government-issued formation certificates, business licenses, tax approvals, or regulator filings. It may create clearly labeled synthetic corporate records, board approvals, transaction instruments, internal formation packages, and filing-ready drafts where this handoff authorizes them.

**Override:** Any earlier “no PR,” “no push,” “no merge,” or “wait for authorization” wording embedded in the appended reconciliation reports applies only to those earlier reconciliation passes. It is superseded by this R2 execution authority.

## Source hierarchy

When sources conflict, apply this order:

1. The latest explicit user decisions in this handoff.
2. Existing locked canon that does not conflict with those decisions.
3. Directly derived arithmetic and engineering needed to implement the locked decisions.
4. Earlier provisional models and draft branches as reusable evidence only.
5. Real-world official sources for laws, regulations, unions, geography, rail standards, federal nuclear programs, and technical benchmarks.
6. Older assistant proposals only if they are expressly preserved here.

Do not silently reopen decisions because the current repository still labels them `OPEN`. Do not silently promote an implementation choice to canon without recording its derivation and state.

## Required state labels

Use explicit epistemic and canon states throughout:

- `LOCKED_CANON`
- `LOCKED_DERIVED_IMPLEMENTATION`
- `PROVISIONAL_ASSUMPTION`
- `BOUNDED_IMPLEMENTATION_AUTHORIZED`
- `OPEN_GATED`
- `SUPERSEDED_PRESERVED`
- `REFERENCE_ONLY`

Every newly engineered customer, employee, locomotive, bridge, contract, accident, facility, rate, or exact coordinate must carry provenance showing whether it is locked, derived, externally researched, or synthetic.

---

# 1. IMPLEMENTATION OBJECTIVE

Build one coherent, enterprise-grade Sable Harbor package that closes and reconciles four connected bodies of work:

1. **Pale Sun Inc.** — the nuclear-materials platform, its origin inside J2, its founder/president Evan Vilander, its relationship to Alexandria, its organization, federal and commercial mandate, and its first operating asset.
2. **Red Wash Mining, LLC** — the selected mine case, corrected geography, legal identity, Northstar sale, operating model, technical record, maps, contracts, economics, and relationship to Pale Sun.
3. **American Resource Utility, Inc.** — the acquired industrial-logistics platform, seller group, transaction, terminals, trucking, warehousing, employees, customers, facilities, assets, and financial statements.
4. **Blood, Sweat & Tears Railway Company** — the wholly owned shortline, historical spine, route and facility GIS, equipment, labor, safety history, bridge/culvert inventory, customer traffic, rates, operating plan, and Red Wash interface.

The package must also create a **point-in-time M&A participant case study** in the same substantive pattern as Blackridge. It must not dump the whole SABLEHARBOR repository on a participant. It must not place evaluator truth in this repository. The private evaluator side remains in the separate `SABLEHARBOR-ALEXANDRIA-CONTROL` repository.

This is not a redesign exercise. Do not change names, economics, relationships, or intent merely because another arrangement appears cleaner.

---

# 2. CONTROLLING CORPORATE AND LEGAL STRUCTURE

Implement the following structure. Where the placement through the intermediate is described as derived, it is the required coherent implementation of the separately locked ownership decisions.

```text
Sable Harbor, LLC
Delaware limited liability company
Headquarters: Sacramento, California
Registered/qualified in California as an out-of-state (“foreign”) LLC
│
└── Sable Harbor Industrial Holdings, Inc.
    Delaware C corporation
    Permanent intermediate for industrial acquisitions
    │
    ├── Pale Sun Inc.
    │   Delaware C corporation
    │   Nuclear-materials platform
    │   │
    │   └── Red Wash Mining, LLC
    │       Wyoming limited liability company
    │       Owner/operator of the Red Wash Mine
    │
    └── American Resource Utility, Inc.
        Wyoming corporation
        Acquired January 7, 2026
        │
        └── Blood, Sweat & Tears Railway Company
            Wyoming corporation
            Wholly owned by ARU
            STB Class III common-carrier shortline railroad
```

## 2.1 Sable Harbor legal identity

Lock and implement:

- Legal name: **Sable Harbor, LLC**.
- Form: Delaware limited liability company.
- Headquarters: Sacramento, California.
- California status: registered/qualified to do business as a foreign LLC. “Foreign” means organized in another U.S. state, not a non-U.S. company.
- The stable internal entity code `SHI`, if deeply embedded, may remain as a legacy technical identifier. It must no longer be presented as proof that the legal name ends in “Inc.” Document that distinction rather than breaking every historical key unnecessarily.
- Actual Delaware and California filing replicas, certificates of formation, business licenses, and government-issued documents were expressly deferred to a separate chat. Do not fabricate them here.

## 2.2 Industrial holding company

Lock and implement:

- **Sable Harbor Industrial Holdings, Inc.**
- Delaware C corporation.
- Wholly owned by Sable Harbor, LLC.
- Permanent intermediate, not a one-off ARU shell.
- It is the corporate buyer in the ARU stock acquisition and the durable ownership home for the industrial platforms.

## 2.3 Pale Sun legal identity

This supersedes prior language saying Pale Sun is only a business-line label and not a legal entity.

Lock and implement:

- **Pale Sun Inc.**
- Delaware C corporation.
- Wholly owned by Sable Harbor, implemented beneath Sable Harbor Industrial Holdings, Inc. so that Pale Sun and ARU are sister industrial platforms.
- Pale Sun remains both a platform brand and a legal company.
- Pale Sun owns 100% of Red Wash Mining, LLC.

## 2.4 Red Wash legal identity

Lock and implement:

- **Red Wash Mining, LLC**.
- Wyoming limited liability company.
- Owns/operates the Red Wash Mine and its permits, workforce, mine assets, mill, inventory, liabilities, and contracts.
- Wholly owned by Pale Sun Inc. after the July 18, 2025 transaction.
- Pale Sun is not a substitute name for the mine operator; the two must have separate books, roles, and authority.

## 2.5 Northstar seller identity

Lock and implement:

- **Northstar Minerals, Inc.**
- Abbreviation: **NMI**.
- Wyoming corporation.
- Long-tenured owner/CEO and principal seller: **Henry Norwood**.
- NMI is the Red Wash seller. It is not the ARU seller.
- Supersede “Northstar Resources,” “Northstar Resources, Inc.,” and any other seller legal name.

## 2.6 ARU and BS&T legal identity

Lock and implement:

- **American Resource Utility, Inc.** — Wyoming corporation.
- **Blood, Sweat & Tears Railway Company** — Wyoming corporation, wholly owned by ARU.
- BS&T is an STB Class III common-carrier shortline.
- ARU remains a distinct operating company during integration.
- BS&T retains its identity, personnel, operating rhythm, and regulatory responsibilities.

---

# 3. NAME AND ROLE CONTROLS

These spellings and distinctions are mandatory.

| Subject | Controlling identity/role |
|---|---|
| Sable Harbor principal steward/founder | **Daniel Mercer** |
| Red Wash transaction lead on Sable Harbor side | **Martin Shaw** |
| Red Wash seller and NMI owner/CEO | **Henry Norwood** |
| ARU seller-group lead and long-time CEO/controlling shareholder | **Fred Tolman** |
| Pale Sun originator and president | **Evan Vilander** |
| Pale Sun/Red Wash senior mining operator | **Marianne “Mari” Varela** |
| Retired Red Wash geologist/source | **Walt Sutter** |

Mandatory corrections:

- `Vilander`, not `Vylander`.
- `Vilander`, not `Rylander`.
- Evan was a **J2 Judgment Officer**, not a judge advocate.
- Fred Tolman replaces the discarded `Huck Lamb` proposal.
- Northstar Minerals, Inc. replaces Northstar Resources, Inc.
- Daniel Mercer resolves the surname collision. A document that omitted his surname did not establish a competing identity.

## 3.1 Martin Shaw

Martin Shaw is canonical. He is the Red Wash transaction lead on the Sable Harbor side. His role is to separate transaction authority from Mari Varela’s technical and operating ownership. Evan Vilander originates and develops the Pale Sun thesis; Martin Shaw executes the formal transaction process. Do not collapse those roles.

## 3.2 Mari Varela and Evan Vilander role reconciliation

Earlier canon described Mari as the Pale Sun leader. Later explicit decisions establish Evan Vilander as the founder/originator who earns the Pale Sun presidency. Preserve both people and their actual authority by implementing a clear two-axis structure:

- Evan Vilander owns the Pale Sun platform thesis, strategic development, federal and downstream interface, capital case, acquisitions, and company-building mandate.
- Mari Varela owns substantive mining and technical operating authority for Red Wash, including hostile kill-study discipline, mine protection, and the rule “Pale Sun first; proving ground second.”
- Assign coherent titles that preserve those authorities. The recommended implementation is Evan as `President, Pale Sun Inc.` and Mari as `Chief Operating Officer, Pale Sun Inc.` plus `President/Chief Executive, Red Wash Mining, LLC`, but title wording is a bounded implementation choice. Do not demote Mari to an adviser and do not erase Evan’s presidency.
- Document the supersession of the former generic “Pale Sun leader” phrasing.

---

# 4. TWO SEPARATE ACQUISITIONS — DO NOT CONFLATE THEM

There are two different deals with different sellers, dates, economics, escrows, purposes, and transaction teams.

## 4.1 Red Wash acquisition

- Target: Red Wash Mining, LLC / Red Wash operating company.
- Seller: Northstar Minerals, Inc.
- Seller principal: Henry Norwood.
- Buyer/platform: Pale Sun Inc. / Sable Harbor.
- Close: **July 18, 2025**.
- This deal creates Pale Sun’s first operating asset.

## 4.2 ARU acquisition

- Target: 100% of American Resource Utility, Inc.
- Seller group: private shareholder group led by Fred Tolman.
- Buyer: Sable Harbor Industrial Holdings, Inc.
- Close: **January 7, 2026**.
- This deal acquires an independently viable industrial logistics company and its wholly owned railroad.

Do not merge the Henry Norwood/NMI seller story with the Fred Tolman/ARU seller story. Do not reuse one deal’s $3.0 million escrow as the other deal’s escrow.

---

# 5. RED WASH SELECTED CASE — PRESERVE AND UPDATE

Preserve the existing selected Red Wash case except where this handoff explicitly supersedes geography, legal identity, ownership, or downstream integration. The Red Wash package remains a synthetic but internally controlled operating record.

## 5.1 Geography

The canonical location is:

- Great Divide Basin / Red Desert.
- Sweetwater County, Wyoming.
- North of Wamsutter.
- Working GIS anchor: **42.2200° N, 108.1800° W**.
- The mine is fictional inside real geography.

Superseded location:

- Carbon County.
- 42.3127° N, 106.9213° W.

Required treatment:

1. Preserve every existing Carbon County map and derivative as a hashed, superseded historical original.
2. Do not overwrite the old bytes in place and destroy provenance.
3. Generate corrected current maps for the Sweetwater County/Great Divide Basin location.
4. Update all current-state casebooks, JSON, database seeds, maps, captions, diagrams, org packages, manifests, controlled publications, and links.
5. Add explicit supersession metadata linking old to new.
6. Search the full repository for the old coordinates, Carbon County, and map-derived statements. No current-state artifact may continue to assert the superseded location.

## 5.2 Red Wash transaction economics already selected

Preserve unless an explicit current repository record proves a later user decision:

| Item | Selected amount |
|---|---:|
| Operating assets | $42.0M |
| Current assets | $4.5M |
| Assumed ARO | $16.0M |
| Other assumed liabilities | $2.5M |
| Cash consideration | $28.0M |
| Goodwill | $0 |
| Transaction debt | $0 |
| Environmental/title escrow | $3.0M |
| Holdback | $0.5M |
| H2 2025 stabilization program | $11.0M |
| Capitalized rehabilitation | $8.0M |
| Repair/stabilization expense | $3.0M |

The Red Wash $3.0M escrow is separate from the ARU $3.0M escrow.

## 5.3 Resource and mine basis

Preserve the selected operating case:

- Indicated resource: 2.5 million short tons.
- Indicated grade: 0.17% U3O8.
- Contained U3O8: 8.5 million lb.
- Modeled recovery: 92%.
- Recoverable U3O8: 7.82 million lb.
- Inferred resource: 0.9 million short tons at 0.145% U3O8.
- Inferred material is not included in the base valuation.
- Mining method: selective drift-and-fill with cemented paste backfill.
- Planned depth: approximately 2,500 ft.
- Nameplate: approximately 600 tons/day.

## 5.4 2026 selected operating case

| Measure | Selected result |
|---|---:|
| Ore mined/processed | 175,000 short tons |
| Head grade | 0.17% U3O8 |
| Contained uranium | 595,000 lb U3O8 |
| Recovery | 92% |
| Produced | 547,400 lb U3O8, commonly summarized as ~550,000 lb |
| Opening finished inventory | 125,000 lb |
| Sold | 500,000 lb |
| Ending finished inventory | 172,400 lb |
| Total FTE | 140 |
| Pale Sun/platform layer | 12 |
| Red Wash site | 128 |

Site function allocation to preserve/reconcile:

- Site general management: 1.
- Underground operations: 44.
- Maintenance/reliability: 22.
- Mill/metallurgy: 24.
- Geology/resource control: 8.
- Safety/radiation: 7.
- Environmental/permitting: 6.
- Supply/warehouse: 6.
- Site finance/people/administration: 6.
- Security/medical/emergency: 4.

If Pale Sun’s newly formalized corporate team requires reclassification of the 12-person platform layer, preserve the total 140 and explicitly bridge old to new rather than silently changing the headcount.

## 5.5 Red Wash production trajectory

Lock the three-case scaffold:

| Case | Ore throughput | U3O8 production | State |
|---|---:|---:|---|
| 2026 rehabilitation/selective case | 175,000 tons | 547,400 lb / ~550,000 lb | Locked selected case |
| Normalized target | 225,000 tons | approximately 700,000 lb; direct formula at 0.17% and 92% gives 703,800 lb | Locked planning target; exact target year remains implementation-derived |
| Future expansion option | 300,000 tons | approximately 880,000 lb with some grade dilution | Locked option, not committed production |

Do not convert the normalized or expansion cases into historical production.

## 5.6 Red Wash 2026 commercial and financial data

Preserve the selected contract book and economics unless a current locked repository record contains an explicitly later decision:

Contracts:

1. `UCA-2019-04` — Prairie States Electric Cooperative — 150,000 lb at $61/lb — base-escalated utility term — inherited — delivery to licensed conversion facility in Illinois — consent obtained.
2. `UCA-2024-11` — Great Basin Nuclear Supply Pool — 150,000 lb at $72/lb — market-related utility term collar — inherited — Illinois licensed conversion facility — change-of-control notice satisfied.
3. `UCA-2025-03` — Heartland Atomic Power LLC — 125,000 lb at $80/lb — fixed-price term — inherited and renegotiated — Illinois licensed conversion facility — consent obtained.
4. `SPOT-2026-01` — Continental Nuclear Trading LLC — 75,000 lb at $87/lb — discretionary placement — Pale Sun originated — Illinois licensed conversion facility.

Selected 2026 finance:

| Measure | Amount |
|---|---:|
| Weighted realized price | $72.95/lb |
| Revenue | $36.475M |
| Cash production cost incurred | $27.950M |
| Production/mineral taxes | $2.125M |
| Royalties | $0.7295M |
| Freight, assay and handling | $0.600M |
| Pale Sun/site G&A | $2.800M |
| ARO accretion | $1.040M |
| Sustaining capex | $4.000M |
| Rehabilitation capex | $5.000M |

Preserve the selected composite units-of-production DD&A model as a model proposal, not audited GAAP fact. Preserve opening finished inventory cash cost of $45/lb, opening DD&A of $5.50/lb, 18% modeled income tax rate, and $550,000 other working-capital use as scenario inputs unless later locked values exist.

## 5.7 Closure and liability basis

Preserve:

- Current closure cost: $25.0M.
- Opening ARO: $16.0M.
- Inflation: 2.5%.
- Discount rate: 6.5%.
- Cash-flow horizon: 2026–2039.
- Scope: progressive reclamation; underground sealing/demobilization; mill decontamination and demolition; tailings final cover; water management; monitoring; long-term surveillance transfer.

## 5.8 Existing Red Wash diligence spine

Preserve and reconcile the existing diligence findings, including at minimum:

- smoothed East 12 lens boundaries and overstated continuity;
- inconsistent historic dilution/cutoff treatment;
- nonlinear acid/recovery response for carbonate-rich feed;
- tailings Cell 1 underdrain and MW-17 trends;
- omitted monitoring and mill-demolition ARO scopes;
- maintenance backlog exceeding seller schedule;
- inadequate main exhaust fan/control redundancy;
- motor-control-center obsolescence;
- drum ledger moisture/assay timing inconsistencies;
- contract escalation reference-month error;
- incomplete change-of-control consents;
- East 12 royalty step-up;
- predecessor-name easement/title issues.

Do not sanitize the diligence record merely because the acquisition closes.

---

# 6. PALE SUN — PURPOSE, HISTORY, AND OPERATING MANDATE

Pale Sun is not a discarded alias and not merely an exploration banner. It is a real Sable Harbor company with real work.

## 6.1 Core purpose

Pale Sun Inc. is Sable Harbor’s specialized platform for:

- uranium and nuclear-materials strategy;
- uranium commercialization and offtake;
- federal and strategic-program interfaces;
- downstream conversion, enrichment, fabrication, utility, and trading partnerships;
- domestic nuclear-fuel-chain intelligence and opportunity development;
- future acquisitions and investments across the nuclear-materials chain;
- ownership and stewardship of Red Wash Mining, LLC.

Pale Sun begins lean. It must have a credible path to grow beyond one mine, but it must not claim to own or operate conversion, enrichment, or fabrication facilities unless separately acquired, licensed, and implemented.

## 6.2 Federal boundary

Pale Sun may interface with U.S. federal nuclear-fuel and domestic-supply programs, but do not silently turn it into:

- a federal agency;
- an enrichment operator;
- a conversion licensee;
- a fuel fabricator;
- a government-owned contractor;
- a FedRAMP-authorized cloud company;
- a separate “Federal Systems LLC” unless separately authorized.

Codex must use current official sources to develop a cited federal-program and market-interface brief. It should identify real procurement, consortium, stockpile, domestic conversion/enrichment, utility, and strategic-supply pathways that a company like Pale Sun could lawfully pursue through contracts, partnerships, investment, market intelligence, and acquisitions. Every real-world statement needs an official citation and retrieval date.

## 6.3 Pale Sun slogan

No Pale Sun slogan was locked. Do not fabricate one as canon. A proposed tagline set may be included in a clearly marked `PROPOSAL` appendix, but the existing name and logo control.

## 6.4 Pale Sun logo

The canonical Pale Sun logo already exists and was explicitly preserved. Do not regenerate or replace it.

A prior voice response stated that it was the “third standalone concept” and gave the hash-like string:

```text
eedcabfca73460e8ff5ad72864c9f669ba2375097daa2912f30c9ff35c025
```

That string is only 61 hexadecimal characters, so it is not a valid SHA-256 digest. Treat it as a corrupted transcript record. Locate the current canonical Pale Sun asset in the repository, compute its actual SHA-256, reconcile it to the existing manifest, and preserve exact bytes. Record the correction transparently; do not pretend the corrupted string was valid.

---

# 7. EVAN VILANDER — CANONICAL ORIGIN AND CAREER ARC

## 7.1 Identity

- Name: **Evan Vilander**.
- Nationality: South African.
- Prior career: contracted security specialist.
- Prior employer: a South African security company called **BTC**.
- The expansion and exact legal name of `BTC` were not established. Do not invent an expansion without clearly marking it as a bounded implementation choice.
- BTC work included contracted security across South Africa for resource-management clients and wealthy private citizens.
- He was on a plausible track to eventually run BTC.
- Sable Harbor offered him more compensation to join as a J2 Judgment Officer than he expected to earn taking over BTC.

## 7.2 How Sable Harbor found him

Do not write that Sable Harbor randomly found one of his reports. Do not invent a Sable Harbor security contract in South Africa.

The canonical recruitment mechanism is:

1. Sable Harbor’s talent system deliberately searches nontraditional candidate pools for Judgment Officer traits: claims investigators, intelligence analysts, journalists, security professionals, and adjacent roles.
2. Vilander enters that pool based on his operating/security background.
3. The decisive assessment gives him a messy case with contradictory evidence and no clean answer.
4. Most candidates try to “solve” it. Vilander instead distinguishes what is known, what is not known, what would change his mind, and what action he recommends despite uncertainty.
5. That reasoning pattern—not pedigree or a lucky report—causes Sable Harbor to recruit him.

This is a proof that Sable Harbor’s talent system works as intended.

## 7.3 Progression bounds

The user approved this general progression:

- He is in his late 30s in 2026, approximately 38.
- Birth year therefore falls around 1987–1988. Exact date is a bounded implementation detail, not yet locked.
- He spends roughly a decade or more at BTC, progressing from field work into operations, client risk, and management responsibility.
- Sable Harbor recruits him around 2021.
- From 2021 through roughly 2023 he is a competent, credible Judgment Officer but not an instant star. He needs ordinary repetitions and institutional trust.
- The uranium/fuel-chain thread begins in 2023 or 2024.
- Pale Sun is formed in late 2024 or early 2025, before the Red Wash close.
- Red Wash is acquired in July 2025.
- Vilander earns the Pale Sun presidency in late 2025 after proving he can build and lead, not merely identify an opportunity.
- In 2026 he runs Pale Sun while still young for the role but no longer implausibly inexperienced.

Codex is authorized to choose exact dates inside those bounds, but every exact date must be recorded as `LOCKED_DERIVED_IMPLEMENTATION` and must not conflict with the Red Wash and ARU transaction timeline.

## 7.4 The uranium thread

Vilander does not begin with a grand top-down thesis that Sable Harbor should vertically integrate uranium.

The trigger is routine J2 judgment work on a supply-chain dependency that happens to touch uranium. He asks simple questions and follows them further than required:

- Who are we selling uranium to?
- Who would buy it?
- What happens at the next step?
- Who can actually perform that step?
- Where does control sit?
- What is the real bottleneck?
- Why does the company keep treating each link as an isolated uranium issue when the constraint and opportunity exist across the fuel chain?

He uses Alexandria to combine disparate data, interviews, access, claims, and chronology. The system works as intended:

- he surfaces a consequential pattern;
- he brings it to his boss;
- the boss is not dismissive but does not personally seize and run the opportunity;
- the evidence moves through the proper internal portals;
- someone with the appropriate capital/enterprise authority recognizes the opportunity;
- Vilander is given room to keep developing it;
- he is eventually told, in substance, “then you run it.”

This is one of the champion historical cases for J2 and Alexandria. Alexandria does not “decide to buy uranium.” It preserves, connects, and tests the evidence so a human can own the decision.

## 7.5 Three required false starts

Build these as real dated case briefs with fictional names, artifacts, assumptions, dissent, kill criteria, and after-action lessons. They must not be generic bullet points.

### False Start 1 — downstream conversion/processing asset

A distressed downstream conversion or processing asset appears strategically ideal and undervalued. Vilander models it enthusiastically. Deeper diligence shows:

- required capital is far greater than represented;
- environmental liabilities are material;
- customer requalification timelines are brutal;
- essential capabilities cannot simply be purchased with the asset;
- the asset is cheap for a reason.

Vilander kills his own proposed deal when the facts change. Management begins remembering his name because he does not defend his thesis at the expense of reality.

### False Start 2 — Western uranium deposit

A western U.S. uranium property appears attractive:

- good headline grades;
- credible historic drilling;
- inexpensive entry price.

It fails because:

- time to production is much longer than expected;
- water and access issues are severe;
- processing assumptions do not hold;
- the seller’s case is materially optimistic.

Vilander improves: he brings specialists in earlier, separates geological confidence from commercial confidence, and does not let a low sticker price become the thesis.

### False Start 3 — outsourced judgment to one expert

Vilander recruits or relies heavily on a veteran uranium specialist with a strong résumé and network. He overweights that person’s judgment. Red flags are explained away as “how the industry works,” and Vilander defers when others challenge the thesis. The opportunity fails when the optimism proves personality-driven rather than evidence-driven.

The resulting rule is:

> Respect expertise. Never outsource judgment.

That lesson directly shapes his treatment of Henry Norwood and Red Wash. Norwood’s knowledge is valuable, but it is not treated as truth without testing.

## 7.6 Required Vilander/Pale Sun artifacts

Create:

- a dated Vilander biography and career timeline;
- a BTC background note with the unresolved legal-name boundary preserved;
- the Judgment Officer recruitment and assessment record;
- the initial uranium-thread case file;
- an Alexandria provenance/reconstruction record;
- the escalation and internal-portal history;
- three complete false-start case briefs;
- the Pale Sun founding memorandum;
- the “why you run it” appointment decision;
- Vilander’s promotion and authority record;
- a 2026 Pale Sun leadership profile;
- an AAR tying the three failures to the Red Wash acquisition discipline.

Use existing J2, Judgment Officer, Orientation, Alexandria, and governance doctrine. Do not invent a separate bureaucracy.

---

# 8. ARU ACQUISITION — LOCKED TRANSACTION

## 8.1 Date, seller, and ownership

- Baseline date: December 31, 2025.
- Close: **January 7, 2026**.
- Buyer: Sable Harbor Industrial Holdings, Inc.
- Target: 100% of American Resource Utility, Inc.
- Seller group: private eligible shareholder group led by long-time CEO and controlling shareholder **Fred Tolman**.
- No rollover equity.
- No earn-out.
- No synergy-dependent valuation.
- Fred Tolman has no post-close operating authority.

Codex is authorized to create a realistic pre-close shareholder register and cap table consistent with:

- Fred Tolman as controlling shareholder;
- minority family and/or management holders;
- ARU’s pre-close eligibility as an S corporation;
- every shareholder being eligible and participating in the joint §338(h)(10) election;
- 100% sale at close;
- no rollover.

Do not create ineligible corporate shareholders that break the elected tax structure.

## 8.2 Purchase price and closing math

Lock and reconcile exactly:

| Item | Amount |
|---|---:|
| Enterprise value | $62.0M |
| Pre-close term/equipment debt | $11.5M |
| Pre-close drawn revolver | $2.0M |
| Finance leases | $2.5M |
| Gross pre-close debt | $16.0M |
| Pre-close cash | $3.5M |
| Net debt | $12.5M |
| Seller equity value | $49.5M |
| Minimum cash retained in ARU | $2.0M |
| Excess-cash bridge | $1.5M |
| Buyer-funded purchase consideration | $48.0M |
| Cash paid directly at close | $45.0M |
| Escrow | $3.0M |
| Debt refinanced at close | $13.5M |
| Finance leases retained | $2.5M |
| New acquisition debt | $22.5M |
| Sable Harbor equity before fees | $39.0M |
| New revolving capacity | $5.0M |
| Revolver draw at close | $0 / essentially undrawn |

Reconciliation:

```text
$62.0M EV - $12.5M net debt = $49.5M seller equity value
$49.5M equity value - $1.5M excess-cash bridge = $48.0M buyer-funded purchase consideration
$48.0M consideration = $45.0M cash at close + $3.0M escrow
$48.0M consideration + $13.5M debt refinancing = $61.5M buyer-funded close uses before fees
$61.5M uses - $22.5M new acquisition debt = $39.0M Sable Harbor equity before fees
```

Additional locked terms:

- Normalized working-capital peg excluding cash and debt, with dollar-for-dollar true-up.
- 18-month general survival.
- Longer environmental survival.
- Known $1.5M–$2.0M environmental reserve treated as operating reality.
- Seller protection for undisclosed environmental matters.
- Seller covers adverse development above the recorded accrual for the identified larger claim.
- Seller CEO transition: nine months through approximately October 7, 2026.
- Seller CEO consulting compensation: $225,000 total.
- Management retention pool: $500,000 over 12 months, half at six months and half at 12 months.
- Separate $11.0M catch-up capital funded with Sable Harbor equity, not acquisition debt.

## 8.3 Tax structure

Lock the intended structure:

- 100% stock purchase by Sable Harbor Industrial Holdings, Inc.
- ARU is an eligible S corporation immediately before close.
- All eligible selling shareholders participate.
- Buyer and sellers make a joint Internal Revenue Code §338(h)(10) election.
- The acquisition is legally a stock purchase while receiving deemed asset-sale tax treatment.
- ARU’s S status terminates when acquired by the corporate buyer and it continues post-close as a wholly owned corporate subsidiary.

Codex must create a cited tax-structure memorandum based on current official IRS authority. It must state all eligibility assumptions and distinguish synthetic deal facts from actual law. Do not present the memo as legal or tax advice.

---

# 9. ARU 2025 OPERATING AND FINANCIAL BASELINE

This segment bridge was already completed. Do not reopen it as a new decision.

## 9.1 Consolidated baseline

| Measure | Locked baseline |
|---|---:|
| Revenue | $42.000M |
| Operating expense before D&A | $32.200M |
| Normalized EBITDA | $9.800M |
| EBITDA margin | 23.33% |
| FTE | 131 |
| Sustaining capex | $3.300M |
| EBITDA less sustaining capex | $6.500M |
| Deferred catch-up capex | $11.000M |

## 9.2 Segment bridge

| Segment | Revenue | EBITDA | Margin | FTE | Sustaining capex |
|---|---:|---:|---:|---:|---:|
| BS&T Railway | $15.500M | $1.500M | 9.68% | 58 | $2.050M |
| Industrial terminals/transload | $13.000M | $4.300M | 33.08% | 27 | $0.550M |
| Heavy industrial trucking/drayage | $7.500M | $1.500M | 20.00% | 24 | $0.480M |
| Warehousing/materials handling | $6.000M | $2.700M | 45.00% | 12 | $0.220M |
| ARU corporate/unallocated | $0 | $(0.200)M | — | 10 | $0 |
| **Total** | **$42.000M** | **$9.800M** | **23.33%** | **131** | **$3.300M** |

The nonrail margins, particularly warehousing/materials handling, must be supported by realistic contracts and operating drivers. Codex is authorized to build the supporting customer book; it is not authorized to change the total merely because support did not previously exist.

## 9.3 Customer concentration

Lock:

- Largest customer: approximately 11% of consolidated revenue, approximately $4.62M.
- Top five customers: approximately 40%, approximately $16.8M.
- One material renewal risk during diligence.
- Red Wash contributes $0 to ARU’s 2025 pre-acquisition external revenue.

## 9.4 Full financial implementation

Build the complete 2025 financial case, not only an EBITDA schedule:

- customer and contract register;
- monthly revenue/volume schedule;
- seasonality;
- pricing and accessorial schedules;
- working capital;
- accounts receivable and allowance;
- inventory, parts, fuel and materials;
- accounts payable/accruals;
- payroll and benefits;
- fixed assets and D&A;
- leases;
- debt and interest;
- taxes;
- reported-to-normalized EBITDA bridge;
- trial balance;
- income statement;
- balance sheet;
- cash-flow statement;
- acquisition-day opening balance sheet;
- purchase accounting/PPA layers as synthetic case data;
- intercompany eliminations;
- scenario and sensitivity schedules.

All schedules must reconcile to the locked totals and transaction math.

---

# 10. BS&T 2025 RAILWAY BASELINE

## 10.1 Operating physics

Lock:

- Approximately 40 total system route-miles.
- Five service/interchange days per week, approximately 260 per year.
- 9,000 annual loaded revenue carloads.
- Approximately 8,100 empty returns as a planning conversion.
- Approximately 17,100 total annual car movements.
- Approximately 65.8 total car movements per service day.
- Four locomotives owned.
- Three generally available.
- Two normally required.
- 58 employees.
- Targeted-capital incremental network capacity: approximately 5,000–7,500 additional annual revenue carloads.

The 5,000–7,500 figure is network capacity, not Red Wash demand.

## 10.2 Traffic and revenue schedule

Implement exactly or reconcile to exact arithmetic:

| Traffic class | Cars | Avg. rail revenue/car | Freight revenue |
|---|---:|---:|---:|
| Soda ash, trona and minerals | 3,150 | $1,375 | $4,331,250 |
| Energy and oilfield materials | 1,650 | $1,950 | $3,217,500 |
| Aggregates and construction | 1,350 | $1,250 | $1,687,500 |
| Industrial chemicals and metals | 1,050 | $1,925 | $2,021,250 |
| Agriculture and ranch supply | 750 | $1,300 | $975,000 |
| Transload, project and other | 1,050 | $1,635 | $1,716,750 |
| **Freight subtotal** | **9,000** | **$1,549.92 weighted avg.** | **$13,949,250** |
| Switching/accessorial/storage/demurrage | — | — | **$1,550,750** |
| **Total BS&T revenue** | **9,000** | **$1,722.22 total revenue/car** | **$15,500,000** |

This is an internal planning schedule, not a published tariff. The customer/contract register must substantiate it.

## 10.3 BS&T expense schedule

Implement:

| Expense class | 2025 expense |
|---|---:|
| Train and engine labor/benefits | $2.80M |
| Maintenance-of-way labor/materials | $2.15M |
| Mechanical labor, parts and contract work | $1.65M |
| Fuel and lubricants | $1.12M |
| Car hire and equipment leases | $0.76M |
| Purchased services/interchange handling | $0.45M |
| Insurance and claims | $0.95M |
| Property tax, regulatory and fees | $0.52M |
| Facilities, utilities and communications | $0.40M |
| Safety, environmental and compliance | $0.34M |
| Management, admin and customer service | $1.28M |
| ARU shared-services allocation | $0.83M |
| Other operating expense | $0.75M |
| **Total before D&A** | **$14.00M** |
| **Normalized EBITDA** | **$1.50M** |

BS&T EBITDA operating ratio: **90.32%**. Do not call ARU’s 76.67% expense ratio the railroad operating ratio.

## 10.4 BS&T employee census

Lock 58 and implement a named/anonymized employee census that reconciles to:

- Train and engine: 22.
- Maintenance of way: 10.
- Mechanical: 8.
- Operations/dispatch/customer service: 6.
- Safety/environmental/compliance: 3.
- Management/administration: 9.

The complete ARU employee census must reconcile to 131:

- BS&T: 58.
- Terminals/transload: 27.
- Trucking/drayage: 24.
- Warehousing/material handling: 12.
- ARU corporate/shared services: 10.

## 10.5 Labor agreements

Lock and implement:

- BS&T train-and-engine employees: property-specific SMART-TD collective bargaining agreement.
- BS&T maintenance-of-way employees: property-specific BMWED agreement.
- Do not assume national Class I terms.
- Mechanical, dispatch, management, administrative, terminal, trucking, warehouse, and ARU corporate personnel are nonunion unless a specific existing record proves otherwise.
- Existing CBAs survive the stock acquisition.
- Build realistic agreement summaries, represented crafts, seniority, crew rules, overtime, grievance, discipline, benefits, duration, reopening, and change-of-control treatment.
- Use current official union and regulatory sources for external facts.

## 10.6 Track class and speed

Lock:

- Main line and branches: FRA Class 2, 25 mph maximum freight speed.
- Yards, shops, and industrial spurs: FRA Class 1, 10 mph maximum.
- Lower temporary slow orders where condition requires.
- No blanket Class 3 upgrade.

Build a track-segment register with mileposts, class, speed, condition, rail weight, ties, surfacing, drainage, signal/authority method, owner, and capital need.

## 10.7 Locomotive and railcar roster

Locomotive count is locked:

- Four owned.
- Three generally available.
- Two normally required.
- No standing acquisition-day leased locomotive.

Codex is authorized to derive and canonize a realistic locomotive roster consistent with a 40-mile, 9,000-car shortline and the maintenance backlog. Include model, builder, year, horsepower, acquisition history, condition, availability, overhaul status, emissions treatment, ownership, and assigned service.

The exact railcar count was not separately locked. Build a modest controlled pool. Most traffic should move in customer-owned, private, or connecting-carrier equipment. Derive the owned/leased/service-car roster from customer and operating needs; do not backsolve a huge fleet from 9,000 cars.

## 10.8 Customer and contract register

Build a complete fictional but realistic register consistent with:

- six locked traffic classes;
- 9,000 annual cars;
- $15.5M BS&T revenue;
- $42.0M consolidated ARU revenue;
- approximately 11% largest consolidated customer;
- approximately 40% top-five concentration;
- one material renewal risk;
- independent pre-Red-Wash economics.

Each record must include stable ID, legal/display name, sector, commodity/service, segment, origin/destination, annual physical volume, annual revenue, contract type, term, pricing basis, escalator, minimum commitment, renewal date, credit status, margin, asset use, concentration, diligence risk, source/provenance, and fact state.

Do not use real customer names as if they were parties to the fictional case.

---

# 11. BS&T HISTORY, TAYLOR, AND BLOODSTONE

## 11.1 Geographic/naming controls

- The current fictional railroad town, shop, yard, and operating hub is **Taylor, Wyoming**.
- Wamsutter is the real-reference Union Pacific interchange corridor.
- `Bloodstone` is not the current town name.
- Bloodstone may remain in historical names such as Bloodstone Coal & Coke Company, Bloodstone No. 2, a coal field, or predecessor assets.

## 11.2 Historical spine to preserve

The conversation established a Wyoming coal-rooted history rather than the discarded Utah/Ballard & Thompson/Cane Creek concept. Preserve the following spine and reconcile exact wording against any existing canonical history:

- Bloodstone Coal & Coke Company as the early industrial parent.
- Thomas R. Bell as an early historical figure.
- Bloodstone & Southern Railway as the predecessor railroad identity.
- Labor organization by approximately 1909.
- Parent failure in 1953.
- Walt Mercer’s 1954 rescue/reorganization as the railroad’s institutional year zero.
- Survival with poor equipment, disappearing anchor traffic, payroll obligations, small creditors, and unglamorous freight such as clay, pipe, and scrap.
- Expansion through the 1960s–1970s into transload pads, warehouses, materials handling, and careful custody/handoff work.
- A failed Frontier Resource Transport venture.
- Eventual formalization of American Resource Utility around the railroad and broader logistics estate.
- “Blood, Sweat & Tears” grows out of the railroad’s institutional history and becomes the actual railway name.

Earlier references to a 1907 runaway and a 1916 Bloodstone No. 2 disaster appeared in the reconstructed history, but a later retrieval pass did not recover source-secure detail. Do not silently present invented exact casualty counts, dates, or mechanics as previously locked. You are authorized to build a realistic historical and modern safety record. If those two incidents are retained, state that their detailed implementation is derived from the conversation’s remembered spine and document the derivation.

## 11.3 Safety and accident history

The user authorized Codex to build a complete realistic safety history after source recovery failed.

Required constraints:

- no concealed existential safety failure that would make the acquisition incoherent;
- no hidden shutdown order;
- one larger open claim with approximately $0.5M–$0.8M uncertainty;
- enough minor/recordable events, grade-crossing incidents, employee injuries, derailments, environmental releases, rule violations, and corrective actions to look like a real long-running industrial operation;
- modern history must reconcile to insurance expense, environmental reserve, training, CBAs, maintenance backlog, and acquisition diligence;
- historical incidents must be plausible for the period and geography;
- do not make BS&T implausibly spotless or catastrophically unsafe.

Build an accident register, FRA-style event summaries, claim reserve bridge, corrective-action log, trend analysis, and board/diligence narrative. Use official FRA definitions and current sources where relevant.

---

# 12. ROUTE GEOMETRY, FACILITIES, BRIDGES, AND CULVERTS

The user authorized implementation rather than leaving these as placeholders.

## 12.1 Route geometry

Build the complete canonical BS&T route geometry now, consistent with:

- approximately 40 total system route-miles;
- Taylor as yard/shop/operating hub;
- Wamsutter as Union Pacific interchange;
- Great Divide Basin / Red Desert setting;
- the locked customer and commodity portfolio;
- no V1 Red Wash mine spur;
- Taylor-to-Red-Wash truck last mile;
- Class 2 main/branches and Class 1 yard/spurs;
- plausible terrain, rights-of-way, grades, curvature, waterways, roads, industrial nodes, and historical branches.

Deliver GIS source files and rendered maps:

- GeoJSON;
- GeoPackage if supported;
- CSV node/milepost registers;
- route LineStrings;
- facility points/polygons;
- bridge/culvert points;
- track class and speed layers;
- ownership/jurisdiction layers;
- current and historical route maps;
- provenance and license manifest;
- deterministic map-build scripts.

Use real public geospatial sources and license them correctly. The fictional alignment must not be falsely represented as an actual railroad.

## 12.2 Core facilities

At minimum, implement:

1. Taylor Yard and Shops.
2. Taylor Industrial Transload Terminal/Complex.
3. Taylor warehouse, materials-handling, and trucking interface.
4. Wamsutter interchange with Union Pacific.

Build any additional satellite terminal, warehouse, customer siding, team track, storage yard, fuel point, or maintenance location required to make the traffic, headcount, and economics work. The user explicitly authorized deriving and canonizing the complete facility register rather than leaving it abstract.

For each facility include:

- exact derived coordinates;
- ownership/entity;
- acreage;
- tracks and capacity;
- structures;
- commodities/services;
- employees;
- equipment;
- environmental controls;
- operating hours;
- customer relationships;
- condition;
- sustaining/catch-up capex;
- current/historical state;
- map references.

## 12.3 Bridges and culverts

Derive a realistic inventory from the engineered alignment.

Constraints:

- no previously undisclosed major bridge replacement crisis;
- minor bridges, drainage structures, culverts, timber/steel/concrete structures, and deficiencies are realistic;
- deficiencies tie to the $1.2M drainage/culvert catch-up allocation and any track capital;
- include span, material, year/era, rating, inspection state, condition, restriction, waterway/road crossed, and capital plan;
- do not create a structurally impossible line merely to make the map interesting.

---

# 13. $11.0M ARU/BS&T CATCH-UP CAPITAL PROGRAM

Implement and tie every item to specific assets, facilities, findings, and cash timing:

| Category | Amount |
|---|---:|
| Track, ties and surfacing | $3.4M |
| Drainage and culverts | $1.2M |
| Locomotive overhaul and parts | $1.8M |
| Taylor yard and shop | $0.8M |
| Environmental and stormwater | $1.0M |
| Truck fleet | $1.2M |
| Terminal and warehouse equipment | $0.8M |
| Dispatch, IT and control systems | $0.5M |
| Contingency | $0.3M |
| **Total** | **$11.0M** |

This is separate from:

- $3.3M annual sustaining capex;
- $8.5M Red Wash Phase 1 interface capex;
- the $15.0M Red Wash interface ceiling;
- acquisition consideration.

Sable Harbor funds the catch-up program with equity.

---

# 14. TAYLOR–RED WASH INTERFACE

## 14.1 Demand basis

Lock:

- approximately 225 recurring annual inbound Red Wash railcars;
- 300-car annual design allowance including surge/project flexibility;
- no V1 direct mine spur;
- truck last mile between Taylor and Red Wash;
- permanent right to use a mixed external-carrier/truck/transload/rail model;
- no minimum volume guarantee to ARU/BS&T.

225-car planning schedule:

| Flow | Annual cars |
|---|---:|
| Sulfuric acid | 68 |
| Cement/binder | 80 |
| Lime | 17 |
| Steel | 28 |
| Other process/MRO | 12 |
| Heavy/project freight | 10 |
| Planning buffer | 10 |
| **Total** | **225** |

- Aggregate is locally sourced, not hauled by rail.
- Fuel begins truck-delivered; rail remains a future option.
- Finished uranium concentrate is not part of the 225-car inbound-material basis.

## 14.2 Taylor physical design

Implement:

- two 10-car transload tracks;
- one six-car liquid track;
- heavy-freight hardstand;
- warehouse interface;
- hazmat-compatible liquid transfer;
- truck staging and dispatch;
- scales, custody timestamps, access control, drainage, spill containment, emergency response, and secure records;
- enough room for the 300-car design allowance without claiming 5,000 Red Wash cars.

## 14.3 Red Wash receiving design

Implement mine-side receiving/storage only:

- 10–14 days acid and binder storage;
- steel laydown;
- MRO receiving;
- hazmat controls;
- truck scales;
- custody systems;
- no V1 mine spur.

## 14.4 Service schedule and SLA

Lock:

- two scheduled Taylor handling windows per week, nominally Tuesday and Friday, inside BS&T’s existing five-day service;
- typical week: 2–4 Red Wash cars;
- default interchange-receipt-to-empty-release cycle: 72 hours;
- operating goal: 36–48 hours;
- steel may extend to 96 hours;
- 95% on-time service for acid and binder;
- no unassigned demurrage;
- custody timestamps at every handoff;
- 10–14 days critical-consumables buffer at the mine.

## 14.5 Capital

Lock:

- Phase 1: approximately $8.5M.
- Red Wash-specific assets: approximately $3.0M–$3.5M.
- ARU strategic/multi-customer Taylor assets: approximately $5.0M–$5.5M.
- $15.0M remains a ceiling, not approved spend.
- Residual approximately $6.5M is gated to later expansion.

---

# 15. INTERCOMPANY AGREEMENT AND RATE CARD

## 15.1 Intercompany policy

Lock:

- separate P&Ls and books;
- arm’s-length, market-based pricing;
- five-year agreement;
- annual indexing and review;
- two weekly service windows;
- 72-hour default SLA;
- custody timestamp at every handoff;
- demurrage assigned by cause;
- Red Wash owns mine-specific assets;
- ARU owns reusable multi-customer Taylor infrastructure;
- no hidden subsidy;
- no minimum volume guarantee;
- no preferential treatment that harms external customers;
- Red Wash remains free to use external carriers if ARU is not competitive or qualified;
- intercompany revenue and expense eliminate in Sable Harbor consolidated reporting.

## 15.2 Rate-card development

The user explicitly required that the rate card be done well. Do not force it to hit a predetermined answer.

Earlier planning anchors were:

- acid rail movement to Taylor: approximately $3,500 per car, with transload and last mile separately identified;
- cement: approximately $3,000 per car;
- lime: approximately $2,500 per car;
- steel/MRO/project freight: case-specific;
- aggregate planning outcome: approximately $875,000 annual ARU-group revenue and $365,000 incremental EBITDA.

Treat $875,000 and $365,000 as **reconciliation targets, not forced outcomes**. Build the final rate card from first principles and realistic benchmarks:

- line-haul/switching cost;
- interchange and car-hire exposure;
- crew and locomotive time;
- terminal labor/equipment;
- liquid-transfer equipment and hazmat controls;
- drayage mileage/time;
- fuel surcharge;
- storage and free time;
- demurrage;
- special handling;
- custody/security documentation;
- insurance and compliance;
- minimum charges;
- project/surge rates;
- annual escalators;
- market comparables;
- cost-to-serve and target return.

If the defensible result differs materially from the old planning anchors, preserve the analysis, explain the variance, and classify the final rate as derived rather than silently forcing it.

## 15.3 Direct uranium custody

Status: `OPEN_GATED`.

- Uranium concentrate may be rail-eligible where practical in a future qualified service.
- Rail eligibility is not present authority.
- BS&T receives no automatic direct custody.
- Direct custody requires regulatory, customer, route, security, insurance, training, emergency-response, operating, equipment, and commercial approval.
- External qualified carriers remain permissible permanently.
- Any product movement must be separately contracted and does not inflate the 225 inbound-car basis.

---

# 16. POST-ACQUISITION MANAGEMENT

## 16.1 ARU/BS&T leadership

The user authorized Codex to build the complete management team and coherent fictional biographies. Implement names, histories, authority, compensation, retention, succession, and reporting for at least:

- retained BS&T general manager;
- ARU industrial-operations leader;
- ARU controller/finance leader;
- ARU safety/environmental leader;
- terminal/transload leader;
- trucking/drayage leader;
- warehouse/materials-handling leader;
- mechanical/MOW leadership;
- internal ARU successor with day-one operating authority.

Constraints:

- Fred Tolman is the seller CEO and controlling shareholder, not post-close operating management.
- Tolman provides nine months of knowledge transfer for $225,000 total and has no operating authority after close.
- Management retention pool totals $500,000.
- Preserve local operating competence and identity.
- Do not fill the organization with Sable Harbor outsiders or create a purge/synergy story.
- Check all proposed names against the existing Sable Harbor people catalog and avoid accidental family relationships or collisions.

## 16.2 Integration doctrine

Lock:

- no immediate integration office for its own sake;
- no synergy quota;
- no automatic headcount cuts;
- no purge;
- day-one authority is clear;
- first 24 months emphasize durable operations, succession, maintenance, environmental compliance, and measured capital deployment;
- Red Wash does not retroactively justify ARU;
- Red Wash presents requirements and ARU responds commercially;
- capital follows a justified case.

---

# 17. THE M&A PARTICIPANT CASE STUDY

Question 43 is not deferred. Build it.

## 17.1 What the participant receives

This is a point-in-time M&A case study analogous to Blackridge’s participant-facing case. It is **not**:

- the entire SABLEHARBOR repository;
- a thin “surfacing” view;
- a hand-maintained duplicate canon;
- an evaluator repository;
- a set of hidden answers in the participant package.

It is the complete, frozen participant corpus for the Pale Sun/Red Wash/ARU/BS&T acquisition and integration case: all narrative, evidence, models, contracts, maps, diligence records, operating data, financial statements, disputes, uncertainty, and chronology that the participant should actually see at the case cutoff.

## 17.2 Pattern

Before building, inspect the actual Blackridge case package in the repository and mirror its substantive pattern:

- narrative case spine;
- source/evidence artifacts;
- structured data;
- financial/operating model;
- uncertainty and defects;
- participant instructions;
- deterministic build;
- manifest and hashes;
- temporal binding;
- no evaluator truth.

Do not invent a manifest-only “participant edition” that simply points at the whole repository.

## 17.3 Temporal binding

Use a controlled publication cutoff of **September 5, 2026** for this completed retrospective M&A case, with every artifact retaining its own effective date and what-was-known-when state. If the Blackridge mechanical architecture uses a different but equivalent binding convention, follow it and record the mapping.

No post-cutoff facts may leak into the participant package. The transaction chronology must remain visible rather than flattened into hindsight.

## 17.4 Evaluator boundary

- Hidden evaluator truth belongs only in `SABLEHARBOR-ALEXANDRIA-CONTROL`.
- Do not add hidden scoring keys, expected conclusions, evaluator-only facts, or answer rubrics to SABLEHARBOR.
- Produce a clean revision/hash binding that the control repo can consume later.
- Do not modify the control repository in this task unless separately authorized.

## 17.5 Case focus

The case is an M&A and integration study, including:

- how Vilander’s J2/Alexandria work created Pale Sun;
- the false starts and judgment development;
- the Red Wash acquisition from NMI/Henry Norwood;
- the mine’s real defects and operating rehabilitation;
- the Q3/Q4 2025 carrier/logistics problem;
- how ARU/BS&T was surfaced through operating analysis;
- the ARU acquisition from Fred Tolman’s shareholder group;
- transaction, tax, financing, diligence, people, labor, safety, and capital issues;
- the choice to preserve ARU/BS&T independence;
- the Taylor interface and intercompany discipline;
- unresolved direct-uranium-custody gates;
- the difference between strategic logic and subsidy.

Do not mislabel the stock acquisition as a statutory legal merger unless a separate artifact explicitly models a merger. “M&A case” is accurate; “merger” is colloquial in the conversation.

---

# 18. CHAT-SUPPLIED GRAPHICS AND VISUAL WORK

The handoff package contains five exact chat-supplied PNG files plus a manifest.

## 18.1 ARU assets

- `assets/aru/aru_primary_centered_chat_asset.png`
- `assets/aru/aru_brand_board_chat_asset.png`
- `assets/aru/aru_alternate_chat_asset.png`

The first two are approved chat concepts to preserve and reconcile. The third is a reference variant. The board contains “People Purpose Progress” and “Stronger Together”; those phrases are graphic-board content, not separately locked slogans.

## 18.2 BS&T assets

- `assets/bst/bst_railway_primary_chat_asset.png`
- `assets/bst/bst_bulk_storage_transport_candidate.png`

The railway logo is a chat-supplied approved concept. The “Bulk Storage & Transport” file is a candidate/companion concept and must not replace the locked legal name `Blood, Sweat & Tears Railway Company`. It may become a separate ARU service brand only if that placement is explicitly reconciled and useful.

## 18.3 Pale Sun and Red Wash visuals

- Preserve the existing canonical Pale Sun logo exact bytes.
- Regenerate all Red Wash maps that conflict with the Sweetwater County location.
- Preserve old Carbon County map files as superseded originals.
- Search every report, deck, PDF, screenshot, README, casebook, publication, and generated image for incorrect location, town, route, ownership, legal name, or carload information.
- Re-render and repost every current-state image with conflicting information.
- Update manifests, hashes, captions, alt text, provenance, and controlled-document indexes.

## 18.4 Visual standard

The user requires enterprise-ready work, not generic AI-looking layouts. Visuals should resemble serious industrial, transaction, railway, mining, and board materials. Avoid decorative clutter, fake dashboards, illegible microtext, random rounded cards, and inconsistent logos. Maps must have scale, legend, north arrow, source/provenance, fictional-status disclosure, and useful operational layers.

---

# 19. REQUIRED IMPLEMENTATION WORKSTREAMS

Execute all of the following. Do not stop after writing a plan.

## Workstream A — Canon and entity reconciliation

- Create a new decision-register addendum capturing every locked decision in this handoff.
- Update canon changelog and collision register.
- Supersede all prior legal-form and Pale Sun nonentity statements.
- Update legal/reporting structure docs and machine-readable entity records.
- Preserve superseded history rather than deleting it.

## Workstream B — Pale Sun/Vilander build

- Full origin narrative.
- Dated biography/timeline.
- BTC background boundary.
- Talent-search and assessment artifacts.
- Judgment Officer service record.
- Uranium-thread Alexandria case.
- Escalation chain.
- Three false-start case files.
- Founding memo, appointment, leadership and organization.
- Federal/downstream strategy with official citations.
- Pale Sun/Red Wash authority matrix.
- Brand and logo manifest reconciliation.

## Workstream C — Red Wash reconciliation

- Update legal name/owner/seller.
- Correct geography in all sources and outputs.
- Preserve superseded maps.
- Rebuild current maps.
- Reconcile selected mine, workforce, contract, finance, closure, permit, and diligence records.
- Reconcile Mari/Evan authority.

## Workstream D — ARU transaction

- Seller group/cap table.
- Fred Tolman profile.
- LOI, diligence, approval, purchase-agreement summary, closing statement, sources/uses, working-capital peg, escrow, claim, environmental, transition, retention, and tax artifacts.
- §338(h)(10) memo.
- Acquisition-day opening balance sheet and PPA.

## Workstream E — ARU/BS&T operations

- 2025 bottom-up financial statements.
- Customer/contract register.
- Employee census and payroll model.
- Labor agreement summaries.
- Route GIS.
- Facility register.
- Locomotive/railcar/truck/material-handling roster.
- Track/bridge/culvert register.
- Safety/claims history.
- Maintenance backlog and capital plan.
- Service plan and capacity model.

## Workstream F — Taylor/Red Wash interface

- Final engineering layout.
- Car plan and commodity flows.
- Five-year intercompany agreement.
- Defensible rate card from first principles.
- SLA, demurrage, custody, security, insurance, and external-carrier rights.
- Capital ownership and depreciation.
- 225/300 load scenario and expansion gates.

## Workstream G — Participant case

- Inspect Blackridge package.
- Build full frozen M&A participant corpus.
- Create deterministic build and allowlist.
- Bind exact source revision and artifact hashes.
- Exclude evaluator truth.
- Produce participant README, case guide, data dictionary, known limitations, and validation report.

## Workstream H — Graphics and publications

- Preserve exact supplied assets.
- Reconcile logo system.
- Regenerate conflicting maps/graphics.
- Create enterprise-quality organization, ownership, transaction, timeline, route, facility, traffic, capital, and integration visuals.
- Render controlled PDFs only through deterministic source documents.
- Update publication manifest and hashes.

## Workstream I — Engineering and validation

- Structured JSON/CSV/SQLite representations where appropriate.
- Schema validation.
- Arithmetic reconciliation tests.
- Cross-document consistency tests.
- Geography/name/date regression tests.
- Deterministic repeat-build tests.
- Public-safety and secret scan.
- Broken-link and manifest scan.
- Unit/integration tests.
- Full repository CI locally where available.

---

# 20. SPECIFIC ACCEPTANCE TESTS

The work is not complete unless all of these pass.

## 20.1 Entity and name tests

- Legal parent displays as Sable Harbor, LLC.
- Sable Harbor Industrial Holdings, Inc. exists and owns the industrial platforms.
- Pale Sun Inc. is a legal company and owns Red Wash Mining, LLC.
- ARU owns BS&T.
- NMI/Henry Norwood is only the Red Wash seller.
- Fred Tolman is only the ARU seller-group lead.
- Martin Shaw is the Red Wash transaction lead.
- Evan Vilander is spelled correctly everywhere.
- No `Vylander`, `Rylander`, or `judge advocate` remains in current-state artifacts.
- Daniel’s surname is Mercer.

## 20.2 Geography tests

- Current Red Wash location is Sweetwater County/Great Divide Basin at the new anchor.
- No current-state source asserts Carbon County or the old coordinates.
- Old maps remain available with `SUPERSEDED` status and hashes.
- Taylor is the current fictional town/hub.
- Bloodstone is not the current town.
- Wamsutter/Union Pacific interchange is represented correctly.

## 20.3 Chronology tests

- Red Wash closes July 18, 2025.
- ARU is surfaced in Q4 2025, not first discovered in Q1 2026.
- ARU baseline is December 31, 2025.
- ARU closes January 7, 2026.
- External qualified carriers handle all 2025 Red Wash movements.
- Custody incident occurs post-acquisition and does not imply unauthorized prior custody.

## 20.4 Financial tests

- ARU revenue = $42.0M.
- ARU EBITDA = $9.8M.
- ARU opex before D&A = $32.2M.
- ARU FTE = 131.
- Sustaining capex = $3.3M.
- Catch-up capex = $11.0M.
- BS&T revenue = $15.5M.
- BS&T opex before D&A = $14.0M.
- BS&T EBITDA = $1.5M.
- BS&T carloads = 9,000.
- BS&T FTE = 58.
- Traffic schedule sums exactly.
- Transaction sources and uses reconcile exactly.
- Red Wash contributes no 2025 ARU revenue.
- Intercompany activity eliminates in consolidation.

## 20.5 Operating tests

- Four locomotives owned / three generally available / two normally required.
- Class 2 main/branches and Class 1 yards/spurs.
- SMART-TD and BMWED property-specific labor structure.
- Complete customer, employee, facility, equipment, bridge, culvert, track, safety, and capital registers exist.
- No hidden existential bridge or safety crisis is introduced.
- $11.0M catch-up program ties to identified assets and findings.

## 20.6 Red Wash interface tests

- 225 recurring cars, 300 design allowance.
- No V1 mine spur.
- Two 10-car transload tracks and one six-car liquid track.
- Two weekly service windows.
- 72-hour SLA; 36–48-hour goal; 96-hour steel bound.
- 10–14 days critical inventory.
- $8.5M Phase 1 inside $15M ceiling.
- No minimum volume guarantee.
- Mixed-carrier model retained.
- No automatic direct uranium custody.
- Rate card has cost and benchmark support and is not merely forced to $875k/$365k.

## 20.7 Participant-case tests

- Package mirrors Blackridge’s real case pattern.
- Participant receives the complete case corpus, not whole-repo access.
- Exact cutoff/revision is bound.
- No evaluator-only data exists in SABLEHARBOR.
- Every artifact has provenance and temporal status.
- Deterministic rebuild produces identical hashes.

## 20.8 Graphics tests

- Chat-supplied assets remain byte-identical.
- Pale Sun canonical logo remains byte-identical and has a valid calculated SHA-256.
- Current maps use correct geography.
- Superseded maps remain preserved.
- No current image contains old location, old seller name, wrong town, wrong legal form, wrong carload volume, or 2026-Q1 discovery chronology.

---

# 21. SUPERSEDED OR REJECTED STATES

Do not reintroduce any of the following as current canon:

- Red Wash in Carbon County at 42.3127, -106.9213.
- Bloodstone as the current railroad town.
- ARU first discovered in 2026-Q1.
- $76.0M ARU enterprise value.
- $23.6M ARU/BS&T revenue as the governing case.
- $20.3M ARU/BS&T operating cost as the governing case.
- 5,000 Red Wash cars as annual demand.
- 375 recurring Red Wash cars.
- automatic BS&T uranium custody.
- a V1 Red Wash rail spur.
- Northstar Resources, Inc.
- Huck Lamb.
- judge advocate.
- Pale Sun as merely a field banner or nonlegal label.
- whole-repository participant access.
- evaluator truth in SABLEHARBOR.
- automatic authorization of draft PR #95.
- a Utah/Cane Creek/Ballard & Thompson origin for the current Wyoming BS&T history.
- a statutory “merger” if the legal transaction remains a stock acquisition and integration.

---

# 22. TRUE OPEN OR GATED ITEMS

These are the only items that should remain open after implementation, unless Codex can close them within the supplied bounds and record the derivation:

1. Exact BTC legal name/expansion.
2. Exact Vilander birth date and education, within the approved progression.
3. Exact titles used to reconcile Evan Vilander and Mari Varela, provided authority is preserved.
4. Exact Pale Sun founding date within late 2024/early 2025.
5. Pale Sun slogan.
6. Final direct uranium custody authorization — remains gated.
7. Exact future expansion timing for Red Wash’s 225k/300k-ton cases.
8. Any future direct mine spur.
9. Any separate federal subsidiary or secure federal operating entity.
10. Any post-cutoff evaluator material in the control repo.

The user has already authorized Codex to derive and canonize route geometry, facilities, equipment, customers, management names, safety history, bridge/culvert inventory, and final rates inside the constraints. Do not send those back as broad conceptual questions.

---

# 23. COMPLETION REPORT REQUIRED FROM CODEX

At the end, provide a factual closeout containing:

- exact branch and commit hashes;
- exact implementation branch, commit hashes, PR number if one was used, final merge commit, and final pushed `main` SHA;
- full changed-file inventory;
- new controlled documents and structured artifacts;
- all generated graphics and their hashes;
- all archived/superseded graphics and their hashes;
- arithmetic reconciliation results;
- test commands and results;
- deterministic rebuild result;
- citation/provenance coverage;
- unresolved true open items only;
- explicit confirmation that no evaluator truth entered SABLEHARBOR;
- disposition of draft PR #95 and an explanation of what, if anything, was reused from it;
- explicit confirmation that the completed package was pushed and merged into `main`, or exact evidence of the genuine external blocker that prevented delivery.

Do not end with “I will build” or a plan. Build it, validate it, and report the evidence.

---

# 24. PACKAGE FILES

This handoff package contains:

- `SABLE_HARBOR_ARU_RED_WASH_PALE_SUN_CODEX_HANDOFF_FULL_STATE.md` — this complete execution prompt.
- `DECISION_LEDGER_FULL.json` — machine-readable current decision state.
- `ASSET_MANIFEST.json` — exact local asset hashes and state.
- `assets/aru/*` — three ARU chat assets.
- `assets/bst/*` — two BS&T chat assets.
- `source_reconciliation/ARU_BST_RECONCILIATION_REPORT_v1.0.md` — earlier full reconciliation.
- `source_reconciliation/ARU_BST_RECONCILIATION_REPORT_2026-09-05.md` — second detailed reconciliation.
- `source_reconciliation/aru_bst_reconciled_decision_ledger_v1.0.json` — earlier machine-readable ledger.

The appendices below preserve both prior reconciliation reports verbatim so Codex has the full arithmetic, chronology, and source-recovery record rather than a shortened restatement. Their earlier repository-operation restrictions are historical and are expressly superseded by Section 0 of this R2 handoff.

---

# APPENDIX A — PRIOR RECONCILIATION REPORT, VERBATIM

# ARU / BS&T Reconciliation Report

**Document ID:** `SH-ARU-REC-001`  
**Version:** `1.0.0-draft`  
**Decision cutoff:** September 5, 2026  
**Repository compared:** `SquirmyWormy275/SABLEHARBOR`  
**Main commit reviewed:** `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`  
**Unapproved staging branch reviewed only for reconciliation:** `feature/aru-bst-2025-baseline` at `e385d29c4cd6fc49438e956027c8165102608e1b`  
**Scope:** Textual canon, operating model, transaction, financial model, Red Wash interface, chronology, and geography.  
**Excluded from this pass:** All graphics and image inspection, packaging, pushing, merging, and publication.

---

## 1. Reconciliation rule

The governing authority order for this pass is:

1. The user's latest explicit decisions in the September 5, 2026 ARU / BS&T conversation.
2. Existing locked SABLEHARBOR canon where it does not conflict with those later decisions.
3. Model-derived arithmetic needed to implement an explicit decision.
4. Older scenarios and exploratory statements only as superseded archaeology.
5. Unrecoverable older conversation detail remains held for source recovery; it is not reopened or reinvented.

A statement appearing in a generated map, model, branch, or prior assistant proposal does not outrank a later explicit user decision.

---

## 2. Reconciliation conclusion

The ARU / BS&T concept is substantively closed. The remaining work is implementation and controlled source integration, not renewed worldbuilding.

The reconciled state is:

- Sable Harbor owns American Resource Utility.
- American Resource Utility owns Blood, Sweat & Tears Railway.
- Red Wash remains a separate Sable Harbor operating company under the Pale Sun business line.
- ARU is an established, independently viable industrial-logistics operator.
- BS&T is an established Wyoming common-carrier shortline with an independent pre-Red-Wash traffic base.
- Red Wash caused the search that surfaced ARU, but Red Wash is not ARU's sole purpose or economic justification.
- The January 7, 2026 ARU close, transaction terms, 2025 baseline economics, Taylor logistics design, Red Wash production trajectory, service arrangement, and capital split are governing decisions.
- The old $23.6 million ARU scenario, Carbon County Red Wash site, Bloodstone-as-town label, 5,000-car Red Wash forecast, and 375-load preliminary estimate are superseded.

---

## 3. Governing entity structure

| Subject | Reconciled result | State |
|---|---|---|
| Parent | Sable Harbor | LOCKED |
| Acquired company | American Resource Utility (`ARU`) | LOCKED |
| Railway | Blood, Sweat & Tears Railway (`BS&T`) | LOCKED |
| Ownership | Sable Harbor → ARU → BS&T | LOCKED |
| Red Wash | Separate operating company; not inside ARU or BS&T | LOCKED |
| Pale Sun | Business-line/operating layer associated with Red Wash; not substituted for the Red Wash legal operator | LOCKED boundary |
| ARU identity | Retained as a distinct operating company after acquisition | LOCKED |
| BS&T identity | Retained as a distinct railroad and legal subsidiary | LOCKED |
| Exact ARU legal suffix/jurisdiction | Not decided in the recovered record | OPEN implementation |
| Exact BS&T legal suffix/jurisdiction | Not decided in the recovered record | OPEN implementation |
| ARU seller legal identity | Long-tenured owner/CEO seller profile is established; exact name/legal identity is not | OPEN implementation |

The current repository already preserves the parent/subsidiary shape but incorrectly describes most of the now-decided operating and transaction fields as open.

---

## 4. Reconciled chronology

### 4.1 Historical spine recovered from the conversation

The source-secure history is:

1. BS&T is Wyoming-centered and coal-founded.
2. The prior Utah / Thompson / Ballard & Thompson concept was discarded.
3. The coal parent's 1954 collapse is the railroad's institutional “year zero.”
4. After the collapse, the railroad survives with poor equipment, disappearing anchor traffic, continuing payroll obligations, local management, small creditors, and unglamorous traffic such as clay, pipe, and scrap.
5. During the 1960s and 1970s, the operating estate expands into transload pads, warehouses, materials handling, and careful custody/handoff work.
6. ARU grows around BS&T and the broader logistics estate; the railroad is not bolted onto an unrelated modern holding company.
7. “Blood, Sweat & Tears” emerges from the railroad's history and becomes the actual railway name.
8. By 2025, ARU is a functioning resource-logistics business with BS&T beneath it.

### 4.2 History held for source recovery, not reinvention

The accessible records do not safely establish the final exact wording or approval status of:

- the original railroad corporate name;
- a precise founding year before 1954;
- the proposed 1907 wreck;
- the proposed 1916 mine fire;
- names and biographies of early railroad personnel;
- exact 1970s second-line acquisition/lease and disposition;
- exact dates when ARU's corporate form replaced or consolidated predecessor entities;
- exact date on which BS&T became a wholly owned ARU subsidiary.

These items are not reopened. They must be recovered verbatim from the full conversation record before inclusion in the push package.

### 4.3 2025–2026 controlling chronology

| Period/date | Reconciled event |
|---|---|
| July 18, 2025 | Sable Harbor closes the Red Wash acquisition. |
| Q3 2025 | Qualified external carriers continue all Red Wash movements; a synthetic carrier-consolidation/capacity event emerges. |
| Q4 2025 | The replacement-carrier search broadens to durable logistics and rail mapping; ARU/BS&T is surfaced through operating analysis. |
| Q4 2025 | ARU acquisition diligence, negotiation, financing, and transition planning occur. |
| December 31, 2025 | ARU/BS&T pre-acquisition operating and financial baseline date. |
| January 7, 2026 | Sable Harbor closes the acquisition of 100% of ARU. |
| January–March 2026 | Confirmatory condition work, first-90-day operating verification, urgent catch-up capital, and Red Wash interface engineering. This is not the start of acquisition diligence. |
| Approximately months 3–6 | Engineering, approvals, contracting, procurement, training, and early Taylor implementation. |
| Approximately month 6 onward | Limited Red Wash service only after applicable operating, regulatory, insurance, customer, and custody gates pass. |
| 2026 | Custody-timestamp incident occurs after acquisition. It must not be represented as proof that BS&T had unauthorized direct uranium custody. |

### Chronology correction

The current Red Wash bridge says ARU/BS&T is first surfaced in 2026 Q1. That cannot coexist with a January 7, 2026 acquisition close. The discovery event moves to Q4 2025 while preserving the established causal sequence and “operating analysis, not banker pitch” rule.

---

## 5. 2025 ARU / BS&T operating baseline

### 5.1 Consolidated ARU

| Measure | Reconciled 2025 baseline |
|---|---:|
| Revenue | $42.000M |
| Operating expense before D&A | $32.200M |
| Normalized EBITDA | $9.800M |
| Normalized EBITDA margin | 23.33% |
| Employees | 131 |
| Sustaining capital expenditure | $3.300M |
| EBITDA less sustaining capex | $6.500M |
| Deferred catch-up capital | $11.000M |

### 5.2 Segment bridge

| Segment | Revenue | Normalized EBITDA | Margin | FTE | Sustaining capex |
|---|---:|---:|---:|---:|---:|
| BS&T Railway | $15.500M | $1.500M | 9.68% | 58 | $2.050M |
| Industrial terminals and transload | $13.000M | $4.300M | 33.08% | 27 | $0.550M |
| Heavy industrial trucking and drayage | $7.500M | $1.500M | 20.00% | 24 | $0.480M |
| Warehousing and materials handling | $6.000M | $2.700M | 45.00% | 12 | $0.220M |
| ARU corporate and unallocated | $0 | $(0.200)M | — | 10 | $0 |
| **Total** | **$42.000M** | **$9.800M** | **23.33%** | **131** | **$3.300M** |

The segment bridge is a governing working model. Contract and customer records must be generated to support it; they are not a reason to reopen the approved totals.

### 5.3 Customer concentration

| Measure | Reconciled result |
|---|---:|
| Largest customer | Approximately 11% / $4.620M |
| Top five customers | Approximately 40% / $16.800M |
| Material renewal risks during diligence | One |
| 2025 Red Wash revenue to ARU | $0 |

---

## 6. BS&T 2025 operating baseline

| Measure | Reconciled result |
|---|---:|
| Total system route miles | Approximately 40 |
| Annual loaded revenue carloads | Approximately 9,000 |
| Service/interchange days | Five per week |
| Locomotives owned | Four |
| Generally available | Three |
| Normally required | Two |
| Employees | 58 |
| Revenue | $15.500M |
| Expense before D&A | $14.000M |
| Normalized EBITDA | $1.500M |
| EBITDA operating ratio | 90.32% |
| Targeted-capex incremental network capacity | Approximately 5,000–7,500 annual revenue carloads |

### Traffic portfolio

| Traffic class | Working carloads | Working freight revenue |
|---|---:|---:|
| Soda ash, trona, and minerals | 3,150 | $4.331M |
| Energy and oilfield materials | 1,650 | $3.218M |
| Aggregates and construction | 1,350 | $1.688M |
| Industrial chemicals and metals | 1,050 | $2.021M |
| Agriculture and ranch supply | 750 | $0.975M |
| Transload, project, and other | 1,050 | $1.717M |
| **Freight subtotal** | **9,000** | **$13.949M** |
| Switching, storage, demurrage, and accessorial revenue | — | $1.551M |
| **Total** | **9,000** | **$15.500M** |

The class-level carload allocation is an implementation schedule beneath the approved 9,000-car/$15.5M case. It is not a published tariff or a claim that named customer contracts already exist.

### Route-mile interpretation

The approximately 40 route-miles refers to the total pre-acquisition BS&T system, not a direct 40-mile Red Wash mine spur. V1 has no direct mine spur. Taylor is the rail/transload hub and truck last mile connects Taylor to Red Wash.

---

## 7. Balance sheet and liability frame

| Item | Reconciled amount/treatment |
|---|---:|
| Term and equipment debt | $11.500M |
| Revolver drawn pre-close | $2.000M |
| Finance leases | $2.500M |
| Cash | $3.500M |
| Net debt | $12.500M |
| Known environmental reserve | Approximately $1.500M–$2.000M |
| Larger open claim uncertainty | Approximately $0.500M–$0.800M |
| Working capital | Normalized peg; dollar-for-dollar close true-up; cash and debt excluded |
| Distress status | Solvent going concern; seller motivation is succession and capital-cycle pressure, not distress |

The exact pre-acquisition balance sheet remains to be generated, but these amounts and treatments control that build.

---

## 8. Acquisition transaction

| Term | Reconciled result |
|---|---|
| Close date | January 7, 2026 |
| Acquired interest | 100% of ARU |
| Enterprise value | $62.000M |
| Multiple on $9.8M normalized EBITDA | Approximately 6.33× |
| Net debt bridge | Approximately $12.500M |
| Total seller equity value | Approximately $49.500M |
| Seller rollover | None |
| Earn-out | None |
| New acquisition debt | $22.500M |
| New revolver | $5.000M, undrawn at close |
| Existing term debt/revolver | Refinance at close |
| Ordinary finance leases | Retain |
| Minimum operating cash retained | $2.000M |
| Excess cash | $1.500M handled as pre-close distribution or dollar-for-dollar close-bridge item |
| Escrow | $3.000M, included in seller value rather than added to enterprise value |
| General working-capital mechanism | Normalized peg and dollar-for-dollar true-up |
| Environmental treatment | Buyer assumes known reserve; longer survival for undisclosed environmental matters |
| Open claim | Seller covers adverse development above closing accrual |
| Targeted retention pool | $0.500M over 12 months; half at month 6 and half at month 12 |
| Seller CEO transition | Nine months |
| Seller CEO consulting compensation | $0.225M total; defined scope and no continuing management authority |
| Authority transfer | Day one |
| Catch-up capital funding | Sable Harbor equity, not additional ARU debt |

### Reconciled sources and uses before fees

For a close in which only $2.0M remains as operating cash and $1.5M excess cash is distributed or credited to the seller:

| Use | Amount |
|---|---:|
| Buyer-funded equity purchase consideration | $48.000M |
| Existing term debt and revolver repayment | $13.500M |
| **Net closing uses before fees** | **$61.500M** |
| New acquisition debt | $22.500M |
| **Sable Harbor closing equity before fees** | **$39.000M** |

Seller economics remain $49.5M: $48.0M buyer-funded consideration plus $1.5M excess cash. Of the $48.0M buyer-funded consideration, $3.0M is held in escrow and approximately $45.0M is paid at close. Retained $2.5M finance leases remain on the acquired balance sheet.

The $0.500M retention pool, $0.225M consulting agreement, transaction fees, and post-close capital are separate from purchase consideration.

---

## 9. Post-close doctrine

The governing post-close posture is:

- ARU and BS&T retain their names, identity, workforce, management, and operating rhythm.
- No immediate integration office.
- No synergy target.
- No acquisition-driven headcount program.
- No “prove the deal” EBITDA extraction.
- First 90 days confirm conditions with operators and fund urgent track, drainage, locomotive, environmental, and compliance work.
- The first 24 months prioritize durability, succession depth, maintenance discipline, environmental compliance, and measured capital deployment.
- The seller CEO has no continuing authority after close; the nine-month agreement is knowledge transfer.
- Red Wash and ARU maintain separate P&Ls and transact at market-based terms.
- Common ownership does not permit hidden subsidies or blurred operating accountability.

---

## 10. Red Wash production trajectory

| Case | Ore mined | Grade/recovery basis | Approximate U3O8 production | State |
|---|---:|---|---:|---|
| 2026 rehabilitation year | 175,000 short tons | ~0.170% U3O8 / ~92% recovery | 547,400 lb, conventionally rounded to ~550,000 lb | LOCKED |
| Normalized target | 225,000 short tons | Similar grade/recovery | ~703,800 lb, conventionally rounded to ~700,000 lb | LOCKED planning target; target year not assigned |
| Future expansion option | 300,000 short tons | Some grade dilution permitted | ~880,000 lb | LOCKED option; not committed |

The 2026 case does not get overwritten by the normalized and expansion cases. They are sequential states.

---

## 11. Red Wash rail and logistics design

### 11.1 Final volume interpretation

| Item | Reconciled result |
|---|---:|
| Red Wash normalized recurring rail loads | Approximately 225 annually |
| Red Wash design allowance | 300 annually |
| Earlier 375-load estimate | SUPERSEDED |
| Earlier 5,000-loaded-car Red Wash case | SUPERSEDED as a Red Wash forecast |
| BS&T base external carloads | Approximately 9,000 |
| Operational carloads after normalized Red Wash service | Approximately 9,225 before other growth |
| 5,000–7,500 figure | BS&T network headroom after targeted capital, not Red Wash demand |

Red Wash is meaningful but not dominant. It is a strategic catalyst and a useful customer, not the sole financial justification for acquiring ARU.

### 11.2 Normalized 225-load planning schedule

| Flow | Loads |
|---|---:|
| Sulfuric acid | 68 |
| Cement/binder | 80 |
| Lime | 17 |
| Steel/ground support | 28 |
| Other process and MRO | 12 |
| Heavy/project freight | 10 |
| Planning buffer | 10 |
| **Total** | **225** |

Aggregate is locally sourced rather than hauled in by rail. Fuel begins as truck-delivered and remains a later rail option.

### 11.3 Product movement

- Natural uranium concentrate remains rail-eligible where commercially, operationally, regulatorily, and contractually practical.
- Concentrate is not a material driver of the 225-load base.
- Direct uranium custody is not automatically authorized.
- Any specialized product movement must pass the existing qualification, insurance, security, customer, emergency-response, route, and custody gates.
- Optional concentrate movements fall outside the recurring inbound-material base and within the 300-load design allowance unless later separately committed.

### 11.4 Physical design

Taylor is the V1 rail/transload hub.

Taylor receives:

- two approximately 10-car general/transload tracks;
- one approximately 6-car liquid-handling track;
- heavy-freight hardstand;
- warehouse/materials-handling interface;
- custody, scale, dispatch, and transfer controls.

Red Wash receives:

- truck-based last-mile delivery;
- approximately 10–14 days of acid and binder storage;
- steel and MRO laydown;
- scales;
- hazardous-material controls;
- custody timestamps at each handoff.

There is no V1 direct mine rail spur.

### 11.5 Service standard

| Term | Reconciled result |
|---|---|
| Red Wash handling windows | Two scheduled Taylor windows per week within BS&T's five-day service |
| Default car-cycle SLA | 72 hours from interchange receipt to empty release |
| Operating target | 36–48 hours where practical |
| Steel/project allowance | Up to 96 hours where required |
| Acid/binder on-time target | 95% |
| Mine critical-material buffer | 10–14 days |
| Demurrage | Assigned by cause |
| Custody record | Timestamp required at every handoff |

### 11.6 Commercial model

| Measure | Reconciled result |
|---|---:|
| Annual ARU-group intercompany revenue | Approximately $0.875M |
| Annual incremental EBITDA | Approximately $0.365M |
| Average revenue per planned load including services | Approximately $3,889 |
| Intercompany term | Five years |
| Pricing | Arm's-length/market-based; indexed and reviewed annually |
| Red Wash external-carrier right | Preserved |
| Volume guarantee | None |
| Preferential treatment | None |

The $0.875M is ARU-group intercompany revenue before Sable Harbor consolidation. It must be allocated among BS&T rail service, Taylor terminal service, and ARU last-mile trucking, then eliminated at consolidated Sable Harbor.

The working rate skeleton is:

- acid: approximately $3,500 per car to Taylor, with transload and last-mile charges separately identified;
- cement: approximately $3,000 per car;
- lime: approximately $2,500 per car;
- steel, MRO, and project freight: case-specific;
- demurrage and custody-related charges: explicit and cause-based.

### 11.7 Capital

| Capital category | Reconciled treatment |
|---|---:|
| ARU catch-up capital | $11.000M; existing-business stewardship; Sable Harbor equity funded |
| Red Wash Phase 1 | Approximately $8.500M |
| Red Wash-specific portion | Approximately $3.000M–$3.500M |
| ARU strategic/multi-customer Taylor portion | Approximately $5.000M–$5.500M |
| Total Red Wash integration ceiling | Up to $15.000M |
| Residual ceiling | Gated to later expansion; not approved automatically |

The $8.5M cannot be justified by the $0.365M annual incremental EBITDA alone. The reconciliation therefore preserves the approved split:

- Red Wash owns/funds mine-specific assets and economics.
- ARU owns/funds multi-customer Taylor infrastructure.
- The strategic Taylor portion must earn its return across Red Wash and other customers.
- The $15.0M amount remains a ceiling, not a target or booked commitment.

---

## 12. Geography

| Subject | Reconciled result |
|---|---|
| Red Wash region | Great Divide Basin / Red Desert, Sweetwater County, Wyoming |
| Red Wash working anchor | 42.2200° N, 108.1800° W |
| Red Wash fictionality | Fictional mine in real geography |
| Superseded site | Carbon County, 42.3127° N, 106.9213° W |
| National-network context | Wamsutter, Wyoming |
| Railroad community/hub | Taylor, Wyoming |
| Taylor fictionality | Fictional community in real geography |
| Bloodstone as town | SUPERSEDED |
| Direct mine spur | None in V1 |
| Exact BS&T alignment | Separate geospatial engineering work; must follow the reconciled business model |

The working Red Wash anchor is approximately 39 straight-line miles from Wamsutter. This reinforces that the approximately 40 route-miles cannot be interpreted as a direct mine branch. The GIS model must treat 40 miles as total BS&T system mileage and locate Taylor so truck last mile and the existing pre-acquisition network remain physically coherent.

---

## 13. Explicit supersessions

The following must not appear as current controlling facts:

1. ARU/BS&T 2026 external revenue of $23.6M.
2. ARU/BS&T 2026 operating cost of $20.3M.
3. ARU acquisition enterprise value of $76M.
4. Carbon County Red Wash site at 42.3127, -106.9213.
5. Bloodstone as the current railroad town.
6. 5,000 annual Red Wash loaded railcars as forecast or commitment.
7. Approximately 375 recurring Red Wash loads.
8. “Concentrate stays off rail” as a categorical rule.
9. Red Wash as a pre-existing BS&T customer.
10. ARU/BS&T as a Northstar carrier or vendor.
11. ARU first being discovered in 2026 Q1.
12. The $15M interface envelope as approved capex or purchase price.
13. “Soon after acquisition” language that implies unauthorized uranium custody before qualification.
14. Any statement that the 40-mile system is a direct Taylor/Red Wash mine branch.
15. Any statement that Red Wash alone economically justifies ARU.

---

## 14. Current repository collisions

| Collision | Current repository state | Required controlling correction |
|---|---|---|
| Full ARU case | `ARU-007`, `RW-025`, organization documents, and bridge records call it open | Replace with a closed operating/transaction decision set and retain only true implementation fields as open |
| Financial assumptions | `FIN-Q-005` = $23.6M revenue; `FIN-Q-006` = $20.3M cost | Supersede; implement 2025 $42.0M/$32.2M baseline and build a separately derived 2026 forecast |
| Booking architecture | Aggregate ARU economics book to BS&T | Create separate ARU non-rail books/drivers and consolidation eliminations |
| Red Wash geography | Carbon County coordinate appears throughout the Red Wash package | Supersede with Great Divide Basin / Sweetwater / 42.22, -108.18 and rebuild text/data outputs |
| Taylor | No current Taylor record | Add Taylor as fictional BS&T hub; ensure Bloodstone is not used as town |
| Discovery chronology | Bridge event says ARU surfaced in 2026 Q1 | Move discovery to Q4 2025 so January 7 close is possible |
| Post-close first 90 days | Described as broad diligence | Recast as confirmatory condition work and implementation design; acquisition diligence occurred pre-close |
| Red Wash terminal | Current record says none exists | Preserve this as pre-acquisition condition, then add approved Taylor Phase 1 design as post-close plan |
| Interface capex | $15M entirely open | Preserve ceiling; add $8.5M Phase 1 and approved dedicated/strategic split |
| Volume | Final committed Red Wash volume called open | Add 225 recurring / 300 design allowance; no minimum guarantee |
| Custody | Open, with external carriers authoritative | Preserve gate; add product rail eligibility without automatic authority |
| Route miles | Open in current canon | Add approximately 40 total system route-miles; exact GIS alignment remains engineered detail |
| Fleet/headcount | Open in current canon | Add four locomotives, three generally available, two required; 58 BS&T FTE; 131 ARU FTE |
| Transaction | Entire ARU transaction open | Add January 7 close and full term set in this report |
| History | Detailed history open | Add the source-secure Wyoming/coal/1954/logistics spine; recover exact remaining history before push |

---

## 15. Staging branch and PR treatment

The `feature/aru-bst-2025-baseline` branch is useful as reconciliation evidence because its arithmetic ties to the approved headline case.

It is not the controlling repository state because:

- it was created before this full reconciliation;
- it contains only the first operating baseline;
- it does not resolve all collisions in this report;
- the associated pull request was opened without explicit user authorization.

No merge, publication, graphics work, or additional repository write is authorized by this reconciliation report.

The branch content should ultimately be either:

- incorporated into the final reconciled package after correction; or
- abandoned in favor of a clean package branch.

That disposition is a repository action, not part of this textual reconciliation pass.

---

## 16. Reconciliation acceptance criteria before packaging

The later push-ready package may be assembled only after:

1. Every decision in this report is represented in a single machine-readable decision ledger.
2. The chronology uses Q4 2025 discovery and January 7, 2026 close.
3. Old finance assumptions are explicitly superseded rather than silently overwritten.
4. 2025 baseline and 2026 post-close forecast are separated.
5. ARU's non-rail segments are represented separately from BS&T.
6. Transaction sources and uses reconcile.
7. The $11M catch-up program and $8.5M Red Wash Phase 1 program remain separate.
8. Red Wash volumes are 225 recurring / 300 design allowance, not 5,000.
9. Direct uranium custody remains gated.
10. Taylor replaces Bloodstone as the town.
11. Carbon County outputs are identified for regeneration.
12. History details not securely recovered are not filled with invention.
13. Exact approved graphics are handled only after textual reconciliation is accepted.
14. No PR, push, merge, or publication occurs without an explicit instruction authorizing that action.

---

## 17. Final reconciliation verdict

**The decision set is internally reconcilable.**

The material corrections are chronology, old scenario retirement, ARU non-rail accounting, Red Wash geography, Taylor naming, and the distinction among:

- BS&T base traffic;
- BS&T network headroom;
- Red Wash actual planning loads;
- Red Wash integration capital;
- ARU existing-business catch-up capital.

No further business-design decision is required to begin constructing the final push-ready package.

The only source-integrity hold is recovery of exact older railroad-history details that were developed in the conversation but are not safely present in the accessible repository or retrieved transcript excerpts. Those details must be imported, not recreated.

# APPENDIX B — SECOND RECONCILIATION REPORT, VERBATIM

# ARU / BS&T RECONCILIATION REPORT

**Program:** SABLE HARBOR  
**Subject:** American Resource Utility / Blood, Sweat & Tears Railway  
**Reconciliation date:** 2026-09-05  
**Repository baseline:** `SquirmyWormy275/SABLEHARBOR` `main` at `8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd`  
**Working branch reviewed:** `feature/aru-bst-2025-baseline` at `e385d29c4cd6fc49438e956027c8165102608e1b`  
**PR status:** Draft PR #95 exists but was not authorized by the user, is not merged, and is not canon.  
**Graphics status:** Deliberately excluded from this reconciliation phase. No logo or map was inspected, modified, copied, or packaged after the user's stop instruction.

---

## 1. Governing authority for this reconciliation

Where sources disagree, apply this order:

1. Explicit user decisions in the September 5, 2026 ARU/BS&T conversation, including later corrections.
2. Current locked canon on repository `main` at the baseline commit above.
3. User-approved conversation history that fills fields deliberately left open on `main`.
4. Model-derived schedules on `feature/aru-bst-2025-baseline`.
5. Older reversible finance scenarios and discarded geography/history concepts.

A later explicit correction supersedes an earlier approval only for the corrected subject. It does not erase unaffected historical facts.

---

## 2. Reconciled corporate and legal structure

### Controlling result

- **Sable Harbor** owns 100% of **American Resource Utility**.
- **American Resource Utility (ARU)** is an established industrial-logistics operating company acquired by Sable Harbor, not a greenfield Sable Harbor build.
- **Blood, Sweat & Tears Railway (BS&T)** is ARU's wholly owned railroad subsidiary and preserves separate identity, books, assets, employees, contracts, insurance, regulatory obligations, capital program, and operating authority.
- **Red Wash** remains a separate Pale Sun operating asset/company. It is not folded into ARU or BS&T.
- ARU and Red Wash use separate P&Ls and an arm's-length intercompany logistics agreement. Common ownership does not erase cost visibility, accountability, or capital discipline.

### Repository treatment

The existing `ARU-001` through `ARU-006` and `ARU-009` directions remain valid. `ARU-007` and `RW-025`, which currently leave the full ARU case open, must be superseded or narrowed when the closeout package is implemented.

---

## 3. Reconciled historical spine

The following post-Wyoming-reset history was approved in the conversation and is compatible with the current corporate structure.

### Early railroad and coal era

- **Bloodstone Coal & Coke Company** is the original coal parent.
- **Thomas R. Bell**, a Pennsylvania-trained mining engineer and promoter/front man, assembled the coal enterprise with outside capital.
- The railroad began under the corporate name **Bloodstone & Southern Railway**.
- A loaded-coal-train downgrade runaway around **1907** killed two railroaders. “Blood, Sweat & Tears” emerged as a gallows nickname from the wreck and the work required to keep the line operating.
- The operation unionized with the **United Mine Workers of America around 1909**.
- The **1916 Bloodstone No. 2 underground fire and partial collapse** killed 23 miners. Three railroad employees also died during rescue work.
- Thomas Bell died around **1924**.
- The Blood, Sweat & Tears identity later became the railroad's formal name. The exact legal rename date remains unassigned and should not be invented in the package.

### Town-name correction

- **Taylor, Wyoming** is the railroad community and BS&T shop/yard town.
- Earlier references to the settlement as “Bloodstone” are superseded.
- “Bloodstone” may remain only in non-town historical names, including the coal company, coal field, mine, or other explicitly identified historical assets.

### Orphan railroad and ARU evolution

- **1953** is the coal parent's failure year.
- **1954** is BS&T's year zero as an orphaned railroad.
- BS&T superintendent **Walt Mercer** and a group of Wyoming investors acquired the surviving railroad assets.
- Mine-only trackage was abandoned; the active system contracted from roughly 22 miles to approximately 14–16 miles.
- Survival traffic included clay, scrap, petroleum, lumber, building materials, agricultural inputs, drilling pipe, machinery, and other cash-paying bulk freight.
- The survival culture became: clear custody, hard bids, narrow promises, paperwork before movement, and refusal of work whose exposure was not understood.
- During the 1960s and 1970s, the enterprise gradually added transload, warehouse, scale, forklift/material-handling, switching, custody, and limited industrial-service capability.
- A second off-rail terminal property near Rawlins was part of the expansion concept.
- In the 1980s, the enterprise acquired **Frontier Resource Transport** and attempted a broader trucking expansion. The venture failed because trucking labor, maintenance, insurance, and dispatch economics differed from railroad operations. Most of the venture was sold at a loss within roughly four years.
- Limited drayage serving the company's own terminals was retained.
- The **American Resource Utility** name and broader holding/operating structure were formalized in the late 1980s or early 1990s. BS&T retained its separate railroad identity underneath ARU.

### Historical precision boundary

The exact ARU formation date, formal BS&T rename date, detailed post-1990 ownership generations, and named seller identity were not given a final exact answer. They remain bounded open fields. They must not be filled by reviving the discarded Utah/Ballard & Thompson/Cane Creek history or the unrelated older Bay State & Timber concept.

---

## 4. Discarded and superseded history/geography

The following must not re-enter current canon:

- Ballard & Thompson / Thompson-Sego as ARU or BS&T's controlling origin.
- Cane Creek Branch as BS&T's controlling history.
- Grand Junction–Green River, southeastern Utah, eastern Utah, or Colorado Plateau as the controlling ARU/BS&T geographic origin.
- The earlier oversized provisional 2025 ARU snapshot of approximately 335 employees, $118 million revenue, $18 million EBITDA, $27 million debt, 43 route-miles, 14 locomotives, and seven sites.
- “Bloodstone, Wyoming” as the current or historical town name unless the user later explicitly restores it. The current town is Taylor.

The approved Wyoming coal history replaces those discarded origin concepts.

---

## 5. Reconciled 2025 pre-acquisition operating baseline

### Consolidated ARU

| Measure | Reconciled result | State |
|---|---:|---|
| Revenue | $42.0 million | User-approved working canon |
| Normalized EBITDA | $9.8 million | User-approved working canon |
| EBITDA margin | 23.3% | Derived |
| Employees | 131 | User-approved working canon |
| Sustaining capex | $3.3 million | User-approved working canon |
| EBITDA less sustaining capex | $6.5 million | Derived |
| Deferred catch-up capex | $11.0 million | User-approved working canon |

### Segment bridge

| Segment | Revenue | Normalized EBITDA | FTE | Sustaining capex |
|---|---:|---:|---:|---:|
| BS&T Railway | $15.5M | $1.5M | 58 | $2.05M |
| Industrial terminals and transload | $13.0M | $4.3M | 27 | $0.55M |
| Heavy industrial trucking and drayage | $7.5M | $1.5M | 24 | $0.48M |
| Warehousing and materials handling | $6.0M | $2.7M | 12 | $0.22M |
| ARU corporate/shared services | $0 | $(0.2)M | 10 | $0 |
| **Total** | **$42.0M** | **$9.8M** | **131** | **$3.3M** |

The totals are reconciled. The segment allocations are model-derived implementation values and need contract/customer/asset support, but they do not require a new business-architecture decision.

### BS&T operating profile

| Measure | Reconciled result |
|---|---:|
| Revenue carloads | 9,000 annually |
| Working route scale | Approximately 40 route-miles |
| Interchange/service pattern | Five days per week |
| Revenue | $15.5M |
| Normalized EBITDA | $1.5M |
| EBITDA operating ratio | 90.3% |
| Employees | 58 |
| Locomotives owned | 4 |
| Generally available | 3 |
| Normally required | 2 |
| Incremental capacity after targeted investment | 5,000–7,500 additional annual revenue carloads |

The 5,000-car figure is **system expansion capacity**, not Red Wash's forecast traffic.

### BS&T model-derived traffic schedule

| Traffic class | Cars | Revenue |
|---|---:|---:|
| Soda ash, trona, and minerals | 3,150 | $4.331M |
| Energy and oilfield materials | 1,650 | $3.218M |
| Aggregates and construction | 1,350 | $1.688M |
| Industrial chemicals and metals | 1,050 | $2.021M |
| Agriculture and ranch supply | 750 | $0.975M |
| Transload, project, and other | 1,050 | $1.717M |
| Switching, accessorial, storage, and demurrage | — | $1.551M |
| **Total** | **9,000** | **$15.500M** |

This traffic allocation is a model-derived schedule, not a published tariff or named-customer register.

### Customer profile

- Largest consolidated customer: approximately 11% of revenue.
- Top five customers: approximately 40% of revenue.
- One material renewal is under active diligence at the transaction date.
- ARU is viable but capital-constrained and succession-thin, not distressed.

---

## 6. Superseded finance assumptions

The current finance engine's reversible assumptions are superseded for the ARU/BS&T selected case:

- `FIN-Q-005`: $23.6 million ARU/BS&T external revenue.
- `FIN-Q-006`: $20.3 million ARU/BS&T operating cost.
- Earlier $76 million ARU enterprise-value scenario.
- Earlier oversized operating scale noted above.

They may remain only as clearly labeled scenario archaeology. They must not feed the selected ARU/BS&T baseline after implementation.

The engine must not book the entire ARU group into BS&T. Separate books/drivers are required for BS&T, terminals/transload, trucking/drayage, warehousing/materials handling, ARU corporate/shared services, and eliminations.

---

## 7. Reconciled acquisition transaction

### Date and headline terms

- **Close date:** January 7, 2026.
- **Enterprise value:** $62.0 million.
- **Gross pre-close debt:** $16.0 million, consisting of approximately $11.5 million term/equipment debt, $2.0 million revolver borrowings, and $2.5 million finance leases.
- **Pre-close cash:** approximately $3.5 million.
- **Total seller equity value:** approximately $49.5 million.
- **Minimum cash retained in ARU at close:** $2.0 million.
- **Excess cash treated through the closing bridge:** $1.5 million.

### Reconciled closing math

The earlier $49.5 million seller-equity figure and the later $2.0 million retained-cash decision are both preserved as follows:

- Enterprise value: $62.0M
- Less gross debt: $(16.0)M
- Plus total pre-close cash: $3.5M
- **Total seller equity value:** $49.5M
- Less excess cash distributed/swept through the bridge: $(1.5)M
- **Buyer-funded equity purchase consideration:** $48.0M
- Less ARU transaction escrow: $(3.0)M
- **Buyer-funded cash paid to seller at close:** $45.0M
- Plus seller receipt of excess pre-close cash: $1.5M
- **Immediate seller proceeds:** $46.5M
- Plus escrowed consideration: $3.0M
- **Total seller value:** $49.5M

The $3.0 million ARU escrow is separate from the $3.0 million escrow in the Red Wash transaction.

### Financing

- New acquisition term debt: **$22.5 million**.
- Existing $11.5 million term/equipment debt and $2.0 million revolver are refinanced at close.
- Ordinary $2.5 million equipment finance leases remain in place.
- New revolving facility: **$5.0 million**, undrawn or essentially undrawn at close.
- Sable Harbor funds the remaining close uses with equity/cash.
- Buyer-funded uses before fees: $48.0M equity purchase consideration + $13.5M debt refinancing = $61.5M.
- Sable Harbor close funding before fees: $61.5M − $22.5M new debt = **$39.0M**.
- Post-close funded debt: approximately $25.0M including retained finance leases.
- Post-close net debt: approximately $23.0M after retained $2.0M cash.
- Net leverage: approximately 2.35× normalized EBITDA.

### Other locked terms

- 100% acquisition; no rollover equity.
- No earn-out.
- No synergy-dependent valuation.
- Normalized working-capital peg, excluding cash and debt, with dollar-for-dollar closing true-up.
- $3.0 million escrow; 18-month general survival; longer environmental survival.
- Known $1.5–$2.0 million environmental reserve is assumed as an operating reality.
- Seller protects buyer against undisclosed environmental matters through the longer-survival reps.
- For the identified larger claim, seller covers adverse development above the closing balance-sheet accrual.
- Seller CEO has no operating authority after close.
- Seller CEO transition: nine months, through approximately October 7, 2026.
- Seller CEO consulting compensation: $225,000 total over the transition.
- Targeted management retention pool: $500,000 over 12 months, half at six months and half at 12 months.
- The $11.0 million catch-up capital program is funded with Sable Harbor equity, not additional ARU acquisition debt.

---

## 8. Chronology collision and its resolution

### Collision

Current `main` says rail/interface mapping first surfaced ARU/BS&T in **2026-Q1**. That cannot coexist with a **January 7, 2026** acquisition close because a complete search, diligence, negotiation, signing, financing, and closing process cannot occur after first discovery within six days.

### Reconciled chronology

- July 18, 2025: Sable Harbor closes Red Wash acquisition.
- 2025-Q3: Qualified external carrier consolidation reduces capacity allocated to the low-frequency Red Wash lane.
- 2025-Q4: Red Wash begins replacement/additional-carrier search.
- October–November 2025: The search broadens into rail/interface mapping; the question “Whose line is this?” surfaces ARU/BS&T.
- November–December 2025: Sable Harbor conducts ARU diligence, negotiates the transaction, and signs subject to closing conditions.
- December 31, 2025: ARU/BS&T baseline date.
- January 7, 2026: Sable Harbor acquires 100% of ARU.

This retiming changes only the discovery-event date. It preserves the locked rule that ARU/BS&T had no pre-existing Red Wash relationship and that qualified external carriers handled every 2025 Red Wash movement.

---

## 9. Reconciled post-close doctrine

- ARU and BS&T retain names, identity, management, workforce, and operating rhythm.
- No immediate integration office, synergy quota, headcount action, or “purge.”
- Day-one authority transfers to Sable Harbor/ARU management; the seller CEO provides knowledge transfer only.
- First 24 months emphasize durable operations, succession depth, maintenance discipline, environmental compliance, and measured capital deployment.
- The first capital tranche prioritizes track/drainage, locomotive overhaul, and known environmental/compliance work.
- Red Wash is not used to justify the ARU acquisition retroactively and does not automatically receive preferred or subsidized service.
- Red Wash presents requirements; ARU responds commercially and operationally; capital follows a justified case.

---

## 10. Reconciled Red Wash operating and throughput bridge

### Mine production cases

| Case | Ore throughput | U3O8 production |
|---|---:|---:|
| 2026 rehabilitation case | 175,000 short tons | 547,400 lb, commonly summarized as ~550,000 lb |
| Normalized target | 225,000 short tons | Approximately 700,000 lb |
| Future expansion option | 300,000 short tons | Approximately 880,000 lb |

The 2026 selected case on `main` remains valid. The normalized and expansion cases are later planning cases and must be labeled accordingly.

### Rail-volume correction

- The earlier 5,000-car Red Wash design figure is superseded as a Red Wash volume assumption.
- BS&T's 5,000–7,500 additional-car system capacity remains valid as network headroom after targeted capital.
- **Red Wash normalized planning basis:** approximately 225 recurring annual inbound railcars.
- **Red Wash design allowance:** 300 annual recurring/project cars.
- Uranium concentrate is rail-eligible where practical after qualification, but is not the volume driver and is not included in the 225 recurring industrial-input cars.
- Rail eligibility does not authorize current custody. Direct ARU/BS&T uranium custody remains gated.

### Normalized 225-car planning schedule

| Commodity/flow | Annual cars |
|---|---:|
| Sulfuric acid | 68 |
| Cement/binder | 80 |
| Lime | 17 |
| Steel | 28 |
| Other process and MRO | 12 |
| Heavy/project freight | 10 |
| Planning buffer | 10 |
| **Total** | **225** |

- Aggregate is sourced locally rather than moved by rail.
- Fuel begins as truck-delivered; rail remains a later option.

---

## 11. Reconciled Taylor–Red Wash physical and service design

### Taylor hub

- Taylor is the rail/transload hub.
- Two 10-car transload tracks.
- One six-car liquid track.
- Heavy-freight hardstand.
- Warehouse/material-handling interface.
- ARU truck/drayage completes the last mile to Red Wash.

### Red Wash receiving

- Receiving and storage only in V1.
- No dedicated mine rail spur in V1.
- Approximately 10–14 days of acid and binder inventory.
- Steel laydown, scales, hazardous-material controls, custody/timestamp controls, and secure receiving.

### Service

- Two scheduled Taylor handling windows per week within BS&T's existing five-day service.
- Normal windows: Tuesday and Friday.
- Default interchange-receipt-to-empty-release cycle: 72 hours.
- Operating target: 36–48 hours.
- Steel/project cars may extend to 96 hours.
- Acid and binder on-time target: 95%.
- No unassigned demurrage; responsibility follows documented cause.
- Custody timestamps at every handoff.

---

## 12. Reconciled Red Wash integration capital and commercial treatment

- Total Phase I interface capital: **$8.5 million**.
- This sits inside, and does not add to, the previously approved **$15.0 million screening ceiling**.
- Approximately $3.0–$3.5 million is Red Wash-specific receiving, storage, safety, custody, and mine-interface capital.
- Approximately $5.0–$5.5 million is reusable ARU/Taylor strategic infrastructure.
- The exact internal split remains a derived engineering allocation; only the $8.5 million total is locked.
- The remaining $6.5 million of the ceiling is unapproved and gated to expansion/qualification.
- The $8.5 million program is separate from ARU's $11.0 million catch-up program.

### Commercial model

- Five-year arm's-length intercompany logistics agreement.
- No volume guarantee.
- No preferential treatment.
- Red Wash may use outside carriers when ARU is not competitive or qualified.
- ARU owns reusable Taylor/multi-customer assets.
- Red Wash owns mine-specific assets.
- Market pricing reviewed and indexed annually.
- Intercompany ARU revenue and Red Wash expense eliminate on Sable Harbor consolidation.
- Planning economics: approximately $875,000 annual ARU revenue and $365,000 incremental EBITDA at the normalized 225-car case.
- The high-level rate skeleton is preserved, but the detailed rate card still requires a mechanical schedule to reconcile the $875,000 total. This is an implementation item, not a new strategic decision.

---

## 13. Reconciled geography

- Red Wash is a fictional underground uranium mine in the Great Divide Basin / Red Desert, Sweetwater County, Wyoming, north of Wamsutter.
- Current mapping anchor: **42.2200° N, 108.1800° W**.
- The Carbon County point **42.3127° N, 106.9213° W** and related maps are superseded for current use.
- Wamsutter is the real-reference national-network/Class I interchange corridor.
- Taylor is the fictional BS&T shop/yard town and operating hub between Red Wash and Wamsutter.
- Approximately 40 route-miles remains a planning scale until the GIS alignment is engineered.
- No straight-line route is canonical. Exact line vertices, yard geometry, interchanges, branches, structures, and mileposts remain GIS engineering work.

---

## 14. Graphics boundary

The exact user-approved ARU and BS&T images are authoritative. They must not be redrawn from prose or replaced with the repository's current geometric derivatives unless byte/visual identity is established.

Graphics were not examined during this reconciliation. The later package phase must:

1. identify the two exact approved source files;
2. hash them;
3. compare them with current repository assets;
4. designate exact masters;
5. supersede nonmatching derivatives;
6. regenerate maps and collateral only after the text/data reconciliation is implemented.

---

## 15. Remaining bounded open fields

These are not contradictions and do not require reopening the business model:

- exact legal suffixes and jurisdictions for ARU and BS&T;
- exact BS&T formal rename date;
- exact ARU formation/reorganization date within the late-1980s/early-1990s window;
- named ARU seller and exact ownership generation immediately before Sable Harbor;
- complete named customer/contract register;
- exact asset and rolling-stock roster;
- exact fixed-asset, depreciation, working-capital, tax, and three-statement schedules;
- exact Taylor and BS&T GIS geometry;
- final uranium-custody authorization after qualification;
- detailed rate-card allocation supporting the $875,000 intercompany revenue case.

These can be completed as implementation details or explicitly left open. None changes the reconciled ARU/BS&T V1 architecture.

---

## 16. Implementation disposition

### Must be superseded on `main`

- ARU/BS&T $23.6M revenue / $20.3M cost scenario as selected-case inputs.
- ARU/BS&T full-case `OPEN` statements that are now resolved by user decision.
- 2026-Q1 first-discovery timing for ARU.
- Carbon County Red Wash selected-site scenario.
- Any Bloodstone-as-town references.
- Discarded Utah/Ballard & Thompson/Cane Creek origin material if present in any active-looking source.
- Any oversized $118M/335-FTE/14-locomotive ARU snapshot.

### Must be preserved

- No pre-existing Red Wash–ARU/BS&T relationship.
- External carriers handled all 2025 Red Wash movements.
- No automatic uranium custody.
- Operation first / proving ground second.
- Separate ARU/BS&T identity and operating authority.
- Red Wash and ARU separate books and accountability.
- All superseded records retained as clearly labeled history/provenance rather than silently deleted.

### No repository action authorized by this report

This report records reconciliation only. It does not authorize merging, opening or updating a PR, pushing to `main`, or packaging graphics.

---

## 17. Reconciliation conclusion

The ARU/BS&T business case is internally reconcilable.

The major collisions have defined resolutions:

1. **Discovery timing:** retime ARU discovery from 2026-Q1 to 2025-Q4 so the January 7, 2026 close is possible.
2. **Finance baseline:** supersede the $23.6M/$20.3M scenario with the $42.0M/$9.8M selected case and implement separate ARU segment books.
3. **Transaction bridge:** preserve $49.5M total seller value while recognizing $48.0M buyer-funded equity consideration after the $1.5M excess-cash bridge.
4. **Red Wash volume:** 225 recurring cars / 300 design allowance replaces 5,000 as the mine-volume case; 5,000–7,500 remains BS&T system expansion headroom.
5. **Capital:** $11.0M ARU catch-up capital and $8.5M Phase I Red Wash interface capital are separate; the latter remains inside the $15.0M ceiling.
6. **Custody:** U3O8 may be rail-eligible later, but direct custody remains unauthorized until qualification gates pass.
7. **Geography:** Great Divide Basin/Sweetwater/Taylor/Wamsutter supersedes Carbon County/Bloodstone-town geography.
8. **History:** approved Wyoming coal-origin history controls; discarded Utah and unrelated older origin concepts do not.

The reconciliation phase is complete. Graphics and push packaging remain deliberately unstarted pending the user's instruction after review of this report.

# APPENDIX C — EARLIER MACHINE-READABLE RECONCILIATION LEDGER, VERBATIM

```json
{
  "record_id": "SH-ARU-REC-001",
  "version": "1.0.0-draft",
  "decision_cutoff": "2026-09-05",
  "repo_main_commit_reviewed": "8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd",
  "graphics_inspected_in_this_pass": false,
  "repository_write_authorized": false,
  "entities": {
    "parent": "Sable Harbor",
    "aru": "American Resource Utility",
    "bst": "Blood, Sweat & Tears Railway",
    "ownership_chain": [
      "Sable Harbor",
      "American Resource Utility",
      "Blood, Sweat & Tears Railway"
    ],
    "red_wash_separate_from_aru": true
  },
  "chronology": {
    "red_wash_close": "2025-07-18",
    "aru_discovery_period_reconciled": "2025-Q4",
    "aru_baseline_date": "2025-12-31",
    "aru_close": "2026-01-07",
    "seller_ceo_transition_months": 9
  },
  "aru_2025": {
    "revenue_usd": 42000000,
    "operating_expense_before_da_usd": 32200000,
    "normalized_ebitda_usd": 9800000,
    "employees": 131,
    "sustaining_capex_usd": 3300000,
    "deferred_catch_up_capex_usd": 11000000
  },
  "bst_2025": {
    "route_miles_approx": 40,
    "revenue_carloads": 9000,
    "revenue_usd": 15500000,
    "operating_expense_before_da_usd": 14000000,
    "normalized_ebitda_usd": 1500000,
    "employees": 58,
    "locomotives_owned": 4,
    "locomotives_generally_available": 3,
    "locomotives_normally_required": 2,
    "service_days_per_week": 5,
    "incremental_capacity_carloads_low": 5000,
    "incremental_capacity_carloads_high": 7500
  },
  "transaction": {
    "enterprise_value_usd": 62000000,
    "seller_equity_value_usd": 49500000,
    "new_acquisition_debt_usd": 22500000,
    "new_revolver_capacity_usd": 5000000,
    "new_revolver_draw_at_close_usd": 0,
    "escrow_usd": 3000000,
    "minimum_cash_retained_usd": 2000000,
    "excess_cash_bridge_usd": 1500000,
    "debt_refinanced_usd": 13500000,
    "finance_leases_retained_usd": 2500000,
    "sable_harbor_closing_equity_before_fees_usd": 39000000,
    "retention_pool_usd": 500000,
    "seller_ceo_consulting_usd": 225000,
    "earnout": false,
    "seller_rollover": false
  },
  "red_wash": {
    "location": {
      "region": "Great Divide Basin / Red Desert",
      "county": "Sweetwater County",
      "state": "Wyoming",
      "latitude": 42.22,
      "longitude": -108.18,
      "fictional_in_real_geography": true
    },
    "superseded_location": {
      "county": "Carbon County",
      "latitude": 42.3127,
      "longitude": -106.9213
    },
    "town_hub": "Taylor, Wyoming",
    "bloodstone_as_town_superseded": true,
    "v1_direct_mine_spur": false,
    "recurring_rail_loads": 225,
    "design_allowance_rail_loads": 300,
    "intercompany_revenue_usd": 875000,
    "incremental_ebitda_usd": 365000,
    "phase_1_capex_usd": 8500000,
    "integration_capex_ceiling_usd": 15000000,
    "product_rail_eligible": true,
    "direct_uranium_custody_automatic": false,
    "service_term_years": 5,
    "scheduled_windows_per_week": 2,
    "default_car_cycle_hours": 72,
    "critical_inventory_buffer_days_low": 10,
    "critical_inventory_buffer_days_high": 14
  },
  "production_cases": [
    {
      "case": "2026_rehabilitation",
      "ore_short_tons": 175000,
      "u3o8_produced_lb": 547400,
      "state": "LOCKED"
    },
    {
      "case": "normalized_target",
      "ore_short_tons": 225000,
      "u3o8_produced_lb_approx": 703800,
      "state": "LOCKED_PLANNING_TARGET_YEAR_OPEN"
    },
    {
      "case": "future_expansion",
      "ore_short_tons": 300000,
      "u3o8_produced_lb_approx": 880000,
      "state": "LOCKED_OPTION_NOT_COMMITTED"
    }
  ],
  "superseded": [
    "FIN-Q-005 ARU/BS&T 2026 external revenue USD 23.6M",
    "FIN-Q-006 ARU/BS&T 2026 operating cost USD 20.3M",
    "ARU acquisition enterprise value USD 76M",
    "Red Wash Carbon County location 42.3127,-106.9213",
    "Bloodstone as current railroad town",
    "5000 annual Red Wash loaded railcars as forecast",
    "375 recurring Red Wash rail loads",
    "categorical rule that concentrate stays off rail",
    "2026-Q1 first discovery of ARU/BS&T"
  ],
  "history_source_recovery_required": [
    "original railroad corporate name",
    "exact pre-1954 founding year",
    "final approval status and wording of proposed 1907 wreck",
    "final approval status and wording of proposed 1916 mine fire",
    "1970s second industrial-line details",
    "exact ARU predecessor consolidation chronology",
    "exact date BS&T became wholly owned by ARU"
  ]
}
```
