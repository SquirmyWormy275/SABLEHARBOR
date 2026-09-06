PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS release_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_registry(
 source_id TEXT PRIMARY KEY,title TEXT NOT NULL,path TEXT,source_type TEXT NOT NULL,
 authority_rank INTEGER NOT NULL,source_commit TEXT,file_sha256 TEXT,license TEXT NOT NULL,
 accessed_at TEXT NOT NULL,url TEXT,notes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entity_registry(
 entity_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,entity_type TEXT NOT NULL,
 parent_entity_id TEXT REFERENCES entity_registry(entity_id),legal_status TEXT NOT NULL,
 canon_status TEXT NOT NULL,source_id TEXT REFERENCES source_registry(source_id),
 valid_from TEXT,valid_to TEXT,recorded_at TEXT NOT NULL,superseded_at TEXT,
 CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_from<valid_to)
);
CREATE TABLE IF NOT EXISTS object_registry(
 object_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,object_type TEXT NOT NULL,
 contextual_actor TEXT NOT NULL,geographic_constraint TEXT NOT NULL,decision_state TEXT NOT NULL,
 geometry_state TEXT NOT NULL,temporal_scope TEXT,valid_from TEXT,valid_to TEXT,
 recorded_at TEXT NOT NULL,superseded_at TEXT,source_id TEXT NOT NULL REFERENCES source_registry,
 source_path TEXT NOT NULL,source_line INTEGER NOT NULL,exact_source_wording TEXT NOT NULL,
 conflict_id TEXT,next_action TEXT NOT NULL,
 CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_from<valid_to),
 CHECK(superseded_at IS NULL OR recorded_at<superseded_at)
);
CREATE TABLE IF NOT EXISTS decision_registry(
 decision_id TEXT PRIMARY KEY,decision_date TEXT NOT NULL,decision_title TEXT NOT NULL,
 decision_status TEXT NOT NULL,deciding_authority TEXT NOT NULL,source_id TEXT REFERENCES source_registry,
 rationale TEXT NOT NULL,supersedes_decision_id TEXT REFERENCES decision_registry
);
CREATE TABLE IF NOT EXISTS decision_objects(
 decision_id TEXT REFERENCES decision_registry,object_id TEXT REFERENCES object_registry,
 PRIMARY KEY(decision_id,object_id)
);
CREATE TABLE IF NOT EXISTS spatial_assets(
 asset_id TEXT PRIMARY KEY REFERENCES object_registry(object_id),asset_type TEXT NOT NULL,
 owner_entity TEXT REFERENCES entity_registry,operator_entity TEXT REFERENCES entity_registry,
 fictionality TEXT NOT NULL,ownership_status TEXT NOT NULL,opened_on TEXT,closed_on TEXT,
 acquired_on TEXT,disposed_on TEXT,notes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS object_sources(
 object_id TEXT REFERENCES object_registry,source_id TEXT REFERENCES source_registry,
 role TEXT NOT NULL,PRIMARY KEY(object_id,source_id,role)
);
CREATE TABLE IF NOT EXISTS geometry_provenance(
 geometry_id TEXT NOT NULL,layer_name TEXT NOT NULL,object_id TEXT REFERENCES object_registry,
 source_id TEXT NOT NULL REFERENCES source_registry,source_role TEXT NOT NULL,
 decision_id TEXT REFERENCES decision_registry,construction_method TEXT NOT NULL,
 horizontal_accuracy_m REAL,precision_class TEXT NOT NULL,notes TEXT NOT NULL,
 PRIMARY KEY(geometry_id,source_id,source_role)
);
CREATE TABLE IF NOT EXISTS spatial_relationships(
 relationship_id TEXT PRIMARY KEY,subject_id TEXT NOT NULL REFERENCES object_registry,
 predicate TEXT NOT NULL,object_id TEXT NOT NULL REFERENCES object_registry,
 valid_from TEXT,valid_to TEXT,recorded_at TEXT NOT NULL,superseded_at TEXT,
 canon_status TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES source_registry,
 CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_from<valid_to)
);
CREATE TABLE IF NOT EXISTS ownership_history(
 ownership_id TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES object_registry,
 owner_entity TEXT REFERENCES entity_registry,operator_entity TEXT REFERENCES entity_registry,
 host_entity TEXT REFERENCES entity_registry,lessor_entity TEXT REFERENCES entity_registry,
 rights_type TEXT NOT NULL,valid_from TEXT,valid_to TEXT,recorded_at TEXT NOT NULL,
 superseded_at TEXT,source_id TEXT NOT NULL REFERENCES source_registry,
 CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_from<valid_to)
);
CREATE TABLE IF NOT EXISTS rail_routes(
 route_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,railroad_entity TEXT REFERENCES entity_registry,
 origin_node_id TEXT,destination_node_id TEXT,canon_status TEXT NOT NULL,
 valid_from TEXT,valid_to TEXT,recorded_at TEXT NOT NULL,superseded_at TEXT
);
CREATE TABLE IF NOT EXISTS rail_route_segments(
 route_id TEXT REFERENCES rail_routes,sequence INTEGER NOT NULL,segment_id TEXT NOT NULL,
 orientation INTEGER NOT NULL CHECK(orientation IN (-1,1)),PRIMARY KEY(route_id,sequence)
);
CREATE TABLE IF NOT EXISTS event_records(
 event_id TEXT PRIMARY KEY REFERENCES object_registry,event_date TEXT,event_date_precision TEXT NOT NULL,
 description TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES source_registry
);
CREATE TABLE IF NOT EXISTS conflicts(
 conflict_id TEXT PRIMARY KEY,title TEXT NOT NULL,state TEXT NOT NULL,
 recommended_resolution TEXT NOT NULL,blocked_work TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS object_dates_idx ON object_registry(valid_from,valid_to,recorded_at,superseded_at);
