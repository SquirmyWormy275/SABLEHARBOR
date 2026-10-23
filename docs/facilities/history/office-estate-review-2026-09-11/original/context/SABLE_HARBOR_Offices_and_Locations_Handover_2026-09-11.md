# SABLE HARBOR — Offices, Facilities, and Locations Handover

You are continuing the development of SABLE HARBOR's offices, facilities, and geographic operating model. Read the repository, identify what is already decided, develop the remaining locations into a coherent enterprise estate, and help me settle the material choices. After approval, implement and reconcile the decisions in the repository.

Repository: https://github.com/SquirmyWormy275/SABLEHARBOR

The repository is the source of truth. This handover is an orientation and work instruction; it does not supersede accepted canon or establish new locations. This project is SABLE HARBOR. Do not import assumptions from STRATHEX, KYTHEREX, NAILEX, or unrelated projects.

## 1. Objective and scope

Develop a complete, practical account of where Sable Harbor's people and capabilities operate: corporate offices, business-line bases, shared workplaces, teaching facilities, research compounds, industrial sites, field deployments, and computing facilities.

The primary task is physical offices and locations. Also reconcile organizational offices, such as the CFO, General Counsel, or Head of J2, to their actual responsibilities and workplace needs. An unnamed office does not automatically require a new department, employee, or building. Do not turn this task into an unrelated exercise in naming every employee or filling every missing joining year.

I want concrete proposals: what each place does, why it belongs there, who uses it, what capacity it needs, how it is operated, and what it costs. Treat Sable Harbor as the substantial enterprise established by the repository. Avoid generic small-business assumptions, decorative campuses without a purpose, and vague management prose.

Work autonomously on research, reconciliation, technical details, and draft recommendations. Bring me the material choices with a preferred answer. Once I approve a choice, preserve it accurately and move on; do not repeatedly reopen it.

## 2. Verified starting point — refresh before relying on it

On September 11, 2026, current main was `2b52933132e028bf5d9c9a8c151bb45cb0f19597`.

- PR #117 merged the organization-chart redesign.
- PR #118 merged the six approved J2 leaders and updated the chart publication.
- The current publication was revision 1.1.0: 40 chart families, 57 pages, 208 display records, and 51 unique current named people.
- The source and chart register had complete matching coverage. The remaining problem includes unresolved source facts, not merely missing graphic exports.
- A scan found 99 entity/function display records with a location marked as unrecorded. **That is not 99 missing buildings or 99 site-selection decisions.** Many records are functions, systems, programs, or products that may share a workplace or have no independent physical location.
- Issue #19 remains open for residual J2 personnel matters after the six approved appointments were implemented.

Retrieve current main, record its full SHA, inspect relevant open and recently merged PRs/issues, and compare later changes against this baseline. Read files from a consistent revision. Do not operate on an old checkout without detecting its age. If a path has moved, locate its successor.

Do not request repository information already available through the connected GitHub tools. If access genuinely fails, identify the exact failed operation and continue with accessible sources without pretending they are current.

## 3. Required source reading

Read the following sources in full and follow their controlling references as needed. Inspect current sources rather than substituting a PR description or an older generated report.

### Authority, organization, and people

- `MAINTAINERS.md` and any applicable `AGENTS.md`.
- `docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md`.
- `docs/internal/OPEN_CANON_AND_HYGIENE_ISSUE_INDEX.md`.
- `docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md`.
- `docs/structured/corporate_headquarters_closeout_2026-09-03.json`.
- `docs/governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md`.
- `docs/governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md`.
- `docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md` and `docs/structured/j2_leadership_2026-09-10.json`.
- `docs/j2/J2_CHARTER.md`, `docs/j2/J2_ESTABLISHMENT.md`, `docs/j2/J2_HEADQUARTERS.md`, and `docs/j2/EDUCATION.md`.
- `docs/organization/README.md`, `CHART_GOVERNANCE.md`, `DISPLAY_INVENTORY.md`, `UNRESOLVED_AND_EXCLUDED.md`, `CANON_TRACEABILITY_MATRIX.md`, and `SOURCE_LOCK_EXCEPTIONS.md`.
- `docs/organization/source/chartbook.json` and `docs/organization/ORGANIZATION_MAP_REGISTER.json`.

### Geography and operating sites

