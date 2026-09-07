# SABLE HARBOR MASTER GEOSPATIAL / MAPPING PROGRAM
## COMPLETE CONTINUATION HANDOVER — UNIFIED WORK EXECUTION PROMPT
## September 5, 2026

You are taking over the geospatial/world-geography branch of the SABLE HARBOR corporate worldbuilding project.

This is a deliberate fork from the main ARU / Blood, Sweat & Tears Railway (BS&T) worldbuilding conversation. The original conversation is returning to finishing ARU and BS&T as businesses. YOUR job is to continue the geographic work comprehensively and turn Sable Harbor's geography into a governed, reusable spatial dataset.

This is not primarily a "make some maps" task.

The intended end state is a MASTER GEOSPATIAL PACKAGE for the entire Sable Harbor universe: exact coordinates, site polygons, transportation alignments, operating territories, resource geography, historical geography, provenance, temporal state, and cartographic products.

A map should become a VIEW OF THE DATA.

It must not remain the only place where geographic canon exists.

============================================================
0. WORK TRANSFER CONTEXT AND SUPPLIED SOURCE ASSETS
============================================================

This is the single execution handover for the Work environment. Read it as one continuous mandate, including every numbered section, data field, workflow, deliverable, restriction, validation requirement and completion criterion. Do not replace it with an abbreviated brief or discard later sections because the opening sections appear sufficient.

The originating handover made this context distinction explicitly:

"I have separated decisions actually made in this ARU/BS&T session from things the next chat still needs to verify or engineer, so it doesn't accidentally convert our working assumptions into fake canon."

Source handovers carried into this document:

    Pasted markdown(2).md
    Pasted text (2).txt

These are consecutive parts of the same program. Section 15 continues across their original split; the program then continues through Section 49. Their operational instructions remain the body of this handover.

Target repository:

    https://github.com/SquirmyWormy275/SABLEHARBOR

The move to Work does not itself transfer an authenticated repository connection, a checked-out branch, prior execution state, conversation history or uploaded image bytes. Establish what is actually accessible in Work. Inspect current main as required below. Do not claim that the repository was inspected, files were committed, geometry was engineered, or a release was built merely because this prompt describes those actions.

---------------------------
0.1 SUPPLIED RED WASH IMAGES
---------------------------

Two Red Wash map images were supplied with this transfer. Preserve their original bytes and inspect the actual images. Their filenames and corresponding path context from the supplied files are:

    red_wash__site_overview.png
    assets/brand/maps/red_wash__site_overview.png

    red_wash__underground_plan.png
    assets/brand/maps/red_wash__underground_plan.png

The path context is a retrieval lead, not proof that the same bytes exist on current main.

Both supplied images have dimensions of 1536 x 1024 pixels.

SHA-256 of the supplied site-overview image:

    8dbb0053c4a563d57d5a24be4f4687dc11e2e00e2b1e62c279d9be945f68d77a

SHA-256 of the supplied underground-plan image:

    0658de3b7c63ecc9757b545f29895eab51801b2148cb3862935620b6049a7dda

The transfer bundle, when provided, contains these images under:

    source_assets/red_wash__site_overview.png
    source_assets/red_wash__underground_plan.png

If only this prompt is provided in Work, do not assume the images are embedded in it. Search the repository and accessible attachments for the exact files, compare checksums, and record an access gap if the bytes cannot be obtained. Continue independent work while any missing source asset is being recovered.

---------------------------
0.2 OBSERVED IMAGE CONTENT — SOURCE CLAIMS, NOT NEW CANON
---------------------------

The supplied site-overview image is titled "RED WASH MINE — SITE OVERVIEW." The supplied underground-plan image is titled "RED WASH MINE — SITE MAP & UNDERGROUND PLAN."

Both images visibly print:

    42.3127° N
    106.9213° W
    CARBON COUNTY, WYOMING, USA

Both images also display:

    SABLE HARBOR | PALE SUN URANIUM

Those are observations of what the images say. They are NOT a verification that the coordinates fall in the printed county, that the regional inset pin is geographically consistent, that the coordinate grid is coherent, or that the depicted site is current controlling canon.

The site-overview image additionally labels an access road "TO WY-130," gives an elevation of 6,420 ft, and prints "NAD83 / UTM ZONE 13N." Its "KEY METRICS (CURRENT DESIGN)" panel describes underground decline access, a planned depth of approximately 2,500 feet, selective drift-and-fill mining, uranium (U3O8), an approximately 620-acre disturbance footprint, approximately 7,480 acres of property area and an estimated site workforce of approximately 140 FTE.

The underground-plan image depicts surface facilities and five underground levels, with the deepest labeled -2,500 feet. Its site notes explicitly describe the diagram as conceptual, state that development, stope shapes and sequencing may evolve, and state that it is not for navigation or construction.

All such text, facility labels, diagrams, dimensions, regional pins, brand associations and operating metrics are SOURCE CLAIMS to inventory and compare against repository canon. Do not promote them automatically to verified engineering facts, legal property boundaries, organizational facts or operating commitments.

---------------------------
0.3 RED WASH CONFLICT HANDLING AT TRANSFER
---------------------------

The supplied images' printed Carbon County location and coordinates must be compared with the Sweetwater County / Great Divide Basin / Red Desert / north-of-Wamsutter working lock preserved in Sections 5 and 21. This is an apparent source conflict, not permission to silently replace either source.

Sections 4, 21, 22, 31 and 48 retain the originating warnings about a missing historical Red Wash pin map. Two image files are now supplied, but their availability does NOT establish that either is the exact historical map previously referenced, the exact user-approved version, or an authoritative geographic product.

Before locking Red Wash's exact location:

- preserve both supplied images;
- register their filenames, hashes, dimensions and access state;
- inspect their actual contents and repository provenance;
- record their printed coordinates, county names, grid/projection statements and regional pins separately;
- compare those claims with one another, current repository canon and the later siting decisions;
- do not treat the apparent precision of a label or coordinate as proof of accuracy;
- register the location disagreement explicitly rather than georeferencing or correcting the images into a preferred answer;
- present the evidence and a recommended resolution to the user if controlling sources genuinely conflict;
- retain superseded or disputed geography and its provenance rather than deleting it.

Do not pause unrelated census, schema, provenance, tooling or other-site work merely because Red Wash has a conflict. Do not commit disputed Red Wash geometry as settled canon while the conflict is unresolved.

The remaining sections preserve the full geographic program and its original working locks. This transfer-context section records additional supplied evidence; it does not silently resite Red Wash, resolve its ownership or operating model, or redesign ARU or BS&T.

============================================================
1. FIRST PRINCIPLE
============================================================

Build a spatial source of truth for Sable Harbor.

Every important geographic fact should ultimately be represented as structured spatial data with:

- stable object ID;
- canonical name;
- object/entity type;
- geometry;
- geographic coordinates;
- effective dates;
- ownership/operator;
- business line;
- canonical status;
- provenance;
- confidence;
- notes;
- relationships to other spatial objects.

Use real geography wherever possible.

Fictional facilities should be embedded plausibly into real geography rather than floating on an invented continental map.

Do NOT casually overwrite real facilities, companies, mines, railroads, parcels, towns, or institutions with fictional Sable Harbor ownership.

Where a Sable Harbor property is fictional but situated in a real place, construct a fictional site compatible with the real landscape and explicitly mark it as fictional.

============================================================
2. DATA ARCHITECTURE
============================================================

Preferred authoritative GIS format:

    GeoPackage (.gpkg)

Proposed master:

    sable_harbor_master.gpkg

Also maintain Git-friendly derivatives:

    GeoJSON
    CSV coordinate/site registers where useful
    metadata/provenance documents
    map styles
    rendered maps

GeoPackage should ultimately support POINT, LINESTRING/MULTILINESTRING, and POLYGON/MULTIPOLYGON geometries.

Do not reduce railways, campuses, mines, operating districts, etc. to points when their geometry is material.

Suggested repository structure:

geospatial/
├── README.md
├── master/
│   └── sable_harbor_master.gpkg
├── geojson/
│   ├── sites.geojson
│   ├── facilities.geojson
│   ├── rail_network.geojson
│   ├── roads.geojson
│   ├── operating_territories.geojson
│   ├── resource_areas.geojson
│   ├── historical_sites.geojson
│   └── events.geojson
├── registers/
│   ├── SITE_REGISTER.csv
│   ├── GEOGRAPHIC_DECISION_REGISTER.md
│   ├── PROVENANCE_REGISTER.md
│   └── OPEN_GEOGRAPHIC_QUESTIONS.md
├── styles/
├── maps/
│   ├── corporate/
│   ├── aru/
│   ├── bst/
│   ├── mining/
│   ├── cradle/
│   ├── historical/
│   └── reference/
└── docs/
    ├── GEOSPATIAL_DATA_MODEL.md
    ├── CARTOGRAPHIC_STANDARD.md
    ├── CANON_AND_PROVENANCE_POLICY.md
    └── TEMPORAL_GIS_MODEL.md

