"""Normal, scoped CompanyStore access for independently accepted source libraries.

Routing is business metadata. Actual projected custody tuples remain unchanged;
logical family/system names never replace identifiers in a retained receipt.
This module neither creates company facts nor opens a transformation map or Key.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import safe_name
from .company_store import CompanyStore, _time
from .engine import Engine
from .fresh_sec003_procedure import (
    CLOCK_ID,
    NATIVE_ID,
    ProcedureError,
    business_digest,
    discover_history,
    read_only,
    require,
)

EMPTY_WORKROOM = (
    "artifacts",
    "workpapers",
    "populations",
    "selections",
    "reviews",
    "findings",
    "requests",
)
MEDIA_SUFFIX = {
    "application/json": ".json",
    "text/plain": ".txt",
    "text/plain; charset=utf-8": ".txt",
}
BUSINESS_REFERENCE = tuple(key for key in CLOCK_ID if key != "imported_at")
LIBRARY_REVIEW_SCHEMA = "SH_ROOT_COMPANY_LIBRARY_INDEPENDENT_REVIEW_V1"
LIBRARY_REVIEW_VERDICT = "PASS_COMPANY_FACING_LIBRARY_SELECTED_BOUNDARY"
LIBRARY_MANIFEST_SCHEMA = "SH_COMPANY_OPERATIONAL_PROJECTION_V2"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_file(path: Path) -> None:
    path = Path(path).absolute()
    require(
        not any(part.is_symlink() for part in [path, *path.parents]),
        "Private file path aliases are forbidden",
    )
    info = path.lstat()
    require(
        stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1,
        "Private ordinary single-link file required",
    )


def ordinary_copy(original: Path, target: Path) -> None:
    """Copy bytes to an exclusive new file, never a link or reflink."""
    private_file(original)
    before = file_sha(original)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with original.open("rb") as source, os.fdopen(fd, "wb") as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    private_file(target)
    require(file_sha(original) == before == file_sha(target), "Source changed during staging")
    require(
        (original.stat().st_dev, original.stat().st_ino)
        != (target.stat().st_dev, target.stat().st_ino),
        "Independent source copy required",
    )


def schema_sha(path: Path) -> str:
    with read_only(path) as db:
        objects = [
            list(row)
            for row in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ]
        versions = [
            db.execute("PRAGMA user_version").fetchone()[0],
            db.execute("PRAGMA application_id").fetchone()[0],
        ]
    return hashlib.sha256(
        json.dumps([objects, versions], separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class AcceptedLibrary:
    """Trusted operator's exact pins, after separate review and main reproduction."""

    database: Path
    database_sha256: str
    manifest: Path
    manifest_sha256: str
    review: Path
    review_sha256: str
    version_count: int

    def verify(self) -> dict:
        require(
            type(self.version_count) is int and self.version_count > 0,
            "Exact positive accepted version boundary required",
        )
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.database) + suffix)
            require(
                not sidecar.exists() and not sidecar.is_symlink(),
                "Accepted source-side SQLite sidecars are forbidden",
            )
        for path, expected in (
            (self.database, self.database_sha256),
            (self.manifest, self.manifest_sha256),
            (self.review, self.review_sha256),
        ):
            private_file(path)
            require(file_sha(path) == expected, "Accepted library pin changed")
        review = json.loads(self.review.read_bytes())
        manifest = json.loads(self.manifest.read_bytes())
        require(
            review.get("schema") == LIBRARY_REVIEW_SCHEMA
            and review.get("verdict") == LIBRARY_REVIEW_VERDICT
            and review.get("source_quality_accepted_for_final_learner_audit") is True,
            "Independent library acceptance required before audit creation",
        )
        require(
            review.get("library_pins")
            == {"company.sqlite3": self.database_sha256, "MANIFEST.json": self.manifest_sha256}
            and type(review.get("native_versions")) is int
            and review["native_versions"] == self.version_count,
            "Review must bind exact database, manifest and version boundary",
        )
        require(
            manifest.get("schema") == LIBRARY_MANIFEST_SCHEMA
            and manifest.get("files", {}).get("company.sqlite3") == self.database_sha256,
            "Manifest must bind the exact projected library database",
        )
        with read_only(self.database) as db:
            require(
                db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == self.version_count,
                "Accepted library version boundary changed",
            )
            require(
                all(
                    db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
                    for table in ("grants", "collections", "access_events")
                ),
                "Library carries engagement access or collection journals",
            )
        return {
            "database_sha256": self.database_sha256,
            "manifest_sha256": self.manifest_sha256,
            "review_sha256": self.review_sha256,
            "version_count": self.version_count,
            "independent_acceptance_verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
        }


@dataclass(frozen=True)
class BusinessRoute:
    company: str
    branch: str
    system: str
    family: str
    logical_system: str