- `geospatial/README.md`.
- `geospatial/sources/catalog.json` and the applicable accepted operating-decision sources it references.
- `geospatial/registers/SITE_REGISTER.csv`.
- `geospatial/registers/GEOGRAPHIC_DECISION_REGISTER.md`, `GEOGRAPHIC_CONFLICTS.md`, and `OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md`.
- `geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md`, `SITE_SELECTION_EVIDENCE.md`, and `CANON_CONFLICT_EVIDENCE.md`.
- Relevant current geography/closeout records for Bedford/Cradle, Willow/Klein/the Fort, ARU/BS&T, Red Wash, Blackridge, and external hosts.
- `industrial/source/entities.json`, `industrial/source/operations.json`, and `industrial/source/geography/network.geojson` where they govern industrial identities, facilities, or geometry.

### Hosting, services, staffing, and economics

- `docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md`.
- `docs/canon/THIRD_PARTY_SERVICES_IMPLEMENTATION_SCOPE_2026-09-09.md`.
- `docs/internal/development/THIRD_PARTY_SERVICES_RECONCILIATION_2026-09-09.md` and `THIRD_PARTY_SERVICES_IMPLEMENTATION_2026-09-09.md`.
- `enterprise/services/README.md`, its current source registers, operating assumptions, and generated comparison/report.
- The current financial, facilities, workforce, and business-operations sources referenced by those records, including applicable `enterprise/operations/` material.

Search the whole repository for location statements, office references, facility IDs, disputed geography, staffing/capacity assumptions, and unresolved issues beyond this starting list. An org-chart label is only one source surface.

## 4. Preserve existing decisions

Reconfirm these against current main; do not reopen them simply because a display field is empty:

- Corporate headquarters is in **Sacramento, California**. Its physical doctrine calls for a substantial, enduring institutional campus with useful collaboration, project, and education space. Preserve its approved visual reference and genuinely hybrid work doctrine. Sacramento headquarters does not automatically establish the separate address of every corporate function.
- ESS is an administrative umbrella. It does not make the Chief of ESS a super-executive. J2 remains outside ESS; Internal Audit retains its independent Board accountability; CISO and substantive officers retain their established authority boundaries.
- Product engineering remains with the businesses. Atlas Meridian retains its dedicated product organization. Advisory uses its accepted common bench and practices.
- J2's 237 authorized billets are already established. Distinguish authorized billets, actual occupants, visiting cohorts, deployed personnel, simultaneous attendance, and seats. Do not count Education or shared support twice.
- Preserve the six approved J2 leaders below. Company joining years are not dates of office appointment or commission.

| Person | Office | Company joining year |
| --- | --- | ---: |
| Jonathan Goldstryker | Head of J2 | 2020 |
| Amanda Chenahot | Deputy Head of J2 | 2021 |
| Mara Hammer | Head of Contact | 2021 |
| Anika Trish | Head of Judgment | 2021 |
| Grant Kohrs | Head of Orientation | 2020 |
| Brett Calder | Head of Education | 2021 |

- Primary production direction is **Sable Harbor-owned computing equipment and operating stack in professional third-party colocation**, with managed cloud available for transition, burst, and appropriate services. This does not establish a provider, region, rack count, or owned data-center building.
- Recovery requires a separate geographic and operational failure domain. Restricted institutional/Alexandria infrastructure requires its distinct control boundary. Development/evaluation is hybrid; industrial sites require appropriate locally controlled systems.
- Existing industrial sites, external-host relationships, acreage decisions, and transport restrictions remain controlling. Do not convert an external host into a subsidiary, move an accepted industrial anchor for office convenience, or create a Red Wash rail spur.
- Geographic study areas, illustrative buildings, screening coordinates, actual operating locations, and historical sites are different statuses. Preserve those distinctions.

## 5. First deliverable: a reconciled gap inventory

Before proposing a city for everything, produce one comprehensive inventory with stable IDs and source references. Classify every relevant item as:

1. Established location; propagate a supported fact that was omitted from a derivative.
2. Existing site with an unresolved assignment of functions or people.
3. Shared/distributed/field-based capability requiring an explicit operating-base model.
4. Genuine new office, campus, facility, or hosting-location decision.
5. Exact parcel, address, footprint, occupancy date, or tenure detail still needed within an established region.
6. Historical, external, provisional, superseded, or nonphysical record requiring accurate labeling.

Separate legal domicile/registered office, executive headquarters, employee working base, service territory, customer/host site, and data-hosting region. Distinguish physical colocation from organizational reporting. A product, portal, committee, discipline, or software system does not require its own building.

For organizational offices, record existing remit, reporting/independence boundaries, occupant status, staff support, working base, and any unresolved substantive decision. Existing Finance, Legal, P&C, and other teams must be reused where their responsibilities already cover the work.

Refresh the open geography list. Prior records identified J2 Education, exact Blackridge siting, Klein/Fort occupancy history, provisional Reno/Elko/Tucson offices, exact Bedford/Demotte/Kelly Gang parcels, Wallaby/Glasshouse sites, historical offices, and corporate hosting geography. These are investigation leads, not instructions to create or relocate all of them.