Use an appropriate standard CRS for storage/interchange (normally WGS84 / EPSG:4326 for exchange), while allowing projected CRSs appropriate to regional engineering/cartography.

============================================================
3. CANON / PROVENANCE CLASSIFICATION
============================================================

This is essential.

Every spatial object needs an explicit status. Do NOT let "we drew it on a map" automatically mean "canon."

At minimum distinguish:

CANON_LOCKED
    Explicitly established Sable Harbor canon.

CANON_SITED
    Fictional Sable Harbor object whose exact geographic placement has been deliberately selected and locked.

CANON_CONSTRAINED
    Canon determines a region/city/corridor but exact geometry remains unresolved.

ENGINEERED
    Detailed geometry created to implement already-established canon, e.g. the precise route of a fictional railway.

ILLUSTRATIVE
    Used for visualization but not canonical.

REAL_REFERENCE
    Real-world geography used as contextual/reference data.

HISTORICAL
    Geometry that was formerly true in-universe.

PROPOSED
    Candidate geography awaiting a decision.

CONFLICTING
    Existing sources disagree.

UNKNOWN
    Geographic evidence is insufficient.

Also record:

source_document
source_revision
source_commit
decision_date
decision_basis
confidence
notes

Never silently promote PROPOSED or ILLUSTRATIVE geometry to canon.

============================================================
4. IMPORTANT LESSON FROM THE RED WASH PROBLEM
============================================================

The prior conversation encountered a failure where an older Red Wash geographic map apparently existed with a pin, but the map could not be reliably surfaced from the repo searches being performed.

Do NOT invent a location and claim that it came from that missing map.

If that asset is subsequently found:

1. preserve it;
2. identify its provenance;
3. extract/derive its geographic implication;
4. compare it with the newer siting work described below;
5. report any conflict;
6. do NOT silently reconcile the two.

This incident is one of the reasons this GIS package is being created.

Geography must stop existing only as pins embedded in images.

============================================================
5. GEOGRAPHIC DECISIONS MADE IN THE PARENT CONVERSATION
============================================================

The following decisions were made during the ARU/BS&T discussion and should be carried forward as the current working locks.

However, BEFORE committing them permanently into repository canon, compare them against current repository canon and flag any genuine contradiction.

---------------------------
5.1 SABLE HARBOR HQ
---------------------------

Existing corporate canon places Sable Harbor headquarters in Sacramento, California.

The mapping discussion further selected the Sacramento Railyards / River District seam as the intended geographic setting.

Working concept:

- Sacramento headquarters;
- Railyards / River District context;
- fictional Sable Harbor corporate campus;
- approximately 8–15 acres was discussed as a working scale.

Do NOT simply appropriate a real private parcel.

Engineer a plausible fictional campus geometry compatible with the real district.

Exact polygon remains to be engineered.

---------------------------
5.2 EVALON
---------------------------

Existing canon associates Evalon/Willow activity with Pittsburgh.

The mapping discussion selected:

    Hazelwood / Hazelwood Green industrial context
    Pittsburgh, Pennsylvania

The intent is to place Evalon's fictional industrial/R&D footprint in the Hazelwood geography.

A working scale of approximately 10–20 acres was discussed.

IMPORTANT:

Do not claim Sable Harbor owns the real Hazelwood Green development or any actual tenant's parcel.

Create an appropriate fictional site or otherwise clearly distinguish fictional geometry from real reference geography.

Exact polygon remains to be engineered.

---------------------------
5.3 CRADLE
---------------------------

Cradle must NOT be conflated with Evalon.

Cradle grows from Project Cradle and is the recovery-development / critical-minerals / resource-recovery business or capability.

The discussion deliberately connected its geography to the real Appalachian critical-mineral / coal-waste / acid-mine-drainage resource-recovery analogy.

Current siting decision:

    Belle / Kanawha Valley industrial corridor
    West Virginia
    near Charleston

The parent conversation described:

- a fictional redeveloped brownfield site;
- industrial Kanawha River setting;
- roughly 20–30 acres as a working campus scale;
- proximity to Charleston/Emberline while remaining organizationally and geographically distinct.

NOTE TYPOGRAPHY:

The river/valley is KANAWHA, not "Kenawa."

Do not appropriate an actual chemical plant or real company parcel as Sable Harbor property.

Research the real industrial geography and create a defensible fictional brownfield geometry.

Exact parcel polygon remains to be engineered.

---------------------------
5.4 EMBERLINE
---------------------------

Existing canon places Emberline in/at Charleston, West Virginia.

Preserve that.

The new Cradle site should make geographic sense relative to Emberline but should not collapse the two into one facility unless later canon explicitly does so.

---------------------------
5.5 RED WASH MINE
---------------------------

Existing canon establishes:

- Red Wash Mine;
- Wyoming;
- underground uranium operation.

The parent mapping discussion decided to constrain/site it much more specifically in the:

    Great Divide Basin / Red Desert geography
    Sweetwater County, Wyoming
    north of the Wamsutter corridor

The real-world analogy is intended to be geologically and logistically defensible.

Red Wash remains FICTIONAL.

Do not place it directly on top of a real mine and rename the mine.

Research:

- uranium geology;
- terrain;
- land ownership;
- hydrography;
- roads;
- rail access;
- environmental constraints;
- settlement patterns;
- actual mining districts;
- federal/state land context.

Then engineer an exact fictional mine site.

The exact mine coordinate and mine-property polygon have NOT yet been properly engineered against GIS data.

That is a task for this branch.

---------------------------
5.6 BLOODSTONE, WYOMING
---------------------------

Bloodstone is the BS&T railroad's shop/yard community in the emerging design.

Treat Bloodstone as a FICTIONAL Wyoming railroad/industrial settlement within the Red Wash–Wamsutter system.

Do not accidentally replace or rename a real settlement.

It needs deliberate siting.

Its eventual geometry may include:

- town/site point;
- yard polygon;
- shop/roundhouse or diesel-shop footprint;
- station;
- industrial tracks;
- employee/community geography if relevant.

The exact Bloodstone coordinate remains to be engineered.

---------------------------
5.7 WAMSUTTER
---------------------------

Wamsutter, Wyoming is REAL_REFERENCE geography.

The emerging BS&T design uses the Wamsutter corridor as its principal connection to the national railroad network.

The parent discussion referred to it as the Class I interchange context.

Do not invent the real railroad infrastructure.

Research the actual rail corridor and determine exactly how a fictional BS&T interchange could plausibly connect without rewriting real-world railroad geography unnecessarily.

---------------------------
5.8 BLOOD, SWEAT & TEARS RAILWAY
---------------------------

Full company name:

    BLOOD, SWEAT & TEARS RAILWAY

Abbreviation:

    BS&T

The exact BS&T logo created in the parent ARU/BS&T chat was separately LOCKED as the canonical visual reference.

Do not redesign it in this mapping branch.

The railway itself predates acquisition by ARU/Sable Harbor and needs a proper historical network.

The emerging geographic concept is a Wyoming resource/industrial shortline connecting the Red Wash/Bloodstone system to the Wamsutter national-network interchange.

Approximately 40 route-miles was used as an initial working concept in conversation.

IMPORTANT:

That does NOT mean "draw a straight 40-mile line."

The railway must be represented as actual LINESTRING geometry following plausible terrain.

Engineer:

- main line;
- mine branch(es);
- yard leads;
- industrial spurs;
- interchange;
- passing tracks where appropriate;
- abandoned/historical trackage if established;
- trackage-rights segments if established;
- mileposts;
- junctions;
- bridges/major structures where material.

The exact vertex-by-vertex alignment remains UNFINISHED.

This is one of the primary tasks.

The parent conversation explicitly wanted the PRE-ACQUISITION BS&T network map.

Once the line is engineered, create that map.

---------------------------
5.9 ARU
---------------------------

ARU = AMERICAN RESOURCE UTILITY.

The exact ARU logo created in the parent conversation was LOCKED.

Its design is:

- three interlocked triangular forms;
- red, green and black;
- ARU;
- AMERICAN RESOURCE UTILITY underneath.

But DO NOT redraw it from textual description if the exact locked image can be recovered. The exact image—not merely the concept—was locked.

