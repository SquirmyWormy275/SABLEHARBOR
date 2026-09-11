-- Immutable snapshots and version payloads; derived query index, never source authority.
CREATE TABLE snapshot (
  snapshot_id TEXT PRIMARY KEY,
  recorded_on TEXT NOT NULL UNIQUE,
  source_manifest TEXT NOT NULL
);
CREATE TABLE record_version (
  kind TEXT NOT NULL,
  record_id TEXT NOT NULL,
  version TEXT NOT NULL,
  recorded_on TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  payload_sha256 TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (kind, record_id, version),
  CHECK (effective_to IS NULL OR effective_to > effective_from)
);
CREATE TABLE snapshot_record (
  snapshot_id TEXT NOT NULL REFERENCES snapshot(snapshot_id),
  kind TEXT NOT NULL,
  record_id TEXT NOT NULL,
  version TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, kind, record_id),
  FOREIGN KEY (kind, record_id, version) REFERENCES record_version(kind, record_id, version)
);
CREATE TABLE reference_edge (
  snapshot_id TEXT NOT NULL REFERENCES snapshot(snapshot_id),
  from_kind TEXT NOT NULL,
  from_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  to_kind TEXT NOT NULL,
  to_id TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, from_kind, from_id, relation, to_kind, to_id),
  FOREIGN KEY (snapshot_id, from_kind, from_id) REFERENCES snapshot_record(snapshot_id, kind, record_id),
  FOREIGN KEY (snapshot_id, to_kind, to_id) REFERENCES snapshot_record(snapshot_id, kind, record_id)
);
CREATE INDEX record_temporal ON record_version(recorded_on, effective_from);
PRAGMA user_version = 1;
