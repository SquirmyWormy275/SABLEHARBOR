"""Private startup of an existing workroom against its retained company lifetime.

This loader neither initializes a company nor creates an audit, principal, grant,
or evidence. External config/binding/checkpoint pins are operator inputs. Source
and runtime acceptance remain the existing independently reviewed contracts.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import sqlite3
import stat
import sys
import threading
import time
from contextlib import closing
from dataclasses import fields
from pathlib import Path

from .company_store import CompanyStore, _id, _time
from .engine import Engine
from .fresh_sec003_procedure import NATIVE_ID, require
from .history_inspection import _stamp as journal_stamp
from .history_inspection import publish_validated_history, scan_validated_history
from .inference import _json
from .persistent_company_journey import PersistentCompany, native_rows
from .serialized_json import native_code_files
from .source_library_audit import (
    EMPTY_WORKROOM,
    AcceptedLibrary,
    file_sha,
    private_file,
    quiescent_database,
    quiescent_read,
)
from .store import DomainError, digest

CONFIG_SCHEMA = "SH_RETAINED_COMPANY_WORKROOM_SERVICE_CONFIG_V1"
SEALED_CONFIG_SCHEMA = "SH_RETAINED_COMPANY_SEALED_WORKROOM_SERVICE_CONFIG_V1"
BINDING_SCHEMA = "SH_RETAINED_COMPANY_AUDIT_WORKROOM_BINDING_V1"
CODE_MODULES = (
    "__main__.py",
    "artifacts.py",
    "company_collection.py",
    "company_store.py",
    "company_source_lifetime.py",
    "draft_store.py",
    "engine.py",
    "history_inspection.py",
    "history_locators.py",
    "persistent_company_journey.py",
    "persistent_company_service.py",
    "recovery.py",
    "request_integrity.py",
    "serialized_json.py",
    "service.py",
    "source_library_audit.py",
    "store.py",
    "workpaper_links.py",
    "workspace_transport.py",
)
SEALED_CODE_MODULES = CODE_MODULES + (
    "canonical_state_codec.py",
    "pristine_tail_conversion.py",
    "codec_history_inspection.py",
    "sealed_history_authority.py",
    "sealed_history_inspection.py",
    "sealed_history_store.py",
    "compact_prefix_storage.py",
    "sealed_retained_service.py",
)
MANAGED_HISTORY_CODE_MODULES = (
    "history_integrity_reference.py",
    "managed_history_integrity.py",
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
    require(
        isinstance(value, str) and Path(value).is_absolute(),
        "Explicit absolute path required",
    )
    path = Path(value)
    require(
        path == path.resolve()
        and not any(p.is_symlink() for p in [path, *path.parents]),
        "Unaliased operator path required",
    )
    return path


def private_directory(path):
    require(
        path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700,
        "Existing private ordinary directory required",
    )


def same_file_identity(left, right):
    """Read access may update atime; all mutation/alias indicators stay strict."""
    return all(
        getattr(left, name) == getattr(right, name)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
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
    require(
        world.runtime_acceptance is not None,
        "Explicit accepted runtime review required",
    )
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
        "workroom_binding": {
            "path": str(Path(binding_path).absolute()),
            "sha256": binding_sha256,
        },
        "code_pins": {
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name)
            for name in (*CODE_MODULES, *native_code_files())
        },
    }


def retained_native_files(*, sealed=False):
    result = dict(native_code_files())
    if sealed:
        from .canonical_state_codec import native_code_files as encoder_native_files

        result.update(encoder_native_files())
    return result


def sealed_configuration(
    base,
    history,
    authority_head,
    *,
    repository,
    session_revocations=None,
    compact_prefix=None,
    history_integrity=None,
):
    """Serialize explicit opt-in authority; this grants no acceptance or migration."""
    from .sealed_history_authority import loaded_backend

    require(
        base.get("schema") == CONFIG_SCHEMA,
        "Original explicit retained config required",
    )
    require(
        session_revocations is None or type(session_revocations) is dict,
        "Session-revocation pins must be an exact mapping",
    )
    for item in (
        (history, authority_head)
        if compact_prefix is None
        else (history, authority_head, compact_prefix)
    ):
        require(
            type(item) is dict and set(item) == {"path", "sha256"},
            "Exact sealed operator pin required",
        )
        pinned_json(absolute_path(item["path"]), item["sha256"])
    if history_integrity is not None:
        require(type(history_integrity) is dict
                and set(history_integrity) in ({"base", "ledger_directory"},
                    {"base", "ledger_directory", "runtime_source_admission"}),
                "Exact explicit managed history choice required")
        accepted_base = history_integrity["base"]
        require(type(accepted_base) is dict and set(accepted_base) == {"path", "sha256"},
                "Exact Root-selected accepted history base pin required")
        pinned_json(absolute_path(accepted_base["path"]), accepted_base["sha256"],
                    max_bytes=32*1024*1024)
        private_directory(absolute_path(history_integrity["ledger_directory"]))
        if "runtime_source_admission" in history_integrity:
            item = history_integrity["runtime_source_admission"]
            require(type(item) is dict and set(item) == {"path", "sha256"},
                    "Exact Root runtime Source-upgrade admission pin required")
            pinned_json(absolute_path(item["path"]), item["sha256"])
    return json.loads(json.dumps(base)) | {
        "schema": SEALED_CONFIG_SCHEMA,
        "sealed_history": dict(history),
        "authority_head": dict(authority_head),
        "authority_backend": loaded_backend(),
        "session_revocations": {}
        if session_revocations is None
        else dict(session_revocations),
        **({} if compact_prefix is None else {"compact_prefix": dict(compact_prefix)}),
        **({} if history_integrity is None
           else {"history_integrity": json.loads(json.dumps(history_integrity))}),
        "code_pins": {
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name)
            for name in (*SEALED_CODE_MODULES,
                         *(MANAGED_HISTORY_CODE_MODULES if history_integrity is not None else ()),
                         *retained_native_files(sealed=True))
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
        owned_writer_lock_fd=None,
    ):
        self._integrity_lock = threading.RLock()
        self.path = absolute_path(str(config_path))
        private_directory(self.path.parent)
        self.expected_sha256 = expected_sha256
        self.repository = Path(repository).absolute()
        self.config = pinned_json(self.path, expected_sha256)
        self.sealed = self.config.get("schema") == SEALED_CONFIG_SCHEMA
        require(
            set(self.config)
            == {
                "schema",
                "accepted_library",
                "company_lifetime",
                "workroom_binding",
                "code_pins",
            }
            | (
                {
                    "sealed_history",
                    "authority_head",
                    "authority_backend",
                    "session_revocations",
                }
                | ({"compact_prefix"} if "compact_prefix" in self.config else set())
                | ({"history_integrity"} if "history_integrity" in self.config else set())
                if self.sealed
                else set()
            )
            and self.config["schema"] in {CONFIG_SCHEMA, SEALED_CONFIG_SCHEMA},
            "Exact retained-service schema required",
        )
        require(owned_writer_lock_fd is None
                or (self.sealed and "history_integrity" in self.config
                    and type(owned_writer_lock_fd) is int and owned_writer_lock_fd >= 0
                    and stat.S_ISREG(os.fstat(owned_writer_lock_fd).st_mode)),
                "Managed lifetime requires an actual ordinary owned writer descriptor")
        self._owned_writer_lock_fd = owned_writer_lock_fd
        if "history_integrity" in self.config:
            history_choice = self.config["history_integrity"]
            require(type(history_choice) is dict
                    and set(history_choice) in ({"base", "ledger_directory"},
                        {"base", "ledger_directory", "runtime_source_admission"})
                    and type(history_choice["base"]) is dict
                    and set(history_choice["base"]) == {"path", "sha256"},
                    "Exact operator-selected managed history configuration required")
            pinned_json(absolute_path(history_choice["base"]["path"]),
                        history_choice["base"]["sha256"], max_bytes=32*1024*1024)
            private_directory(absolute_path(history_choice["ledger_directory"]))
            if "runtime_source_admission" in history_choice:
                item = history_choice["runtime_source_admission"]
                require(type(item) is dict and set(item) == {"path", "sha256"},
                        "Exact Root runtime Source-upgrade admission pin required")
                pinned_json(absolute_path(item["path"]), item["sha256"])
        self.check_code()
        source = self.config["accepted_library"]
        require(
            isinstance(source, dict)
            and set(source) == {f.name for f in fields(AcceptedLibrary)},
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
        self.binding_path, self.binding_sha256 = (
            absolute_path(choice["path"]),
            choice["sha256"],
        )
        self.binding = pinned_json(self.binding_path, self.binding_sha256)
        require(
            set(self.binding) == BINDING_FIELDS
            and self.binding["schema"] == BINDING_SCHEMA,
            "Exact retained-workroom binding required",
        )
        self.root = absolute_path(self.binding["audit_root"])
        require(
            self.root == Path(private_root).absolute(),
            "Selected existing workroom differs",
        )
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
        self.sealed_store = None
        if self.sealed:
            from .sealed_history_store import SealedHistoryStore

            item = self.config["sealed_history"]
            require(
                type(item) is dict and set(item) == {"path", "sha256"},
                "Exact externally pinned sealed journal required",
            )
            self.sealed_store = SealedHistoryStore(
                self.root,
                absolute_path(item["path"]),
                item["sha256"],
                authority_head=self.config["authority_head"],
                session_revocations=self.config["session_revocations"],
                compact_prefix=self.config.get("compact_prefix"),
            )
            require(
                self.sealed_store.prefix["engagement"] == self.engagement,
                "Sealed original engagement differs",
            )
        self.verify_workroom()
        # Do not construct a raw CompanyStore: the accepted lifetime supplies the
        # only company connection and retains its existing grant/clock checks.
        self.engine = RetainedEngine(
            self.root,
            repository=self.repository,
            program_pack=self.pack_path,
            inference_config=inference_config,
            voice_config=voice_config,
            _store=self.sealed_store,
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
        if self.sealed:
            from .sealed_retained_service import finish_startup

            finish_startup(self)
            return
        # Construction/config/source verification must all succeed before the
        # exact Store can inherit integrity metadata from the original scan.
        candidate, identity = self._pending_history
        published = publish_validated_history(
            self.engine.store,
            self.binding["identities"]["operator"],
            self.engagement,
            candidate,
            identity,
        )
        self._retained_integrity = (
            {"history": candidate, "stamp": identity, **self._pending_custody}
            if published
            else None
        )
        self.engine.store._retained_typed_stamp = (
            identity if journal_stamp(self.engine.store.db_path) == identity else None
        )
        del self._pending_history
        del self._pending_custody

    @classmethod
    def prepare_history_metadata_context(
        cls, config_path, expected_sha256, *, private_root, repository,
        prospective_code_pins, root_authorized=False, owned_writer_lock_fd=None,
    ):
        """Root-only exact setup prefix, no history/Engine/certificate publication.

        The supplied baseline config remains byte-exact. The prospective map
        closes only its two additional Source origins for later metadata/base
        selection; it is not a new config, Main adoption or runtime admission.
        """
        require(root_authorized is True,
                "Separate actual Root metadata-context authorization required")
        self = cls.__new__(cls)
        self._integrity_lock = threading.RLock()
        self.path = absolute_path(str(config_path))
        private_directory(self.path.parent)
        self.expected_sha256 = expected_sha256
        self.repository = Path(repository).absolute()
        self.config = pinned_json(self.path, expected_sha256)
        self.sealed = self.config.get("schema") == SEALED_CONFIG_SCHEMA
        require(
            set(self.config)
            == {
                "schema",
                "accepted_library",
                "company_lifetime",
                "workroom_binding",
                "code_pins",
            }
            | (
                {
                    "sealed_history",
                    "authority_head",
                    "authority_backend",
                    "session_revocations",
                }
                | ({"compact_prefix"} if "compact_prefix" in self.config else set())
                | ({"history_integrity"} if "history_integrity" in self.config else set())
                if self.sealed
                else set()
            )
            and self.config["schema"] in {CONFIG_SCHEMA, SEALED_CONFIG_SCHEMA},
            "Exact retained-service schema required",
        )
        require(owned_writer_lock_fd is None
                or (self.sealed
                    and type(owned_writer_lock_fd) is int and owned_writer_lock_fd >= 0
                    and stat.S_ISREG(os.fstat(owned_writer_lock_fd).st_mode)),
                "Managed lifetime requires an actual ordinary owned writer descriptor")
        self._owned_writer_lock_fd = owned_writer_lock_fd
        if "history_integrity" in self.config:
            history_choice = self.config["history_integrity"]
            require(type(history_choice) is dict
                    and set(history_choice) in ({"base", "ledger_directory"},
                        {"base", "ledger_directory", "runtime_source_admission"})
                    and type(history_choice["base"]) is dict
                    and set(history_choice["base"]) == {"path", "sha256"},
                    "Exact operator-selected managed history configuration required")
            pinned_json(absolute_path(history_choice["base"]["path"]),
                        history_choice["base"]["sha256"], max_bytes=32*1024*1024)
            private_directory(absolute_path(history_choice["ledger_directory"]))
            if "runtime_source_admission" in history_choice:
                item = history_choice["runtime_source_admission"]
                require(type(item) is dict and set(item) == {"path", "sha256"},
                        "Exact Root runtime Source-upgrade admission pin required")
                pinned_json(absolute_path(item["path"]), item["sha256"])
        self.check_code()
        source = self.config["accepted_library"]
        require(
            isinstance(source, dict)
            and set(source) == {f.name for f in fields(AcceptedLibrary)},
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
        self.binding_path, self.binding_sha256 = (
            absolute_path(choice["path"]),
            choice["sha256"],
        )
        self.binding = pinned_json(self.binding_path, self.binding_sha256)
        require(
            set(self.binding) == BINDING_FIELDS
            and self.binding["schema"] == BINDING_SCHEMA,
            "Exact retained-workroom binding required",
        )
        self.root = absolute_path(self.binding["audit_root"])
        require(
            self.root == Path(private_root).absolute(),
            "Selected existing workroom differs",
        )
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
        self.sealed_store = None
        if self.sealed:
            from .sealed_history_store import SealedHistoryStore

            item = self.config["sealed_history"]
            require(
                type(item) is dict and set(item) == {"path", "sha256"},
                "Exact externally pinned sealed journal required",
            )
            self.sealed_store = SealedHistoryStore(
                self.root,
                absolute_path(item["path"]),
                item["sha256"],
                authority_head=self.config["authority_head"],
                session_revocations=self.config["session_revocations"],
                compact_prefix=self.config.get("compact_prefix"),
            )
            require(
                self.sealed_store.prefix["engagement"] == self.engagement,
                "Sealed original engagement differs",
            )
        require(self.sealed and "history_integrity" not in self.config,
                "Unmanaged sealed baseline config required before initial base issuance")
        if owned_writer_lock_fd is not None:
            lock_path = absolute_path(str(self.root.parent / "room.lock"))
            actual_lock = lock_path.stat()
            held_lock = os.fstat(owned_writer_lock_fd)
            require(stat.S_ISREG(actual_lock.st_mode) and actual_lock.st_nlink == 1
                    and actual_lock.st_uid == os.getuid()
                    and same_file_identity(held_lock, actual_lock)
                    and held_lock.st_uid == actual_lock.st_uid
                    and held_lock.st_gid == actual_lock.st_gid,
                    "Root metadata held descriptor must match the actual owned room lock")
        baseline = self.config["code_pins"]
        require(type(prospective_code_pins) is dict
                and set(prospective_code_pins) == set(baseline) | set(MANAGED_HISTORY_CODE_MODULES)
                and not set(baseline) & set(MANAGED_HISTORY_CODE_MODULES)
                and all(prospective_code_pins[name] == value for name, value in baseline.items()),
                "Prospective Source map must preserve baseline and add exactly two modules")
        self.history_metadata_source_map = json.loads(json.dumps(prospective_code_pins))
        self.check_history_metadata_sources()
        return self

    def check_history_metadata_sources(self):
        """Reclose only two explicitly selected metadata-only Source origins."""
        selected = self.history_metadata_source_map
        baseline = self.config["code_pins"]
        require(type(selected) is dict
                and set(selected) == set(baseline) | set(MANAGED_HISTORY_CODE_MODULES)
                and not set(baseline) & set(MANAGED_HISTORY_CODE_MODULES)
                and all(selected[name] == value for name, value in baseline.items()),
                "Explicit prospective map differs from exact baseline plus two modules")
        for name in MANAGED_HISTORY_CODE_MODULES:
            expected = selected[name]
            require(type(expected) is str and re.fullmatch(r"[a-f0-9]{64}", expected),
                    "Exact prospective Source SHA256 required")
            path = self.repository / "enterprise/audit_suite" / name
            absolute_path(str(path))
            opening = path.stat()
            module_name = "enterprise.audit_suite." + name.removesuffix(".py")
            loaded = sys.modules.get(module_name)
            if loaded is None:
                loaded = importlib.import_module(module_name)
            origin = getattr(getattr(loaded, "__spec__", None), "origin", None)
            require(path.is_file() and origin is not None
                    and Path(origin).resolve() == path.resolve()
                    and Path(loaded.__file__).resolve() == path.resolve()
                    and file_sha(path) == expected
                    and same_file_identity(path.stat(), opening),
                    "Prospective metadata Source bytes/load origin changed")

    def check_code(self):
        """Bind file pins to loaded module origins in this ordinary local process.

        This is not a hostile-process sandbox or an attestation of mutable
        interpreter memory. Operator configuration is pinned before startup.
        """
        pins = self.config["code_pins"]
        require(
            isinstance(pins, dict)
            and set(pins)
            == set(SEALED_CODE_MODULES if self.sealed else CODE_MODULES)
            | set(MANAGED_HISTORY_CODE_MODULES if "history_integrity" in self.config else ())
            | set(retained_native_files(sealed=self.sealed)),
            "Exact retained service/engine/runtime module pins required",
        )
        for name, expected in pins.items():
            path = self.repository / "enterprise/audit_suite" / name
            native_files = retained_native_files(sealed=self.sealed)
            if name in native_files:
                native_path = native_files[name]
                require(
                    not any(p.is_symlink() for p in [path, *path.parents])
                    and path.is_file()
                    and native_path.resolve() == path.resolve()
                    and file_sha(path) == expected,
                    "Pinned native validator code changed or loaded origin differs",
                )
                continue
            module_name = "enterprise.audit_suite." + name.removesuffix(".py")
            loaded = sys.modules.get(module_name)
            if name == "__main__.py":
                entry = sys.modules.get("__main__")
                if (
                    getattr(getattr(entry, "__spec__", None), "name", None)
                    == module_name
                ):
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
        if self.sealed:
            from .sealed_history_authority import loaded_backend

            require(
                digest(self.config["authority_backend"]) == digest(loaded_backend()),
                "Operator signature backend version/ABI/loaded origins changed",
            )

    def _verify_memberships(self, audit_db):
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
                for row in audit_db.execute("SELECT principal,permission FROM members")
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
            principal = audit_db.execute(
                "SELECT roles FROM principals WHERE id=?", (person,)
            ).fetchone()
            member = audit_db.execute(
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
        return identities

    def verify_workroom(self):
        if self.sealed:
            from .sealed_retained_service import verify_sealed

            return verify_sealed(self)
        path = self.root / "engagements.sqlite3"
        private_file(path)
        outside_identity = journal_stamp(path)
        previous_proof = getattr(self, "_retained_integrity", None)
        # Open only the existing database. Reserve the audit writer before any
        # read, then forbid all SQL mutations for this validation transaction.
        # Normal SQLite closing may remove its own empty WAL/SHM. This is
        # query-only SQL with the normal journal lifecycle, not immutable
        # filesystem access or schema initialization.
        with closing(sqlite3.connect(f"file:{path}?mode=rw", uri=True)) as audit_db:
            audit_db.row_factory = sqlite3.Row
            audit_db.execute("BEGIN IMMEDIATE")
            audit_db.execute("PRAGMA query_only=ON")
            schema_sha256 = digest(
                [
                    dict(row)
                    for row in audit_db.execute(
                        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
                    )
                ]
            )
            if previous_proof is None:
                require(
                    audit_db.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                    "Existing workroom database integrity failed",
                )
            else:
                require(
                    schema_sha256 == previous_proof["schema_sha256"],
                    "Previously verified workroom schema changed",
                )
            require(
                not audit_db.execute("PRAGMA foreign_key_check").fetchall(),
                "Existing workroom foreign-key integrity failed",
            )
            require(
                {row[0] for row in audit_db.execute("SELECT id FROM engagements")}
                == {self.engagement},
                "Exactly one retained workroom engagement required",
            )
            with self.world.locked():
                self.world.verify()
                native = native_rows(self.world.database)
                require(
                    _time(self.world.initialization["initialized_at"])
                    <= _time(time_to_iso())
                    and all(
                        _time(value["imported_at"]) <= _time(time_to_iso())
                        for value in native.values()
                    ),
                    "Company real import clock is in the future",
                )
                with quiescent_read(self.world.database) as source_db:
                    journal = {
                        value["command_id"]: json.loads(value["receipt"])
                        for value in source_db.execute(
                            "SELECT command_id,receipt FROM collections"
                        )
                    }
                verified, verified_files, custody = set(), {}, {}
                if previous_proof is not None:
                    verified_files.update(
                        self._verify_integrity_descriptors(
                            previous_proof, native, journal
                        )
                    )
                    custody.update(previous_proof["custody"])
                previous_clock, previous_real = None, 0

                def validate_original(event, state, prior_header=None):
                    nonlocal previous_clock, previous_real
                    if prior_header is not None:
                        require(
                            prior_header["scope_sha256"]
                            == digest(self.binding["scope"]),
                            "Previously verified retained scope descriptor differs",
                        )
                        require(
                            prior_header["company_binding_sha256"]
                            in {digest(None), digest(self.selected)},
                            "Previously verified company binding descriptor differs",
                        )
                        state = {
                            name: prior_header[name]
                            for name in ("id", "mode", "simulated_at")
                        } | {
                            "company_source_binding": (
                                None
                                if prior_header["company_binding_sha256"]
                                == digest(None)
                                else self.selected
                            ),
                            "artifacts": [],
                            "scope": self.binding["scope"],
                        }
                    real = event["recorded_at"]
                    clock = _time(state["simulated_at"])
                    require(
                        type(real) in (int, float)
                        and math.isfinite(real)
                        and previous_real <= real <= time.time()
                        and (previous_clock is None or previous_clock <= clock),
                        "Workroom actual/simulated clock chronology changed",
                    )
                    require(
                        state["id"] == self.engagement
                        and state["mode"] == self.binding["mode"],
                        "Retained engagement identity/mode differs",
                    )
                    require(
                        type(state.get("scope")) is dict
                        and digest(state["scope"]) == digest(self.binding["scope"]),
                        "Historical retained workroom scope differs",
                    )
                    if state.get("company_source_binding") is not None:
                        require(
                            state["company_source_binding"] == self.selected,
                            "Historical company branch binding changed",
                        )
                    self.verify_artifacts(
                        state,
                        native,
                        verified=verified,
                        journal=journal,
                        files=verified_files,
                        custody=custody,
                    )
                    previous_clock, previous_real = clock, real

                history, candidate, identity = scan_validated_history(
                    audit_db,
                    path,
                    self.engagement,
                    revisions=[0],
                    row_validator=validate_original,
                    previous_integrity=(
                        None if previous_proof is None else previous_proof["history"]
                    ),
                )
                # Fresh closing native verification under the same source lock.
                # A failure prevents publication of every candidate digest.
                self.world.verify()
                for original, (identity, sha256, size) in verified_files.items():
                    private_file(original)
                    require(
                        same_file_identity(original.stat(), identity)
                        and original.stat().st_size == size
                        and file_sha(original) == sha256,
                        "Retained original changed during complete validation",
                    )
            initial = history["selected"][0]["state"]
            current = history["latest"]["state"]
            identities = self._verify_memberships(audit_db)
            require(
                initial["created_by"] == identities["operator"]
                and digest(initial["scope"]) == digest(self.binding["scope"])
                and initial["mode"] == self.binding["mode"]
                and _time(initial["simulated_at"])
                == _time(self.binding["initial_simulated_at"])
                and type(self.binding["task_count"]) is int
                and self.binding["task_count"] == len(initial["tasks"]) > 0
                and self.binding["zero_workroom_counts"]
                == {k: 0 for k in EMPTY_WORKROOM}
                and all(
                    type(self.binding["zero_workroom_counts"][k]) is int
                    for k in EMPTY_WORKROOM
                )
                and all(isinstance(initial[k], list) for k in EMPTY_WORKROOM)
                and not any(initial[k] for k in EMPTY_WORKROOM)
                and all(
                    t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                    for t in initial["tasks"]
                ),
                "Original fresh-workroom birth binding differs",
            )
            require(
                current.get("company_source_binding") == self.selected
                and current.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION"
                and current["phase"] in {"READY", "ACTIVE", "CLOSED"},
                "Retained workroom must have an activated exact company binding",
            )
            self._pending_history = candidate, outside_identity
            self._pending_custody = {
                "files": {
                    str(original): {"sha256": sha256, "bytes": size}
                    for original, (_identity, sha256, size) in verified_files.items()
                },
                "custody": custody,
                "schema_sha256": schema_sha256,
            }
        # Like inspect_history, bind the complete invocation to unchanged outer
        # file identities and its separately checked inner read transaction.
        # SQLite may create and remove its own empty WAL/SHM during connection
        # lifetime; preexisting/externally changed sidecars never get normalized.
        require(
            journal_stamp(path) == outside_identity,
            "Journal changed during retained closure",
        )

    def verify_artifacts(
        self, state, native, *, verified=None, journal=None, files=None, custody=None
    ):
        for artifact in state["artifacts"]:
            representation = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
            if verified is not None and representation in verified:
                continue
            path = self.root / "artifacts" / artifact["sha256"]
            require(
                re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"]),
                "Retained artifact hash differs",
            )
            require(
                type(artifact["bytes"]) is int and artifact["bytes"] >= 0,
                "Strict nonnegative retained artifact byte count required",
            )
            private_file(path)
            prior_file = None if files is None else files.get(path)
            if prior_file is None:
                require(
                    file_sha(path) == artifact["sha256"]
                    and path.stat().st_size == artifact["bytes"],
                    "Retained artifact bytes changed",
                )
            else:
                # This invocation has already freshly hashed this exact file.
                # Its closing full hash still covers every historical member.
                require(
                    same_file_identity(path.stat(), prior_file[0])
                    and prior_file[1:] == (artifact["sha256"], artifact["bytes"]),
                    "Retained artifact bytes changed",
                )
            if files is not None:
                files.setdefault(
                    path, (path.stat(), artifact["sha256"], artifact["bytes"])
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
            if custody is not None:
                descriptor = {
                    "receipt_sha256": digest(receipt),
                    "native_id": tuple(source[k] for k in NATIVE_ID),
                    "native_metadata_sha256": digest(CompanyStore._metadata(row)),
                }
                previous = custody.setdefault(receipt["command_id"], descriptor)
                require(
                    previous == descriptor,
                    "Historical collection custody descriptor differs",
                )
            if verified is not None:
                verified.add(representation)

    def _verify_integrity_descriptors(self, proof, native, journal):
        """Fresh every historical original/custody, including absent current artifacts.

        The prior proof holds only file and native locators, byte/metadata hashes
        and sizes. No receipt, source body or examination outcome is retained.
        """
        files = {}
        for name, descriptor in proof["files"].items():
            path = Path(name)
            require(
                path == self.root / "artifacts" / descriptor["sha256"],
                "Historical original file locator differs",
            )
            private_file(path)
            initial = path.stat()
            require(
                initial.st_size == descriptor["bytes"]
                and file_sha(path) == descriptor["sha256"]
                and same_file_identity(path.stat(), initial),
                "Retained artifact bytes changed in historical original",
            )
            files[path] = (initial, descriptor["sha256"], descriptor["bytes"])
        for command_id, descriptor in proof["custody"].items():
            row = native.get(descriptor["native_id"])
            saved = journal.get(command_id)
            require(
                row is not None
                and saved is not None
                and digest(CompanyStore._metadata(row))
                == descriptor["native_metadata_sha256"]
                and digest(saved) == descriptor["receipt_sha256"],
                "Historical native collection integrity descriptor differs",
            )
        return files

    def refresh_integrity(self, actor):
        """Fresh protected-call integrity; never evidence or outcome memoization.

        An unchanged physical journal can reuse its complete validated history
        proof, while current membership, native originals, retained original
        files and saved receipt hashes are all rechecked. After any stamp
        change, every old state and command byte is freshly streamed and hashed;
        only exactly identical canonical state representations reuse their
        previously validated identity/clock metadata. New/changed/legacy rows
        undergo the original complete semantic and native validation.
        """
        # Pending cursor descriptors belong to one protected invocation. A
        # concurrent request cannot publish another invocation's candidate.
        with self._integrity_lock:
            self._refresh_integrity(actor)

    def _refresh_integrity(self, actor):
        if self.sealed:
            from .sealed_retained_service import read_sealed

            managed = getattr(self.sealed_store, "_managed_history_integrity", None)
            if managed is not None and not managed.force_full:
                managed.validate_current(actor, self.engagement)
            else:
                read_sealed(self, actor, ())
            return
        self.check_pins()
        proof = self._retained_integrity
        path = self.root / "engagements.sqlite3"
        outside = journal_stamp(path)
        if proof is None or proof["stamp"] != outside:
            self.verify_workroom()
            self.check_pins()
            candidate, identity = self._pending_history
            published = publish_validated_history(
                self.engine.store, actor, self.engagement, candidate, identity
            )
            require(
                candidate is None or published,
                "Journal changed before integrity publication",
            )
            self._retained_integrity = (
                {"history": candidate, "stamp": identity, **self._pending_custody}
                if published
                else None
            )
            self.engine.store._retained_typed_stamp = identity
            del self._pending_history
            del self._pending_custody
            return
        with closing(sqlite3.connect(f"file:{path}?mode=rw", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            db.execute("PRAGMA query_only=ON")
            self.engine.store._authorize(db, actor, self.engagement)
            inside = journal_stamp(path)
            self._verify_memberships(db)
            row = db.execute(
                "SELECT revision,state FROM engagements WHERE id=?", (self.engagement,)
            ).fetchone()
            require(
                row is not None
                and row["revision"] == proof["history"]["count"] - 1
                and hashlib.sha256(row["state"].encode()).hexdigest()
                == proof["history"]["current_raw_sha256"],
                "Current retained engagement differs",
            )
            current = json.loads(row["state"])
            require(
                type(current.get("scope")) is dict
                and digest(current["scope"]) == digest(self.binding["scope"]),
                "Current retained workroom scope differs",
            )
            require(
                current["id"] == self.engagement
                and current["mode"] == self.binding["mode"]
                and current.get("company_source_binding") == self.selected,
                "Current company binding differs",
            )
            with self.world.locked():
                self.world.verify()
                native = native_rows(self.world.database)
                with quiescent_read(self.world.database) as source_db:
                    journal = {
                        value["command_id"]: json.loads(value["receipt"])
                        for value in source_db.execute(
                            "SELECT command_id,receipt FROM collections"
                        )
                    }
                originals = self._verify_integrity_descriptors(proof, native, journal)
                self.verify_artifacts(current, native, journal=journal, files=originals)
                self.world.verify()
                for original, (identity, sha256, size) in originals.items():
                    private_file(original)
                    require(
                        same_file_identity(original.stat(), identity)
                        and original.stat().st_size == size
                        and file_sha(original) == sha256,
                        "Historical original changed during protected validation",
                    )
            self.engine.store._authorize(db, actor, self.engagement)
            require(
                journal_stamp(path) == inside,
                "Journal changed during protected validation",
            )
        require(
            journal_stamp(path) == outside, "Journal changed during protected closure"
        )
        self.check_pins()

    def close_protected_read(self, actor, expected_stamp):
        """Close one private response over its exact validated journal boundary."""
        with self._integrity_lock:
            require(
                expected_stamp is not None
                and self.engine.store._retained_typed_stamp == expected_stamp
                and self.integrity_stamp() == expected_stamp,
                "Journal changed before private response closure",
            )
            self._refresh_integrity(actor)
            require(
                self.engine.store._retained_typed_stamp == expected_stamp
                and self.integrity_stamp() == expected_stamp,
                "Journal changed during private response closure",
            )

    def integrity_stamp(self):
        if self.sealed:
            return self.sealed_store.check_prefix(), journal_stamp(
                self.sealed_store.db_path
            )
        return journal_stamp(self.engine.store.db_path)

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
        if self.sealed and self.sealed_store is not None:
            require(
                self.sealed_store.authority_head == self.config["authority_head"],
                "Signed authority head needs a new exact operator configuration",
            )
            self.sealed_store.check_prefix()
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
            self.pack_path,
            self.binding["program_pack"]["sha256"],
            max_bytes=32 * 1024 * 1024,
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
                "Route unavailable in this retained workroom",
                code="FORBIDDEN",
                status=403,
            )


def time_to_iso():
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="microseconds")


def create_retained_app(
    private_root, config_path, expected_sha256, *, repository, **options
):
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
    app.state.retained_workroom = retained
    return app