ARU's broader route/terminal geography was still being developed in the parent conversation and should NOT be invented by this mapping branch without checking current canon.

The parent conversation is continuing ARU/BS&T business-worldbuilding separately.

Therefore:

    GIS branch should consume new ARU/BS&T canon as it becomes available,
    not independently redesign the businesses.

============================================================
6. OTHER KNOWN GEOGRAPHIC CANON TO INVENTORY
============================================================

Do a COMPLETE repository census rather than relying only on this handover.

Known examples that should be checked include:

- Sacramento HQ;
- Pittsburgh / Willow / Evalon;
- Charleston / Emberline;
- Blackridge Mine — Nevada;
- Red Wash — Wyoming;
- ARU;
- BS&T;
- Cradle;
- Pale Sun;
- Foundry Field;
- Atlas;
- Deloraine-related geography;
- acquisition targets;
- legacy operating sites;
- J2 facilities;
- any named offices;
- warehouses;
- labs;
- mine sites;
- customer sites if geographically canonical;
- infrastructure;
- historical corporate locations.

Do not assume this list is complete.

Search the ENTIRE repository.

Search not merely for place names but for:

location
site
facility
office
headquarters
HQ
mine
plant
yard
terminal
rail
railroad
warehouse
campus
lab
field
district
region
state
county
city
route
corridor
port
interchange
branch
project
acquisition
lease
property
parcel

Also inspect maps/images/assets where possible.

============================================================
7. BUILD A GEOGRAPHIC DECISION REGISTER FIRST
============================================================

Before generating hundreds of geometries, build:

    GEOGRAPHIC_DECISION_REGISTER.md

Every discovered geographic object gets one row.

Suggested fields:

| ID | Name | Entity | Type | Existing geography | Status | Temporal scope | Source | Conflict? | Required decision |

Classify every object:

LOCKED
CONSTRAINED
OPEN
CONFLICTING
REFERENCE_ONLY

This becomes the decision queue.

The next chat should work through that queue with the user.

Do not ask the user fifty questions at once.

Batch related decisions intelligently.

============================================================
8. MASTER SITE IDENTIFIERS
============================================================

Create durable IDs independent of display names.

Example pattern only:

SH-SITE-0001
SH-SITE-0002

Rail objects:

SH-RAIL-BST-ML-001
SH-RAIL-BST-BR-001

Facilities:

SH-FAC-XXXX

Events:

SH-EVT-XXXX

Do not encode too much mutable information into IDs.

Names can change.
IDs should survive.

============================================================
9. TEMPORAL GIS
============================================================

The Sable Harbor universe changes through time.

The spatial database therefore needs temporal fields.

At minimum:

valid_from
valid_to
acquired_on
disposed_on
opened_on
closed_on
status

This should allow questions such as:

"What did Sable Harbor own in 2018?"

"What did BS&T look like immediately before ARU acquired it?"

"What was the footprint immediately after Red Wash?"

"Which facilities existed during the Deloraine decision?"

"What changed geographically between 2024 and 2026?"

Do not overwrite historical geography when ownership changes.

Preserve states through time.

============================================================
10. RAILWAY MODEL
============================================================

BS&T deserves a proper railway network model rather than one polyline.

Recommended layers/tables:

rail_lines
rail_segments
rail_nodes
rail_yards
rail_facilities
rail_interchanges
rail_bridges
rail_tunnels
rail_crossings
rail_mileposts
rail_industries
rail_abandoned
rail_trackage_rights

Each segment should be capable of carrying:

segment_id
railroad
ownership
operator
track_class/type
status
valid_from
valid_to
from_node
to_node
length
traffic_type
speed where canonically appropriate
notes
provenance

The GIS should eventually permit actual network analysis.

============================================================
11. RESOURCE GEOGRAPHY
============================================================

Do not map Sable Harbor facilities in isolation from why they exist.

Add contextual resource layers where legally/licensably possible:

- uranium districts/geology around Red Wash;
- coal/resource geography relevant to ARU/BS&T;
- Appalachian coal waste / AMD / critical-mineral context for Cradle;
- mineral/resource geography around Blackridge;
- relevant watersheds;
- industrial corridors;
- transportation corridors;
- power infrastructure where relevant.

Separate REAL_REFERENCE datasets from fictional canon.

============================================================
12. CORPORATE FOOTPRINT
============================================================

Build multiple levels of corporate geography:

LEVEL 1 — GLOBAL/NATIONAL
All Sable Harbor operating locations.

LEVEL 2 — BUSINESS LINE
Each operating company/business.

LEVEL 3 — SITE
Actual campuses, mines, yards, plants, etc.

LEVEL 4 — FACILITY
Buildings/major operating areas where useful.

LEVEL 5 — INTERNAL SITE GEOGRAPHY
Only where worldbuilding benefits from it.

This allows maps ranging from a board-level corporate footprint to a detailed BS&T yard diagram.

============================================================
13. EVENT GEOGRAPHY
============================================================

Create spatially addressable corporate-history events.

Examples:

- acquisitions;
- openings;
- closures;
- accidents if canonically established;
- Project Cradle milestones;
- Red Wash acquisition;
- ARU acquisition;
- BS&T acquisition;
- major expansion;
- Deloraine-related events;
- divestitures;
- reorganizations tied to facilities.

Events should have:

event_id
date
location geometry
entities involved
event type
source
description
canon status

This will eventually allow an interactive historical map/timeline.

============================================================
14. CARTOGRAPHIC PRODUCTS
============================================================

Once the underlying data exists, produce a coherent map series.

Potential maps:

01 — Sable Harbor Corporate Footprint, 2026
02 — Sable Harbor Historical Expansion
03 — Sable Harbor Operating Companies
04 — Western Resource Operations
05 — Appalachian Operations
06 — Red Wash Regional Context
07 — Red Wash Mine Site
08 — BS&T Pre-Acquisition System Map
09 — BS&T Detailed Track Chart
10 — BS&T Acquisition-Era Network
11 — ARU System Map
12 — ARU + BS&T Integrated Network
13 — Evalon Pittsburgh Site
14 — Cradle Kanawha Valley Site
15 — Sacramento Headquarters
16 — Blackridge Regional Map
17 — Corporate Acquisition Timeline Map
18 — Resource/Infrastructure Overlay
19 — Ownership Change Map
20 — Canon Confidence / Provenance Map

Maps should share a cartographic system but can have business-specific styling.

============================================================
15. MAP DESIGN STANDARD
============================================================

Avoid generic AI-infographic aesthetics.

These should resemble professional:

- engineering maps;
- railroad system maps;
- USGS/resource maps;
- corporate asset maps;
- infrastructure planning maps;
- historical railroad maps;
- mine-planning maps;
- industrial site plans;
- corporate infrastructure atlases;
- professional GIS products.

Each map should contain, where appropriate:

- map title;
- map-series identifier;
- revision;
- effective or “as of” date;
- canon status;
- scale bar;
- north arrow;
- coordinate system;
- source note;
- legend;
- data-confidence or precision note;
- distinction between fictional Sable Harbor assets and real-world reference geography;
- author/build information;
- checksum or release identifier for controlled products.

Avoid:

- generic shaded infographic boxes;
- decorative fake topography;
- routes that ignore terrain;
- unlabeled arbitrary pins;
- inconsistent place names;
- illegible microtext;
- excessive gradients;
- fake engineering precision;
- using a basemap screenshot as the source of truth;
- AI-generated labels or malformed text inside maps;
- “antique” texture unless intentionally producing an in-universe historical artifact.

The modern enterprise map series should be clean, restrained and technical.

Historical maps may use period-appropriate railroad styling, but historical appearance must not obscure factual status, dates or route ownership.

Business-line colors should be used with discipline.

For example:

- BS&T active owned track: the BS&T dark red/cream/black visual system;
- trackage rights or leased track: differentiated dashed treatment;
- abandoned or out-of-service track: subdued gray or broken line;
- real external railroad: neutral reference color;
- ARU assets: ARU red/green/black system;
- real-world contextual features: neutral and subordinate;
- proposed geometry: visibly different from locked geometry;
- conflicting geometry: visually flagged.

Do not rely on color alone. Use line patterns, symbols and labels so the maps remain understandable in grayscale and for users with color-vision deficiencies.

============================================================
16. CANONICAL GEOSPATIAL TECHNOLOGY STACK
============================================================

Use an open, durable and inspectable stack.

Recommended core:

