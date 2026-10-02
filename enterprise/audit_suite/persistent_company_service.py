"""Private startup of an existing workroom against its retained company lifetime.

This loader neither initializes a company nor creates an audit, principal, grant,
or evidence. External config/binding/checkpoint pins are operator inputs. Source
and runtime acceptance remain the existing independently reviewed contracts.
"""

from __future__ import annotations

import importlib
import json
import math
import re
import sqlite3
import stat
import sys
import time
from contextlib import closing
from dataclasses import fields
from pathlib import Path

from .company_store import CompanyStore, _id, _time
from .engine import Engine
from .fresh_sec003_procedure import NATIVE_ID, require
from .inference import _json
from .persistent_company_journey import PersistentCompany, native_rows
from .recovery import _history
from .source_library_audit import (
    EMPTY_WORKROOM,
    AcceptedLibrary,
    file_sha,
    private_file,
    quiescent_database,
    quiescent_read,
)
from .store import DomainError

CONFIG_SCHEMA = "SH_RETAINED_COMPANY_WORKROOM_SERVICE_CONFIG_V1"
BINDING_SCHEMA = "SH_RETAINED_COMPANY_AUDIT_WORKROOM_BINDING_V1"
CODE_MODULES = (
    "__main__.py",
    "artifacts.py",
    "company_collection.py",
    "company_store.py",
    "draft_store.py",
    "engine.py",
    "persistent_company_journey.py",
    "persistent_company_service.py",
    "service.py",
    "source_library_audit.py",
    "store.py",
    "workpaper_links.py",
    "workspace_transport.py",
)
BINDING_FIELDS = {
    "schema",
    "company_root",
    "company_initialization_sha256",
    "accepted_baseline_pins",
    "audit_root",
    "engagement_id",
    "company",
    "branch",
    "identities",
    "company_operator_id",
    "program_pack",
    "task_count",
    "mode",
    "initial_simulated_at",
    "scope",
    "zero_workroom_counts",
}


def absolute_path(value):
    require(isinstance(value, str) and Path(value).is_absolute(), "Explicit absolute path required")
    path = Path(value)
    require(
        path == path.resolve() and not any(p.is_symlink() for p in [path, *path.parents]),
        "Unaliased operator path required",
    )
    return path


def private_directory(path):
    require(
        path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700,
        "Existing private ordinary directory required",
    )


def pinned_json(path, expected, *, max_bytes=1024 * 1024):
    require(
        isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected),
        "External exact SHA-256 required",
    )
    private_file(path)
    require(
        path.stat().st_size <= max_bytes and file_sha(path) == expected,
        "Pinned operator file changed or exceeds limit",
    )
    value = _json(path.read_bytes())
    require(isinstance(value, dict), "Pinned operator object required")
    private_file(path)
    require(file_sha(path) == expected, "Pinned operator file changed during read")
    return value


def configuration(world, binding_path, binding_sha256, *, repository):
    """Serialize explicitly supplied accepted authority, never infer latest pins.

    The caller preserves the resulting config hash outside the mutable workroom.
    This is configuration serialization, not independent acceptance or activation.
    """
    world.require_runtime()
    require(world.runtime_acceptance is not None, "Explicit accepted runtime review required")
    pinned_json(Path(binding_path), binding_sha256)
    return {
        "schema": CONFIG_SCHEMA,
        "accepted_library": {
            f.name: str(getattr(world.accepted, f.name))
            if isinstance(getattr(world.accepted, f.name), Path)
            else getattr(world.accepted, f.name)
            for f in fields(AcceptedLibrary)
        },
        "company_lifetime": {
            "root": str(world.root),
            "checkpoint": str(world.checkpoint),
            "checkpoint_sha256": world.checkpoint_sha256,
            "runtime_review": world.runtime_acceptance["path"],
            "runtime_review_sha256": world.runtime_acceptance["sha256"],
        },
        "workroom_binding": {"path": str(Path(binding_path).absolute()), "sha256": binding_sha256},
        "code_pins": {
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name)
            for name in CODE_MODULES
        },
    }


class RetainedEngine(Engine):
    """Keep an accepted company investigation on its existing source path.

    Scope reconciliation currently returns the general engine to generated
    scenario mode. It needs a company-aware reconciliation contract before it
    can be used in this retained service.
    """

    def command(self, actor, engagement_id, command):
        kind = command.get("kind", "") if isinstance(command, dict) else ""
        if isinstance(kind, str) and (
            kind in {"scope.update", "company.activate"}
            or kind.startswith(("scenario.", "generation."))
        ):
            raise DomainError(
                "Retained company scope and source activation require operator reconciliation",
                code="FORBIDDEN",
                status=403,
            )
        return super().command(actor, engagement_id, command)


