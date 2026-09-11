# CODEX HANDOVER — CLOSE OUT SABLE HARBOR HEADCOUNT / CAMPUS / BUILDING / FLOOR-PLAN / ATLAS WORKFLOW

You are taking ownership of an unfinished SABLE HARBOR repository workline. Your job is to recover every relevant partial artifact, establish the authoritative headcount-and-space program, finish the Sacramento headquarters campus and building plans, extend the same disciplined mapping system across every applicable facility in the SABLE HARBOR universe, make the atlas drill down to the saved site/building/floor assets, validate the complete package, and close the workline in GitHub.

Do not stop after an inventory, another planning memo, a sample building, an atlas shell, or a status update. Do not tell me the conversation is too long. Use the repository and commits as durable state, commit in coherent increments, and continue until the definition of done below is actually satisfied or a specific external blocker makes completion impossible.

Repository: `https://github.com/SquirmyWormy275/SABLEHARBOR`

The repository is the canonical source of truth. This prompt carries forward explicit user decisions and execution requirements, but it does not authorize silently contradicting newer accepted canon. If a genuine conflict exists, document both sources and apply the repository's authority rules. Do not import STRATHEX, KYTHEREX, NAILEX, or unrelated-project assumptions.

## 1. Execution authority and expected behavior

- Begin with repository inspection; do not ask me to provide information that is already in GitHub.
- You are authorized to create/reuse an isolated branch, modify the necessary repository files, generate and save source plus rendered artifacts, push commits, open or update the workline PR, resolve ordinary conflicts, run validation, and merge after required gates are green.
- Use best judgment for normal design, file organization, sizing, code, and reconciliation decisions. Ask only when a genuinely material unresolved canon choice would produce meaningfully different outcomes and cannot be represented safely as a labeled planning assumption.
- Do not reopen approved personnel, organizational, site, branding, or visual decisions merely because an older derivative is incomplete.
- The main agent must read all controlling repository sources before delegating. Parallel subagents are authorized and encouraged for bounded facility packages, but partition their outputs so two agents do not edit the same registers/generators. The main agent owns reconciliation, integration, and QA.
- Preserve unrelated concurrent work. At the September 11 snapshot, PR #119 (runtime estate) and PR #120 (enterprise security/vendor direction) were open. Read them when they contain relevant current facts, but do not absorb, rewrite, merge, or close their worklines as part of this task unless current GitHub state shows they have already become controlling main.
- Communicate progress with evidence: branch, commits, files completed, render counts, validation results, and the exact remaining queue. Do not substitute repeated promises for execution.

## 2. Starting snapshot — verify live state before relying on it

At the last inspection on September 11, 2026:

- `main` was `2b52933132e028bf5d9c9a8c151bb45cb0f19597`.
- PR #117 had merged the organization-chart redesign.
- PR #118 had merged the six approved J2 leaders and refreshed the organization publication.
- The then-current organization publication was revision 1.1.0: 40 chart families, 57 pages, 208 display records, and 51 unique current named people.
- The chart source and chart register had complete matching coverage. The remaining problem was unresolved or unpropagated source facts, not simply missing image exports.
- A scan found 99 entity/function display records whose location was unrecorded. That is not 99 missing sites or buildings. Many are functions, systems, committees, programs, products, or shared capabilities.
- Issue #19 remained open for residual J2 personnel matters. Do not turn this facilities task into a personnel-naming exercise.
- Issue #106, `Geo: complete precise site geometry and historical occupancy records`, remained the important geography boundary. It requires supported geometry or an explicit unresolved disposition, temporal occupancy evidence, precision/fictionality classification, stable IDs, regenerated registers/layers/maps, and preservation of accepted constraints.

Refresh all of that. Record the current main SHA and the exact source revision used for the build. Inspect open and recently merged PRs/issues and all relevant remote branches before editing.

## 3. Recover stranded work before building

Perform explicit branch/commit archaeology. Do not assume an old branch should be merged wholesale, and do not discard useful unmerged assets without reviewing them.

Known branches requiring inspection include:

