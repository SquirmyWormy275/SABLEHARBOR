# Data model and authority

## Independent concepts

| Concept | Storage | Meaning |
|---|---|---|
| Entity | `entity_registry` | Company, subsidiary, program or external operator; no invented legal suffix |
| Geographic object | `object_registry` | A named place, site, facility, event, infrastructure object or unlocated physical reference |
| Source claim | `source_claims` | Exact wording and locator, retained even when disputed |
| Decision | `decision_registry` | Governance instruction and rationale, separate from a source observation |
| Geometry | Spatial feature tables | A particular representation with status, method and source |
| Asset state | `asset_states` | Dated operation, custody or rights assertions; operator and title owner are separate |
| Relationship | `spatial_relationships` | Dated institutional or spatial relationship; not automatic co-location |
| Event | `event_registry` | Historical occurrence with date precision and references |
| Conflict | `conflicts` | Unresolved competing assertions with question, recommendation and implications |
| Route | `rail_routes` | Ordered member segment IDs and operational endpoints; preliminary scenario routes, without inferred historical dates |
| Geometry provenance | `geometry_provenance` | Feature-level WKB hash, inputs, construction method and supersession |

All feature and attribute tables use an integer primary key as required by GeoPackage. Stable string IDs are separate unique columns. GeoPackage 1.3 uses EPSG:4326 in longitude/latitude order. The authoritative schema is `schema/geospatial_schema.sql`; common feature fields are defined in `scripts/build_geopackage.py`.

Every spatial feature records fictionality, relation to real geography, canon status, geometry status, location method, precision class, horizontal/vertical accuracy if known, source/decision IDs, timestamps, owners/operators/hosts/lessors where supported, engineering fields and original properties. Unknown accuracy is null; six decimal places in an export are not a claim of sub-meter accuracy.

## Layers in this candidate

Six search polygons, two historical source/diagnostic points and five Census municipal reference labels accompany the new approved anchor and preliminary engineering geometry. Federal snapshots occupy distinct `ref_*` layers. The approved Red Wash anchor, preliminary Red Wash/Taylor sites, mine functional zones, three rail nodes, two connected rail segments and yard/interchange reservations are populated. Other empty classes remain reservations, not evidence of completed engineering.

Search polygons are analyst-defined study windows. Their construction is recorded in each feature, including the Wyoming county clipping input. They are not cadastral parcels or official planning-district boundaries. The HQ, Hazelwood and Cradle target acreages apply to eventual facilities, not the much larger study windows.

Municipal label points use Census internal-point fields. They are display references, not exact Sable Harbor locations. They are not necessarily mathematical centroids despite the broad `CENTROID` method vocabulary. The note and precision class retain this distinction.

## Status does not follow visual polish

The census classification (`LOCKED`, `CONSTRAINED`, `OPEN`, `CONFLICTING`, `NON_SPATIAL`) is separate from detailed feature canon status and geometry status. `REAL_REFERENCE` describes real-world context. `SOURCE_CLAIM` describes an assertion. `CANON_CONSTRAINED` does not mean `CANON_SITED`; a source point that looks precise can still be disputed. The approved Red Wash map control is `CANON_SITED`; its detailed site and all proposed rail geometry remain separately qualified.

The repository's canon hierarchy governs conflicts: approved canon and decisions precede lower-authority narrative or generated derivatives. The user's latest mandate adds controlling instructions but expressly requires surfacing material conflicts. The private NAILEX research attachment is not a corporate geography source merely because it was supplied with the task.

## Edits and supersession

Edit governed inputs, add the source and decision, preserve the prior assertion, rebuild, validate, render, inspect and commit through a PR. Keep stable object IDs when the same asset changes. Use new feature/state IDs for a materially changed geometry or period and connect superseded records. Never overwrite a historical location to make the current map convenient.

Database indexes, additional controlled vocabularies and more populated relationships may be added when exact-site work needs them. The model is implemented and validated; a fully populated corporate asset history is not claimed.
