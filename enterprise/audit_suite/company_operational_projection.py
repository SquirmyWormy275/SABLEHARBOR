"""Initialize an audit-independent company library from pinned private authoring history.

The explicit registry is an operator-only migration recipe. It is not a learner
source, evidence response, grading key, or source-completeness assertion. Every
unmodified business field survives byte-equivalent JSON projection; declared
authoring fields and labels have separate private custody. Original stores never
receive writes, grants, collections, or audit links.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_COMPANY_OPERATIONAL_PROJECTION_V1"
SPEC = "enterprise/audit_suite/company_operational_projection_registry_v1.json"
SPEC_SHA = "c6d488e877d3ca6988d5e37278ab6c5c603fd7ba501ce9126f9bcef9d804fe4a"
MODULE = "enterprise/audit_suite/company_operational_projection.py"
COMPANY = "SABLE-HARBOR-REFERENCE"
FILES = {"company.sqlite3", "MANIFEST.json", "RECEIPT.json", "TRANSFORMATION.json"}
BRANCHES = ("HARBOR-OPERATIONS-A", "HARBOR-OPERATIONS-B")
AUTHOR_KEYS = {
    "scenario",
    "false_clean",
    "false_pass",
    "expected_finding",
    "expected_findings",
    "rubric",
    "instructor_key",
    "answer_key",
    "hidden_key",
    "historical_october_false_pass_retained",
}
ANSWER_VALUES = (
    "FALSE_CLEAN",
    "FALSE_PASS",
    "INCORRECTLY_ACCEPTED",
    "OMITS_TWO_ADVERSE_DECISIONS",
)
TRIGGERS = {
    "no_version_update": "CREATE TRIGGER no_version_update BEFORE UPDATE ON versions "
    "BEGIN SELECT RAISE(ABORT,'Immutable source'); END",
    "no_version_delete": "CREATE TRIGGER no_version_delete BEFORE DELETE ON versions "
    "BEGIN SELECT RAISE(ABORT,'Immutable source'); END",
    "no_collection_update": "CREATE TRIGGER no_collection_update BEFORE UPDATE ON collections "
    "BEGIN SELECT RAISE(ABORT,'Immutable collection'); END",
    "no_collection_delete": "CREATE TRIGGER no_collection_delete BEFORE DELETE ON collections "
    "BEGIN SELECT RAISE(ABORT,'Immutable collection'); END",
}


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _private(path, directory=False):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Projection private aliases forbidden")
    info = path.stat()
    if directory:
        valid = stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
    else:
        valid = (
            stat.S_ISREG(info.st_mode)
            and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_nlink == 1
        )
    if not valid:
        raise CompanyStoreError("Projection private permissions/link custody differ")
    return path


def _frozen(paths):
    result = {}
    for name, path in paths.items():
        _private(path)
        if path.suffix == ".sqlite3" and any(
            Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise CompanyStoreError("Projection immutable input has sidecar")
        s = path.stat()
        result[name] = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, _digest(path))
    return result


def _read_db(path):
    return sqlite3.connect(f"file:{Path(path)}?mode=ro&immutable=1", uri=True)


def _db_schema(db):
    return [
        [row[0], row[1], " ".join(row[2].split()) if row[2] else None]
        for row in db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name")
    ]


def _registry(repository):
    path = Path(repository) / SPEC
    if _digest(path) != SPEC_SHA:
        raise CompanyStoreError("Projection explicit registry pin differs")
    value = json.loads(path.read_text())
    if value.get("schema") != SCHEMA or value.get("company") != COMPANY:
        raise CompanyStoreError("Projection registry identity differs")
    return value


def _inputs(registry, private_repository):
    paths = {
        entry["path"]: Path(private_repository) / entry["path"] for entry in registry["inputs"]
    }
    frozen = _frozen(paths)
    for entry in registry["inputs"]:
        if frozen[entry["path"]][-1] != entry["sha256"]:
            raise CompanyStoreError("Projection raw source pin differs")
    rows = {}
    systems = {}
    for entry in registry["inputs"]:
        if entry.get("role") not in {"MIGRATED_NATIVE_STORE", "RESTRICTED_UPSTREAM_STORE"}:
            continue
        with closing(_read_db(paths[entry["path"]])) as db:
            db.row_factory = sqlite3.Row
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise CompanyStoreError("Projection raw database integrity differs")
            for r in db.execute("SELECT * FROM systems"):
                systems[(entry["cohort"], r["company"], r["branch"], r["system"])] = r["owner"]
            for raw in db.execute("SELECT * FROM versions"):
                r = dict(raw)
                if sha(r["content"]) != r["sha256"]:
                    raise CompanyStoreError("Projection raw content custody differs")
                r["body"] = json.loads(r["content"])
                r["cohort"] = entry["cohort"]
                r["source_path"] = entry["path"]
                r["role"] = entry["role"]
                if r["sha256"] in rows:
                    raise CompanyStoreError("Projection ambiguous raw native hash")
                rows[r["sha256"]] = r
    expected = {r["input_sha256"] for r in registry["records"]}
    actual = {h for h, r in rows.items() if r["role"] == "MIGRATED_NATIVE_STORE"}
    if expected != actual or len(expected) != len(registry["records"]):
        raise CompanyStoreError("Projection exact raw record population differs")
    return paths, frozen, rows, systems


def _leaks(value, path=""):
    """Declared diagnostic detectors. They never redact or award clearance."""
    findings = []
    if isinstance(value, dict):
        for key, item in value.items():
            p = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key in AUTHOR_KEYS:
                findings.append({"path": p, "reason": "AUTHORING_KEY"})
            findings.extend(_leaks(item, p))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            findings.extend(_leaks(item, path + "/" + str(i)))
    elif isinstance(value, str):
        if any(t in value.upper() for t in ANSWER_VALUES) or re.search(
            r"(?:^|[-_])(?:CLEAN|MESSY)(?:$|[-_])", value
        ):
            findings.append({"path": path, "reason": "AUTHORING_VALUE"})
    return findings


def inventory(destination, *, repository, private_repository):
    """Read all pinned V18 native bytes, including non-JSON, without granting access.

    A detector hit is a review lead, not a claim every phrase is illegitimate.
    No-hit components also remain unreviewed until their explicit projection is
    reviewed. Physical count reconciliation never rewrites historical reports.
    """
    registry = _registry(repository)
    roster_pin = next(e for e in registry["inputs"] if e["role"] == "PRIVATE_ACCEPTED_ROSTER")
    roster_path = Path(private_repository) / roster_pin["path"]
    _private(roster_path)
    if _digest(roster_path) != roster_pin["sha256"]:
        raise CompanyStoreError("Projection inventory roster differs")
    roster = json.loads(roster_path.read_text())
    base = Path(private_repository) / "enterprise/generated/audit-suite"
    components, observed_paths = [], {roster_pin["path"]: roster_path}
    for source in roster["sources"]:
        pins = source["database_sha256"]
        expected = set(pins.values()) if isinstance(pins, dict) else {pins}
        matched = set()
        for path in sorted((base / source["run"]).rglob("*.sqlite3")):
            _private(path)
            digest = _digest(path)
            if digest not in expected:
                continue
            if digest in matched:
                raise CompanyStoreError("Projection inventory ambiguous physical component")
            matched.add(digest)
            relative = str(path.relative_to(private_repository))
            observed_paths[relative] = path
            before = _frozen({relative: path})
            flags, records = [], []
            with closing(_read_db(path)) as db:
                db.row_factory = sqlite3.Row
                for row in db.execute(
                    "SELECT * FROM versions ORDER BY company,branch,system,record,version"
                ):
                    if sha(row["content"]) != row["sha256"]:
                        raise CompanyStoreError("Projection inventory native body hash differs")
                    record = {
                        k: row[k]
                        for k in ("company", "branch", "system", "record", "version", "sha256")
                    }
                    for field in ("content", "provenance"):
                        try:
                            value = json.loads(row[field])
                            kind = "JSON"
                        except (ValueError, TypeError):
                            value = bytes(row[field]).decode("utf-8", errors="strict")
                            kind = "UTF8_TEXT"
                        hits = _leaks(value)
                        if hits:
                            flags.append({"identity": record, "field": field, "findings": hits})
                        if field == "content":
                            record["format"] = kind
                    records.append(record)
            if _frozen({relative: path}) != before:
                raise CompanyStoreError("Projection inventory source custody changed")
            components.append(
                {
                    "cohort": source["source"],
                    "path": relative,
                    "sha256": digest,
                    "native_versions": len(records),
                    "records": records,
                    "findings": flags,
                    "gate": "EXPLICIT_PROJECTION_REVIEW_REQUIRED_NO_BLANKET_CLEARANCE",
                }
            )
        if matched != expected:
            raise CompanyStoreError("Projection inventory missing pinned native component")
    value = {
        "schema": "SH_PRIVATE_COMPANY_SOURCE_ANNOTATION_INVENTORY_V1",
        "roster_sha256": roster_pin["sha256"],
        "cohort_count": len(roster["sources"]),
        "physical_component_count": len(components),
        "historical_reported_source_component_count": roster["source_component_count"],
        "physical_count_reconciled_without_rewriting_history": True,
        "native_versions": sum(c["native_versions"] for c in components),
        "declared_detectors": {
            "keys": sorted(AUTHOR_KEYS),
            "values": list(ANSWER_VALUES),
            "routing_labels": "CLEAN_OR_MESSY_ENUM_OR_DELIMITED_TOKEN",
        },
        "limitations": [
            "Hits require business-context review; later company findings may be legitimate.",
            "No-hit components are not cleared by this inventory.",
            "Private authoring custody only; never attach this inventory to a learner source.",
        ],
        "components": components,
        "source_complete": False,
        "audit_task_credit": False,
    }
    destination = Path(destination).absolute()
    _private(destination.parent, True)
    _write(destination, value)
    return value


def _project(registry, rows):
    """Exact pointer operations only; no blanket redaction or outcome predicates."""
    plans = {r["input_sha256"]: r for r in registry["records"]}
    projected, active, custody = {}, set(), []

    def build(raw_hash):
        if raw_hash in projected:
            return projected[raw_hash]
        if raw_hash in active:
            raise CompanyStoreError("Projection cyclic business dependency")
        active.add(raw_hash)
        plan, raw = plans[raw_hash], rows[raw_hash]
        if [raw[k] for k in ("cohort", "company", "branch", "system", "record", "version")] != plan[
            "identity"
        ]:
            raise CompanyStoreError("Projection raw identity differs")
        operations, used = plan["operations"], set()

        def visit(value, pointer=""):
            op = operations.get(pointer)
            if op:
                used.add(pointer)
                if op["kind"] == "DROP_AUTHORING":
                    return None
                if op["kind"] == "ENUM":
                    if value != op["from"]:
                        raise CompanyStoreError("Projection declared enum differs")
                    return op["to"]
                if op["kind"] == "NATIVE_REFERENCE":
                    if not isinstance(value, dict):
                        raise CompanyStoreError("Projection reference shape differs")
                    target = rows.get(value["sha256"])
                    if target is None or any(
                        key in value and value[key] != target[key]
                        for key in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "event_at",
                            "available_at",
                        )
                    ):
                        raise CompanyStoreError("Projection reference custody differs")
                    if value["sha256"] in plans:
                        out = build(value["sha256"])
                        if out["branch"] != plan["branch"]:
                            raise CompanyStoreError("Projection cross-branch reference forbidden")
                        result = {
                            key: out[key]
                            for key in (
                                "company",
                                "branch",
                                "system",
                                "record",
                                "version",
                                "event_at",
                                "available_at",
                                "sha256",
                            )
                        }
                    else:
                        result = {
                            "company": COMPANY,
                            "branch": plan["branch"],
                            "system": target["system"],
                            "record": target["record"],
                            "version": target["version"],
                            "event_at": target["event_at"],
                            "available_at": target["available_at"],
                            "custody_id": "UPSTREAM-" + sha(encoded(value))[:24],
                            "status": "RESTRICTED_UPSTREAM_NOT_IMPORTED",
                        }
                    custody.append(
                        {
                            "input_sha256": raw_hash,
                            "path": pointer,
                            "raw_reference": value,
                            "projected_reference": result,
                        }
                    )
                    return result
                raise CompanyStoreError("Projection undeclared operation kind")
            if isinstance(value, dict):
                result = {}
                for key, item in value.items():
                    p = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                    if operations.get(p, {}).get("kind") == "DROP_AUTHORING":
                        used.add(p)
                        continue
                    result[key] = visit(item, p)
                return result
            if isinstance(value, list):
                return [visit(item, pointer + "/" + str(i)) for i, item in enumerate(value)]
            return value

        body = visit(raw["body"])
        if used != set(operations):
            raise CompanyStoreError("Projection declared path missing")
        body["schema"] = "SH_COMPANY_OPERATIONAL_RECORD_V1"
        if _leaks(body):
            raise CompanyStoreError("Projection learner body contains undeclared answer annotation")
        result = {
            "cohort": raw["cohort"],
            "company": COMPANY,
            "branch": plan["branch"],
            "system": plan["system"],
            "record": plan["record"],
            "version": raw["version"],
            "event_at": raw["event_at"],
            "available_at": raw["available_at"],
            "input_sha256": raw_hash,
            "sha256": sha(encoded(body)),
            "body": body,
        }
        projected[raw_hash] = result
        active.remove(raw_hash)
        return result

    # Reference hashes depend on business bytes, never migration/import wall clocks.
    for plan in registry["records"]:
        build(plan["input_sha256"])
    ordered = sorted(
        projected.values(),
        key=lambda r: (
            r["branch"],
            r["event_at"] or "",
            r["cohort"],
            r["system"],
            r["record"],
            r["version"],
        ),
    )
    custody.sort(key=lambda r: (r["input_sha256"], r["path"]))
    transformations = [
        {
            "identity": plans[r["input_sha256"]]["identity"],
            "input_sha256": r["input_sha256"],
            "raw_provenance_sha256": sha(rows[r["input_sha256"]]["provenance"].encode()),
            "projected_identity": [
                r[k] for k in ("company", "branch", "system", "record", "version")
            ],
            "projected_content_sha256": r["sha256"],
            "operations": plans[r["input_sha256"]]["operations"],
        }
        for r in ordered
    ]
    transformation = {
        "schema": SCHEMA,
        "records": transformations,
        "reference_custody": custody,
        "private_authoring_history_preserved": True,
        "audit_task_credit": False,
        "source_complete": False,
    }
    if registry.get("expected_transformation_sha256") != sha(encoded(transformation)):
        raise CompanyStoreError("Projection expected transformation hash differs")
    return ordered, transformation


def _provenance(raw_hash, initialized_at):
    return {
        "source_reference": "company-library://harbor-operations/initialization-v1",
        "qualification": "FICTIONAL_COMPANY_HISTORY_NOT_REAL_DEPLOYMENT_OR_PHI",
        "migration_schema": SCHEMA,
        "initialized_at": initialized_at,
        "raw_content_sha256": raw_hash,
        "name": "native-" + raw_hash[:24] + ".json",
        "population": "DECLARED_IMPORTED_RECORDS_ONLY_NOT_FULL_ESTATE_OR_AUDIT_COMPLETENESS",
    }


def _write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination, *, repository, private_repository):
    """Create persistent company source first; no engagement, access, or evidence."""
    destination = Path(destination).absolute()
    _private(destination.parent, True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Projection fresh destination required")
    registry = _registry(repository)
    paths, frozen, rows, systems = _inputs(registry, private_repository)
    ordered, transformation = _project(registry, rows)
    initialized = datetime.now(UTC).isoformat(timespec="microseconds")
    if initialized < _time(registry["migration_not_before"]):
        raise CompanyStoreError("Projection initialization precedes migration authorization")
    with tempfile.TemporaryDirectory(
        prefix=".operational-projection-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = []
        for record in ordered:
            plan = next(
                p for p in registry["records"] if p["input_sha256"] == record["input_sha256"]
            )
            owner = systems[tuple(plan["identity"][:4])]
            store.register_system(COMPANY, record["branch"], record["system"], owner)
            ref = store.append_version(
                COMPANY,
                record["branch"],
                record["system"],
                record["record"],
                expected_version=record["version"] - 1,
                command_id="MIG-" + record["input_sha256"][:60],
                event_at=record["event_at"],
                available_at=record["available_at"],
                content=encoded(record["body"]),
                provenance=_provenance(record["input_sha256"], initialized),
                origin="MIGRATED_SYNTHETIC_HISTORY",
            )
            refs.append(ref)
        completed = datetime.now(UTC).isoformat(timespec="microseconds")
        receipt = {
            "schema": SCHEMA,
            "status": "PERSISTENT_FICTIONAL_COMPANY_LIBRARY_INITIALIZED",
            "company": COMPANY,
            "initialized_at": initialized,
            "completed_at": completed,
            "records": refs,
            "native_versions": len(refs),
            "branches": list(BRANCHES),
            "source_complete": False,
            "audit_task_credit": False,
            "engagement_created": False,
            "access_granted": False,
        }
        _write(stage / "TRANSFORMATION.json", transformation)
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA,
            "projection_registry_sha256": SPEC_SHA,
            "module_sha256": _digest(Path(repository) / MODULE),
            "input_pins": registry["inputs"],
            "expected_transformation_sha256": sha(encoded(transformation)),
            "files": {
                name: _digest(stage / name)
                for name in ("company.sqlite3", "TRANSFORMATION.json", "RECEIPT.json")
            },
        }
        _write(stage / "MANIFEST.json", manifest)
        if _frozen(paths) != frozen:
            raise CompanyStoreError("Projection raw source changed during initialization")
        verify(stage, repository=repository, private_repository=private_repository)
        publish(stage, destination)
    return receipt


def verify(root, *, repository, private_repository):
    """Reperform projection and custody against raw pins; no database writes."""
    root = _private(root, True)
    if {p.name for p in root.iterdir()} != FILES:
        raise CompanyStoreError("Projection exact private file set differs")
    target_paths = {name: root / name for name in FILES}
    target_frozen = _frozen(target_paths)
    registry = _registry(repository)
    paths, frozen, rows, systems = _inputs(registry, private_repository)
    ordered, transformation = _project(registry, rows)
    manifest = json.loads((root / "MANIFEST.json").read_text())
    expected_manifest = {
        "schema": SCHEMA,
        "projection_registry_sha256": SPEC_SHA,
        "module_sha256": _digest(Path(repository) / MODULE),
        "input_pins": registry["inputs"],
        "expected_transformation_sha256": sha(encoded(transformation)),
        "files": {
            name: _digest(root / name)
            for name in ("company.sqlite3", "TRANSFORMATION.json", "RECEIPT.json")
        },
    }
    if (
        manifest != expected_manifest
        or json.loads((root / "TRANSFORMATION.json").read_text()) != transformation
    ):
        raise CompanyStoreError("Projection exact transformation/manifest differs")
    receipt = json.loads((root / "RECEIPT.json").read_text())
    expected_refs = []
    expected_systems = set()
    with closing(_read_db(root / "company.sqlite3")) as db:
        db.row_factory = sqlite3.Row
        if (
            db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise CompanyStoreError("Projection database integrity differs")
        if _db_schema(db) != registry["database_schema"]:
            raise CompanyStoreError("Projection exact database schema differs")
        triggers = {
            r["name"]: " ".join(r["sql"].split())
            for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
        }
        if triggers != TRIGGERS:
            raise CompanyStoreError("Projection immutable triggers differ")
        for table in ("grants", "access_events", "collections"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("Projection unauthorized access or audit collection")
        actual = {r["command_id"]: dict(r) for r in db.execute("SELECT * FROM versions")}
        if len(actual) != len(ordered):
            raise CompanyStoreError("Projection native population differs")
        for record in ordered:
            raw_hash = record["input_sha256"]
            command = "MIG-" + raw_hash[:60]
            r = actual.pop(command, None)
            if r is None:
                raise CompanyStoreError("Projection native command identity differs")
            provenance = _provenance(raw_hash, receipt["initialized_at"])
            expected = {
                key: record[key]
                for key in (
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "event_at",
                    "available_at",
                    "sha256",
                )
            }
            expected.update(
                content=encoded(record["body"]),
                provenance=encoded(provenance).decode(),
                origin="MIGRATED_SYNTHETIC_HISTORY",
                command_id=command,
                imported_at=r["imported_at"],
            )
            expected["input_digest"] = sha(
                encoded(
                    [
                        [record[k] for k in ("company", "branch", "system", "record")],
                        record["version"] - 1,
                        record["event_at"],
                        record["available_at"],
                        "MIGRATED_SYNTHETIC_HISTORY",
                        provenance,
                        record["sha256"],
                    ]
                )
            )
            if r != expected or not (
                _time(receipt["initialized_at"])
                <= _time(r["imported_at"])
                <= _time(receipt["completed_at"])
            ):
                raise CompanyStoreError("Projection native body/provenance/clock custody differs")
            expected_refs.append(CompanyStore._metadata(r))
            plan = next(p for p in registry["records"] if p["input_sha256"] == raw_hash)
            expected_systems.add(
                (COMPANY, record["branch"], record["system"], systems[tuple(plan["identity"][:4])])
            )
        if {
            tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("Projection exact system owner population differs")
    expected_receipt = {
        "schema": SCHEMA,
        "status": "PERSISTENT_FICTIONAL_COMPANY_LIBRARY_INITIALIZED",
        "company": COMPANY,
        "initialized_at": receipt["initialized_at"],
        "completed_at": receipt["completed_at"],
        "records": expected_refs,
        "native_versions": len(expected_refs),
        "branches": list(BRANCHES),
        "source_complete": False,
        "audit_task_credit": False,
        "engagement_created": False,
        "access_granted": False,
    }
    if receipt != expected_receipt or not (
        _time(registry["migration_not_before"])
        <= _time(receipt["initialized_at"])
        <= _time(receipt["completed_at"])
        <= datetime.now(UTC).isoformat(timespec="microseconds")
    ):
        raise CompanyStoreError("Projection exact receipt/boundary/clock differs")
    if _frozen(paths) != frozen or _frozen(target_paths) != target_frozen:
        raise CompanyStoreError("Projection verifier mutated custody")
    return receipt
