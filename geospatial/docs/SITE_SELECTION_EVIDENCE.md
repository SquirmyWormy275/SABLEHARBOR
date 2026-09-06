# Site-selection evidence and engineering gates

Research accessed 6 September 2026. These findings advance the constrained search areas; none selects a parcel or proves ownership. External planning and physical facts are distinguished from fictional program choices.

## Sacramento headquarters

The handover's Railyards / River District seam is retained. The city describes the River District as a roughly 773-acre planning area north of downtown, with rivers and rail infrastructure defining major edges. The [city plan page](https://www.cityofsacramento.gov/community-development/planning/major-projects/RiverDistrictSpecificPlan.html) and [plan update page](https://www.cityofsacramento.gov/community-development/planning/major-projects/RiverDistrictSpecificPlan/AboutRiverDistrictSpecificPlan.html) provide planning context; an update in progress is not treated as adopted zoning. The [state environmental record](https://ceqanet.lci.ca.gov/2006032058/16) describes the roughly 244-acre Railyards project. Its actual project boundaries and parcels are not Sable Harbor property.

The archived NAIP screening export shows a mixed developed landscape: warehouses, roads, rail approaches, river edges, utilities and large cleared construction areas. Its catalog contains 2022 source tiles, including imagery acquired June 21, 2022. It does not establish current vacancy in 2026. The returned image extent differs from the requested bbox because the service adjusts aspect ratio; both are recorded. No footprint was digitized from a guessed pixel-to-ground transform.

The eventual 8–15-acre campus needs a connected street approach, plausible institutional-industrial adjacency, room for the approved architectural program, and evidence that it does not cover an active railway, river, public facility or occupied third-party development. An 8–15-acre rectangle placed in the study box would satisfy area arithmetic but would not complete those checks. The source priority for the next pass is the [city GIS portal](https://data.cityofsacramento.org/), [Sacramento County map services](https://mapservices.gis.saccounty.net/arcgis/rest/services) and current adopted project plans, followed by a deliberately fictional property history. The locked exterior reference binary remains missing; architectural massing must not be silently redesigned to suit a convenient parcel.

## Hazelwood / Evalon–Willow

The [Greater Hazelwood Neighborhood Plan](https://engage.pittsburghpa.gov/greater-hazelwood-neighborhood-plan) identifies a real Pittsburgh neighborhood; [Hazelwood Green](https://hazelwoodgreen.com/) describes an approximately 178-acre redevelopment with real occupants and projects. The handover's 10–20-acre working campus scale does not make any portion of this development available to Willow.

The historical outside-Pittsburgh shop conflicts with applying Hazelwood retroactively. GEO-C002 must establish the program and time period before exact occupancy is assigned. Independent road, rail and hydrography context is already fetched. Current tenant footprints and the city's [specially planned district materials](https://www.pittsburghpa.gov/Business-Development/City-Planning/Zoning/Planning-Applications-and-Processes/Specially-Planned-Districts) are the next parcel-scale references. Do not co-locate the 2021 shop and later campus merely because they share institutional lineage.

## Cradle / Belle–Kanawha

The study corridor is consistent with the recovery-development role, rather than ownership of a host mine or an automatic legal corporation. Cradle stays separate from Evalon/Willow and from the historical Charleston Emberline venture.

The [Chemours Belle site](https://www.chemours.com/en/about-chemours/global-reach/belle) is a real chemical operation. The [archived EPA cleanup profile](https://19january2021snapshot.epa.gov/hwcorrectiveactionsites/hazardous-waste-cleanup-chemours-belle-plant-formerly-dupont-belle-west_.html) describes a large industrial site and historical contamination context. That profile is historical evidence, not a current permitting or remediation determination. No part of the real plant is represented as Cradle-owned.

The NAIP export shows a narrow, heavily used valley floor between the Kanawha River and wooded relief, with existing industrial plants, residential areas, roads and rail. Catalog tiles in this window were acquired October 20–21, 2022. A 20–30-acre recovery-development facility needs a contiguous usable footprint and credible service access; the rectangular corridor currently includes river and hillside and is intentionally not a site boundary.

[NETL's acid-mine-drainage and coal-waste research](https://netl.doe.gov/node/11886), [project FE0031834](https://netl.doe.gov/project-information?p=FE0031834), and [WVU rare-earth research](https://rareearthelements.wvu.edu/) support the regional industrial research context. They do not establish fictional feedstock supply, a host agreement, a reserve or Cradle process performance. The [Kanawha County assessor mapping service](https://kanawhacountyassessor.com/mappings) and [WV parcel viewer](https://www.mapwv.gov/parcel/) are cadastral research leads. Their boundaries and ownership require source-specific accuracy and currency review before a proposed fictional lease footprint is drafted.

## Wyoming / Red Wash, Taylor and Wamsutter

GEO-C001 is resolved by the approved addendum; the controlling mine anchor is 42.22 N, 108.18 W. The Red Wash study window is clipped to the fetched Sweetwater County boundary; it is not a deposit, claim block, orebody or reserve. The [USGS Great Divide Basin uranium-bearing coal report](https://pubs.usgs.gov/publication/tei477) provides historical regional evidence. It does not validate a particular underground uranium mine, depth, grade, ventilation arrangement or mining method. Wyoming State Geological Survey material should guide the next geology and real-project exclusion pass.

The preferred Taylor C proposal is at 42.17 N, 108.225 W, with a new northern study window. It is not an incorporated real town or an approved property boundary. FRA rail reference near Wamsutter supplies real context; no BS&T operating rights are inferred from proximity to UP.

## Required railway analysis after endpoint decisions

Create distinct node and segment records for the legacy line, proposed mine connection, yards, interchange tracks, sidings, branches, bridges, tunnels, grade crossings, industries, abandoned alignments and trackage rights. Decide the historical effective date before publishing the pre-acquisition state. Store route membership, endpoint IDs, source/decision IDs, ownership and operation separately.

Fetch an appropriate elevation model with resolution and vertical datum. Compare multiple terrain-following alignments and report actual geodesic route length, elevation profile, ruling/maximum grade, minimum curvature, water/road crossings, structures and land constraints. Forty miles is a working scenario target, not permission to mismeasure or draw a straight line. A connected LINESTRING network with a plausible grade profile and independently justified junction layout is required before the railway can be described as engineered.

This release implements checks for endpoint snapping, graph connectivity, duplicate segments, owner/operator attribution and length consistency. A preliminary connected proposal now has separate ground/formation profiles, measured curvature and water screening. These checks do not establish final construction or operating acceptance. Floodplain, wetlands, land title, geotechnical conditions, rail standards and operating authority also remain unevaluated at exact-site scale.
