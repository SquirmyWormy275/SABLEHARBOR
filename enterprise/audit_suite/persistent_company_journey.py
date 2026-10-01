"""Shared append-only company lifetime, separate from disposable audit workrooms.

This candidate requires its own independent runtime/source-operation acceptance.
The previously accepted frozen-library adapter gate cannot authorize evolution.
A deliberately restricted neutral engineering mode cannot admit Sable Harbor data.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _id, _json, _time
from .engine import Engine
from .fresh_sec003_procedure import NATIVE_ID, require
from .source_library_audit import (
    EMPTY_WORKROOM,
    AcceptedLibrary,
    BusinessRoute,
    LibraryAudit,
    QuiescentCompanyStore,
    file_sha,
    ordinary_copy,
    private_file,
    quiescent_read,
    schema_sha,
    typed_content,
)

RUNTIME_SCHEMA = "SH_ROOT_PERSISTENT_COMPANY_RUNTIME_REVIEW_V1"
RUNTIME_VERDICT = "PASS_SHARED_APPEND_ONLY_COMPANY_RUNTIME_SELECTED_BOUNDARY"
OPERATION_SCHEMA = "SH_ROOT_COMPANY_SOURCE_OPERATION_REVIEW_V1"
OPERATION_VERDICT = "PASS_COMPANY_OWNED_APPEND_OPERATION_SELECTED_BOUNDARY"
OPERATION_FIELDS = {
    "company",
    "branch",
    "system",
    "record",
    "expected_version",
    "command_id",
    "event_at",
    "available_at",
    "content_sha256",
    "provenance",
    "origin",
}


def validate_operation(operation, content, predecessor=None):
    """The same exact operation contract governs live admission and custody replay."""
    require(
        isinstance(operation, dict)
        and set(operation) == OPERATION_FIELDS
        and isinstance(content, bytes)
        and 0 < len(content) <= 25 * 1024 * 1024
        and hashlib.sha256(content).hexdigest() == operation["content_sha256"],
        "Exact approved source-operation fields/bytes required",
    )
    for key in (*NATIVE_ID[:4], "command_id"):
        _id(operation[key])
    require(
        type(operation["expected_version"]) is int and operation["expected_version"] >= 0,
        "Strict integer source predecessor version required",
    )
    require(
        operation["origin"]
        in {
            "AUTHORED_TRAINING_SOURCE",
            "MIGRATED_SYNTHETIC_HISTORY",
            "REPOSITORY_SYNTHETIC_DOCUMENT",
        }
        and isinstance(operation["provenance"], dict)
        and operation["provenance"].get("source_reference")
        and len(_json(operation["provenance"]).encode()) <= 65536,
        "Explicit synthetic origin and bounded source provenance required",
    )
    event, available = _time(operation["event_at"]), _time(operation["available_at"])
    require(event <= available, "Source publication cannot precede business event")
    typed_content({**operation, "sha256": operation["content_sha256"], "content": content})
    if predecessor is not None:
        require(
            type(predecessor["version"]) is int
            and operation["expected_version"] == predecessor["version"]
            and all(operation[key] == predecessor[key] for key in NATIVE_ID[:4])
            and predecessor["event_at"] is not None
            and event >= _time(predecessor["event_at"])
            and available >= _time(predecessor["available_at"]),
            "Exact current predecessor and nonretroactive correction chronology required",
        )
    return event, available


def now():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def write(path, data):
    raw = data if isinstance(data, bytes) else (_json(data) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    private_file(path)


def native_rows(path):
    """Complete custody rows, including immutable command/input digests and bytes."""
    with quiescent_read(path) as db:
        return {
            tuple(row[key] for key in NATIVE_ID): {**dict(row), "content": row["content"].hex()}
            for row in db.execute(
                "SELECT * FROM versions ORDER BY company,branch,system,record,version"
            )
        }


def rows_sha(rows):
    return hashlib.sha256(_json([rows[key] for key in sorted(rows)]).encode()).hexdigest()


def registered_systems(path):
    with quiescent_read(path) as db:
        return [
            list(row) for row in db.execute("SELECT * FROM systems ORDER BY company,branch,system")
        ]


def neutral_boundary(rows):
    return (
        rows
        and all(key[0].startswith("NEUTRAL-") for key in rows)
        and all(
            json.loads(bytes.fromhex(row["content"])).get("engineering_neutral_fixture") is True
            for row in rows.values()
        )
    )


@dataclass(frozen=True)
class CompanyOperator:
    """Trusted in-process capability, never an auditor-controlled actor parameter."""

    principal: str


class SharedCompanyStore(QuiescentCompanyStore):
    """Serialize normal DELETE-journal operations; reject unaccepted sidecar views."""

    def __init__(self, world):
        self.world = world
        super().__init__(world.root)

    @contextmanager
    def _db(self):
        with self.world.locked():
            if self.world.ready and not self.world.writing:
                self.world.require_runtime()
                self.world.verify()
            with super()._db() as db:
                yield db
            if self.world.ready and not self.world.writing:
                self.world.require_runtime()
                self.world.verify()

    def append_version(self, *args, **kwargs):
        require(self.world.writing, "Company-owned approved append operation required")
        return super().append_version(*args, **kwargs)

    def register_system(self, *args, **kwargs):
        raise ValueError("Successor runtime does not admit new system registrations")


class PersistentCompany:
    """One company source root, initialized independently before any Engine exists.

    Checkpoints are immutable externally pinned custody, not self-authorized source
    acceptance. Reopening requires the operator's exact latest checkpoint hash.
    Grants/collection journals may persist; business source versions never change.
    """

    @classmethod
    def initialize(cls, accepted, root, *, operator_id, engineering_only=False):
        require(type(engineering_only) is bool, "Explicit engineering boundary required")
        pins = accepted.verify()
        root = Path(root).absolute()
        require(not root.exists(), "New independent company lifetime required")
        require(
            not any(p.is_symlink() for p in [root, *root.parents])
            and stat.S_IMODE(root.parent.stat().st_mode) == 0o700,
            "Private unaliased company parent required",
        )
        rows = native_rows(accepted.database)
        if engineering_only:
            require(
                neutral_boundary(rows),
                "Neutral engineering mode cannot admit actual company sources",
            )
        root.mkdir(mode=0o700)
        (root / "operations").mkdir(mode=0o700)
        ordinary_copy(accepted.database, root / "company.sqlite3")
        write(root / "LOCK", b"")
        initialization = {
            "schema": "SH_PERSISTENT_COMPANY_INITIALIZATION_V1",
            "accepted_baseline_pins": pins,
            "baseline_native_rows_sha256": rows_sha(rows),
            "schema_sha256": schema_sha(accepted.database),
            "systems_sha256": hashlib.sha256(
                _json(registered_systems(accepted.database)).encode()
            ).hexdigest(),
            "operator_id": _id(operator_id),
            "initialized_at": now(),
            "engineering_only": engineering_only,
            "audit_engagements_at_initialization": 0,
        }
        write(root / "INITIALIZATION.json", initialization)
        checkpoint = {
            "schema": "SH_PERSISTENT_COMPANY_CHECKPOINT_V1",
            "initialization_sha256": file_sha(root / "INITIALIZATION.json"),
            "previous_checkpoint_sha256": None,
            "operations": [],
            "native_versions": len(rows),
            "native_rows_sha256": rows_sha(rows),
        }
        path = root / "CHECKPOINT-000000.json"
        write(path, checkpoint)
        return cls(accepted, root, path, file_sha(path))

    def __init__(
        self, accepted: AcceptedLibrary, root, checkpoint, checkpoint_sha256, *, read_only=False
    ):
        self.accepted, self.pins = accepted, accepted.verify()
        self.root = Path(root).absolute()
        require(
            self.root.is_dir()
            and stat.S_IMODE(self.root.stat().st_mode) == 0o700
            and not any(p.is_symlink() for p in [self.root, *self.root.parents]),
            "Private persistent company root required",
        )
        self.database = self.root / "company.sqlite3"
        self.checkpoint, self.checkpoint_sha256 = Path(checkpoint), checkpoint_sha256
        self._mutex = threading.RLock()
        self._local = threading.local()
        self.ready = False
        self.writing = False
        self.read_only = read_only
        self.runtime_acceptance = None
        private_file(self.root / "LOCK")
        self.verify()
        self.operator = CompanyOperator(self.initialization["operator_id"])
        self.store = None if read_only else SharedCompanyStore(self)
        self.ready = True
        self.verify()

    @contextmanager
    def locked(self):
        """Reentrant thread mutex plus advisory process lock, never delete sidecars."""
        with self._mutex:
            depth = getattr(self._local, "depth", 0)
            if not depth:
                private_file(self.root / "LOCK")
                self._local.fd = os.open(self.root / "LOCK", os.O_RDWR | os.O_NOFOLLOW)
                fcntl.flock(self._local.fd, fcntl.LOCK_EX)
            self._local.depth = depth + 1
            try:
                yield
            finally:
                self._local.depth -= 1
                if not self._local.depth:
                    fcntl.flock(self._local.fd, fcntl.LOCK_UN)
                    os.close(self._local.fd)

    def verify(self):
        """Allow only pinned baseline rows plus specifically receipted new versions."""
        with self.locked():
            require(self.accepted.verify() == self.pins, "Accepted baseline pins changed")
            private_file(self.checkpoint)
            require(
                self.checkpoint.parent == self.root
                and file_sha(self.checkpoint) == self.checkpoint_sha256,
                "Externally pinned current company checkpoint changed",
            )
            checkpoint = json.loads(self.checkpoint.read_bytes())
            private_file(self.root / "INITIALIZATION.json")
            require(
                checkpoint["schema"] == "SH_PERSISTENT_COMPANY_CHECKPOINT_V1"
                and checkpoint["initialization_sha256"]
                == file_sha(self.root / "INITIALIZATION.json"),
                "Company initialization custody changed",
            )
            initialization = json.loads((self.root / "INITIALIZATION.json").read_bytes())
            require(
                type(initialization["engineering_only"]) is bool
                and stat.S_IMODE((self.root / "operations").stat().st_mode) == 0o700
                and not (self.root / "operations").is_symlink(),
                "Private source-operation receipt directory and explicit runtime boundary required",
            )
            baseline, current = native_rows(self.accepted.database), native_rows(self.database)
            systems = registered_systems(self.database)
            require(
                initialization["accepted_baseline_pins"] == self.pins
                and initialization["baseline_native_rows_sha256"] == rows_sha(baseline)
                and initialization["schema_sha256"]
                == schema_sha(self.accepted.database)
                == schema_sha(self.database)
                and systems == registered_systems(self.accepted.database)
                and initialization["systems_sha256"]
                == hashlib.sha256(_json(systems).encode()).hexdigest(),
                "Exact accepted baseline/schema/immutable triggers changed",
            )
            require(
                all(current.get(key) == row for key, row in baseline.items()),
                "Accepted company history was changed or removed",
            )
            expected = dict(baseline)
            if initialization["engineering_only"]:
                require(
                    neutral_boundary(baseline),
                    "Neutral engineering mode cannot admit actual company baseline",
                )
            prefix_digests = {0: rows_sha(baseline)}
            previous_receipt = None
            for index, entry in enumerate(checkpoint["operations"], 1):
                require(
                    entry["name"] == f"OPERATION-{index:06d}.json",
                    "Exact append-operation receipt sequence required",
                )
                path = self.root / "operations" / entry["name"]
                require(path.parent == self.root / "operations", "Unsafe operation receipt path")
                private_file(path)
                require(
                    file_sha(path) == entry["sha256"], "Pinned source-operation receipt changed"
                )
                receipt = json.loads(path.read_bytes())
                row = receipt["native_row"]
                key = tuple(row[k] for k in NATIVE_ID)
                require(
                    receipt["schema"] == "SH_COMPANY_APPEND_OPERATION_RECEIPT_V1"
                    and receipt["operator_id"] == initialization["operator_id"]
                    and receipt["previous_operation_sha256"] == previous_receipt
                    and key not in expected
                    and current.get(key) == row
                    and _time(initialization["initialized_at"])
                    <= _time(receipt["authorized_at"])
                    <= _time(row["imported_at"])
                    <= _time(receipt["completed_at"])
                    <= _time(now()),
                    "Unaccepted source operation or actual import chronology",
                )
                operation = receipt["operation"]
                predecessors = [r for k, r in expected.items() if k[:4] == key[:4]]
                require(predecessors, "Correction requires an existing accepted native record")
                latest = max(predecessors, key=lambda r: r["version"])
                event, available = validate_operation(
                    operation, bytes.fromhex(row["content"]), latest
                )
                if initialization["engineering_only"]:
                    require(
                        row["company"].startswith("NEUTRAL-")
                        and json.loads(bytes.fromhex(row["content"]))["engineering_neutral_fixture"]
                        is True
                        and receipt["approval"]
                        == {
                            "engineering_only": True,
                            "operation_sha256": receipt["operation_sha256"],
                        },
                        "Neutral operation crossed its engineering boundary",
                    )
                else:
                    self.operation_approval(
                        operation,
                        initialization["operator_id"],
                        Path(receipt["approval"]["path"]),
                        receipt["approval"]["sha256"],
                    )
                require(
                    predecessors
                    and max(r["version"] for r in predecessors) == operation["expected_version"]
                    and all(row[k] == operation[k] for k in NATIVE_ID[:4])
                    and row["event_at"] == event
                    and row["available_at"] == available
                    and row["imported_at"] == _time(row["imported_at"])
                    and row["origin"] == operation["origin"]
                    and json.loads(row["provenance"]) == operation["provenance"]
                    and receipt["operation_sha256"]
                    == hashlib.sha256(_json(operation).encode()).hexdigest()
                    and hashlib.sha256(bytes.fromhex(row["content"])).hexdigest() == row["sha256"]
                    and row["sha256"] == operation["content_sha256"]
                    and row["input_digest"]
                    == hashlib.sha256(
                        _json(
                            [
                                list(key[:4]),
                                operation["expected_version"],
                                row["event_at"],
                                row["available_at"],
                                row["origin"],
                                json.loads(row["provenance"]),
                                row["sha256"],
                            ]
                        ).encode()
                    ).hexdigest()
                    and key[-1] == operation["expected_version"] + 1
                    and row["command_id"] == operation["command_id"],
                    "Append command, input digest or exact bytes changed",
                )
                expected[key] = row
                prefix_digests[index] = rows_sha(expected)
                previous_receipt = entry["sha256"]
            require(
                self.checkpoint.name == f"CHECKPOINT-{len(checkpoint['operations']):06d}.json",
                "Exact company checkpoint sequence required",
            )
            prior_pin = checkpoint["previous_checkpoint_sha256"]
            for count in range(len(checkpoint["operations"]) - 1, -1, -1):
                prior = self.root / f"CHECKPOINT-{count:06d}.json"
                private_file(prior)
                prior_body = json.loads(prior.read_bytes())
                require(
                    file_sha(prior) == prior_pin
                    and prior_body["schema"] == "SH_PERSISTENT_COMPANY_CHECKPOINT_V1"
                    and prior_body["initialization_sha256"] == checkpoint["initialization_sha256"]
                    and prior_body["operations"] == checkpoint["operations"][:count]
                    and prior_body["native_versions"] == len(baseline) + count
                    and prior_body["native_rows_sha256"] == prefix_digests[count],
                    "Immutable predecessor company checkpoint changed",
                )
                prior_pin = prior_body["previous_checkpoint_sha256"]
            require(prior_pin is None, "Baseline checkpoint must have no predecessor")
            require(
                expected == current
                and checkpoint["native_versions"] == len(current)
                and checkpoint["native_rows_sha256"] == rows_sha(current),
                "Unreceipted company change or source sequence gap",
            )
            self.initialization = initialization
            return checkpoint

    def accept_runtime(self, review, expected_sha256):
        private_file(review)
        require(file_sha(review) == expected_sha256, "Independent runtime review pin changed")
        data = json.loads(review.read_bytes())
        require(
            data.get("schema") == RUNTIME_SCHEMA
            and data.get("verdict") == RUNTIME_VERDICT
            and data.get("source_execution_authorized") is True
            and data.get("runtime_module_sha256") == file_sha(Path(__file__))
            and data.get("adapter_module_sha256")
            == file_sha(Path(__file__).with_name("source_library_audit.py"))
            and data.get("accepted_baseline_pins") == self.accepted.verify() == self.pins,
            "Separate independent persistent-runtime acceptance with exact baseline pins required",
        )
        self.runtime_acceptance = {"path": str(review), "sha256": expected_sha256}

    def require_runtime(self):
        self.verify()
        if self.initialization["engineering_only"]:
            return
        require(
            self.runtime_acceptance is not None, "Independent persistent runtime review required"
        )
        self.accept_runtime(
            Path(self.runtime_acceptance["path"]), self.runtime_acceptance["sha256"]
        )

    def operation_approval(self, operation, operator_id, review, review_sha256):
        private_file(review)
        require(
            file_sha(review) == review_sha256, "Independent source-operation review pin changed"
        )
        data = json.loads(review.read_bytes())
        require(
            data.get("schema") == OPERATION_SCHEMA
            and data.get("verdict") == OPERATION_VERDICT
            and data.get("accepted_baseline_pins") == self.pins
            and data.get("operation_sha256")
            == hashlib.sha256(_json(operation).encode()).hexdigest()
            and data.get("company_operator_id") == operator_id,
            "Independent approval of exact company-owned source operation required",
        )
        return {"path": str(review), "sha256": review_sha256}

    def append(self, actor, operation, content, *, review=None, review_sha256=None):
        """Company-owned append, independent of engagements and audit commands."""
        require(not self.read_only, "Read-only company verification cannot append")
        require(actor is self.operator, "Actual trusted company operator capability required")
        self.require_runtime()
        validate_operation(operation, content)
        operation_sha = hashlib.sha256(_json(operation).encode()).hexdigest()
        if self.initialization["engineering_only"]:
            require(
                operation["company"].startswith("NEUTRAL-")
                and json.loads(content).get("engineering_neutral_fixture") is True,
                "Engineering operation cannot activate actual company history",
            )
            approval = {"engineering_only": True, "operation_sha256": operation_sha}
        else:
            approval = self.operation_approval(operation, actor.principal, review, review_sha256)
        with self.locked():
            checkpoint = self.verify()
            key = tuple(operation[k] for k in NATIVE_ID[:4])
            rows = native_rows(self.database)
            predecessors = [r for k, r in rows.items() if k[:4] == key]
            require(predecessors, "Correction requires an existing accepted native record")
            latest = max(predecessors, key=lambda r: r["version"])
            validate_operation(operation, content, latest)
            authorized = now()
            self.writing = True
            try:
                metadata = self.store.append_version(
                    *key,
                    expected_version=operation["expected_version"],
                    command_id=operation["command_id"],
                    event_at=operation["event_at"],
                    available_at=operation["available_at"],
                    content=content,
                    provenance=operation["provenance"],
                    origin=operation["origin"],
                )
                updated = native_rows(self.database)
                native = updated[(*key, metadata["version"])]
                typed_content({**metadata, "content": content})
                entry_name = f"OPERATION-{len(checkpoint['operations']) + 1:06d}.json"
                receipt = {
                    "schema": "SH_COMPANY_APPEND_OPERATION_RECEIPT_V1",
                    "operator_id": actor.principal,
                    "authorized_at": authorized,
                    "completed_at": now(),
                    "operation": operation,
                    "operation_sha256": operation_sha,
                    "approval": approval,
                    "native_row": native,
                    "previous_operation_sha256": (
                        checkpoint["operations"][-1]["sha256"] if checkpoint["operations"] else None
                    ),
                }
                path = self.root / "operations" / entry_name
                write(path, receipt)
                successor = {
                    **checkpoint,
                    "previous_checkpoint_sha256": self.checkpoint_sha256,
                    "operations": [
                        *checkpoint["operations"],
                        {"name": entry_name, "sha256": file_sha(path)},
                    ],
                    "native_versions": len(updated),
                    "native_rows_sha256": rows_sha(updated),
                }
                target = self.root / f"CHECKPOINT-{len(successor['operations']):06d}.json"
                write(target, successor)
                self.checkpoint, self.checkpoint_sha256 = target, file_sha(target)
            finally:
                self.writing = False
            self.verify()
            return {
                "source": metadata,
                "receipt": str(path),
                "receipt_sha256": file_sha(path),
                "checkpoint": str(target),
                "checkpoint_sha256": self.checkpoint_sha256,
            }


class PersistentAudit(LibraryAudit):
    """Reuse accepted bound discovery/typed collection against one shared company.

    Engine instances and workrooms are fresh; source grants/journals belong to the
    persistent company lifetime and are scoped to their distinct engagement IDs.
    """

    def __init__(self, world: PersistentCompany, routes: list[BusinessRoute]):
        require(not world.read_only, "Read-only company verifier cannot create an audit")
        world.require_runtime()
        world.verify()
        require(routes and len(set(routes)) == len(routes), "Distinct business routes required")
        require(
            len({(r.company, r.branch) for r in routes}) == 1
            and len({(r.company, r.branch, r.system) for r in routes}) == len(routes),
            "One isolated company branch with unambiguous business routes required",
        )
        with quiescent_read(world.database) as db:
            systems = {tuple(r) for r in db.execute("SELECT company,branch,system FROM systems")}
        self.routes = {(r.company, r.branch, r.system): r for r in routes}
        require(set(self.routes) <= systems, "Unregistered business route")
        self.world, self.accepted, self.pins = world, world.accepted, world.pins
        self.database, self.store = world.database, world.store
        self.access_log = []
        self.engine = self.engagement = self.identities = None

    def check_unchanged(self):
        self.world.require_runtime()
        self.world.verify()

    def create(self, *, repository, audit_root, payload, program_pack=None):
        with self.world.locked():
            self.check_unchanged()
            require(
                self.engine is None and not audit_root.exists(), "New empty audit workroom required"
            )
            company, branch = next(iter({(r.company, r.branch) for r in self.routes.values()}))
            engine = Engine(
                audit_root,
                repository=repository,
                program_pack=program_pack,
                company_root=self.world.root,
            )
            self.check_unchanged()
            engine.company_store = self.store
            operator = engine.store.provision("Company access operator", ["instructor"])["id"]
            auditor = engine.store.provision("Independent audit performer", ["learner"])["id"]
            reviewer = engine.store.provision("Reserved independent reviewer", ["reviewer"])["id"]
            require(
                len({operator, auditor, reviewer, self.world.operator.principal}) == 4,
                "Persistent company writer and audit identities must be distinct",
            )
            state = engine.create(operator, payload)
            empty = {key: len(state[key]) for key in EMPTY_WORKROOM}
            require(not any(empty.values()), "Fresh audit inherited evidence or work")
            require(
                all(
                    t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                    for t in state["tasks"]
                ),
                "Fresh audit inherited task credit",
            )
            engagement = state["id"]
            engine.store.grant(engagement, auditor, "learn")
            engine.store.grant(engagement, reviewer, "review")
            engine.company_bindings[engagement] = {"company": company, "branch": branch}
            self.engine, self.engagement = engine, engagement
            self.identities = {"operator": operator, "auditor": auditor, "reviewer": reviewer}
            self.check_unchanged()
            return (
                engine,
                state,
                {
                    **self.identities,
                    "zero_workroom_counts": empty,
                    "company_operator": self.world.operator.principal,
                    "company_checkpoint_sha256": self.world.checkpoint_sha256,
                    "accepted_baseline": self.pins,
                },
            )
