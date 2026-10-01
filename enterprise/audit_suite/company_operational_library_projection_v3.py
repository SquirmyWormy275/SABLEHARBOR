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

SCHEMA = "SH_COMPANY_OPERATIONAL_PROJECTION_V3"
SPEC = "enterprise/audit_suite/company_operational_library_projection_registry_v3.json"
SPEC_SHA = "6fa8e6ba1e428762e1554a5e2779402889dbe48983b3362412536f7744995d66"
MODULE = "enterprise/audit_suite/company_operational_library_projection_v3.py"
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
    "RESTRICTED_ARCHIVE_MOTIVATION_ONLY",
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


def _frozen(paths, public_code_paths=frozenset()):
    result = {}
    for name, path in paths.items():
        if name in public_code_paths:
            ordinary = path.absolute()
            info = ordinary.stat()
            if (
                ordinary.suffix != ".py"
                or any(p.is_symlink() for p in (ordinary, *ordinary.parents))
                or not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) not in {0o644, 0o444}
                or info.st_nlink != 1
            ):
                raise CompanyStoreError("Projection ordinary pinned writer contract differs")
        else:
            _private(path)
        if path.suffix == ".sqlite3" and any(
            Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise CompanyStoreError("Projection immutable input has sidecar")
        s = path.stat()
        result[name] = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, _digest(path))
    return result


def _input_frozen(paths, registry):
    public_code_paths = set()
    for entry in registry["inputs"]:
        if entry.get("role") != "PUBLIC_PINNED_NATIVE_WRITER_CONTRACT":
            continue
        path = Path(entry["path"])
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.parts[:2] != ("enterprise", "audit_suite")
        ):
            raise CompanyStoreError("Projection writer contract escapes declared code namespace")
        public_code_paths.add(entry["path"])
    return _frozen(paths, public_code_paths)


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


def _plans(registry, rows):
    """Separate raw custody from explicitly declared projected counterparts.

    An original input has exactly one output unless a pinned operator contract
    names every counterpart identity. This creates no source authority, aliases
    or broad access to another branch. Counterparts retain the exact approved
    source bytes and clocks, and their distinct native version sequence is an
    explicit part of the private migration contract.
    """
    plans = {p["projection_id"]: p for p in registry["records"]}
    if len(plans) != len(registry["records"]):
        raise CompanyStoreError("Projection duplicate projected custody identity")
    groups = {}
    identities = set()
    for projection_id, plan in plans.items():
        raw = rows.get(plan["input_id"])
        if raw is None:
            raise CompanyStoreError("Projection original input identity missing")
        identity = tuple(plan[k] for k in ("branch", "system", "record", "version"))
        if identity in identities or plan["branch"] not in BRANCHES:
            raise CompanyStoreError("Projection output identity collides or escapes scope")
        identities.add(identity)
        groups.setdefault(plan["input_id"], []).append(plan)
        if not isinstance(projection_id, str) or not re.fullmatch("[0-9a-f]{64}", projection_id):
            raise CompanyStoreError("Projection exact projected custody key required")
    contracts = {c["input_id"]: c for c in registry.get("common_upstream_admissions", [])}
    if len(contracts) != len(registry.get("common_upstream_admissions", [])):
        raise CompanyStoreError("Projection duplicate common upstream contract")
    duplicated = {input_id for input_id, values in groups.items() if len(values) != 1}
    if duplicated != set(contracts):
        raise CompanyStoreError("Projection undeclared or omitted common counterpart")
    for input_id, values in groups.items():
        raw = rows[input_id]
        if input_id not in contracts:
            if values[0]["projection_id"] != input_id or values[0]["version"] != raw["version"]:
                raise CompanyStoreError("Projection undeclared original identity remapping")
            continue
        contract = contracts[input_id]
        expected_raw_identity = [
            raw[k] for k in ("component", "company", "branch", "system", "record", "version")
        ]
        actual = sorted(
            [
                p["projection_id"],
                COMPANY,
                *[p[k] for k in ("branch", "system", "record", "version")],
            ]
            for p in values
        )
        if (
            set(contract)
            != {
                "input_id",
                "raw_identity",
                "raw_content_sha256",
                "counterpart_identities",
                "basis",
                "contract_pins",
            }
            or contract["raw_identity"] != expected_raw_identity
            or contract["raw_content_sha256"] != raw["sha256"]
            or actual != sorted(contract["counterpart_identities"])
            or len(values) != 2
            or {p["branch"] for p in values} != set(BRANCHES)
            or contract["basis"] != "PINNED_SHARED_UPSTREAM_BUSINESS_SOURCE_CONTRACT"
            or not contract["contract_pins"]
        ):
            raise CompanyStoreError("Projection exact common upstream custody contract differs")
        input_pins = {e["path"]: e["sha256"] for e in registry["inputs"]}
        if any(
            input_pins.get(path) != digest for path, digest in contract["contract_pins"].items()
        ):
            raise CompanyStoreError("Projection common upstream writer/runtime contract unpinned")
        for plan in values:
            if (
                any(not path.startswith("/@operational_metadata/") for path in plan["operations"])
                or plan["rename_keys"]
                or plan.get("added_business_fields")
            ):
                raise CompanyStoreError("Projection common original business bytes must survive")
    return plans