- `docs/organization-maps-v0.1` at the old snapshot `57339ee47c1b23a41fde5f02fb80cad77ee286fe`; it was 16 commits ahead and roughly 320 behind current main. Much of its organization work has newer successors on main. Treat it as salvage evidence, not a merge candidate.
- `feature/geospatial-execution-current` at `2849424fd25dd626d1ea2523add65a374f884457`; it was materially behind main. Compare its map/build/release work against current `geospatial/` and salvage only non-superseded content.
- `feature/master-geospatial-package` at `7471ba0f405e94e22813b03890d950f5a8aa1582`; also materially behind main. Review its constraint, source, schema, and build work without overwriting current accepted geography.
- `cleanup/company-org-charts-2026-09-09` and any successor/related org-chart branches.
- `advisory-atlas-rebuild` at `043d7715646c860b79dbe6def58b5f7e3cf36af3`; its name refers primarily to Atlas Meridian/advisory work, so do not confuse it with the geographic atlas. Inspect only for relevant estate/function facts.
- Any newer branch, stash, PR, workflow artifact, or commit whose name or files mention headcount, office, location, campus, facilities, buildings, floor plans, organization, geospatial, map, or atlas.

Create a short recovery ledger listing each candidate, its relationship to current main, relevant files, and disposition: `reuse`, `port selectively`, `superseded`, `unrelated`, or `needs decision`. This ledger is evidence for the closeout, not the final deliverable by itself.

## 4. Required reading

Read applicable `AGENTS.md`, `MAINTAINERS.md`, repository packaging/delivery policy, and current build instructions first. Then read the following current sources in full, following controlling references and successors:

### Organization, governance, and people

- `docs/canon/CORPORATE_HEADQUARTERS_CLOSEOUT_2026-09-03.md`
- `docs/structured/corporate_headquarters_closeout_2026-09-03.json`
- `docs/governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md`
- `docs/governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md`
- `docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md`
- `docs/structured/j2_leadership_2026-09-10.json`
- `docs/j2/J2_CHARTER.md`, `J2_ESTABLISHMENT.md`, `J2_HEADQUARTERS.md`, and `EDUCATION.md`
- `docs/organization/README.md`, `CHART_GOVERNANCE.md`, `DISPLAY_INVENTORY.md`, `UNRESOLVED_AND_EXCLUDED.md`, `CANON_TRACEABILITY_MATRIX.md`, and `SOURCE_LOCK_EXCEPTIONS.md`
- `docs/organization/source/chartbook.json`
- `docs/organization/ORGANIZATION_MAP_REGISTER.json`
- Current chart generator/validator sources under `scripts/`, `tools/organization/`, and `.github/workflows/`

### Geography, facilities, and maps

- `geospatial/README.md`
- `geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md`, `DEFINITION_OF_DONE.md`, `DATA_MODEL.md`, `CARTOGRAPHIC_STANDARD.md`, `SITE_SELECTION_EVIDENCE.md`, `CANON_CONFLICT_EVIDENCE.md`, `TEMPORAL_MODEL.md`, and `PROVENANCE_AND_REPRODUCIBILITY.md`
- `geospatial/sources/catalog.json` and every accepted operating-decision source governing included sites
- `geospatial/registers/SITE_REGISTER.csv`, `GEOGRAPHIC_DECISION_REGISTER.md`, `GEOGRAPHIC_CONFLICTS.md`, `OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md`, and `PROGRAM_DISPOSITION.json`
- `geospatial/geojson/facilities.geojson`, `sites.geojson`, `industrial_facilities.geojson`, `historical_sites.geojson`, and related network layers
- `geospatial/maps/MAP_MANIFEST.json` and the current atlas/map outputs
- `industrial/source/entities.json`, `industrial/source/operations.json`, and `industrial/source/geography/network.geojson`
- Current closeout records for Sacramento HQ; J2; Willow/Klein/the Fort; Cradle/Bedford; ARU/BS&T; Red Wash; Blackridge; Foundry/Foundry Field; Atlas Meridian; Advisory; Demotte; Kelly Gang Mining; Wallaby/Glasshouse; historical and external hosts

### Staffing, services, hosting, and economics