def typed_content(row: dict) -> tuple[object, str]:
    """Inspect the supplied ordinary source type without inventing a filename."""
    provenance = row["provenance"]
    content_type = provenance.get("content_type")
    name = provenance.get("name")
    require(content_type in MEDIA_SUFFIX, "Unsupported company evidence type")
    require(isinstance(name, str), "Explicit typed company filename required")
    safe_name(name)
    require(name.endswith(MEDIA_SUFFIX[content_type]), "Company filename/type disagreement")
    raw = row["content"]
    require(hashlib.sha256(raw).hexdigest() == row["sha256"], "Company bytes changed")
    try:
        document = json.loads(raw) if content_type == "application/json" else raw.decode("utf-8")
    except (ValueError, UnicodeError) as error:
        raise ProcedureError("Company bytes do not match declared type") from error
    if content_type == "application/json":
        require(isinstance(document, (dict, list)), "Structured native JSON required")
    return document, content_type


def exact_projected_reference(reference: dict, discovered_or_collected: list[dict]) -> dict:
    """Join a business pointer to actual projected custody, never a logical alias.

    A producer pointer is a locator, not a population or sufficiency conclusion.
    Its exact version must have been independently discovered/collected under the
    auditor's grant; unavailable/missing versions and changed hashes fail closed.
    """
    require(
        set(BUSINESS_REFERENCE) <= reference.keys(),
        "Exact projected business reference clocks required",
    )
    matches = []
    for row in discovered_or_collected:
        actual = row.get("source", row)
        if all(actual[key] == reference[key] for key in NATIVE_ID):
            matches.append(row)
    require(len(matches) == 1, "Exact projected reference not uniquely discovered")
    actual = matches[0].get("source", matches[0])
    fields = (
        (*BUSINESS_REFERENCE, "imported_at") if "imported_at" in reference else BUSINESS_REFERENCE
    )
    require(
        all(actual[key] == reference[key] for key in fields),
        "Projected reference hash or clocks disagree",
    )
    require(
        actual["imported_at"] == _time(actual["imported_at"])
        and _time(actual["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
        "Target real import clock is invalid",
    )
    return matches[0]


class LibraryAudit:
    """Disposable grants/journals over an immutable accepted company history.

    Stage this library before Engine construction/creation. Each engagement gets
    an independent ordinary-byte source copy; original company stores stay sealed.
    The auditor discovers through normal grants and CompanyStore APIs, and uses
    Engine's ordinary company.collect command. No prepared audit state is copied.
    """

    def __init__(self, accepted: AcceptedLibrary, destination: Path, routes: list[BusinessRoute]):
        self.accepted = accepted
        self.pins = accepted.verify()
        require(routes and len(set(routes)) == len(routes), "Distinct business routes required")
        require(
            len({(r.company, r.branch, r.system) for r in routes}) == len(routes),
            "Ambiguous native business routing",
        )
        self.routes = {(r.company, r.branch, r.system): r for r in routes}
        destination = Path(destination).absolute()
        require(not destination.exists(), "New source-workroom destination required")
        info = destination.parent.lstat()
        require(
            stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700,
            "Private source-workroom parent required",
        )
        destination.mkdir(mode=0o700)
        self.database = destination / "company.sqlite3"
        ordinary_copy(accepted.database, self.database)
        self.business_sha256 = business_digest(self.database)
        self.schema_sha256 = schema_sha(self.database)
        self.access_log = []
        with read_only(self.database) as db:
            registered = {
                tuple(row) for row in db.execute("SELECT company,branch,system FROM systems")
            }
        require(
            set(self.routes) <= registered, "Business route names an unregistered native system"
        )
        self.store = CompanyStore(destination)
        self.check_unchanged()

    def check_unchanged(self):
        self.accepted.verify()
        private_file(self.database)
        require(
            business_digest(self.database) == self.business_sha256,
            "Staged native company history changed",
        )
        require(schema_sha(self.database) == self.schema_sha256, "Staged native schema changed")

    def authorize(
        self, *, operator: str, auditor: str, reviewer: str, engagement: str, active=True
    ):
        require(
            len({operator, auditor, reviewer}) == 3, "Separate company/auditor/reviewer required"
        )
        self.check_unchanged()
        for company, branch, system in sorted(self.routes):
            self.store.grant(auditor, engagement, company, branch, system, active=active)
            self.access_log.append(
                {
                    "operator_id": operator,
                    "principal_id": auditor,
                    "reviewer_id": reviewer,
                    "engagement_id": engagement,
                    "company": company,
                    "branch": branch,
                    "system": system,
                    "active": active,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            )
        self.check_unchanged()

    def discover(self, auditor: str, engagement: str, company: str, branch: str, *, as_of: str):
        self.check_unchanged()
        systems = sorted(
            r.system for r in self.routes.values() if (r.company, r.branch) == (company, branch)
        )
        require(systems, "Declared company/branch route required")
        rows, pages = discover_history(
            self.store, auditor, engagement, company, branch, as_of=as_of, systems=systems
        )
        views = []
        for row in rows:
            require(
                row["imported_at"] == _time(row["imported_at"])
                and _time(row["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
                "Discovered real import clock is invalid",
            )
            route = self.routes[(row["company"], row["branch"], row["system"])]
            typed_content(row)
            views.append(
                {
                    **row,
                    "logical_family": route.family,
                    "logical_system": route.logical_system,
                    "discovered_as_of": _time(as_of),
                }
            )
        self.check_unchanged()
        return views, pages

    def create(
        self, *, repository: Path, audit_root: Path, payload: dict, program_pack: Path | None = None
    ):
        """Supported create/configuration mechanics; never read a frozen audit state."""
        self.check_unchanged()
        branches = {(r.company, r.branch) for r in self.routes.values()}
        require(len(branches) == 1, "One explicit company branch per engagement required")
        company, branch = next(iter(branches))
        with read_only(self.database) as db:
            require(
                all(
                    db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
                    for table in ("grants", "collections", "access_events")
                ),
                "Fresh engagement requires zero source access/collection journals",
            )
        require(not audit_root.exists(), "New audit workroom required")
        engine = Engine(
            audit_root,
            repository=repository,
            program_pack=program_pack,
            company_root=self.database.parent,
        )
        operator = engine.store.provision("Company source operator", ["instructor"])["id"]
        auditor = engine.store.provision("Independent audit performer", ["learner"])["id"]
        reviewer = engine.store.provision("Reserved independent reviewer", ["reviewer"])["id"]
        require(len({operator, auditor, reviewer}) == 3, "Distinct identities required")
        state = engine.create(operator, payload)
        empty = {key: len(state[key]) for key in EMPTY_WORKROOM}
        require(not any(empty.values()), "Fresh engagement inherited audit work")
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
            ),
            "Fresh engagement inherited task dispositions",
        )
        engagement = state["id"]
        engine.store.grant(engagement, auditor, "learn")
        engine.store.grant(engagement, reviewer, "review")
        engine.company_bindings[engagement] = {"company": company, "branch": branch}
        return (
            engine,
            state,
            {
                "operator": operator,
                "auditor": auditor,
                "reviewer": reviewer,
                "zero_workroom_counts": empty,
                "accepted_library": self.pins,
            },
        )

    def collect(
        self, engine, auditor: str, engagement: str, request: str, row: dict, *, command_id: str
    ):
        self.check_unchanged()
        require(
            isinstance(engine.company_store, CompanyStore)
            and engine.company_store.path.absolute() == self.database,
            "Engine company connection differs from the staged library",
        )
        state = engine.store.get(auditor, engagement)
        bound = engine.company_bindings.get(engagement)
        require(
            bound == {"company": row["company"], "branch": row["branch"]},
            "Discovered source belongs to another engagement branch",
        )
        require(
            _time(row["available_at"]) <= _time(state["simulated_at"]),
            "Collected source unavailable at engagement clock",
        )
        require(
            row["event_at"] is None or _time(row["event_at"]) <= _time(state["simulated_at"]),
            "Collected event occurs after engagement clock",
        )
        actual = self.store.read_version(
            auditor,
            engagement,
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            version=row["version"],
            as_of=state["simulated_at"],
        )
        require(
            all(actual[k] == row[k] for k in CLOCK_ID) and actual["content"] == row["content"],
            "Discovery-to-collection source changed",
        )
        document, content_type = typed_content(actual)
        previous = {artifact["id"] for artifact in state["artifacts"]}
        state = engine.command(
            auditor,
            engagement,
            {
                "command_id": command_id,
                "expected_revision": state["revision"],
                "kind": "company.collect",
                "payload": {
                    "system_id": actual["system"],
                    "record_id": actual["record"],
                    "version": actual["version"],
                    "request_id": request,
                },
            },
        )
        added = [artifact for artifact in state["artifacts"] if artifact["id"] not in previous]
        require(len(added) == 1, "Exact newly retained company artifact required")
        artifact = added[0]
        receipt = artifact["source"]["receipt"]
        require(
            all(receipt["source"][key] == actual[key] for key in CLOCK_ID),
            "Retained projected custody tuple changed",
        )
        require(
            receipt["source"]["provenance"] == actual["provenance"],
            "Retained projected provenance changed",
        )
        require(
            engine.artifacts.read(artifact) == actual["content"], "Retained native bytes changed"
        )
        route = self.routes[tuple(actual[k] for k in NATIVE_ID[:3])]
        self.check_unchanged()
        return {
            "source": receipt["source"],
            "receipt": receipt,
            "logical_family": route.family,
            "logical_system": route.logical_system,
            "artifact_id": artifact["id"],
            "artifact_sha256": artifact["sha256"],
            "document": document,
            "content_type": content_type,
            "discovered_as_of": row["discovered_as_of"],
        }