def _inputs(registry, private_repository):
    paths = {
        entry["path"]: Path(private_repository) / entry["path"] for entry in registry["inputs"]
    }
    frozen = _input_frozen(paths, registry)
    for entry in registry["inputs"]:
        if frozen[entry["path"]][-1] != entry["sha256"]:
            raise CompanyStoreError("Projection raw source pin differs")
    rows = {}
    systems = {}
    for entry in registry["inputs"]:
        if entry.get("role") not in {
            "MIGRATED_NATIVE_STORE",
            "MIGRATED_NATIVE_SELECTION",
            "RESTRICTED_UPSTREAM_STORE",
        }:
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
                input_id = _input_id(entry["path"], r)
                r["role"] = entry["role"]
                if entry["role"] == "MIGRATED_NATIVE_SELECTION":
                    if input_id not in entry["selected_input_ids"]:
                        r["role"] = "RESTRICTED_UPSTREAM_STORE"
                if input_id in rows:
                    raise CompanyStoreError("Projection ambiguous raw native identity")
                rows[input_id] = r
    expected = {r["input_id"] for r in registry["records"]}
    actual = {
        h
        for h, r in rows.items()
        if r["role"] in {"MIGRATED_NATIVE_STORE", "MIGRATED_NATIVE_SELECTION"}
    }
    for entry in registry["inputs"]:
        if entry.get("role") == "MIGRATED_NATIVE_SELECTION":
            selected = entry["selected_input_ids"]
            if (
                not selected
                or len(selected) != len(set(selected))
                or any(
                    key not in rows or rows[key]["source_path"] != entry["path"] for key in selected
                )
            ):
                raise CompanyStoreError("Projection exact selected original population differs")
    if expected != actual:
        raise CompanyStoreError("Projection exact raw record population differs")
    return paths, frozen, rows, systems


