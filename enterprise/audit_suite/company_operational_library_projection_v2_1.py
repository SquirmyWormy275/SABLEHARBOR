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

SCHEMA = "SH_COMPANY_OPERATIONAL_PROJECTION_V2_1"
SPEC = "enterprise/audit_suite/company_operational_library_projection_registry_v2_1.json"
SPEC_SHA = "46dfd5b3e24d751c8403af80e8c40ebe8900207cf37e44b3b57acf9cd8261960"
MODULE = "enterprise/audit_suite/company_operational_library_projection_v2_1.py"
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
    "selected_task_id",
    "unsupported_authored_task_ids",
    "learner_engagement_grant_created",
    "source_pins",
}
ANSWER_VALUES = (
    "FALSE_CLEAN",
    "FALSE_PASS",
    "INCORRECTLY_ACCEPTED",
    "OMITS_TWO_ADVERSE_DECISIONS",
)
RESTRICTED_STATUSES = {
    "RESTRICTED_UNREGISTERED_DEPENDENCY",
    "RESTRICTED_AMBIGUOUS_DEPENDENCY",
    "RESTRICTED_CROSS_BRANCH_DEPENDENCY",
}
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


def _input_id(path, row):
    return sha(
        encoded(
            [
                path,
                *[row[k] for k in ("company", "branch", "system", "record", "version", "sha256")],
            ]
        )
    )


def _pointer(value, pointer):
    if pointer == "":
        return value
    for segment in pointer.lstrip("/").split("/"):
        key = segment.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
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
                systems[(entry["component"], r["company"], r["branch"], r["system"])] = r["owner"]
            for raw in db.execute("SELECT * FROM versions"):
                r = dict(raw)
                if sha(r["content"]) != r["sha256"]:
                    raise CompanyStoreError("Projection raw content custody differs")
                try:
                    r["body"] = json.loads(r["content"])
                    r["format"] = "JSON"
                except ValueError:
                    r["body"] = r["content"].decode("utf-8", errors="strict")
                    r["format"] = "UTF8_TEXT"
                r["cohort"] = entry["cohort"]
                r["component"] = entry["component"]
                r["source_path"] = entry["path"]
                r["role"] = entry["role"]
                input_id = _input_id(entry["path"], r)
                if input_id in rows:
                    raise CompanyStoreError("Projection ambiguous raw native identity")
                rows[input_id] = r
    expected = {r["input_id"] for r in registry["records"]}
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
            if key.casefold() in AUTHOR_KEYS:
                findings.append({"path": p, "reason": "AUTHORING_KEY"})
            findings.extend(_leaks(item, p))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            findings.extend(_leaks(item, path + "/" + str(i)))
    elif isinstance(value, str):
        if (
            value.startswith("TASK-SH-")
            or any(t in value.upper() for t in ANSWER_VALUES)
            or re.search(r"(?:^|[-_])(?:CLEAN|MESSY)(?:$|[-_])", value, re.IGNORECASE)
        ):
            findings.append({"path": path, "reason": "AUTHORING_VALUE"})
    return findings


