-- Metadata substrate. OGC feature tables are created with the same governed
-- columns by build_geopackage.py; geometry is encoded as GeoPackageBinary.
PRAGMA foreign_keys=ON;
CREATE TABLE source_registry (
 fid INTEGER PRIMARY KEY,
 source_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL, publisher_or_author TEXT,
 source_type TEXT, publication_date TEXT, accessed_date TEXT NOT NULL,
 url_or_repo_path TEXT NOT NULL, repository_commit TEXT, file_sha256 TEXT,
 license TEXT NOT NULL, citation TEXT, coverage TEXT, source_quality TEXT, notes TEXT
);
CREATE TABLE entity_registry (
 fid INTEGER PRIMARY KEY,
 entity_id TEXT NOT NULL UNIQUE, canonical_name TEXT NOT NULL, entity_type TEXT NOT NULL,
 parent_entity_id TEXT REFERENCES entity_registry(entity_id), valid_from TEXT,
 valid_to TEXT, legal_status TEXT, canon_status TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES source_registry(source_id), notes TEXT,
 CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to>valid_from)
);
CREATE TABLE decision_registry (
 fid INTEGER PRIMARY KEY,
 decision_id TEXT NOT NULL UNIQUE, decision_date TEXT NOT NULL, decision_title TEXT NOT NULL,
 decision_type TEXT NOT NULL, affected_object_ids TEXT NOT NULL,
 decision_status TEXT NOT NULL, deciding_authority TEXT NOT NULL,
 source_conversation TEXT, source_document TEXT, rationale TEXT NOT NULL,
 alternatives_considered TEXT, supersedes_decision_id TEXT REFERENCES decision_registry(decision_id), notes TEXT
);
CREATE TABLE object_registry (
 fid INTEGER PRIMARY KEY,
 object_id TEXT NOT NULL UNIQUE, canonical_name TEXT NOT NULL, object_type TEXT NOT NULL,
 entity_id TEXT REFERENCES entity_registry(entity_id), place TEXT, granularity TEXT,
 census_status TEXT NOT NULL, canon_status TEXT NOT NULL, fictionality TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES source_registry(source_id), source_path TEXT,
 source_commit TEXT, source_locator TEXT, exact_source_wording TEXT NOT NULL,
 relevant_date TEXT, date_precision TEXT, conflict_id TEXT, next_action TEXT,
 notes TEXT, decision_id TEXT NOT NULL REFERENCES decision_registry(decision_id)
);
CREATE TABLE source_claims (
 fid INTEGER PRIMARY KEY,
 claim_id TEXT NOT NULL UNIQUE, object_id TEXT NOT NULL REFERENCES object_registry(object_id),
 source_id TEXT NOT NULL REFERENCES source_registry(source_id), source_locator TEXT,
 exact_source_wording TEXT NOT NULL, claim_status TEXT NOT NULL, notes TEXT
);
CREATE TABLE spatial_relationships (
 fid INTEGER PRIMARY KEY,
 relationship_id TEXT NOT NULL UNIQUE, subject_id TEXT NOT NULL, predicate TEXT NOT NULL,
 object_id TEXT NOT NULL, valid_from TEXT, valid_to TEXT, date_text TEXT,
 canon_status TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES source_registry(source_id),
 decision_id TEXT REFERENCES decision_registry(decision_id), notes TEXT,
 CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to>valid_from)
);
CREATE TABLE conflicts (
 fid INTEGER PRIMARY KEY,
 conflict_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL, affected_object_ids TEXT NOT NULL,
 status TEXT NOT NULL, source_ids TEXT NOT NULL, recommendation TEXT NOT NULL,
 question TEXT NOT NULL, implications TEXT NOT NULL
);
CREATE TABLE rail_routes (
 fid INTEGER PRIMARY KEY,
 route_id TEXT NOT NULL UNIQUE, canonical_name TEXT NOT NULL, railroad TEXT,
 route_type TEXT, origin_node TEXT, destination_node TEXT, segment_ids TEXT NOT NULL,
 valid_from TEXT, valid_to TEXT, status TEXT, canon_status TEXT NOT NULL,
 decision_id TEXT NOT NULL REFERENCES decision_registry(decision_id), notes TEXT
);
CREATE TABLE asset_states (
 fid INTEGER PRIMARY KEY,
 state_id TEXT NOT NULL UNIQUE, asset_id TEXT NOT NULL REFERENCES object_registry(object_id),
 canonical_name TEXT NOT NULL, owner_entity TEXT REFERENCES entity_registry(entity_id),
 operator_entity TEXT REFERENCES entity_registry(entity_id), host_entity TEXT REFERENCES entity_registry(entity_id),
 lessor_entity TEXT REFERENCES entity_registry(entity_id), rights_type TEXT,
 operating_status TEXT, valid_from TEXT, valid_to TEXT, opened_on TEXT, closed_on TEXT,
 acquired_on TEXT, disposed_on TEXT, earliest_start TEXT, latest_start TEXT,
 earliest_end TEXT, latest_end TEXT, date_precision TEXT, snapshot_as_of TEXT,
 recorded_at TEXT NOT NULL, superseded_at TEXT, source_effective_date TEXT, world_state_date TEXT,
 source_id TEXT NOT NULL REFERENCES source_registry(source_id), decision_id TEXT REFERENCES decision_registry(decision_id), notes TEXT,
 CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to>valid_from),
 CHECK(latest_start IS NULL OR earliest_start IS NULL OR latest_start>=earliest_start),
 CHECK(latest_end IS NULL OR earliest_end IS NULL OR latest_end>=earliest_end)
);
CREATE TABLE event_registry (
 fid INTEGER PRIMARY KEY,
 event_id TEXT NOT NULL UNIQUE REFERENCES object_registry(object_id), canonical_name TEXT NOT NULL,
 event_type TEXT NOT NULL, event_date TEXT, event_end_date TEXT, date_text TEXT,
 date_precision TEXT NOT NULL, entity_ids TEXT NOT NULL, asset_ids TEXT NOT NULL,
 canon_status TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES source_registry(source_id),
 decision_id TEXT REFERENCES decision_registry(decision_id), description TEXT, notes TEXT
);
CREATE TABLE geometry_provenance (
 fid INTEGER PRIMARY KEY,
 feature_id TEXT NOT NULL UNIQUE, layer_name TEXT NOT NULL,
 object_id TEXT REFERENCES object_registry(object_id), geometry_sha256 TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES source_registry(source_id), decision_id TEXT REFERENCES decision_registry(decision_id),
 reference_source_ids TEXT NOT NULL, construction_method TEXT NOT NULL,
 reviewed_by TEXT, review_date TEXT, supersedes_feature_id TEXT REFERENCES geometry_provenance(feature_id), notes TEXT
);
CREATE TABLE package_metadata (fid INTEGER PRIMARY KEY, key TEXT NOT NULL UNIQUE, value TEXT NOT NULL);