def _leaks(value, path="", business_key_exemptions=frozenset()):
    """Declared diagnostic detectors. They never redact or award clearance."""
    findings = []
    if isinstance(value, dict):
        for key, item in value.items():
            p = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key.casefold() in AUTHOR_KEYS and p not in business_key_exemptions:
                findings.append({"path": p, "reason": "AUTHORING_KEY"})
            findings.extend(_leaks(item, p, business_key_exemptions))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            findings.extend(_leaks(item, path + "/" + str(i), business_key_exemptions))
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
    plans = _plans(registry, rows)
    projected, active, custody, digest_custody = {}, set(), [], []
    equivalents = {}
    for contract in registry.get("same_branch_business_equivalences", []):
        original = rows[contract["original_input_id"]]
        admitted = rows[contract["admitted_input_id"]]
        fields = (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "event_at",
            "available_at",
            "sha256",
        )
        if (
            set(contract)
            != {
                "original_input_id",
                "admitted_input_id",
                "original_identity",
                "admitted_identity",
                "business_sha256",
                "basis",
            }
            or contract["basis"]
            != "EXACT_SAME_BRANCH_NATIVE_BYTES_CLOCKS_DIFFERENT_ARCHIVE_METADATA"
            or original["content"] != admitted["content"]
            or any(original[k] != admitted[k] for k in fields)
            or contract["business_sha256"] != original["sha256"]
            or contract["original_identity"] != [original[k] for k in ("component", *fields[:5])]
            or contract["admitted_identity"] != [admitted[k] for k in ("component", *fields[:5])]
            or admitted["role"] not in {"MIGRATED_NATIVE_STORE", "MIGRATED_NATIVE_SELECTION"}
            or contract["original_input_id"] in equivalents
        ):
            raise CompanyStoreError("Projection physical archive business equivalence differs")
        equivalents[contract["original_input_id"]] = contract["admitted_input_id"]

    def target_matches(plan, original_id):
        return plan is not None and plan["input_id"] in {original_id, equivalents.get(original_id)}

    def native_reference_differs(value, target, compact=False):
        for key in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "event_at",
            "available_at",
            "sha256",
        ):
            if key not in value:
                continue
            if compact and key in {"event_at", "available_at"}:
                if _time(value[key]) != _time(target[key]):
                    return True
            elif value[key] != target[key]:
                return True
        return False

    def build(raw_hash):
        if raw_hash in projected:
            return projected[raw_hash]
        if raw_hash in active:
            raise CompanyStoreError("Projection cyclic business dependency")
        active.add(raw_hash)
        plan = plans[raw_hash]
        raw = rows[plan["input_id"]]
        if (
            [raw[k] for k in ("component", "company", "branch", "system", "record", "version")]
            != plan["identity"]
            or raw["sha256"] != plan["input_sha256"]
            or raw["format"] != plan["format"]
        ):
            raise CompanyStoreError("Projection raw identity differs")
        operations, used = plan["operations"], set()
        original_metadata = json.loads(raw["provenance"])

        def original_at(pointer):
            prefix = "/@operational_metadata"
            return (
                _pointer(original_metadata, pointer[len(prefix) :])
                if pointer.startswith(prefix + "/")
                else _pointer(raw["body"], pointer)
            )

        def visit(value, pointer="", excluded_paths=frozenset()):
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
                    target_plan = plans.get(op["target_projection_id"])
                    target = rows.get(op["target_original_input_id"])
                    if target_plan and not target_matches(
                        target_plan, op["target_original_input_id"]
                    ):
                        raise CompanyStoreError(
                            "Projection scalar original/counterpart custody differs"
                        )
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
                    out = build(op["target_projection_id"])
                    if out["branch"] != plan["branch"]:
                        raise CompanyStoreError("Projection scalar digest crosses branch")
                    result = out["sha256"]
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": "HASH_REFERENCE",
                            "raw_digest": value,
                            "target_identity": op["target_identity"],
                            "target_projection_id": op["target_projection_id"],
                            "projected_digest": result,
                            "basis": op["basis"],
                        }
                    )
                    return result
                if op["kind"] == "DERIVED_DIGEST":
                    if op["algorithm"] != "CANONICAL_JSON_SHA256":
                        raise CompanyStoreError("Projection derived digest algorithm differs")
                    original = original_at(op["basis_pointer"])
                    if value != op["from"] or sha(encoded(original)) != value:
                        raise CompanyStoreError("Projection original vector digest basis differs")
                    if pointer == op["basis_pointer"]:
                        raise CompanyStoreError("Projection self-referential vector digest")
                    result = sha(encoded(visit(original, op["basis_pointer"])))
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": "DERIVED_DIGEST",
                            "raw_digest": value,
                            "projected_digest": result,
                            "basis_pointer": op["basis_pointer"],
                            "algorithm": op["algorithm"],
                        }
                    )
                    return result
                if op["kind"] == "DERIVED_OBJECT_DIGEST":
                    if op["algorithm"] != "CANONICAL_JSON_SHA256_EXCLUDING_DECLARED_KEYS":
                        raise CompanyStoreError("Projection object digest algorithm differs")
                    original = original_at(op["basis_pointer"])
                    excluded = set(op["excluded_keys"])
                    if (
                        not isinstance(original, dict)
                        or not excluded
                        or pointer != op["basis_pointer"] + "/" + next(iter(excluded))
                        or len(excluded) != 1
                        or value != op["from"]
                        or sha(encoded({k: v for k, v in original.items() if k not in excluded}))
                        != value
                    ):
                        raise CompanyStoreError("Projection original object digest basis differs")
                    basis = {k: v for k, v in original.items() if k not in excluded}
                    result = sha(encoded(visit(basis, op["basis_pointer"], {pointer})))
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": op["kind"],
                            "raw_digest": value,
                            "projected_digest": result,
                            "basis_pointer": op["basis_pointer"],
                            "excluded_keys": op["excluded_keys"],
                            "algorithm": op["algorithm"],
                        }
                    )
                    return result
                if op["kind"] in {"TARGET_VALUE_REFERENCE", "DERIVED_TARGET_HASH_MAP"}:
                    targets = op["targets"]
                    before, after = {}, {}
                    for declared in targets:
                        original_id, projected_id = (
                            declared["original_input_id"],
                            declared["projection_id"],
                        )
                        target_plan = plans.get(projected_id)
                        if not target_matches(target_plan, original_id):
                            raise CompanyStoreError("Projection value target custody differs")
                        before[declared["key"]] = _pointer(
                            rows[original_id]["body"], declared["pointer"]
                        )
                        out = build(projected_id)
                        if out["branch"] != plan["branch"]:
                            raise CompanyStoreError("Projection value target crosses branch")
                        after[declared["key"]] = _pointer(out["body"], declared["pointer"])
                    if len(before) != len(targets):
                        raise CompanyStoreError("Projection duplicate digest map key")
                    if op["kind"] == "TARGET_VALUE_REFERENCE":
                        if len(targets) != 1:
                            raise CompanyStoreError("Projection scalar value target count differs")
                        raw_value, result = next(iter(before.values())), next(iter(after.values()))
                    else:
                        raw_value, result = sha(encoded(before)), sha(encoded(after))
                    if value != raw_value or value != op["from"]:
                        raise CompanyStoreError("Projection original value/map basis differs")
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": op["kind"],
                            "raw_digest": value,
                            "projected_digest": result,
                            "targets": targets,
                        }
                    )
                    return result
                if op["kind"] == "DERIVED_TARGET_VECTOR_DIGEST":
                    if op["algorithm"] != "CANONICAL_JSON_SHA256":
                        raise CompanyStoreError("Projection linked vector digest algorithm differs")
                    target_plan = plans.get(op["target_projection_id"])
                    if (
                        target_plan is None
                        or target_plan["input_id"] != op["target_original_input_id"]
                    ):
                        raise CompanyStoreError("Projection linked vector original custody differs")
                    target = rows[target_plan["input_id"]]
                    original = _pointer(target["body"], op["basis_pointer"])
                    if value != op["from"] or sha(encoded(original)) != value:
                        raise CompanyStoreError("Projection original linked vector basis differs")
                    out = build(op["target_projection_id"])
                    if out["branch"] != plan["branch"]:
                        raise CompanyStoreError("Projection linked vector crosses branch")
                    result = sha(encoded(_pointer(out["body"], op["basis_pointer"])))
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": "DERIVED_TARGET_VECTOR_DIGEST",
                            "raw_digest": value,
                            "projected_digest": result,
                            "target_original_input_id": op["target_original_input_id"],
                            "target_projection_id": op["target_projection_id"],
                            "basis_pointer": op["basis_pointer"],
                            "algorithm": op["algorithm"],
                        }
                    )
                    return result
                if op["kind"] == "ARCHIVED_METADATA_DIGEST":
                    if op["algorithm"] != "CANONICAL_ORIGINAL_METADATA_JSON_SHA256":
                        raise CompanyStoreError("Projection archived metadata algorithm differs")
                    keys = (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "event_at",
                        "available_at",
                        "origin",
                        "provenance",
                    )
                    members = [rows[i] for i in op["original_input_ids"]]
                    members.sort(key=lambda r: tuple(r[k] for k in keys[:5]))
                    basis = [{key: row[key] for key in keys} for row in members]
                    if value != op["from"] or sha(encoded(basis)) != value:
                        raise CompanyStoreError("Projection archived metadata digest basis differs")
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": "ARCHIVED_METADATA_DIGEST",
                            "raw_digest": value,
                            "projected_digest": value,
                            "original_input_ids": op["original_input_ids"],
                            "algorithm": op["algorithm"],
                        }
                    )
                    return value
                if op["kind"] == "ARCHIVED_METADATA_BUNDLE_DIGEST":
                    keys = (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "event_at",
                        "available_at",
                        "origin",
                        "provenance",
                    )
                    basis = {
                        name: {key: rows[input_id][key] for key in keys}
                        for name, input_id in op["original_metadata_members"].items()
                    }
                    if (
                        set(basis) != {"original", "definition"}
                        or value != op["from"]
                        or sha(encoded(basis)) != value
                    ):
                        raise CompanyStoreError(
                            "Projection archived admission metadata bundle differs"
                        )
                    digest_custody.append(
                        {
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "kind": op["kind"],
                            "raw_digest": value,
                            "projected_digest": value,
                            "original_metadata_members": op["original_metadata_members"],
                        }
                    )
                    return value
                if op["kind"] in {"NATIVE_REFERENCE", "COMPACT_NATIVE_REFERENCE"}:
                    if not isinstance(value, dict):
                        raise CompanyStoreError("Projection reference shape differs")
                    if sha(encoded(value)) != op["raw_reference_sha256"]:
                        raise CompanyStoreError("Projection exact reference bytes differ")
                    original_value = value
                    aliases = op.get("native_key_aliases", {})
                    if op["kind"] == "COMPACT_NATIVE_REFERENCE":
                        if aliases != {
                            "company_id": "company",
                            "branch_id": "branch",
                            "system_id": "system",
                            "record_id": "record",
                        }:
                            raise CompanyStoreError(
                                "Projection compact native key contract differs"
                            )
                        value = {aliases.get(k, k): v for k, v in value.items()}
                    extras = op.get("preserved_business_fields", {})
                    custody_fields = {
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "origin",
                        "provenance",
                    }
                    original_extras = {
                        key: item for key, item in value.items() if key not in custody_fields
                    }
                    if extras != original_extras:
                        raise CompanyStoreError(
                            "Projection original reference business fields differ"
                        )
                    if set(extras) & custody_fields:
                        raise CompanyStoreError("Projection business extras overlap native custody")
                    target_plan = plans.get(op["target_projection_id"])
                    target = rows.get(op["target_original_input_id"])
                    if target_plan and not target_matches(
                        target_plan, op["target_original_input_id"]
                    ):
                        raise CompanyStoreError(
                            "Projection original/counterpart reference custody differs"
                        )
                    compact = op["kind"] == "COMPACT_NATIVE_REFERENCE"
                    if target is not None and native_reference_differs(value, target, compact):
                        raise CompanyStoreError(
                            "Projection exact original reference custody differs"
                        )
                    if target is not None and any(
                        key in value
                        and value[key]
                        != (
                            json.loads(target[key])
                            if key == "provenance" and isinstance(value[key], dict)
                            else target[key]
                        )
                        for key in ("origin", "provenance")
                    ):
                        raise CompanyStoreError(
                            "Projection original reference metadata custody differs"
                        )
                    archive_provenance = op.get("archive_provenance_digest_contract")
                    if archive_provenance:
                        if (
                            target is None
                            or archive_provenance
                            != {
                                "field": "provenance_sha256",
                                "original_digest": sha(target["provenance"].encode()),
                                "published_field": "original_provenance_sha256",
                                "basis": (
                                    "EXACT_PRIVATE_ORIGINAL_PROVENANCE_BYTES_NOT_PROJECTED_METADATA"
                                ),
                            }
                            or extras.get("provenance_sha256")
                            != archive_provenance["original_digest"]
                        ):
                            raise CompanyStoreError(
                                "Projection original provenance digest basis differs"
                            )

                    def publish_extras(result):
                        result.update(extras)
                        if archive_provenance:
                            result["original_provenance_sha256"] = result.pop("provenance_sha256")
                            result["original_provenance_digest_basis"] = archive_provenance["basis"]
                        return result

                    if op.get("restricted_status"):
                        if target_plan is not None:
                            raise CompanyStoreError(
                                "Projection restricted reference cannot grant a target"
                            )
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
                        if op["restricted_status"] in {
                            "RESTRICTED_CROSS_BRANCH_DEPENDENCY",
                            "RESTRICTED_ARCHIVE_MOTIVATION_ONLY",
                        }:
                            # No identity, hash, availability, or result from another
                            # branch is published through a restricted pointer.
                            result = {k: result[k] for k in ("custody_id", "status")}
                        publish_extras(result)
                        custody.append(
                            {
                                "input_id": plan["input_id"],
                                "projection_id": raw_hash,
                                "path": pointer,
                                "raw_reference": original_value,
                                "projected_reference": result,
                            }
                        )
                        return result
                    if target is None or native_reference_differs(value, target, compact):
                        raise CompanyStoreError("Projection reference custody differs")
                    if op["target_projection_id"] in plans:
                        out = build(op["target_projection_id"])
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
                            "input_id": plan["input_id"],
                            "projection_id": raw_hash,
                            "path": pointer,
                            "raw_reference": original_value,
                            "projected_reference": result,
                        }
                    )
                    publish_extras(result)
                    if op["kind"] == "COMPACT_NATIVE_REFERENCE":
                        reverse = {v: k for k, v in aliases.items()}
                        result = {reverse.get(k, k): v for k, v in result.items()}
                        custody[-1]["projected_reference"] = result
                    return result
                raise CompanyStoreError("Projection undeclared operation kind")
            if isinstance(value, dict):
                result = {}
                for key, item in value.items():
                    p = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                    if p in excluded_paths:
                        continue
                    if operations.get(p, {}).get("kind") == "DROP_AUTHORING":
                        used.add(p)
                        continue
                    output_key = plan["rename_keys"].get(p, key)
                    if output_key in result:
                        raise CompanyStoreError("Projection renamed field collides")
                    result[output_key] = visit(item, p, excluded_paths)
                return result
            if isinstance(value, list):
                return [
                    visit(item, pointer + "/" + str(i), excluded_paths)
                    for i, item in enumerate(value)
                ]
            return value

        body = visit(raw["body"])
        metadata_contract = plan.get("operational_metadata", {})
        if set(metadata_contract) - set(original_metadata):
            raise CompanyStoreError("Projection operational metadata selection differs")
        operational_metadata = {}
        for key, declaration in metadata_contract.items():
            if declaration != {
                "raw_value_sha256": sha(encoded(original_metadata[key])),
                "published_key": plan.get("metadata_rename_keys", {}).get(key, key),
                "basis": "EXPLICIT_SCHEMA_OPERATIONAL_PROVENANCE_FIELD",
            }:
                raise CompanyStoreError("Projection exact operational metadata field differs")
            published_key = declaration["published_key"]
            if published_key in operational_metadata:
                raise CompanyStoreError("Projection operational metadata key collision")
            operational_metadata[published_key] = visit(
                original_metadata[key], "/@operational_metadata/" + key
            )
        if operational_metadata:
            operational_metadata["custody_scope"] = (
                "PRESERVED_ORIGINAL_OPERATING_FACTS_WITH_DECLARED_REFERENCE_MIGRATION; "
                "ORIGINAL_EXTERNAL_DIGEST_DECLARATIONS_DO_NOT_BIND_NEW_LIBRARY_METADATA"
            )
        if plan.get("operational_admission_contract"):
            admission = operational_metadata.get("source_admission")
            if plan[
                "operational_admission_contract"
            ] != "EXACT_ORIGINAL_AND_PROJECTED_PRODUCER_METADATA_BUNDLES" or not isinstance(
                admission, dict
            ):
                raise CompanyStoreError("Projection operational admission contract differs")
            admission["original_metadata_digest_basis"] = (
                "EXACT_PRIVATE_ORIGINAL_EXPORT_AND_RUNTIME_METADATA_WITH_ORIGINAL_PROVENANCE"
            )
            admission["projected_metadata_sha256"] = sha(
                encoded(
                    {
                        "original": admission["metadata"],
                        "definition": admission["definition_metadata"],
                    }
                )
            )
            admission["projected_metadata_digest_basis"] = (
                "CANONICAL_JSON_OF_PUBLISHED_ORIGINAL_AND_DEFINITION_REFERENCE_HEADERS; "
                "NOT_ORIGINAL_METADATA_HASH"
            )
        for key, declaration in plan.get("added_business_fields", {}).items():
            if not isinstance(body, dict) or key in raw["body"] or key in body:
                raise CompanyStoreError("Projection operational limit field already exists")
            if declaration["basis"] not in {
                "EXACT_PINNED_NATIVE_WRITER_DATA_ONLY_CONTRACT",
                "PINNED_ORIGINAL_METADATA_DIGEST_WITH_EXPLICIT_MIGRATED_REFERENCE_VECTOR",
            }:
                raise CompanyStoreError("Projection operational limit basis differs")
            if "derived_from_projected_pointer" in declaration:
                if (
                    declaration["basis"]
                    != "PINNED_ORIGINAL_METADATA_DIGEST_WITH_EXPLICIT_MIGRATED_REFERENCE_VECTOR"
                ):
                    raise CompanyStoreError("Projection reference vector digest basis differs")
                body[key] = sha(
                    encoded(_pointer(body, declaration["derived_from_projected_pointer"]))
                )
            else:
                body[key] = declaration["value"]
        if used != set(operations):
            raise CompanyStoreError("Projection declared path missing")
        if plan["format"] == "JSON":
            # Do not add a schema/envelope to business payloads, or recanonicalize
            # unchanged copy/data objects. Their original bytes are digest inputs.
            data = raw["content"] if body == raw["body"] else encoded(body)
        else:
            if (
                any(not path.startswith("/@operational_metadata/") for path in operations)
                or plan["rename_keys"]
            ):
                raise CompanyStoreError("Projection plain text must preserve raw bytes")
            data = raw["content"]
        exemptions = set(plan.get("diagnostic_business_key_exemptions", []))
        if exemptions and (
            not plan.get("preserved_executed_definition") or exemptions != {"/source_pins"}
        ):
            raise CompanyStoreError(
                "Projection business diagnostic exemption is not executed configuration"
            )
        if _leaks(body, business_key_exemptions=exemptions) or _leaks(operational_metadata):
            raise CompanyStoreError("Projection learner body contains undeclared answer annotation")
        result = {
            "cohort": raw["cohort"],
            "company": COMPANY,
            "branch": plan["branch"],
            "system": plan["system"],
            "record": plan["record"],
            "version": plan["version"],
            "event_at": raw["event_at"],
            "available_at": raw["available_at"],
            "input_id": plan["input_id"],
            "projection_id": raw_hash,
            "input_sha256": raw["sha256"],
            "format": plan["format"],
            "sha256": sha(data),
            "content": data,
            "body": body,
            "operational_metadata": operational_metadata,
            "common_upstream_copy": plan["input_id"]
            in {c["input_id"] for c in registry.get("common_upstream_admissions", [])},
            "original_content_version": raw["version"],
            "preserved_executed_definition": plan.get("preserved_executed_definition", False),
        }
        projected[raw_hash] = result
        active.remove(raw_hash)
        return result

    # Reference hashes depend on business bytes, never migration/import wall clocks.
    for plan in registry["records"]:
        build(plan["projection_id"])
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
    custody = list({(r["projection_id"], r["path"]): r for r in custody}.values())
    custody.sort(key=lambda r: (r["projection_id"], r["path"]))
    # A basis subtree can be visited both directly and while deriving its digest.
    # Preserve a single exact custody entry for each declared owner/path operation.
    digest_custody = list({(r["projection_id"], r["path"]): r for r in digest_custody}.values())
    digest_custody.sort(key=lambda r: (r["projection_id"], r["path"]))
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
            if target["sha256"] != check["raw_digest"] or any(
                p["sha256"] != check["raw_digest"]
                for p in projected.values()
                if p["input_id"] == input_id
            ):
                raise CompanyStoreError("Projection executed file/copy bytes changed")
        if identities != check["raw_target_identities"]:
            raise CompanyStoreError("Projection preserved byte digest identity differs")
    transformations = [
        {
            "identity": plans[r["projection_id"]]["identity"],
            "projection_id": r["projection_id"],
            "input_id": r["input_id"],
            "input_sha256": r["input_sha256"],
            "raw_provenance_sha256": sha(rows[r["input_id"]]["provenance"].encode()),
            "projected_identity": [
                r[k] for k in ("company", "branch", "system", "record", "version")
            ],
            "projected_content_sha256": r["sha256"],
            "operations": plans[r["projection_id"]]["operations"],
            "rename_keys": plans[r["projection_id"]]["rename_keys"],
            "format": r["format"],
            "added_business_fields": plans[r["projection_id"]].get("added_business_fields", {}),
            "preserved_executed_definition": r["preserved_executed_definition"],
            "operational_metadata": plans[r["projection_id"]].get("operational_metadata", {}),
            "metadata_rename_keys": plans[r["projection_id"]].get("metadata_rename_keys", {}),
            "operational_admission_contract": plans[r["projection_id"]].get(
                "operational_admission_contract"
            ),
            "projected_operational_metadata_sha256": sha(encoded(r["operational_metadata"])),
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
        "common_upstream_admissions": registry.get("common_upstream_admissions", []),
        "same_branch_business_equivalences": registry.get("same_branch_business_equivalences", []),
        "provenance_field_classification_sha256": registry[
            "provenance_field_classification_sha256"
        ],
        "raw_source_versions": len({p["input_id"] for p in registry["records"]}),
        "projected_native_versions": len(ordered),
    }
    if registry.get("expected_transformation_sha256") != sha(encoded(transformation)):
        raise CompanyStoreError("Projection expected transformation hash differs")
    return ordered, transformation


def _provenance(record, initialized_at):
    extension = ".json" if record["format"] == "JSON" else ".txt"
    result = {
        "source_reference": "company-library://harbor-operations/initialization-v3",
        "qualification": "FICTIONAL_COMPANY_HISTORY_NOT_REAL_DEPLOYMENT_OR_PHI",
        "migration_schema": SCHEMA,
        "initialized_at": initialized_at,
        "raw_content_sha256": record["input_sha256"],
        "name": "native-" + record["projection_id"][:24] + extension,
        "content_type": "application/json"
        if record["format"] == "JSON"
        else "text/plain; charset=utf-8",
        "population": "DECLARED_IMPORTED_RECORDS_ONLY_NOT_FULL_ESTATE_OR_AUDIT_COMPLETENESS",
    }
    if record["operational_metadata"]:
        result["operational_metadata"] = record["operational_metadata"]
    if record["common_upstream_copy"]:
        result.update(
            common_upstream_copy=True,
            original_content_version=record["original_content_version"],
            common_upstream_basis="DECLARED_COPY_OF_SAME_ORIGINAL_BYTES_AND_SOURCE_CLOCKS",
            runtime_scope="COPIED_ORIGINAL_INPUT_ONLY_NO_NEW_COUNTERPART_EXECUTION_OR_AUTHORITY_ASSERTED",
        )
    if record["preserved_executed_definition"]:
        result["definition_basis"] = (
            "EXACT_ORIGINAL_EXECUTED_CONFIGURATION_BYTES; EMBEDDED_INPUT_IDENTITIES_ARE_"
            "ORIGINAL_ARCHIVE_COORDINATES_NOT_NEW_LIBRARY_BINDINGS; NO_NEW_EXECUTION_ASSERTED"
        )
    return result


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
            plan = next(
                p for p in registry["records"] if p["projection_id"] == record["projection_id"]
            )
            owner = systems[tuple(plan["identity"][:4])]
            store.register_system(COMPANY, record["branch"], record["system"], owner)
            ref = store.append_version(
                COMPANY,
                record["branch"],
                record["system"],
                record["record"],
                expected_version=record["version"] - 1,
                command_id="MIG-" + record["projection_id"][:60],
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
        if _input_frozen(paths, registry) != frozen:
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
            raw_hash = record["projection_id"]
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
            plan = next(p for p in registry["records"] if p["projection_id"] == raw_hash)
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
    if _input_frozen(paths, registry) != frozen or _frozen(target_paths) != target_frozen:
        raise CompanyStoreError("Projection verifier mutated custody")
    return receipt