- Current third-party services sourcing/implementation canon and reconciliation documents
- `enterprise/services/README.md` and its current registers/reports
- Applicable workforce, facilities, financial, security, resilience, and business-operations sources under `enterprise/`
- Current PR #119/main successor for accepted compute-location facts

Search the entire repository, including generated-source manifests and issue references. Read files from a consistent revision and locate successors when paths moved.

## 5. Locked decisions and boundaries

Preserve these unless a later explicit user decision or accepted main record clearly supersedes them:

### Sacramento headquarters

- Sacramento, California is the primary corporate operating base and management/J2 headquarters.
- The intended setting is the Sacramento Railyards / River District seam. The working campus envelope is a fictional/modelled approximately 8–15 acre site until a supported exact polygon or accepted synthetic parcel is recorded.
- All headquarters buildings and functions assigned to this campus must be planned as one integrated campus. Do not design each building or floor independently.
- The physical doctrine is a substantial, enduring institutional campus with useful collaboration, project, education, and hybrid-work space.
- Approved aesthetic: advanced research campus / restrained monumental modernism / durable modern industrial. It should feel formidable, serious, quiet, and permanent: strong lines, honest high-quality materials, controlled landscaping, and a signature SABLE HARBOR element. It must not be gaudy, theme-park-like, or filled with decorative pseudo-technical clutter.
- Produce an overall master campus plan first, then derive every building plan and every floor from it.
- Do not place the primary Alexandria/enterprise production data center in the Sacramento campus plan. The latest direction places primary owned hardware/stack in professional third-party colocation in the Tahoe–Reno/Storey County area, with recovery outside the Reno failure domain. The campus may include network/security operations, local edge systems, secure communications, and appropriate equipment rooms, but not a fictional completed headquarters data center.

### Organizational doctrine

- Board governs; CEO directs; ESS administers and controls shared services; business lines operate; Internal Audit assures independently; J2 remains institutionally outside ESS.
- ESS is the administrative umbrella for People & Culture, Finance, technology, Legal, Compliance, Risk, Procurement, Safety, Quality, Security, Resilience, Facilities/Workplace, and related enterprise support. This does not make the Chief of ESS a super-executive or erase substantive officers' authority.
- Internal Audit remains functionally accountable to the Board/Audit & Compliance boundary.
- Product engineering remains with the businesses. Atlas Meridian retains its dedicated product organization. Advisory retains its accepted common bench/practice model.
- “Grand Scheme” is not a headquarters department. Do not invent a centralized strategy department merely to fill space.
- An unnamed office or role-family entry does not automatically authorize a new person, department, suite, or building.

### J2

- J2 has 237 authorized billets. That is not the same as named current occupants, Sacramento daily attendance, resident population, training cohorts, deployed personnel, or assigned desks.
- Education and shared support must not be counted twice.
- Preserve the approved leaders and company joining years:

| Person | Office | Joining year |
| --- | --- | ---: |
| Jonathan Goldstryker | Head of J2 | 2020 |
| Amanda Chenahot | Deputy Head of J2 | 2021 |
| Mara Hammer | Head of Contact | 2021 |
| Anika Trish | Head of Judgment | 2021 |
| Grant Kohrs | Head of Orientation | 2020 |
| Brett Calder | Head of Education | 2021 |

Joining year is not office-appointment date, commission date, occupancy date, or construction date.

### Geographic truth

- Distinguish legal domicile, registered office, executive headquarters, employee working base, service territory, industrial operating site, external/customer host, historical site, recovery region, and physical colocation.
- Distinguish actual, accepted synthetic, proposed, illustrative, study-area, external, historical, superseded, and unresolved geometry. Never silently promote one status to another.
- Do not claim acquisition, ownership, occupancy, lease, permitting, construction, or completion without the appropriate source/status.
- Do not convert external hosts into subsidiaries, move an accepted industrial anchor for office convenience, or create the rejected Red Wash rail spur.

## 6. Build one authoritative headcount-and-space bridge

Before drawing final floor plans, create a structured, reviewable headcount/occupancy/space model. Do not use a single ambiguous `headcount` number.

For every entity, function, site, building, and floor, distinguish at minimum:

