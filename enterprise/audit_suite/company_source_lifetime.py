"""Trusted-local admission/setup of an explicitly reviewed native source edition.

No HTTP surface, new source facts, grants or audit outcomes. The independently
published native library remains immutable; the normal lifetime initializer
creates its own ordinary copy, initialization and zero-operation checkpoint.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .company_store import _json, _time
from .fresh_sec003_procedure import require

EDITION_FORMAT = "PRIVATE_COMPANY_ACTIVITY_RUN_V1"
EDITION_SCHEMA = "LOSSLESS_COMPANY_NATIVE_SOURCE_EDITION_V1"
EDITION_ADMISSION_SCHEMA = "SH_EXPLICIT_NATIVE_SOURCE_EDITION_LIBRARY_ADMISSION_V1"
POPULATION_BOUNDARY = (
    "EXACT_SELECTED_NATIVE_EDITION_NOT_ENTIRE_ENTERPRISE_OR_OPERATING_YEAR_ACCEPTANCE"
)
VERSION_FIELDS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "event_at",
    "available_at",
    "imported_at",
    "origin",
    "provenance",
    "content",
    "sha256",
    "command_id",
    "input_digest",
)
MANIFEST_FIELDS = {
    "format",
    "source_edition_schema",
    "audit_created",
    "grants_created",
    "counts",
    "members",
}
RECEIPT_FIELDS = {
    "schema",
    "status",
    "started_at",
    "published_at",
    "components",
    "native_fields_preserved",
    "native_table_sha256",
    "native_counts",
    "input_operational_ledgers_and_files_must_be_retained",
    "source_snapshot_boundary",
    "publication_atomic_to_concurrent_readers",
    "original_operational_workflow_tables_copied",
    "audit_created",
    "grants_created",
    "assessment_credit",
    "coherent_operating_year_or_whole_estate_completeness",
    "qualification",
    "code_pins",
}
PUBLISHER_FILES = {
    "company_source_edition.py",
    "company_runtime_activation.py",
    "company_store.py",
    "company_activity_plan_sources.py",
    "private_publication.py",
}


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _identity(path):
    info = path.lstat()
    return tuple(
        getattr(info, key)
        for key in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    )


def _schema_inventory(db):
    names = ("systems", "versions", "grants", "collections", "access_events")
    return {
        "objects": [
            list(row)
            for row in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ],
        "columns": {
            name: [list(row) for row in db.execute(f"PRAGMA table_xinfo({name})")] for name in names
        },
        "versions": [
            db.execute("PRAGMA user_version").fetchone()[0],
            db.execute("PRAGMA application_id").fetchone()[0],
        ],
    }


def _application_schema():
    # This is our pinned application source, never an incoming SQL definition.
    # Reproduce only its single literal initializer in memory; no source object
    # creation, CompanyStore constructor or accepted-database writes occur here.
    source = ast.parse(Path(__file__).with_name("company_store.py").read_bytes())
    classes = [
        node
        for node in source.body
        if isinstance(node, ast.ClassDef) and node.name == "CompanyStore"
    ]
    require(len(classes) == 1, "Exact application CompanyStore source required")
    initializers = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    ]
    require(len(initializers) == 1, "Exact application CompanyStore initializer required")
    calls = [
        node
        for node in ast.walk(initializers[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "executescript"
    ]
    require(
        len(calls) == 1
        and len(calls[0].args) == 1
        and not calls[0].keywords
        and isinstance(calls[0].args[0], ast.Constant)
        and type(calls[0].args[0].value) is str,
        "One literal application-owned CompanyStore schema required",
    )
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(calls[0].args[0].value)
        return _schema_inventory(db)


def _pinned_document(path, expected):
    from .source_library_audit import private_file

    private_file(path)
    require(_sha(expected), "Explicit native-edition document SHA required")
    before = _identity(path)
    require(before[4] <= 1024 * 1024, "Bounded native-edition document required")
    raw = path.read_bytes()
    require(
        len(raw) <= 1024 * 1024 and hashlib.sha256(raw).hexdigest() == expected,
        "Native-edition document bytes differ",
    )
    require(
        _identity(path) == before,
        "Native-edition document changed while consumed",
    )

    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "Duplicate native-edition document key")
            value[key] = item
        return value

    return json.loads(raw, object_pairs_hook=unique)


def verify_edition_library(accepted, manifest, review):
    """Additional exact format branch; old projection formats remain untouched."""
    from .source_library_audit import file_sha, private_file, quiescent_database, quiescent_read

    source_paths = (accepted.database, accepted.manifest, accepted.review)
    opening = {}
    for path, expected in zip(
        source_paths,
        (accepted.database_sha256, accepted.manifest_sha256, accepted.review_sha256),
        strict=True,
    ):
        private_file(path)
        opening[path] = _identity(path)
        require(file_sha(path) == expected, "Native-edition opening external pin differs")
    require(
        _same(_pinned_document(accepted.manifest, accepted.manifest_sha256), manifest)
        and _same(_pinned_document(accepted.review, accepted.review_sha256), review),
        "Native-edition consumed manifest/review differ from external pins",
    )

    require(
        type(manifest) is dict
        and set(manifest) == MANIFEST_FIELDS
        and manifest["format"] == EDITION_FORMAT
        and manifest["source_edition_schema"] == EDITION_SCHEMA,
        "Exact native-edition library manifest required",
    )
    require(
        accepted.manifest.name == "MANIFEST.json"
        and accepted.database == accepted.manifest.parent / "company/company.sqlite3",
        "Literal published native-edition namespace required",
    )
    counts = manifest["counts"]
    require(
        type(counts) is dict
        and set(counts) == {"systems", "versions", "grants", "collections", "access_events"}
        and type(counts["systems"]) is int
        and counts["systems"] > 0
        and type(counts["versions"]) is int
        and counts["versions"] == accepted.version_count
        and all(
            type(counts[k]) is int and counts[k] == 0
            for k in ("grants", "collections", "access_events")
        )
        and manifest["audit_created"] is False
        and manifest["grants_created"] is False,
        "Source-only exact native counts/no transferred authority required",
    )
    members = manifest["members"]
    require(
        type(members) is dict
        and set(members) == {"company/company.sqlite3", "SOURCE_EDITION.json"}
        and members["company/company.sqlite3"] == accepted.database_sha256
        and _sha(members["SOURCE_EDITION.json"]),
        "Exact native-edition member pins required",
    )
    receipt_path = accepted.manifest.parent / "SOURCE_EDITION.json"
    opening[receipt_path] = _identity(receipt_path)
    receipt = _pinned_document(receipt_path, members["SOURCE_EDITION.json"])
    require(
        type(receipt) is dict
        and set(receipt) == RECEIPT_FIELDS
        and receipt["schema"] == EDITION_SCHEMA
        and receipt["status"] == "NATIVE_SOURCE_EDITION_PUBLISHED_NOT_ASSESSED"
        and receipt["native_fields_preserved"] == list(VERSION_FIELDS)
        and type(receipt["native_counts"]) is dict
        and set(receipt["native_counts"]) == {"systems", "versions"}
        and all(type(v) is int for v in receipt["native_counts"].values())
        and receipt["native_counts"]
        == {"systems": counts["systems"], "versions": counts["versions"]},
        "Exact lossless native publisher receipt required",
    )
    require(
        receipt["input_operational_ledgers_and_files_must_be_retained"] is True
        and receipt["source_snapshot_boundary"]
        == "PER_COMPONENT_TRANSACTIONS_WITH_GLOBAL_CLOSING_IDENTITIES_AND_TRUSTED_WRITER_QUIESCENCE"
        and receipt["publication_atomic_to_concurrent_readers"] is False
        and all(
            receipt[k] is False
            for k in (
                "original_operational_workflow_tables_copied",
                "audit_created",
                "grants_created",
                "assessment_credit",
                "coherent_operating_year_or_whole_estate_completeness",
            )
        )
        and receipt["qualification"]
        == "EXACT_SELECTED_COMPANY_SOURCE_EDITION_REQUIRES_INDEPENDENT_ADMISSION",
        "Native-edition receipt must not import authority/outcomes/completeness",
    )
    require(
        _time(receipt["started_at"]) <= _time(receipt["published_at"]),
        "Native edition publication chronology differs",
    )
    require(
        type(receipt["components"]) is list
        and 1 <= len(receipt["components"]) <= 16
        and len({c["id"] for c in receipt["components"]}) == len(receipt["components"]),
        "Explicit distinct selected native components required",
    )
    require(
        type(receipt["code_pins"]) is dict
        and set(receipt["code_pins"]) == PUBLISHER_FILES
        and all(_sha(v) for v in receipt["code_pins"].values()),
        "Exact publisher code provenance required",
    )
    expected_admission = {
        "schema": EDITION_ADMISSION_SCHEMA,
        "manifest_format": EDITION_FORMAT,
        "source_edition_schema": EDITION_SCHEMA,
        "source_edition_sha256": members["SOURCE_EDITION.json"],
        "publisher_code_pins": receipt["code_pins"],
        "quiescent_source_only": True,
        "operating_provenance_reviewed": True,
        "audit_outcome_imports": False,
        "population_boundary": POPULATION_BOUNDARY,
    }
    require(
        _same(review.get("source_schema_admission"), expected_admission),
        "New native-edition source-only external review required",
    )
    # Independent rows are supplied by the existing CompanyStore schema, never
    # an incoming trigger/view. Every scalar/type/body/hash remains native.
    with quiescent_read(accepted.database) as db:
        require(
            _same(_schema_inventory(db), _application_schema()),
            "Exact application-owned native-edition schema required",
        )
        columns = tuple(row[1] for row in db.execute("PRAGMA table_info(versions)"))
        require(columns == VERSION_FIELDS, "Native-edition version schema differs")
        require(
            db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == counts["systems"],
            "Native-edition system boundary differs",
        )
        fingerprints = {"systems": hashlib.sha256(), "versions": hashlib.sha256()}
        for row in db.execute(
            "SELECT company,branch,system,owner FROM systems ORDER BY company,branch,system"
        ):
            body = _json(list(row)).encode()
            fingerprints["systems"].update(str(len(body)).encode() + b":" + body)
        for row in db.execute(
            "SELECT * FROM versions ORDER BY company,branch,system,record,version"
        ):
            require(
                type(row["version"]) is int
                and row["version"] > 0
                and type(row["content"]) is bytes
                and hashlib.sha256(row["content"]).hexdigest() == row["sha256"],
                "Native-edition exact version/body bytes differ",
            )
            body = _json(
                [
                    row[k] if k != "content" else {"bytes": len(row[k]), "sha256": row["sha256"]}
                    for k in VERSION_FIELDS
                ]
            ).encode()
            fingerprints["versions"].update(str(len(body)).encode() + b":" + body)
        require(
            _same(
                receipt["native_table_sha256"], {k: v.hexdigest() for k, v in fingerprints.items()}
            ),
            "Native-edition full header/body fingerprint differs",
        )
    private_file(receipt_path)
    require(
        file_sha(receipt_path) == members["SOURCE_EDITION.json"],
        "Native-edition receipt closing pin differs",
    )
    for path, expected in zip(
        source_paths,
        (accepted.database_sha256, accepted.manifest_sha256, accepted.review_sha256),
        strict=True,
    ):
        require(file_sha(path) == expected, "Native-edition final external pin differs")
    for path, before in opening.items():
        private_file(path)
        require(
            _identity(path) == before,
            "Native-edition global closing identity changed",
        )
    quiescent_database(accepted.database)


def initialize_edition_lifetime(
    accepted,
    destination,
    *,
    operator_id,
    runtime_review,
    runtime_review_sha256,
    engineering_only=False,
):
    """One new source lifetime, through existing APIs; never create an audit.

    Both reviews are external operator inputs. This helper emits no acceptance,
    uses no caller outcomes and never changes the immutable published edition.
    Future audit creation/bindings remain the existing PersistentAudit APIs.
    """
    from .persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT, PersistentCompany
    from .source_library_audit import file_sha

    pins = accepted.verify()
    manifest = _pinned_document(accepted.manifest, accepted.manifest_sha256)
    require(
        manifest.get("source_edition_schema") == EDITION_SCHEMA,
        "Explicit new native edition required",
    )
    runtime_review = Path(runtime_review)
    review = _pinned_document(runtime_review, runtime_review_sha256)
    require(
        review.get("schema") == RUNTIME_SCHEMA
        and review.get("verdict") == RUNTIME_VERDICT
        and review.get("source_execution_authorized") is True
        and review.get("runtime_module_sha256")
        == file_sha(Path(__file__).with_name("persistent_company_journey.py"))
        and review.get("adapter_module_sha256")
        == file_sha(Path(__file__).with_name("source_library_audit.py"))
        and review.get("accepted_baseline_pins") == pins
        and review.get("source_setup_module_sha256") == file_sha(Path(__file__))
        and review.get("source_edition_sha256") == manifest["members"]["SOURCE_EDITION.json"],
        "Runtime review must bind this native-edition setup/original receipt",
    )
    world = PersistentCompany.initialize(
        accepted, destination, operator_id=operator_id, engineering_only=engineering_only
    )
    world.accept_runtime(runtime_review, runtime_review_sha256)
    world.require_runtime()
    require(accepted.verify() == pins, "Published library changed during lifetime initialization")
    return world