## 6. Develop one coherent estate proposal

Build a recommended enterprise-wide plan, not disconnected city lists. Cover headquarters and shared offices; Foundry Field/Foundry, Atlas Meridian, Advisory and their working-base needs; J2 and Education; research/industrial facilities; field deployments; and all six accepted hosting classes.

For every material unresolved facility or office, specify:

- Plain-English purpose and actual work performed.
- Owning entity, operationally accountable function, groups served, and shared arrangements.
- Recommended city/region and, where useful, a district or candidate area.
- Whether to colocate, occupy an existing site, lease, own, use a provider, deploy temporarily, or operate without a dedicated premises.
- Current-state evidence, proposed future state, opening/transition sequence, and maturity status.
- Staff/visitor population, realistic concurrent attendance, usable space, specialized rooms/equipment, utilities, connectivity, physical protection, and support coverage.
- Site-specific dependencies: talent, customers, travel, industrial adjacency, research partners, airport/access, utilities/carriers, hazards, recovery separation, and other constraints that materially affect the choice.
- Financial treatment: one-time fit-out/equipment/relocation, recurring facilities/colocation/utilities/connectivity/support, refresh and expansion, with assumptions and ranges.
- Which existing people, space, equipment, and expense are reused; what is incremental; and how shared costs are allocated without duplication.
- A preferred option, credible alternatives where they change the decision, and a clear rationale.

Sable Harbor is synthetic. You may develop detailed fictional proposals and planning assumptions, clearly labeled as such. Use current primary sources to check real geographic, infrastructure, property-market, and hazard claims when they affect a recommendation. Do not describe an actual property as acquired, leased, available, permitted, or occupied without supporting evidence; distinguish modeled sites from real transactions.

Do not force an exact parcel before the operating brief is mature. Do not treat an attractive map point as a completed engineering or property-rights investigation. For computing locations, justify capacity and recovery separation rather than guessing racks or using straight-line distance as the whole resilience argument.

## 7. Decision discussion

Do the source review and develop the complete draft before returning routine questions to me. Start the discussion with:

- The main revision inspected and scope actually reviewed.
- What is settled, what can be reconciled directly, and what needs a new owner decision.
- Your recommended estate model in a concise table.
- The first material decision, your recommendation, and its consequences.

Then work through material decisions one at a time, especially in voice. Maintain the full numbered queue internally and preserve each accepted answer, correction, dependency, and deferred item. Do not ask me to rediscover facts in the repository or repeatedly list the same choices. Batch routine implementation judgments yourself.

Prioritize decisions that resolve multiple gaps, such as shared headquarters occupancy, product/Advisory working bases, J2/Education siting, and hosting geography. Do not reopen accepted locations or personnel unless current controlling sources expose a real conflict or I explicitly request a change.

## 8. Repository implementation and completion

You are authorized to inspect sources, perform research, draft the complete proposal, prepare an isolated branch/PR, and reconcile supported existing facts. New substantive geography, facilities, ownership, funding, staffing, or organizational decisions remain proposals until approved. Implement approved decisions without repeatedly requesting permission for routine edits.

Maintain an organized decision record, structured office/facility/location register, source mapping, cost/capacity bridge, and residual-question list. Reuse existing canonical registers where appropriate instead of creating competing sources of truth. Distinguish approval date, modeled opening date, historical occupancy date, and actual implementation status.

Update affected canon, geography sources, site registers, org-chart display data, service dependencies, financial assumptions, and navigation consistently. Preserve immutable finance inputs and historical releases; use the repository's successor/addendum mechanisms. Keep proposals out of current factual chart fields until accepted.

Preserve the approved chart design and logos. Business cards show only name, location, and a brief description of actual work; people cards show only name, title, and joining year. Update the visual master and corresponding sources together through the current supported workflow. Do not make a stale publication pass by changing its checksum alone.

Run the applicable repository, geography, publication, organization, and financial validation required by the current maintainers/workflows. Regenerate affected outputs and visually inspect changed charts/maps/publications. Report executed results, skips, and remaining failures accurately. Recheck current main before merge and preserve concurrent work. Merge approved changes when existing session authorization and required gates permit it.

Nothing is closed solely because it was discussed in chat. Final delivery must identify accepted commits/PRs, controlling paths, generated artifacts, validation evidence, and every remaining substantive limitation. If the session is planning-only or ends before implementation, produce a precise implementation handback containing the exact accepted decisions, affected IDs/files, unresolved questions, and next actions.

Begin now with the repository inspection and full gap reconciliation. Give me your first concrete recommendation after doing that work.