- current named employees supported by source records;
- authorized billets/positions;
- vacant or unnamed authorized roles;
- proposed future positions by planning horizon;
- remote/distributed/field/deployed staff;
- resident occupants where applicable;
- visitors, customers, trainees, and cohort peaks;
- shift population and maximum concurrent attendance;
- assigned desks, shared/hot desks, touchdown seats, training seats, meeting seats, and special-use capacity;
- current 2026 need versus five-year and ten-year planning capacity.

Every number needs a source reference or a plainly labeled planning assumption. Reconcile totals vertically and horizontally so people shared between functions are not duplicated. Preserve the difference between the 51 named-current-person chart population, company headcount, the J2 billet authorization, contractors/nonemployee directors, unnamed roles, and physical seats.

Create a machine-readable register and a human-readable bridge. The human-readable version must explain why authorized population, actual people, peak attendance, and seats differ. Include a discrepancy report that fails validation when rollups do not reconcile.

Use the space model to derive net assignable area, shared/support area, building gross area, circulation/service/core factor, expansion reserve, parking/loading assumptions, and specialized utility/security requirements. Do not make floor areas look precise without documenting the basis.

## 7. Establish the complete facility/building coverage matrix

Build a stable-ID coverage matrix before rendering. Inventory every physical or potentially physical record and classify it as:

1. campus requiring a master site plan;
2. operating/industrial site requiring a site plan;
3. occupied building requiring building and per-floor plans;
4. small structure requiring a structure plan or documented exemption;
5. external/host/provider location requiring only the permitted context view;
6. distributed/field/nonphysical capability requiring no building;
7. historical/former site requiring historical treatment;
8. proposed/unresolved item requiring a labeled placeholder or decision record.

At minimum, reconcile the expected universe represented by current sources: Sacramento headquarters and J2/Education; Foundry/Foundry Field; Atlas Meridian and Advisory working bases; Willow/Klein/the Fort in the Hazelwood/Pittsburgh context; Cradle/Bedford and its current Kanawha/Fairmont geography; ARU and BS&T sites/network; Red Wash mine/site buildings; Demotte; Kelly Gang Mining; Blackridge; Wallaby/Glasshouse; provisional/former offices; corporate hosting locations; and all external hosts.

This list is a search scope, not authority to invent missing locations. Current main decides which names, sites, ownership relations, and statuses are active. If a record does not warrant a floor plan, the matrix must say why. Nothing may disappear merely because it is hard to draw.

## 8. Design and generate the Sacramento campus coherently

Produce the Sacramento program in this order:

1. functional adjacency and separation matrix;
2. population/attendance/seat model;
3. campus program and area schedule;
4. security/public-to-restricted zoning concept;
5. circulation, deliveries, emergency access, parking, transit/bicycle/pedestrian access, landscape/stormwater, service yard, utilities, and expansion strategy;
6. master site plan and building footprints;
7. building stacking diagrams;
8. one plan per floor for every building;
9. campus context and phasing/construction-status views;
10. visual and numerical reconciliation.

The campus must operate plausibly. Public/visitor, executive/Board, ordinary office, J2-restricted, Education/training, service/loading, security, and after-hours paths must make sense. Buildings must have consistent footprints, cores, structure, vertical circulation, plumbing/service stacking, egress, accessibility, and mechanical/support concepts across floors. Room labels must describe actual work. Avoid giant empty atria, impossible corridors, arbitrary glass boxes, repetitive generic rooms, and decorative “AI” props.

Each floor must be its own saved image, exactly as requested. Also retain an editable/vector source. Use a consistent title block with stable site/building/floor ID, name, revision, date, status, scale/scale caveat, north/reference direction where applicable, gross area, planned peak occupancy, and legend. Site plans need north arrow, scale, access/circulation legend, property/status boundary, and clear differentiation of existing versus proposed/modelled elements.

The September 2026 state must be explicit. A planned shell, fit-out phase, future wing, or proposed acquisition must not appear complete merely because it is drawn. Include a timeline/status schedule tied to the structured source rather than freehand labels.

## 9. Build every other applicable facility package

