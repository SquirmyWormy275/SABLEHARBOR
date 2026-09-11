"""Append-only SQLite index with source-version guards and bitemporal lookup."""

import json
import sqlite3
from datetime import date

from enterprise.ccf.registry import ROOT, canonical, digest, validate


def connect(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def migrate(connection):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version == 1:
        return
    if (
        version != 0
        or connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ):
        raise ValueError("Unsupported or nonempty database; no destructive migration")
    connection.executescript((ROOT / "enterprise/ccf/migrations/001_registry.sql").read_text())
    for table in ("snapshot", "record_version", "snapshot_record", "reference_edge"):
        for event in ("UPDATE", "DELETE"):
            connection.execute(
                f"CREATE TRIGGER immutable_{table}_{event} BEFORE {event} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable CCF history'); END"
            )
    connection.commit()


def edges(record):
    data = record["data"]
    singular = {
        "domain_id": "domain",
        "control_id": "control",
        "boundary_id": "boundary",
        "owner_role_id": "role",
        "performer_role_id": "role",
        "challenge_role_id": "role",
        "approver_role_id": "role",
        "inherits_from_id": "implementation",
        "planned_boundary_id": "boundary",
        "provider_id": "provider",
        "owner_component_id": "component",
    }
    if record["kind"] == "boundary":
        singular["parent_id"] = "boundary"
    plural = {
        "objective_ids": "objective",
        "risk_ids": "risk",
        "enterprise_objective_ids": "enterprise_objective",
        "control_ids": "control",
        "upstream_control_ids": "control",
        "boundary_ids": "boundary",
        "secondary_domain_ids": "domain",
        "component_ids": "component",
        "dependency_ids": "dependency",
    }
    for key, kind in singular.items():
        if data.get(key):
            yield key, kind, data[key]
    for key, kind in plural.items():
        for identifier in data.get(key, []):
            yield key, kind, identifier


def append(connection, registry):
    validate(registry)
    migrate(connection)
    identity = digest(registry)
    if connection.execute("SELECT 1 FROM snapshot WHERE snapshot_id=?", (identity,)).fetchone():
        return identity
    recorded = max(r["recorded_on"] for r in registry["records"])
    latest = connection.execute("SELECT MAX(recorded_on) FROM snapshot").fetchone()[0]
    if latest and recorded <= latest:
        raise ValueError(
            "A distinct snapshot needs a later recorded date; history is not overwritten"
        )
    existing = {
        (k, i) for k, i in connection.execute("SELECT DISTINCT kind,record_id FROM record_version")
    }
    incoming = {(r["kind"], r["id"]) for r in registry["records"]}
    if existing - incoming:
        raise ValueError("Records cannot disappear; retain a retired version")
    with connection:
        connection.execute(
            "INSERT INTO snapshot VALUES (?,?,?)",
            (identity, recorded, canonical(registry["source_manifest"])),
        )
        for r in registry["records"]:
            key = (r["kind"], r["id"], r["version"])
            old = connection.execute(
                "SELECT payload_sha256 FROM record_version WHERE kind=? AND record_id=? AND version=?",
                key,
            ).fetchone()
            if old and old[0] != digest(r):
                raise ValueError("Changed published record requires a new version")
            if not old:
                previous = connection.execute(
                    "SELECT version,recorded_on,effective_from FROM record_version WHERE kind=? AND record_id=? ORDER BY recorded_on DESC LIMIT 1",
                    key[:2],
                ).fetchone()
                if previous and (
                    tuple(map(int, r["version"].split(".")))
                    <= tuple(map(int, previous[0].split(".")))
                    or r["recorded_on"] <= previous[1]
                ):
                    raise ValueError("New version must advance version and recorded date")
                connection.execute(
                    "INSERT INTO record_version VALUES (?,?,?,?,?,?,?,?)",
                    key
                    + (
                        r["recorded_on"],
                        r["effective_from"],
                        r["effective_to"],
                        digest(r),
                        canonical(r),
                    ),
                )
            connection.execute("INSERT INTO snapshot_record VALUES (?,?,?,?)", (identity,) + key)
        for r in registry["records"]:
            for relation, kind, identifier in edges(r):
                connection.execute(
                    "INSERT INTO reference_edge VALUES (?,?,?,?,?,?)",
                    (identity, r["kind"], r["id"], relation, kind, identifier),
                )
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("CCF index foreign key failure")
    return identity


def historical(connection, as_of, known_on):
    date.fromisoformat(as_of)
    date.fromisoformat(known_on)
    records = connection.execute(
        "SELECT payload FROM record_version WHERE effective_from<=? AND recorded_on<=? ORDER BY recorded_on, rowid",
        (as_of, known_on),
    ).fetchall()
    selected = {}
    for (payload,) in records:
        row = json.loads(payload)
        selected[row["kind"], row["id"]] = row
    # An explicit end/retirement must not reveal an older version again.
    return [
        r
        for _, r in sorted(selected.items())
        if r["effective_to"] is None or as_of < r["effective_to"]
    ]