- QGIS for desktop GIS authoring and inspection;
- GeoPackage for packaged spatial delivery;
- GeoJSON for Git-readable geometry;
- CSV for registers and simple coordinate exports;
- SQLite-compatible metadata tables inside the GeoPackage;
- Python for deterministic builds, validation and exports;
- GDAL/OGR where appropriate;
- Shapely / GeoPandas / PyProj where appropriate;
- SVG, PDF and PNG for rendered maps;
- KML/KMZ for convenient lightweight viewing;
- PMTiles, MBTiles or vector tiles for future web maps;
- GeoParquet as an optional analytical export.

Do NOT use ESRI Shapefile as the authoritative source.

Shapefiles may be exported for compatibility, but their field-name, encoding, geometry and file-bundle limitations make them unsuitable as the master format.

Recommended controlled files:

    geospatial/master/sable_harbor_master.gpkg
    geospatial/qgis/sable_harbor_master.qgz
    geospatial/geojson/*.geojson
    geospatial/registers/*.csv
    geospatial/styles/*.qml
    geospatial/maps/*.pdf
    geospatial/maps/*.svg
    geospatial/maps/*.png
    geospatial/releases/*.json

Important source-control distinction:

- The released GeoPackage is the authoritative packaged spatial product.
- The diffable source tables, GeoJSON, schemas, decision registers and build scripts are the authoritative change-control substrate.
- The GeoPackage should be reproducibly generated from those governed inputs whenever practical.
- Each released GeoPackage should have a SHA-256 checksum and release manifest.

Do not allow manual QGIS edits to become undocumented canon.

Any manual geometry edit must be exported back into the controlled source data and tied to a decision/provenance record.

============================================================
17. CORE DATA MODEL
============================================================

Build a real schema, not a single catch-all layer.

At minimum, create these tables/layers.

---------------------------
17.1 spatial_assets
---------------------------

Represents mines, campuses, offices, plants, yards, terminals, warehouses, labs and other physical assets.

Suggested fields:

asset_id
canonical_name
display_name
former_name
asset_type
asset_subtype
entity_id
business_line
owner_entity
operator_entity
fictionality
canon_status
geometry_status
operating_status
valid_from
valid_to
opened_on
closed_on
acquired_on
disposed_on
country
state
county
municipality
postal_context
address_status
source_id
decision_id
location_method
horizontal_accuracy_m
source_scale
confidence
public_precision
notes
created_at
updated_at
supersedes_asset_id

Geometry may be POINT, POLYGON or MULTIPOLYGON depending on the object.

Do not use a centroid as though it were the actual operational location without identifying it as a centroid.

---------------------------
17.2 facilities
---------------------------

Represents components inside a larger site.

Examples:

- headquarters building;
- research laboratory;
- processing plant;
- mine portal;
- shaft;
- headframe;
- rail shop;
- locomotive servicing area;
- administrative building;
- warehouse;
- recovery pilot plant;
- tailings or waste-management area;
- interchange office;
- substation;
- loading track.

Suggested fields:

facility_id
parent_asset_id
canonical_name
facility_type
operator_entity
operating_status
valid_from
valid_to
canon_status
geometry_status
source_id
decision_id
notes

---------------------------
17.3 rail_nodes
---------------------------

Represents topology points.

Examples:

- junctions;
- interchange points;
- yard limits;
- stations;
- mine loadouts;
- branch endpoints;
- control points;
- passing sidings;
- shop leads;
- industry connections.

Suggested fields:

node_id
canonical_name
node_type
railroad
owner
operator
milepost
valid_from
valid_to
canon_status
source_id
decision_id
notes

---------------------------
17.4 rail_segments
---------------------------

Represents actual network edges.

Suggested fields:

segment_id
canonical_name
route_id
subdivision
from_node_id
to_node_id
owner
operator
host_railroad
rights_type
track_status
track_count
traffic_role
commodity_role
valid_from
valid_to
route_miles
geometry_miles
maximum_grade_pct
elevation_min_m
elevation_max_m
engineering_status
canon_status
source_id
decision_id
notes

Geometry should be LINESTRING or MULTILINESTRING.

Store calculated geometric length separately from any canonical timetable or route mileage.

---------------------------
17.5 rail_routes
---------------------------

Represents logical routes assembled from segments.

Examples:

- BS&T Main Line;
- Red Wash Branch;
- Bloodstone Industrial Lead;
- Wamsutter Interchange Lead;
- historical coal branch;
- abandoned alignment.

Suggested fields:

route_id
canonical_name
railroad
route_type
origin_node
destination_node
valid_from
valid_to
status
canon_status
decision_id
notes

---------------------------
17.6 operating_territories
---------------------------

Represents areas of responsibility, service or commercial reach.

Examples:

- ARU utility territory;
- BS&T switching district;
- mine operating boundary;
- field-service region;
- Cradle resource-recovery development region;
- acquisition-search geography.

These are not automatically property boundaries.

Suggested fields:

territory_id
canonical_name
territory_type
entity_id
valid_from
valid_to
canon_status
geometry_status
source_id
decision_id
notes

---------------------------
17.7 resource_areas
---------------------------

Represents real-reference or fictional resource geography.

Examples:

- uranium-bearing formation;
- coal field;
- acid-mine-drainage watershed;
- coal-waste recovery district;
- copper/gold district;
- industrial brownfield corridor.

Suggested fields:

resource_area_id
canonical_name
resource_type
fictionality
source_authority
source_date
license
valid_from
valid_to
notes

---------------------------
17.8 events
---------------------------

Represents geographically situated corporate-history events.

Suggested fields:

event_id
canonical_name
event_type
event_date
event_end_date
entity_ids
asset_ids
canon_status
source_id
decision_id
description
notes

Geometry may be POINT, LINESTRING or POLYGON.

---------------------------
17.9 entity_registry
---------------------------

Represents companies, operating divisions, projects and other institutional actors.

Suggested fields:

entity_id
canonical_name
entity_type
parent_entity_id
valid_from
valid_to
legal_status
canon_status
source_id
notes

Cradle’s exact institutional status must be represented accurately. Do not invent a separate legal entity merely because it has a site.

---------------------------
17.10 spatial_relationships
---------------------------

Connects objects without forcing every relationship into geometry tables.

Examples:

SERVES
CONNECTED_TO
INTERCHANGES_WITH
OWNED_BY
OPERATED_BY
LOCATED_WITHIN
SUPPORTS
REPLACED_BY
PREDECESSOR_OF
SUPPLIES
RECEIVES_FROM
ADJACENT_TO
TRAVERSES
ACQUIRED_WITH
DIVESTED_WITH

Suggested fields:

relationship_id
subject_id
predicate
object_id
valid_from
valid_to
canon_status
source_id
decision_id
notes

---------------------------
17.11 source_registry
---------------------------

Every external dataset, canon document, image, map or user decision used for geography should have a source record.

Suggested fields:

source_id
title
publisher_or_author
source_type
publication_date
accessed_date
url_or_repo_path
repository_commit
file_sha256
license
citation
coverage
source_quality
notes

---------------------------
17.12 decision_registry
---------------------------

Spatial decisions need their own structured records.

Suggested fields:

decision_id
decision_date
decision_title
decision_type
affected_object_ids
decision_status
deciding_authority
source_conversation
source_document
rationale
alternatives_considered
supersedes_decision_id
notes

The user’s explicit locks in this handover are decisions. Record them.

============================================================
18. FICTIONALITY AND REAL-WORLD RELATION POLICY
============================================================

Every object must clearly state what kind of thing it is.

Recommended `fictionality` values:

REAL
    A real-world place, route, facility or geographic feature.

FICTIONAL_IN_REAL_GEOGRAPHY
    A fictional Sable Harbor object deliberately embedded in real geography.

FICTIONAL
    A wholly fictional object without a direct real-world equivalent.

COMPOSITE
    A fictional object derived from several real analogues.

UNRESOLVED
    Insufficient information.

Recommended `real_world_relation` values:

REFERENCE_ONLY
ADJACENT_TO_REAL_ASSET
WITHIN_REAL_DISTRICT
MODELED_ON_REAL_SITE
USES_REAL_CORRIDOR
INTERCHANGES_WITH_REAL_NETWORK
NO_DIRECT_REAL_EQUIVALENT
UNKNOWN

Never label a fictional site with the name, address or parcel ID of a real operating company unless the canon explicitly says the real facility itself exists in-universe and that treatment has been approved.

Avoid false property claims.

For fictional polygons:

- do not label them “legal parcel boundary” unless they actually derive from a controlled fictional cadastral system;
- use “site footprint,” “planning boundary,” “operational boundary,” or “fictional property envelope” as appropriate;
- document how the polygon was generated.

============================================================
19. GEOGRAPHIC PRECISION POLICY
============================================================

Do not confuse decimal places with accuracy.

Store coordinates at sufficient technical precision, but separately record the actual confidence and method.

Recommended `location_method` values:

USER_LOCKED
CANON_DOCUMENT
MAP_PIN_DERIVED
GEOCODED
PARCEL_DERIVED
FIELD_SURVEYED
ENGINEERED_FROM_CONSTRAINTS
DIGITIZED_FROM_SOURCE
CENTROID
APPROXIMATE
UNKNOWN

Recommended accuracy fields:

horizontal_accuracy_m
vertical_accuracy_m
source_scale
precision_class
geometry_reviewed_by
review_date

Recommended `precision_class` values:

EXACT_ENGINEERED
PARCEL_SCALE
SITE_SCALE
CORRIDOR_SCALE
CITY_SCALE
REGIONAL
ILLUSTRATIVE
UNKNOWN

A city-level canon statement should not be represented as a supposedly exact building point.

A map pin from an image should not be treated as survey-grade geometry.

For public-facing maps, also support a `public_precision` field so an exact internal fictional geometry can be generalized where appropriate without corrupting the master dataset.

============================================================
20. SOURCE ACQUISITION AND LICENSING
============================================================

Use high-quality source data.

Potential real-reference sources include:

- USGS geology, topography and elevation;
- US Census boundary data;
- state and county GIS portals;
- Bureau of Land Management datasets;
- USGS National Hydrography data;
- public transportation datasets;
- official railroad regulatory or infrastructure records;
- OpenStreetMap where appropriate;
- local planning and redevelopment documents;
- EPA brownfield records;
- Department of Energy and university critical-mineral research;
- official industrial-site and land-use documents;
- public cadastral data where licensing permits.

Do not assume all state, county or municipal data is public domain.

Record the license and attribution for every imported dataset.

Do not:

- embed Google Maps imagery;
- scrape proprietary basemap tiles;
- commit commercial GIS data without permission;
- derive a route from a proprietary image and omit the source;
- use an attractive online map as evidence without checking its authority;
- commit huge raw datasets to the repo without a reason.

For large external datasets, prefer:

- source manifest;
- download script;
- pinned source URL;
- checksum;
- license file;
- clipping/build script;
- resulting controlled derivative.

Track OpenStreetMap attribution and ODbL obligations where OSM-derived data is used.

Federal public-domain status should still be documented rather than assumed silently.

============================================================
21. LOCKED DECISIONS VERSUS ENGINEERING DETAILS
============================================================

The user has explicitly locked the following geographic direction in the parent conversation:

1. Sable Harbor HQ remains Sacramento.
2. HQ is situated in the Sacramento Railyards / River District seam.
3. Evalon is situated in Pittsburgh’s Hazelwood industrial geography.
4. Cradle is situated in the Belle / Kanawha Valley industrial corridor near Charleston.
5. Cradle is distinct from Evalon.
6. Emberline remains associated with Charleston.
7. Red Wash is in the Great Divide Basin / Red Desert geography of Sweetwater County, north of the Wamsutter corridor.
8. Red Wash is a fictional underground uranium mine.
9. Bloodstone is a fictional BS&T shop/yard community in the Red Wash–Wamsutter system.
10. Wamsutter is the real-reference national-network interchange context.
11. BS&T is to be engineered as a real line alignment, not represented as disconnected pins or a straight schematic.
12. Maps are derivatives of the geospatial source of truth.
13. The GeoPackage program is the authoritative geographic implementation mechanism.

Do not reopen these decisions merely because another location is also plausible.

Only reopen one if:

- current controlling repository canon directly contradicts it;
- the location is physically impossible;
- the user explicitly reopens it;
- the missing historic Red Wash pin map is recovered and creates a conflict.

The following remain engineering tasks rather than open city-level decisions:

- exact HQ polygon;
- exact Evalon polygon;
- exact Cradle polygon;
- exact Red Wash mine point and property footprint;
- exact Bloodstone point and town/yard geometry;
- exact BS&T route vertices;
- exact Wamsutter interchange configuration;
- exact route mileage;
- exact rail structures;
- exact historical route states.

The distinction matters:

    The corridor is locked.
    The engineered geometry is unfinished.

============================================================
22. RED WASH EXACT-SITING WORKFLOW
============================================================

Do not place Red Wash by intuition alone.

Build a defensible siting analysis.

Step 1 — Define operational requirements

At minimum consider:

- underground uranium deposit plausibility;
- room for portal/shaft and surface plant;
- waste-rock and support areas;
- ventilation and utilities;
- road access;
- rail-access potential;
- workforce access;
- water and drainage;
- terrain;
- land-management context;
- distance to Wamsutter;
- compatibility with the emerging BS&T mileage;
- separation from real settlements and real operating mines;
- avoidance of obvious physical impossibilities.

Step 2 — Compile constraint/reference layers

Potential layers:

- uranium geology;
- mapped mineral occurrences;
- elevation and slope;
- hydrography;
- wetlands where available;
- roads;
- existing rail;
- land ownership/management;
- protected or restricted areas;
- existing mines and claims where public data permits;
- population and structures;
- pipelines and utilities where public and relevant;
- wildlife or environmental constraints where relevant;
- county boundaries.

Step 3 — Identify candidate fictional envelopes

Create several candidate zones inside the already-locked Great Divide Basin / north-of-Wamsutter geography.

Do not place a candidate directly atop a real named mine.

Step 4 — Score candidates

Create a transparent scoring table.

Potential categories:

- geology;
- rail feasibility;
- road feasibility;
- terrain;
- environmental conflict;
- land-use conflict;
- distance;
- narrative compatibility;
- BS&T network compatibility.

Step 5 — Select and record

The agent should make a recommended selection and proceed unless a genuinely material choice requires the user.

Once selected:

- create a canonical mine reference point;
- define what the point represents, such as mine portal, shaft collar, site centroid or administration building;
- create a mine-site planning polygon;
- create rail-loadout geometry if applicable;
- create access-road geometry;
- record exact coordinates;
- record decision rationale;
- attach provenance;
- calculate distance to Bloodstone and Wamsutter;
- generate a regional-context map and a detailed site map.

Do not claim that the result is based on the missing historical map unless that map has actually been recovered and reviewed.

============================================================
23. BS&T NETWORK ENGINEERING WORKFLOW
============================================================

The BS&T route is one of the central deliverables.

First resolve the temporal question:

    “Pre-acquisition” must be tied to a specific acquisition and a specific effective date.

Do not assume this means the same thing as:

- before Sable Harbor acquired ARU;
- before ARU acquired BS&T;
- before Sable Harbor acquired Red Wash;
- before BS&T began serving Red Wash.

Check the repository chronology.

If the chronology is still unresolved, represent multiple dated network states rather than collapsing them.

Suggested states:

BST_FOUNDING
BST_PRE_ARU_ACQUISITION
BST_ARU_ACQUISITION_DATE
BST_PRE_RED_WASH_INTEGRATION
BST_2026_CURRENT

Only create states supported by canon or explicitly approved decisions.

---------------------------
23.1 Route logic
---------------------------

The current geographic system is:

    Red Wash Mine
        ↕
    Bloodstone shop/yard community
        ↕
    Wamsutter interchange corridor
        ↕
    national rail network

This is a network concept, not yet a final sequence of stations or branches.

The route must follow plausible terrain.

Do not draw a straight line from Red Wash to Wamsutter.

Use elevation and terrain analysis to find a credible alignment.

Potential engineering considerations:

- grades;
- drainage crossings;
- ridgelines;
- cut-and-fill burden;
- curvature;
- road crossings;
- river/creek crossings;
- existing development;
- interchange geometry;
- room for a yard;
- mine loadout access;
- plausible historical construction economics.

This is worldbuilding-level railway engineering, not a stamped civil design.

State that limitation.

---------------------------
23.2 Route alternatives
---------------------------

Create at least two initial alignments where meaningful:

- minimum-distance alignment;
- terrain-optimized alignment;
- historically plausible lower-capital alignment.

Compare:

- route length;
- elevation gain/loss;
- maximum estimated grade;
- number of significant crossings;
- construction difficulty;
- operating implications;
- narrative fit.

Recommend one.

Do not burden the user with alternatives that are functionally identical.

---------------------------
23.3 Interchange
---------------------------

Research the actual Wamsutter rail corridor and identify:

- real corridor owner/operator as of the relevant date;
- actual orientation of tracks;
- local industrial or siding geography;
- a plausible fictional BS&T connection;
- turnout and interchange-track space;
- whether a fictional interchange yard must be situated outside the existing town footprint.

Do not draw BS&T over the real main line and call it BS&T property.

Separate:

- real host railroad;
- BS&T-owned connection;
- jointly used or interchange tracks;
- trackage rights, if any.

---------------------------
23.4 Bloodstone
---------------------------

Engineer Bloodstone as a functional railroad place.

Potential components:

- main yard;
- arrival/departure track;
- classification tracks;
- locomotive shop;
- maintenance-of-way area;
- fuel/service track;
- caboose or crew facility if historically appropriate;
- station/office;
- wye or turning facility if operationally needed;
- town or company-settlement footprint;
- industrial/customer tracks.

Do not overbuild it into a giant Class I terminal.

Its size must match the traffic and history eventually established in ARU/BS&T canon.

---------------------------
23.5 Red Wash rail facilities
---------------------------

Potential components:

- mine branch;
- loadout track;
- runaround;
- empty-car storage;
- loaded-car holding track;
- maintenance access;
- safety separation from mine operations;
- possible transload if direct mine loading is not canonical.

Whether uranium product itself moves by rail must be determined from canon and operational logic.

Do not casually depict hazardous-material movements without deciding what Red Wash produces, how it is packaged and where processing occurs.

---------------------------
23.6 Route validation
---------------------------

For every proposed alignment calculate:

- geometry length;
- route mileage;
- elevation profile;
- estimated maximum grade;
- total ascent/descent;
- major crossings;
- distance between operational nodes;
- curve-density proxy where feasible;
- land-management intersections;
- real infrastructure conflicts.

Produce:

    BST_ROUTE_ENGINEERING_NOTE.md
    BST_ALIGNMENT_COMPARISON.csv
    BST_ELEVATION_PROFILE.png
    BST_NETWORK.geojson
    BST_PRE_ACQUISITION_SYSTEM_MAP.pdf
    BST_TRACK_CHART.pdf

The first map should include Red Wash at its canonical location even if Red Wash was not yet owned or served at the map’s effective date.

Use symbology and labels to show its historical relationship accurately.

============================================================
24. SACRAMENTO HQ GEOMETRY
============================================================

The headquarters should be situated in the Railyards / River District seam, not arbitrarily in downtown Sacramento.

Research:

- district boundaries;
- rail infrastructure;
- redevelopment plans;
- floodplain and levee context;
- roads;
- river access;
- transit;
- actual parcels and ownership where public;
- surrounding land uses;
- historic railroad geography.

Create a fictional 8–15 acre campus envelope compatible with the real district.

Potential internal geometry:

- headquarters building;
- executive/board functions;
- J2 access if canonically applicable;
- archive or institutional-memory facilities if canonically applicable;
- visitor entrance;
- service entrance;
- parking/transport;
- landscaped/security perimeter;
- adjacent transit or rail relationship.

Do not invent a giant isolated corporate campus if the district context supports a denser urban headquarters.

The final geometry should reflect the actual corporate culture and scale established elsewhere in canon.

Deliver:

    SAC_HQ_SITE_SELECTION.md
    SAC_HQ_SITE.geojson
    SAC_HQ_CONTEXT_MAP.pdf
    SAC_HQ_SITE_PLAN.pdf

============================================================
25. EVALON / HAZELWOOD GEOMETRY
============================================================

Evalon is to be situated in Pittsburgh’s Hazelwood industrial geography.

Research:

- Hazelwood and Hazelwood Green geography;
- former industrial land;
- rail access;
- river access;
- roads;
- surrounding institutions;
- redevelopment boundaries;
- topography;
- existing real tenants and projects.

Create a fictional 10–20 acre industrial/R&D site without claiming a real operating tenant’s property.

Potential components must follow Evalon canon, not generic “innovation campus” aesthetics.

Possible geometry categories:

- experimental shop;
- systems lab;
- fabrication space;
- test yard;
- warehouse;
- office/analysis building;
- controlled outdoor area;
- rail or truck interface if operationally justified.

The map should look industrial and credible.

Do not turn Evalon into an immaculate suburban technology park unless canon supports that.

Deliver:

    EVALON_SITE_SELECTION.md
    EVALON_SITE.geojson
    EVALON_HAZELWOOD_CONTEXT_MAP.pdf
    EVALON_SITE_PLAN.pdf

============================================================
26. CRADLE / BELLE GEOMETRY
============================================================

Cradle is situated in the Belle / Kanawha Valley industrial corridor.

The facility exists because of its relationship to:

- critical-mineral recovery;
- coal waste;
- acid mine drainage;
- industrial residues;
- pilot processing;
- resource-recovery development;
- Appalachian industrial geography.

Research:

- Belle industrial geography;
- Kanawha River;
- brownfield sites;
- rail;
- barge access;
- roads;
- floodplain;
- chemical and industrial neighbors;
- Charleston relationship;
- Appalachian resource-recovery research;
- waste-stream logistics;
- utility access.

Create a fictional 20–30 acre brownfield redevelopment envelope.

Do not appropriate the real identity of the former OxyChem or any current chemical complex.

The real site may be an analogy, not the fictional parcel itself.

Potential components:

- feedstock receiving;
- covered waste handling;
- pilot separation plant;
- hydrometallurgical or other process areas only if canonically appropriate;
- analytical laboratory;
- water treatment;
- residue handling;
- secure storage;
- rail/truck/barge interface as justified;
- administrative and engineering space;
- expansion pad.

Cradle should feel like an industrial recovery-development center, not a generic office campus.

Maintain the distinction:

    Emberline — Charleston-associated operating capability.
    Cradle — Belle/Kanawha recovery-development site.
    Related, but not the same facility or organization.

Deliver:

    CRADLE_SITE_SELECTION.md
    CRADLE_SITE.geojson
    CRADLE_KANAWHA_CONTEXT_MAP.pdf
    CRADLE_SITE_PLAN.pdf
    CRADLE_RESOURCE_FLOW_CONTEXT.pdf

============================================================
27. BLACKRIDGE AND OTHER MAJOR ASSETS
============================================================

Current known canon places Blackridge Mine in Nevada.

That is not enough to create an exact site.

Do not guess.

Perform the same controlled siting process:

- identify current canon;
- identify commodity and mine type;
- identify regional constraints;
- determine whether a more exact location exists;
- classify as LOCKED, CONSTRAINED, OPEN or CONFLICTING;
- create exact geometry only after the evidence or user decision supports it.

Apply this to every other major asset.

Potential asset families include:

- Foundry;
- Foundry Field;
- Willow;
- Atlas Meridian;
- Pale Sun;
- Red Wash;
- Blackridge;
- ARU;
- BS&T;
- Advisory;
- J2;
- Alexandria-related physical infrastructure;
- legacy offices;
- acquired businesses;
- divested assets;
- historical sites;
- customer or engagement sites that are genuinely canonical.

Do not assume every business line owns a dedicated campus.

Some may operate from shared facilities, leased offices, client sites or distributed teams.

============================================================
28. CORPORATE ASSET CENSUS
============================================================

Build a full asset census before claiming the enterprise map is complete.

Recommended categories:

CORPORATE
- headquarters;
- board/executive facilities;
- shared-service sites;
- records/archive locations;
- training facilities.

RESEARCH AND ENGINEERING
- labs;
- test facilities;
- fabrication shops;
- field engineering bases;
- data or compute facilities where geographically material.

MINING AND RESOURCE
- mines;
- exploration areas;
- portals;
- shafts;
- process plants;
- waste facilities;
- loadouts;
- storage;
- reclamation areas.

TRANSPORTATION
- railways;
- yards;
- shops;
- terminals;
- warehouses;
- interchanges;
- transloads;
- ports;
- fleet bases.

UTILITY AND INDUSTRIAL
- plants;
- utility territories;
- industrial customer sites;
- substations;
- pipeline or corridor assets only if canonically owned or operated.

RECOVERY
- brownfield recovery sites;
- pilot plants;
- water-treatment facilities;
- residue-processing sites;
- feedstock collection areas.

PROFESSIONAL SERVICES
- offices;
- project hubs;
- embedded client locations if canonical and appropriate.

HISTORICAL
- former headquarters;
- closed sites;
- divested assets;
- failed projects;
- predecessor-company locations.

Every asset should end in one of these states:

MAPPED
CONSTRAINED
OPEN
CONFLICTING
NOT_SPATIAL
OUT_OF_SCOPE

============================================================
29. TEMPORAL AND BITEMPORAL INTEGRITY
============================================================

At minimum, distinguish:

- when a geographic fact was true in-universe;
- when the fact was entered or revised in the repository.

Use:

valid_from
valid_to
recorded_at
superseded_at
source_effective_date
world_state_date

This prevents a 2026 map from overwriting a 2018 state.

For ownership and operation, preserve separate fields:

owner_entity
operator_entity
host_entity
lessor_entity
rights_type

A railroad segment may be:

- owned by BS&T;
- operated by BS&T;
- hosted by another railroad;
- used under trackage rights;
- jointly used;
- abandoned but still owned;
- sold but historically operated.

Do not reduce all of those to one “railroad” field.

============================================================
30. CORPORATE-HISTORY MAP ENGINE
============================================================

The package should eventually support historical queries and map generation.

Examples:

    render_map(as_of="2019-12-31")
    render_map(as_of="2024-06-30", entity="ARU")
    render_map(as_of="2025-12-31", entity="BS&T")
    render_map(event="RED_WASH_ACQUISITION")
    render_map(compare=["2024-01-01", "2026-01-01"])

A future timeline should allow users to move through:

- founding;
- early offices;
- major projects;
- acquisitions;
- expansions;
- closures;
- reorganizations;
- current footprint.

Historical maps must display only assets and ownership relationships valid at the selected date.

============================================================
31. PROVENANCE MUST BE FEATURE-LEVEL
============================================================

Dataset-level provenance alone is not enough.

Each important Sable Harbor geometry should link to:

- canon source;
- decision source;
- real-world reference source;
- geometry-construction method;
- reviewer;
- date;
- prior geometry if superseded.

For engineered fictional geometry, preserve:

- constraint layers used;
- candidate alternatives;
- selected alternative;
- reason for selection;
- calculated metrics;
- decision approving it.

For map-derived points, preserve:

- source image;
- image checksum;
- image dimensions;
- pin pixel coordinate;
- map extent or georeferencing method;
- resulting uncertainty.

That is particularly important if the missing Red Wash pin map is ever recovered.

============================================================
32. REPOSITORY INTEGRATION
============================================================

Repository:

    SquirmyWormy275/SABLEHARBOR

Use the current `main` branch as the starting canon authority.

Before writing:

1. inspect current main;
2. record the commit SHA;
3. inspect canon, decision-register, organization, finance and brand material;
4. search the full tree;
5. identify active branches or pending work that may affect geography;
6. do not rely on stale snippets from prior chats.

Recommended working branch:

    feature/master-geospatial-package

Alternative if naming conventions require:

    worldbuilding/geospatial-master

Create coherent commits.

Suggested commit sequence:

1. Establish geospatial program structure and governance.
2. Add enterprise geographic census and decision register.
3. Add controlled geospatial schema and build tooling.
4. Add Sacramento, Evalon and Cradle constrained site geometry.
5. Add Red Wash siting analysis and selected geometry.
6. Add Bloodstone and Wamsutter network nodes.
7. Add engineered BS&T alignment and validation.
8. Add temporal model and historical network states.
9. Add initial corporate and business-line map series.
10. Add validation, provenance and release package.

Do not make one enormous opaque commit if the work can be separated cleanly.

Do not merge unresolved contradictions into main as though they are settled.

However, do not use “awaiting review” as an excuse to stop building scaffolding, candidate geometry, validation and draft products.

============================================================
33. BRAND ASSET HANDLING
============================================================

The ARU and BS&T logos were locked as exact images in the parent chat.

The exact images matter.

Do not recreate them from prose.

First search:

- current repo brand assets;
- project uploads;
- current-conversation images;
- prior generated image assets;
- manifests and checksums.

The current repository tree includes ARU and BS&T brand assets, but verify whether those files are the exact user-approved images or later approximations.

If exact identity cannot be established:

- do not silently substitute;
- create maps without the logo or use a clearly labeled placeholder;
- record the missing-asset issue;
- request the exact image only when needed for final branded output.

Map geometry work must continue even while a logo asset is unresolved.

============================================================
34. MAP PRODUCT CONTROL
============================================================

Every controlled map should have a map identifier.

Suggested pattern:

SH-MAP-ENT-001
SH-MAP-BST-001
SH-MAP-ARU-001
SH-MAP-RWM-001
SH-MAP-CRD-001
SH-MAP-EVL-001
SH-MAP-HIST-001

Metadata should include:

map_id
title
version
effective_date
world_state
canon_status
source_package_version
source_commit
projection
build_timestamp
builder
review_status
file_sha256

Recommended visual status marks:

CANON
ENGINEERED DRAFT
PROPOSED
REFERENCE
HISTORICAL
CONFLICT REVIEW

Do not distribute a proposed route without a visible status label.

============================================================
35. VALIDATION REQUIREMENTS
============================================================

Build automated validation.

---------------------------
35.1 Geometry validation
---------------------------

Check:

- valid geometry;
- correct geometry type;
- no empty geometry;
- no impossible latitude/longitude;
- no unintended self-intersections;
- polygons close properly;
- lines connect to their declared nodes;
- multipart geometry is intentional;
- projected calculations use an appropriate CRS.

---------------------------
35.2 Topology validation
---------------------------

For rail:

- segment endpoints match nodes;
- routes are connected;
- no unexplained gaps;
- no duplicate overlapping BS&T segments;
- ownership and operation are defined;
- interchange connects to the real-reference network;
- branches connect to the main line;
- milepost order is logical;
- historical states do not create impossible simultaneous ownership unless documented.

---------------------------
35.3 Temporal validation
---------------------------

Check:

- `valid_from` precedes `valid_to`;
- acquisition does not precede entity existence;
- disposed assets are not shown as currently owned;
- closed assets are not shown as active;
- historical maps filter correctly;
- superseded records remain traceable.

---------------------------
35.4 Provenance validation
---------------------------

Check:

- every canonical or engineered geometry has a source or decision record;
- every real-reference dataset has license information;
- every locked site has a decision record;
- no “exact” point uses only city-level evidence;
- no map-only decision lacks source-image provenance.

---------------------------
35.5 Naming validation
---------------------------

Check:

- AMERICAN RESOURCE UTILITY is written correctly;
- BLOOD, SWEAT & TEARS RAILWAY is written correctly;
- BS&T punctuation is consistent;
- Kanawha is spelled correctly;
- Wamsutter is spelled correctly;
- Red Wash and Bloodstone names are consistent;
- Evalon and Cradle are not conflated;
- current and former names are temporally correct.

---------------------------
35.6 Cartographic validation
---------------------------

Check:

- labels do not overlap materially;
- legend includes all line types;
- fictional versus real features are distinguishable;
- scale and projection are stated;
- map effective date is visible;
- map status is visible;
- sources and attribution are present;
- route geometry is not obscured by basemap clutter;
- exported PDFs remain legible at intended print size.

Create:

    geospatial/reports/GEOSPATIAL_VALIDATION_REPORT.md
    geospatial/reports/GEOMETRY_VALIDATION.json
    geospatial/reports/PROVENANCE_COVERAGE.csv
    geospatial/reports/OPEN_CONFLICTS.md

============================================================
36. TESTS
============================================================

Add tests for:

- stable unique IDs;
- schema conformity;
- valid CRS declarations;
- GeoJSON generation;
- GeoPackage generation;
- route connectivity;
- temporal filtering;
- ownership filtering;
- map manifest completeness;
- source-license completeness;
- checksum generation;
- deterministic builds where practical.

A clean checkout should be able to rebuild the package or clearly document any externally fetched inputs required.

Do not make the GeoPackage depend on an undocumented local QGIS state.

============================================================
37. WEB AND INTERACTIVE MAP FUTURE
============================================================

Design the data so it can later power:

- an Alexandria spatial portal;
- a Sable Harbor corporate atlas;
- an interactive acquisition timeline;
- a BS&T route explorer;
- site-detail pages;
- map-based canon search;
- historical comparison;
- asset lineage;
- network analysis.

Potential future outputs:

    sable_harbor_master.pmtiles
    sable_harbor_style.json
    site-detail JSON API
    vector-tile layers
    static map service
    temporal map controls

Do not build an elaborate web interface before the underlying geographic data is governed.

The web map must consume the source package, not create a second independent geography.

============================================================
38. DECISION-MAKING METHOD
============================================================

The next chat should not ask the user to decide every coordinate manually.

For each unresolved geography:

1. establish canon constraints;
2. research real geography;
3. produce a recommendation;
4. explain the material tradeoffs;
5. ask only for decisions that materially change the universe;
6. once decided, record and implement the decision immediately.

When asking:

- ask one coherent decision at a time;
- give a recommended option;
- identify what becomes locked;
- identify what remains engineering detail;
- do not ask vague questions such as “what do you think?” without a concrete proposal.

Examples of decisions that may genuinely require the user:

- which of two materially different Red Wash candidate zones becomes canonical;
- whether BS&T historically served a coal property before Red Wash;
- the acquisition date defining “pre-acquisition”;
- whether Bloodstone is a company town, an existing independent town, or only a railroad location;
- whether Cradle has barge access as a core design element;
- whether a disputed old map overrides a newer siting decision.

Examples that normally should not require the user:

- exact coordinate-system choice;
- GeoPackage table design;
- where to place a legend;
- minor route vertices;
- file naming;
- routine geometry validation;
- routine source attribution;
- ordinary map-export settings.

============================================================
39. USER CONTINUATION RULE
============================================================

The user has explicitly established this working rule:

    KEEP GOING unless the user says HOLD/STOP
    or a genuine user decision is required.

An acknowledgment is not a stopping instruction.

“Okay,” “yeah,” “sounds good,” and similar responses mean continue.

Do not repeatedly say:

- “one moment”;
- “working on it”;
- “next I would”;
- “I’m going to”;

and then stop without producing work.

Every turn should do one of the following:

- produce a substantive artifact;
- make a concrete decision recommendation;
- report completed implementation;
- surface a genuine blocking contradiction;
- ask a necessary decision question.

Do not end with a status-only response.

============================================================
40. OPEN QUESTIONS TO SURFACE, NOT SILENTLY ANSWER
============================================================

The comprehensive census should determine whether current canon resolves:

- the exact acquisition date and chain for ARU and BS&T;
- which entity acquired which;
- what “pre-acquisition BS&T” precisely means;
- BS&T’s founding date;
- BS&T’s original traffic base;
- whether BS&T existed before Red Wash;
- whether Red Wash was a BS&T customer before Sable Harbor ownership;
- whether BS&T has historical coal branches;
- whether Bloodstone predates the railroad;
- whether Bloodstone is incorporated;
- whether Wamsutter is the only interchange;
- whether BS&T owns all of its route;
- whether ARU owns utility infrastructure geographically separate from BS&T;
- whether Cradle is a project, operating division, branded capability or legal entity;
- exact Blackridge geography;
- exact Foundry/Foundry Field geography;
- exact Willow geography beyond Pittsburgh/Evalon;
- J2’s physical geography;
- Alexandria’s physical hosting geography, if relevant;
- historical headquarters;
- former and divested sites.

Do not allow these questions to prevent building the schema and census.

Mark them OPEN and continue.

============================================================
41. FIRST EXECUTION PHASE
============================================================

Immediately perform a repository-wide geographic census.

Deliver:

    geospatial/registers/GEOGRAPHIC_CENSUS_v0.1.csv
    geospatial/registers/GEOGRAPHIC_DECISION_REGISTER_v0.1.md
    geospatial/registers/OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md
    geospatial/docs/CANON_SOURCE_HIERARCHY.md

The census must include every discovered named place, facility, corridor, territory and site.

For each, record:

- exact quoted/source wording;
- source path;
- commit;
- relevant date;
- entity;
- place;
- granularity;
- status;
- conflicts;
- next action.

Do not summarize the census from memory.

Build it from the current repository.

============================================================
42. SECOND EXECUTION PHASE
============================================================

Build the geospatial foundation.

Deliver:

    geospatial/docs/GEOSPATIAL_DATA_MODEL.md
    geospatial/docs/CANON_AND_PROVENANCE_POLICY.md
    geospatial/docs/TEMPORAL_GIS_MODEL.md
    geospatial/schema/geospatial_schema.sql
    geospatial/scripts/build_geopackage.py
    geospatial/scripts/validate_geospatial.py
    geospatial/master/sable_harbor_master_v0.1.gpkg
    geospatial/qgis/sable_harbor_master.qgz

The first GeoPackage may contain constrained or proposed objects, provided their statuses are explicit.

It should not wait until every site is finalized.

============================================================
43. THIRD EXECUTION PHASE
============================================================

Implement the already-locked city/corridor decisions.

Create constrained geometries for:

- Sacramento HQ district;
- Evalon/Hazelwood district;
- Cradle/Belle-Kanawha corridor;
- Red Wash candidate envelope;
- Bloodstone siting envelope;
- Wamsutter interchange study area.

These are not yet the final parcel and railway geometries.

They define the locked search areas.

Deliver:

    geospatial/geojson/locked_search_areas.geojson
    geospatial/maps/SH-MAP-ENT-001_locked-geographic-framework.pdf

============================================================
44. FOURTH EXECUTION PHASE
============================================================

Engineer the exact core sites.

Order:

1. Red Wash;
2. Bloodstone;
3. Wamsutter interchange;
4. BS&T alignment;
5. Sacramento HQ;
6. Evalon;
7. Cradle.

This order is recommended because Red Wash/Bloodstone/Wamsutter jointly constrain the railway.

Do not fully engineer the BS&T route before its endpoints and operating nodes are credible.

============================================================
45. FIFTH EXECUTION PHASE
============================================================

Build the initial map series.

Minimum first release:

- Sable Harbor Corporate Footprint;
- Locked Geographic Framework;
- Red Wash Regional Context;
- Red Wash Site;
- BS&T Pre-Acquisition System;
- BS&T Engineering Alignment;
- Sacramento HQ Context;
- Evalon Hazelwood Context;
- Cradle Kanawha Context;
- Open Geographic Questions map.

Export each as:

- PDF;
- SVG;
- PNG;
- metadata JSON.

============================================================
46. RELEASE PACKAGE
============================================================

Create a versioned package.

Suggested release:

    geospatial/releases/sable-harbor-geospatial-v0.1.0/

Contents:

- GeoPackage;
- QGIS project;
- GeoJSON;
- registers;
- source manifest;
- license manifest;
- validation reports;
- rendered maps;
- checksums;
- release notes;
- known limitations.

Suggested files:

    RELEASE_NOTES.md
    MANIFEST.json
    SOURCES.json
    LICENSES.md
    CHECKSUMS.sha256
    KNOWN_LIMITATIONS.md

Do not call the release complete if it contains undocumented geometry.

============================================================
47. DEFINITION OF DONE
============================================================

The initial program is complete when:

- every known geographic reference in the repo has been inventoried;
- every item is classified as locked, constrained, open, conflicting or non-spatial;
- the locked decisions from this handover are represented;
- a valid GeoPackage exists;
- the GeoPackage opens cleanly in QGIS;
- geometry is reproducibly sourced;
- Red Wash has a deliberately selected exact site;
- Bloodstone has a deliberately selected exact site;
- BS&T has an actual connected LINESTRING network;
- Wamsutter interchange geometry is plausible and clearly distinguishes real and fictional infrastructure;
- HQ, Evalon and Cradle have site polygons;
- temporal fields exist;
- provenance exists at feature level;
- the first map series is rendered;
- automated validation passes;
- remaining uncertainty is explicitly registered;
- no illustrative point or route has silently become canon;
- no real property has been falsely claimed as Sable Harbor-owned.

============================================================
48. DO-NOT-DO LIST
============================================================

Do not:

- return to vague “somewhere in Wyoming” geography;
- create only pins;
- draw BS&T as a straight line;
- use city centroids as exact facilities;
- silently appropriate real parcels;
- silently appropriate real mines;
- silently appropriate real rail infrastructure;
- conflate Cradle with Evalon;
- conflate Emberline with Cradle;
- treat a map rendering as the database;
- lose historical geometry;
- omit effective dates;
- omit source licenses;
- recreate the locked logos;
- invent that the missing Red Wash map was found;
- stop after writing another plan;
- ask permission for routine implementation details;
- re-litigate locked corridor decisions without evidence of a conflict;
- mark proposed geometry as final;
- answer with an acknowledgment and no work.

============================================================
49. IMMEDIATE START INSTRUCTION
============================================================

Begin now.

Your first response must not merely restate this handover.

Perform the work.

Start by:

1. inspecting the current SABLEHARBOR repository;
2. recording the current main commit;
3. conducting the comprehensive geographic census;
4. locating every geographic map/image/asset, including any possible Red Wash pin map;
5. classifying all geographic facts;
6. creating the decision register;
7. establishing the geospatial directory and schema;
8. producing the first controlled search-area GeoJSON and framework map.

Continue without waiting unless:

- a genuine canon conflict is found;
- a material worldbuilding decision must be made by the user;
- the user says HOLD or STOP.

When a decision is required, present:

- the exact question;
- the evidence;
- the recommended answer;
- the implications;
- what will be locked after approval.

Then resume implementation immediately after the decision.

============================================================
END OF HANDOVER
============================================================