After the Sacramento master establishes the graphic and data standard, apply it to every other item in the coverage matrix. Do not isolate the designs from their real organizational, industrial, geographic, and transport context.

Each applicable location package must contain:

- context map;
- site/campus plan;
- building register and program;
- per-building/per-floor plans where an occupied building is established or intentionally modelled;
- staffing/occupancy/capacity summary;
- status, ownership/tenure, temporal, precision, fictionality, and provenance fields;
- dependencies and constraints;
- editable source plus rendered SVG/PNG/PDF as supported by repository policy;
- direct atlas/index links to every saved underlying asset.

Industrial/mine/rail plans must respect current engineering and canon. Do not use office-floor styling to fabricate underground mine geometry, track, plant, or installed equipment. Where engineering detail is unknown, preserve the known envelope and mark the missing layer rather than drawing false precision.

## 10. Make the atlas a drill-down interface, not a dead PDF

The individual plans must exist independently in the repository before the atlas is treated as complete.

Build a data-driven navigation chain:

`enterprise atlas -> location -> campus/site -> building -> floor/structure plan`

Required behavior:

- Clicking/selecting a location opens its location record and saved maps.
- A campus/site view exposes its buildings/structures.
- A building view exposes each floor as a separate image and the applicable PDF/vector source.
- Historical, external, proposed, illustrative, and unresolved items are visibly differentiated.
- Every link target is generated from stable IDs/manifest data; no fragile hand-maintained duplicate index.
- Provide a repository-viewable static HTML atlas/index if allowed by repository policy, plus a portable PDF atlas with internal links/bookmarks where technically practical.
- Preserve the current geographic atlas and map-manifest system; extend or migrate it deliberately instead of creating an unrelated competing portal.
- Update repository navigation/README so a user can reach the atlas and every individual map without guessing paths.

The current repository already contains `geospatial/maps/SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc4.pdf`, `geospatial/maps/MAP_MANIFEST.json`, the `SH-MAP-*` assets, `geospatial/master/sable_harbor_master_v0.1.gpkg`, and the QGIS project. Reuse the established naming, stable-ID, build, manifest, provenance, and release patterns. Allocate successor IDs through the current register; do not invent a parallel naming system.

## 11. Source architecture and reproducibility

Use structured source data as the authority and generated drawings/publications as derivatives. At minimum, the model must support:

- sites/campuses;
- buildings/structures;
- floors/levels;
- functions/occupants;
- capacity and area measures;
- headcount/attendance categories and planning horizon;
- adjacency/security/access classification;
- geometry/status/precision/fictionality;
- effective dates and supersession;
- source/provenance references;
- artifact paths and atlas links;
- build revision and checksum/manifest integration.

Prefer extending current registers/schema/generators. Do not create two competing sources for the same fact. Generated binary outputs must be reproducible from committed source and code. Preserve historical releases and use successor/addendum mechanisms where repository policy requires them.

## 12. Visual standard

The previously approved organization-chart direction remains in force: dark Sable Harbor headers/cards, restrained neutral layout, professional typography, concise human wording, and business-line logos in the appropriate boxes. Business cards show only business name, location, and a brief description of what the business actually does. People cards show only name, title, and joining year.

Carry the same institutional discipline into maps and plans without turning floor plans into org charts. The result should be presentation-ready at a top-tier company or serious architecture/engineering briefing. Use consistent page sizes, margins, hierarchy, symbols, line weights, labels, legends, and revision blocks. No clipped labels, tiny unreadable text, overlaps, broken logos, illegible backgrounds, inconsistent building names, or “AI slop.”

Render and visually inspect every changed SVG/PDF/PNG/HTML surface. Programmatic validation alone is insufficient.

## 13. Repository implementation sequence

Use or create one isolated closeout branch from refreshed main, preferably `build/campus-facility-atlas-closeout-2026-09-11` unless an existing current branch already contains the authorized work.

Commit in coherent stages:

1. recovery ledger and coverage inventory;
2. authoritative headcount/occupancy/space bridge and validators;
3. Sacramento campus source/program/master plan;
4. Sacramento buildings and every per-floor asset;
5. remaining facility packages;
6. interactive atlas/navigation and manifest integration;
7. documentation, release notes, visual QA, and closeout evidence.