class RetainedWorkroom:
    def __init__(
        self,
        config_path,
        expected_sha256,
        *,
        private_root,
        repository,
        inference_config=None,
        voice_config=None,
    ):
        self.path = absolute_path(str(config_path))
        private_directory(self.path.parent)
        self.expected_sha256 = expected_sha256
        self.repository = Path(repository).absolute()
        self.config = pinned_json(self.path, expected_sha256)
        require(
            set(self.config)
            == {"schema", "accepted_library", "company_lifetime", "workroom_binding", "code_pins"}
            and self.config["schema"] == CONFIG_SCHEMA,
            "Exact retained-service schema required",
        )
        self.check_code()
        source = self.config["accepted_library"]
        require(
            isinstance(source, dict) and set(source) == {f.name for f in fields(AcceptedLibrary)},
            "Exact accepted-library configuration required",
        )
        source = dict(source)
        for key in ("database", "manifest", "review"):
            source[key] = absolute_path(source[key])
        accepted = AcceptedLibrary(**source)
        lifetime = self.config["company_lifetime"]
        require(
            isinstance(lifetime, dict)
            and set(lifetime)
            == {
                "root",
                "checkpoint",
                "checkpoint_sha256",
                "runtime_review",
                "runtime_review_sha256",
            },
            "Exact externally pinned company lifetime required",
        )
        self.world = PersistentCompany(
            accepted,
            absolute_path(lifetime["root"]),
            absolute_path(lifetime["checkpoint"]),
            lifetime["checkpoint_sha256"],
        )
        self.world.accept_runtime(
            absolute_path(lifetime["runtime_review"]), lifetime["runtime_review_sha256"]
        )
        self.world.require_runtime()
        choice = self.config["workroom_binding"]
        require(
            isinstance(choice, dict) and set(choice) == {"path", "sha256"},
            "Exact externally pinned workroom binding required",
        )
        self.binding_path, self.binding_sha256 = absolute_path(choice["path"]), choice["sha256"]
        self.binding = pinned_json(self.binding_path, self.binding_sha256)
        require(
            set(self.binding) == BINDING_FIELDS and self.binding["schema"] == BINDING_SCHEMA,
            "Exact retained-workroom binding required",
        )
        self.root = absolute_path(self.binding["audit_root"])
        require(self.root == Path(private_root).absolute(), "Selected existing workroom differs")
        private_directory(self.root)
        private_directory(self.root / "artifacts")
        self.engagement = _id(self.binding["engagement_id"])
        self.selected = {k: _id(self.binding[k]) for k in ("company", "branch")}
        require(
            self.binding["company_root"] == str(self.world.root)
            and self.binding["company_initialization_sha256"]
            == file_sha(self.world.root / "INITIALIZATION.json")
            and self.binding["accepted_baseline_pins"] == self.world.pins
            and self.binding["company_operator_id"] == self.world.operator.principal,
            "Workroom binding differs from accepted company lifetime",
        )
        pack = self.binding["program_pack"]
        require(
            isinstance(pack, dict) and set(pack) == {"path", "sha256"},
            "Pinned original instruction pack required",
        )
        self.pack_path = absolute_path(pack["path"])
        pinned_json(self.pack_path, pack["sha256"], max_bytes=32 * 1024 * 1024)
        self.verify_workroom()
        # Do not construct a raw CompanyStore: the accepted lifetime supplies the
        # only company connection and retains its existing grant/clock checks.
        self.engine = RetainedEngine(
            self.root,
            repository=self.repository,
            program_pack=self.pack_path,
            inference_config=inference_config,
            voice_config=voice_config,
        )
        self.engine.company_store = self.world.store
        self.engine.company_bindings = {self.engagement: dict(self.selected)}
        self.engine.capabilities.update(
            company_sources=True,
            company_message_sources=True,
            company_consultations=True,
            company_source_census=True,
            company_populations=True,
            source_impact_dispositions=True,
            company_source_impact=True,
        )
        self.check_pins()

    def check_code(self):
        """Bind file pins to loaded module origins in this ordinary local process.

        This is not a hostile-process sandbox or an attestation of mutable
        interpreter memory. Operator configuration is pinned before startup.
        """
        pins = self.config["code_pins"]
        require(
            isinstance(pins, dict) and set(pins) == set(CODE_MODULES),
            "Exact retained service/engine/runtime module pins required",
        )
        for name, expected in pins.items():
            path = self.repository / "enterprise/audit_suite" / name
            module_name = "enterprise.audit_suite." + name.removesuffix(".py")
            loaded = sys.modules.get(module_name)
            if name == "__main__.py":
                entry = sys.modules.get("__main__")
                if getattr(getattr(entry, "__spec__", None), "name", None) == module_name:
                    loaded = entry
            if loaded is None:
                loaded = importlib.import_module(module_name)
            origin = getattr(getattr(loaded, "__spec__", None), "origin", None)
            require(
                not path.is_symlink()
                and path.is_file()
                and origin is not None
                and Path(origin).resolve() == path.resolve()
                and Path(loaded.__file__).resolve() == path.resolve()
                and file_sha(path) == expected,
                "Pinned retained service/runtime code changed or loaded module differs",
            )

    def verify_workroom(self):
        path = self.root / "engagements.sqlite3"
        private_file(path)
        # Audit workrooms intentionally use WAL. A normal read-only connection
        # sees their actual committed current state; immutable reads are reserved
        # for the separately quiescent accepted company source.
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")
            require(
                db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                and not db.execute("PRAGMA foreign_key_check").fetchall(),
                "Existing workroom database integrity failed",
            )
            require(
                {row[0] for row in db.execute("SELECT id FROM engagements")} == {self.engagement},
                "Exactly one retained workroom engagement required",
            )
            _history(db)
            events = db.execute("SELECT * FROM events ORDER BY revision").fetchall()
            initial, current = json.loads(events[0]["state"]), json.loads(events[-1]["state"])
            identities = self.binding["identities"]
            require(
                isinstance(identities, dict)
                and set(identities) == {"operator", "auditor", "reviewer"}
                and len(set(identities.values()) | {self.world.operator.principal}) == 4,
                "Distinct original audit and company identities required",
            )
            require(
                {
                    (row["principal"], row["permission"])
                    for row in db.execute("SELECT principal,permission FROM members")
                }
                == {
                    (identities["operator"], "instruct"),
                    (identities["auditor"], "learn"),
                    (identities["reviewer"], "review"),
                },
                "Original isolated workroom memberships differ",
            )
            for role, permission, expected_roles in (
                ("operator", "instruct", ["instructor"]),
                ("auditor", "learn", ["learner"]),
                ("reviewer", "review", ["reviewer"]),
            ):
                person = _id(identities[role])
                principal = db.execute(
                    "SELECT roles FROM principals WHERE id=?", (person,)
                ).fetchone()
                member = db.execute(
                    "SELECT permission FROM members WHERE principal=? AND engagement=?",
                    (person, self.engagement),
                ).fetchone()
                require(
                    principal is not None
                    and json.loads(principal[0]) == expected_roles
                    and member is not None
                    and member[0] == permission,
                    "Retained audit identity or membership differs",
                )
            require(
                initial["created_by"] == identities["operator"]
                and initial["scope"] == self.binding["scope"]
                and initial["mode"] == self.binding["mode"]
                and _time(initial["simulated_at"]) == _time(self.binding["initial_simulated_at"])
                and type(self.binding["task_count"]) is int
                and self.binding["task_count"] == len(initial["tasks"]) > 0
                and self.binding["zero_workroom_counts"] == {k: 0 for k in EMPTY_WORKROOM}
                and all(
                    type(self.binding["zero_workroom_counts"][k]) is int for k in EMPTY_WORKROOM
                )
                and all(isinstance(initial[k], list) for k in EMPTY_WORKROOM)
                and not any(initial[k] for k in EMPTY_WORKROOM)
                and all(
                    t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                    for t in initial["tasks"]
                ),
                "Original fresh-workroom birth binding differs",
            )
            previous_clock, previous_real = _time(initial["simulated_at"]), 0
            for event in events:
                state = json.loads(event["state"])
                real = event["recorded_at"]
                clock = _time(state["simulated_at"])
                require(
                    type(real) in (int, float)
                    and math.isfinite(real)
                    and previous_real <= real <= time.time()
                    and previous_clock <= clock,
                    "Workroom actual/simulated clock chronology changed",
                )
                require(
                    state["id"] == self.engagement and state["mode"] == self.binding["mode"],
                    "Retained engagement identity/mode differs",
                )
                if state.get("company_source_binding") is not None:
                    require(
                        state["company_source_binding"] == self.selected,
                        "Historical company branch binding changed",
                    )
                previous_clock, previous_real = clock, real
            require(
                current.get("company_source_binding") == self.selected
                and current.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION"
                and current["phase"] in {"READY", "ACTIVE", "CLOSED"},
                "Retained workroom must have an activated exact company binding",
            )
        with self.world.locked():
            self.world.verify()
            native = native_rows(self.world.database)
            require(
                _time(self.world.initialization["initialized_at"]) <= _time(time_to_iso())
                and all(
                    _time(row["imported_at"]) <= _time(time_to_iso()) for row in native.values()
                ),
                "Company real import clock is in the future",
            )
            # A retained artifact appears in every subsequent state snapshot.
            # Validate each complete typed representation once in this fresh
            # locked invocation, at its earliest (most restrictive) clock. No
            # result survives this invocation. Changed historical fields,
            # including JSON booleans versus integers, are distinct inputs.
            verified = set()
            with quiescent_read(self.world.database) as db:
                journal = {
                    row["command_id"]: json.loads(row["receipt"])
                    for row in db.execute("SELECT command_id,receipt FROM collections")
                }
            for event in events:
                self.verify_artifacts(
                    json.loads(event["state"]), native, verified=verified, journal=journal
                )

    def verify_artifacts(self, state, native, *, verified=None, journal=None):
        for artifact in state["artifacts"]:
            representation = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
            if verified is not None and representation in verified:
                continue
            path = self.root / "artifacts" / artifact["sha256"]
            require(
                re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"]), "Retained artifact hash differs"
            )
            require(
                type(artifact["bytes"]) is int and artifact["bytes"] >= 0,
                "Strict nonnegative retained artifact byte count required",
            )
            private_file(path)
            require(
                file_sha(path) == artifact["sha256"] and path.stat().st_size == artifact["bytes"],
                "Retained artifact bytes changed",
            )
            if artifact["source"].get("kind") != "COLLECTED_COMPANY_SOURCE":
                if verified is not None:
                    verified.add(representation)
                continue
            receipt = artifact["source"]["receipt"]
            source = receipt["source"]
            require(
                type(source["version"]) is int
                and source["version"] > 0
                and type(receipt["content_bytes"]) is int
                and receipt["content_bytes"] >= 0,
                "Strict retained source version and receipt byte count required",
            )
            row = native.get(tuple(source[k] for k in NATIVE_ID))
            require(
                row is not None
                and source == CompanyStore._metadata(row)
                and all(source[k] == self.selected[k] for k in self.selected)
                and receipt["engagement_id"] == self.engagement
                and receipt["principal_id"] == self.binding["identities"]["auditor"]
                and source["sha256"] == artifact["sha256"]
                and receipt["content_bytes"] == artifact["bytes"]
                and _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= _time(state["simulated_at"])
                and _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(time_to_iso()),
                "Retained company collection receipt/source custody differs",
            )
            if journal is None:
                with quiescent_read(self.world.database) as db:
                    saved = db.execute(
                        "SELECT receipt FROM collections WHERE command_id=?",
                        (receipt["command_id"],),
                    ).fetchone()
                    saved_receipt = None if saved is None else json.loads(saved[0])
            else:
                saved_receipt = journal.get(receipt["command_id"])
            require(
                saved_receipt is not None and saved_receipt == receipt,
                "Retained original company collection journal differs",
            )
            if verified is not None:
                verified.add(representation)

    def check_pins(self):
        require(
            pinned_json(self.path, self.expected_sha256) == self.config,
            "Retained service configuration changed",
        )
        require(
            pinned_json(self.binding_path, self.binding_sha256) == self.binding,
            "Retained workroom binding changed",
        )
        self.check_code()
        lifetime = self.config["company_lifetime"]
        private_file(self.world.checkpoint)
        require(
            file_sha(self.world.checkpoint) == lifetime["checkpoint_sha256"],
            "Externally pinned company checkpoint changed",
        )
        require(
            file_sha(absolute_path(lifetime["runtime_review"]))
            == lifetime["runtime_review_sha256"],
            "Accepted runtime review changed",
        )
        pinned_json(
            self.pack_path, self.binding["program_pack"]["sha256"], max_bytes=32 * 1024 * 1024
        )
        for path in (self.world.accepted.database, self.world.database):
            quiescent_database(path)
        self.world.require_runtime()

    def guard(self, request):
        self.check_pins()
        path = request.url.path
        selected = re.match(r"/api/engagements/([^/]+)", path)
        if (
            (path == "/api/engagements" and request.method == "POST")
            or (selected and selected[1] != self.engagement)
            or "instructor" in path
            or "private-corpus" in path
        ):
            raise DomainError(
                "Route unavailable in this retained workroom", code="FORBIDDEN", status=403
            )


def time_to_iso():
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="microseconds")


def create_retained_app(private_root, config_path, expected_sha256, *, repository, **options):
    """Use the existing local service/UI; never expose operator custody configuration."""
    from .service import create_app

    require(
        not any(
            name in options
            for name in (
                "engine_factory",
                "request_guard",
                "company_root",
                "company_bindings",
                "company_registry",
                "company_profile",
                "instructor_key_root",
                "instructor_bindings",
                "company_rights_factory",
                "company_native_rights_factory",
                "program_pack",
                "corpus_root",
            )
        ),
        "Retained service cannot combine source, private Key or authority overrides",
    )
    retained = RetainedWorkroom(
        config_path,
        expected_sha256,
        private_root=private_root,
        repository=repository,
        inference_config=options.get("inference_config"),
        voice_config=options.get("voice_config"),
    )
    app = create_app(
        private_root,
        repository=repository,
        engine_factory=lambda: retained.engine,
        request_guard=retained.guard,
        enable_instructor_writeback=False,
        **options,
    )
    return app