def _project(registry, rows):
    """Exact pointer operations only; no blanket redaction or outcome predicates."""
    plans = {r["input_id"]: r for r in registry["records"]}
    projected, active, custody, digest_custody = {}, set(), [], []

    def build(raw_hash):
        if raw_hash in projected:
            return projected[raw_hash]
        if raw_hash in active:
            raise CompanyStoreError("Projection cyclic business dependency")
        active.add(raw_hash)
        plan, raw = plans[raw_hash], rows[raw_hash]
        if (
            [raw[k] for k in ("component", "company", "branch", "system", "record", "version")]
            != plan["identity"]
            or raw["sha256"] != plan["input_sha256"]
            or raw["format"] != plan["format"]
        ):
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
                if op["kind"] == "HASH_REFERENCE":
                    target = rows.get(op["target_input_id"])
                    if (
                        target is None
                        or value != target["sha256"]
                        or [
                            target[k]
                            for k in (
                                "component",
                                "company",
                                "branch",
                                "system",
                                "record",
                                "version",
                            )
                        ]
                        != op["target_identity"]
                    ):
                        raise CompanyStoreError("Projection scalar digest identity/basis differs")
                    out = build(op["target_input_id"])
                    if out["branch"] != plan["branch"]:
                        raise CompanyStoreError("Projection scalar digest crosses branch")
                    result = out["sha256"]
                    digest_custody.append(
                        {
                            "input_id": raw_hash,
                            "path": pointer,
                            "kind": "HASH_REFERENCE",
                            "raw_digest": value,
                            "target_identity": op["target_identity"],
                            "target_input_id": op["target_input_id"],
                            "projected_digest": result,
                            "basis": op["basis"],
                        }
                    )
                    return result
                if op["kind"] == "DERIVED_DIGEST":
                    if op["algorithm"] != "CANONICAL_JSON_SHA256":
                        raise CompanyStoreError("Projection derived digest algorithm differs")
                    original = _pointer(raw["body"], op["basis_pointer"])
                    if value != op["from"] or sha(encoded(original)) != value:
                        raise CompanyStoreError("Projection original vector digest basis differs")
                    if pointer == op["basis_pointer"]:
                        raise CompanyStoreError("Projection self-referential vector digest")
                    result = sha(encoded(visit(original, op["basis_pointer"])))
                    digest_custody.append(
                        {
                            "input_id": raw_hash,
                            "path": pointer,
                            "kind": "DERIVED_DIGEST",
                            "raw_digest": value,
                            "projected_digest": result,
                            "basis_pointer": op["basis_pointer"],
                            "algorithm": op["algorithm"],
                        }
                    )
                    return result
                if op["kind"] == "NATIVE_REFERENCE":
                    if not isinstance(value, dict):
                        raise CompanyStoreError("Projection reference shape differs")
                    if sha(encoded(value)) != op["raw_reference_sha256"]:
                        raise CompanyStoreError("Projection exact reference bytes differ")
                    target = rows.get(op["target_input_id"])
                    if target is None and op.get("restricted_status"):
                        if op["restricted_status"] not in RESTRICTED_STATUSES:
                            raise CompanyStoreError(
                                "Projection restricted dependency status differs"
                            )
                        result = {
                            "company": COMPANY,
                            "branch": plan["branch"],
                            "system": value["system"],
                            "record": op["projected_record"],
                            "version": value["version"],
                            "event_at": value.get("event_at"),
                            "available_at": value.get("available_at"),
                            "custody_id": "UPSTREAM-" + sha(encoded(value))[:24],
                            "status": op["restricted_status"],
                        }
                        if op["restricted_status"] == "RESTRICTED_CROSS_BRANCH_DEPENDENCY":
                            # No identity, hash, availability, or result from another
                            # branch is published through a restricted pointer.
                            result = {k: result[k] for k in ("custody_id", "status")}
                        custody.append(
                            {
                                "input_id": raw_hash,
                                "path": pointer,
                                "raw_reference": value,
                                "projected_reference": result,
                            }
                        )
                        return result
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
                            "sha256",
                        )
                    ):
                        raise CompanyStoreError("Projection reference custody differs")
                    if op["target_input_id"] in plans:
                        out = build(op["target_input_id"])
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
                            "input_id": raw_hash,
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
                    output_key = plan["rename_keys"].get(p, key)
                    if output_key in result:
                        raise CompanyStoreError("Projection renamed field collides")
                    result[output_key] = visit(item, p)
                return result
            if isinstance(value, list):
                return [visit(item, pointer + "/" + str(i)) for i, item in enumerate(value)]
            return value

        body = visit(raw["body"])
        for key, declaration in plan.get("added_business_fields", {}).items():
            if not isinstance(body, dict) or key in raw["body"] or key in body:
                raise CompanyStoreError("Projection operational limit field already exists")
            if declaration["basis"] != "EXACT_PINNED_NATIVE_WRITER_DATA_ONLY_CONTRACT":
                raise CompanyStoreError("Projection operational limit basis differs")
            body[key] = declaration["value"]
        if used != set(operations):
            raise CompanyStoreError("Projection declared path missing")
        if plan["format"] == "JSON":
            # Do not add a schema/envelope to business payloads, or recanonicalize
            # unchanged copy/data objects. Their original bytes are digest inputs.
            data = raw["content"] if body == raw["body"] else encoded(body)
        else:
            if operations or plan["rename_keys"]:
                raise CompanyStoreError("Projection plain text must preserve raw bytes")
            data = raw["content"]
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
            "input_id": raw_hash,
            "input_sha256": raw["sha256"],
            "format": plan["format"],
            "sha256": sha(data),
            "content": data,
            "body": body,
        }
        projected[raw_hash] = result
        active.remove(raw_hash)
        return result

    # Reference hashes depend on business bytes, never migration/import wall clocks.
    for plan in registry["records"]:
        build(plan["input_id"])
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
    custody = list({(r["input_id"], r["path"]): r for r in custody}.values())
    custody.sort(key=lambda r: (r["input_id"], r["path"]))
    # A basis subtree can be visited both directly and while deriving its digest.
    # Preserve a single exact custody entry for each declared owner/path operation.
    digest_custody = list({(r["input_id"], r["path"]): r for r in digest_custody}.values())
    digest_custody.sort(key=lambda r: (r["input_id"], r["path"]))
    for check in registry.get("unchanged_byte_digest_checks", []):
        owner = rows[check["input_id"]]
        if _pointer(owner["body"], check["path"]) != check["raw_digest"]:
            raise CompanyStoreError("Projection preserved byte digest owner differs")
        identities = []
        for input_id in check["raw_target_input_ids"]:
            target = rows[input_id]
            identities.append(
                [
                    target[k]
                    for k in ("component", "company", "branch", "system", "record", "version")
                ]
            )
            if (
                target["sha256"] != check["raw_digest"]
                or projected[input_id]["sha256"] != check["raw_digest"]
            ):
                raise CompanyStoreError("Projection executed file/copy bytes changed")
        if identities != check["raw_target_identities"]:
            raise CompanyStoreError("Projection preserved byte digest identity differs")
    transformations = [
        {
            "identity": plans[r["input_id"]]["identity"],
            "input_id": r["input_id"],
            "input_sha256": r["input_sha256"],
            "raw_provenance_sha256": sha(rows[r["input_id"]]["provenance"].encode()),
            "projected_identity": [
                r[k] for k in ("company", "branch", "system", "record", "version")
            ],
            "projected_content_sha256": r["sha256"],
            "operations": plans[r["input_id"]]["operations"],
            "rename_keys": plans[r["input_id"]]["rename_keys"],
            "format": r["format"],
            "added_business_fields": plans[r["input_id"]].get("added_business_fields", {}),
        }
        for r in ordered
    ]
    transformation = {
        "schema": SCHEMA,
        "records": transformations,
        "reference_custody": custody,
        "digest_custody": digest_custody,
        "unresolved_digest_limits": registry.get("unresolved_digest_limits", []),
        "unchanged_byte_digest_checks": registry.get("unchanged_byte_digest_checks", []),
        "private_authoring_history_preserved": True,
        "audit_task_credit": False,
        "source_complete": False,
    }
    if registry.get("expected_transformation_sha256") != sha(encoded(transformation)):
        raise CompanyStoreError("Projection expected transformation hash differs")
    return ordered, transformation