Rebase or merge current main safely before final validation, following repository policy. Do not overwrite unrelated dirty-worktree changes. Do not merge stale branches wholesale. Do not manipulate checksums simply to make stale publications pass.

Open/update a PR whose description includes:

- scope and authoritative base SHA;
- recovered/superseded branch disposition;
- headcount reconciliation summary;
- facility coverage totals and exemption counts;
- Sacramento campus/building/floor totals;
- complete artifact index;
- validation commands/results;
- visual QA evidence;
- known planning assumptions and truly unresolved external facts;
- issues closed or updated.

## 14. Validation and acceptance tests

Run every applicable current repository, organization, geography, publication, document, and financial validator. Add focused validation for this workline.

The build must fail if:

- a physical record lacks a coverage-matrix disposition;
- an included building lacks its required floors;
- a floor artifact is missing from the manifest or link graph;
- atlas links are broken or point to nonexistent artifacts;
- site/building/floor IDs are duplicated or unstable;
- building/floor areas or occupancies fail rollup reconciliation;
- named people, authorized billets, attendance, or seats are conflated;
- current/proposed/historical/external/illustrative status is absent or inconsistent;
- a generated artifact is stale relative to its structured source;
- Sacramento building footprints, floor stacks, functions, access zones, or capacity contradict the master plan;
- map geometries are invalid or required provenance/temporal fields are missing;
- changed visual assets fail render or contain clipping/overflow.

At minimum verify:

- JSON/CSV/GeoJSON/schema validity;
- geometry and QGIS/geospatial validation;
- organization source/register/render consistency;
- headcount and space rollups;
- complete map/floor manifest coverage;
- internal HTML/PDF/repository link integrity;
- deterministic regeneration or documented nondeterminism;
- current main compatibility;
- all required CI workflows green.

Render contact sheets or another efficient review surface, then inspect every page/image at readable resolution. Record issues found and corrected.

## 15. Hard definition of done

This workline is closed only when all of the following are true:

- Current main and all plausible partial-work branches/PRs/issues were inspected and recorded.
- Every relevant physical/nonphysical/historical/external/proposed record has a stable coverage disposition.
- One authoritative headcount/occupancy/seat/space bridge exists, reconciles, and does not manufacture people.
- Sacramento has a coherent master campus program and site plan derived from real functions and the authoritative population model.
- Every Sacramento building has a documented program and every floor has its own saved rendered image plus editable/source representation.
- Every other applicable facility/building in the SABLE HARBOR universe has the required context/site/building/floor package or a documented, justified exemption/unresolved status.
- Individual maps and layouts are saved independently; they are not trapped only inside an atlas.
- The atlas drills down from location to site/campus to building to floor with validated links.
- Structured sources, canon/registers, maps, organization displays, financial/capacity assumptions, manifests, navigation, and generated outputs agree.
- September 2026 actual/planned/construction status is visible and no drawing falsely implies completion, ownership, or occupancy.
- All required tests and CI are green and every changed visual has passed manual visual QA.
- The implementation is committed, pushed, reviewed through the repository's required gates, and merged when authorized by those gates.
- Relevant workline issues are closed or updated with exact commit/PR/artifact evidence. Any remaining item is genuinely external or owner-dependent and is stated precisely; “more work could be done” is not an acceptable residual.

## 16. Final response format

Do not end with a vague summary. Report:

1. final branch, PR, merge commit, and current main SHA;
2. exact authoritative source paths added/changed;
3. headcount/occupancy/seat totals and reconciliation outcome;
4. facility/site/building/floor coverage totals, including justified exemptions;
5. Sacramento campus/building/floor deliverables;
6. atlas/index paths and how drill-down navigation works;
7. validation commands, local results, and CI conclusions;
8. visual-QA method and corrections made;
9. branches/artifacts salvaged versus superseded;
10. issues closed/updated;
11. only the genuinely unresolved external facts, with stable IDs and next action.

Begin now. Inspect the repository, establish the recovery ledger and coverage matrix, and then execute the entire closeout. Do not return merely to ask whether you should continue.
