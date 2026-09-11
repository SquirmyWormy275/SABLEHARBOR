"""Explicit allowlisted runtime query schema. No source-driven SQL identifiers."""

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE runtime_site(id TEXT PRIMARY KEY, entity_id TEXT NOT NULL CHECK(entity_id='SHI'),
 facility_id TEXT UNIQUE NOT NULL, geospatial_site_id TEXT UNIQUE NOT NULL, provider_id TEXT,
 status TEXT NOT NULL, operating INTEGER NOT NULL CHECK(operating=0));
CREATE TABLE capacity(scenario TEXT NOT NULL,year INTEGER NOT NULL,site TEXT NOT NULL,
 cpu_hosts INTEGER NOT NULL,gpu_systems INTEGER NOT NULL,storage_shelves INTEGER NOT NULL,
 peak_kw REAL NOT NULL,typical_synthetic_kw REAL NOT NULL,durable_tib REAL NOT NULL,
 PRIMARY KEY(scenario,year,site));
CREATE TABLE annual_cash(scenario TEXT NOT NULL,year INTEGER NOT NULL,gross_cash_request TEXT NOT NULL,
 net_cash_request TEXT NOT NULL,discounted_net_cash TEXT NOT NULL,actual_paid_cash TEXT NOT NULL,
 PRIMARY KEY(scenario,year));
CREATE TABLE local_control(implementation_id TEXT PRIMARY KEY,control_id TEXT NOT NULL,
 runtime_id TEXT NOT NULL REFERENCES runtime_site(id),objective_id TEXT NOT NULL,
 operating_assessment TEXT NOT NULL CHECK(operating_assessment='NOT_ASSERTED'));
CREATE TABLE source_identity(version TEXT PRIMARY KEY,source_sha256 TEXT NOT NULL,state TEXT NOT NULL);
"""


def build(path, result):
    path = Path(path)
    if path.exists():
        raise ValueError("Refusing to overwrite an existing runtime database")
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        for row in result["sites"]:
            db.execute(
                "INSERT INTO runtime_site VALUES(?,?,?,?,?,?,?)",
                tuple(
                    row.get(k)
                    for k in (
                        "id",
                        "entity_id",
                        "facility_id",
                        "geospatial_site_id",
                        "provider_id",
                        "status",
                        "operating",
                    )
                ),
            )
        for row in result["capacity"]:
            db.execute(
                "INSERT INTO capacity VALUES(?,?,?,?,?,?,?,?,?)",
                tuple(
                    row[k]
                    for k in (
                        "scenario",
                        "year",
                        "site",
                        "cpu_hosts",
                        "gpu_systems",
                        "storage_shelves",
                        "peak_kw",
                        "typical_synthetic_kw",
                        "durable_tib",
                    )
                ),
            )
        for row in result["finance"]["annual"]:
            db.execute(
                "INSERT INTO annual_cash VALUES(?,?,?,?,?,?)",
                tuple(
                    row[k]
                    for k in (
                        "scenario",
                        "year",
                        "gross_cash_request",
                        "net_cash_request",
                        "discounted_net_cash",
                        "actual_paid_cash",
                    )
                ),
            )
        for row in result["capital"]["implementation_assumptions"][
            "control_implementations"
        ]:
            db.execute(
                "INSERT INTO local_control VALUES(?,?,?,?,?)",
                (
                    row["implementation_id"],
                    row["control_id"],
                    row["system_or_location"],
                    row["objective_id"],
                    row["operating_assessment"],
                ),
            )
        db.execute(
            "INSERT INTO source_identity VALUES(?,?,?)",
            (result["version"], result["source_sha256"], result["state"]),
        )
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Runtime foreign key mismatch")