def _provenance(record, initialized_at):
    extension = ".json" if record["format"] == "JSON" else ".txt"
    return {
        "source_reference": "company-library://harbor-operations/initialization-v2-1",
        "qualification": "FICTIONAL_COMPANY_HISTORY_NOT_REAL_DEPLOYMENT_OR_PHI",
        "migration_schema": SCHEMA,
        "initialized_at": initialized_at,
        "raw_content_sha256": record["input_sha256"],
        "name": "native-" + record["input_id"][:24] + extension,
        "content_type": "application/json"
        if record["format"] == "JSON"
        else "text/plain; charset=utf-8",
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
    if any(_time(r["imported_at"]) > initialized for r in rows.values()):
        raise CompanyStoreError("Projection initialization precedes raw source custody")
    with tempfile.TemporaryDirectory(
        prefix=".operational-projection-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = []
        for record in ordered:
            plan = next(p for p in registry["records"] if p["input_id"] == record["input_id"])
            owner = systems[tuple(plan["identity"][:4])]
            store.register_system(COMPANY, record["branch"], record["system"], owner)
            ref = store.append_version(
                COMPANY,
                record["branch"],
                record["system"],
                record["record"],
                expected_version=record["version"] - 1,
                command_id="MIG-" + record["input_id"][:60],
                event_at=record["event_at"],
                available_at=record["available_at"],
                content=record["content"],
                provenance=_provenance(record, initialized),
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
            raw_hash = record["input_id"]
            command = "MIG-" + raw_hash[:60]
            r = actual.pop(command, None)
            if r is None:
                raise CompanyStoreError("Projection native command identity differs")
            provenance = _provenance(record, receipt["initialized_at"])
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
                content=record["content"],
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
            plan = next(p for p in registry["records"] if p["input_id"] == raw_hash)
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
