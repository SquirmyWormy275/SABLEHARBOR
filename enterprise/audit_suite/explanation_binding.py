"""Private immutable instructor explanations bound to existing source and audit versions.

Trusted local operator API. No route, learner projection, scoring or archive mutation.
"""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .company_collection import binding
from .company_store import CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .store import DomainError, digest


def _ids(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _authored(value, source_ids, control_ids, repository, state=None):
    if not isinstance(value, dict) or set(value) != {
        "issues",
        "expectations",
        "uncertainty",
        "source_pins",
    }:
        raise DomainError(
            "Exact authored issue, expectation, uncertainty and source-pin fields required"
        )
    if not isinstance(value["uncertainty"], list) or not all(
        isinstance(x, str) and x.strip() for x in value["uncertainty"]
    ):
        raise DomainError("Explicit uncertainty list required")
    if (
        not isinstance(value["issues"], list)
        or not isinstance(value["expectations"], list)
        or not isinstance(value["source_pins"], dict)
    ):
        raise DomainError("Typed authored record lists and source pin mapping required")
    issue_ids = set()
    for issue in value["issues"]:
        if (
            not isinstance(issue, dict)
            or set(issue) != {"id", "control_ids", "source_ids", "claim", "uncertainty"}
            or not isinstance(issue["id"], str)
            or not issue["id"]
            or issue["id"] in issue_ids
            or not isinstance(issue["claim"], str)
            or not issue["claim"].strip()
            or not isinstance(issue["uncertainty"], str)
            or not issue["uncertainty"].strip()
            or not _ids(issue["source_ids"])
            or not set(issue["source_ids"]) <= source_ids
            or not (_ids(issue["control_ids"]) or issue["control_ids"] == [])
            or not set(issue["control_ids"]) <= control_ids
        ):
            raise DomainError(
                "Authored issue must reference exact scoped controls and bound sources"
            )
        issue_ids.add(issue["id"])
    expectation_ids = set()
    scope_issue_ids = {issue["id"] for issue in value["issues"] if issue["control_ids"] == []}
    scope_linked_ids = set()
    for row in value["expectations"]:
        if (
            not isinstance(row, dict)
            or set(row)
            not in (
                {"id", "issue_ids", "procedure", "acceptable_alternatives"},
                {"id", "issue_ids", "procedure", "acceptable_alternatives", "task_ids"},
            )
            or not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in expectation_ids
            or not _ids(row["issue_ids"])
            or not set(row["issue_ids"]) <= issue_ids
            or not isinstance(row["procedure"], str)
            or not row["procedure"].strip()
            or not isinstance(row["acceptable_alternatives"], list)
            or not all(isinstance(x, str) and x.strip() for x in row["acceptable_alternatives"])
        ):
            raise DomainError(
                "Expectations require actual issues and explicit alternative procedures"
            )
        related = [issue for issue in value["issues"] if issue["id"] in row["issue_ids"]]
        scope_related = {issue["id"] for issue in related if issue["control_ids"] == []}
        if scope_related:
            if len(scope_related) != len(related) or not _ids(row.get("task_ids")):
                raise DomainError("Scope issues require explicit scope-only procedure links")
            scope_linked_ids.update(scope_related)
        if "task_ids" in row:
            from .expectation_links import validate_authored_tasks

            validate_authored_tasks(
                state, {c for issue in related for c in issue["control_ids"]}, row["task_ids"]
            )
        expectation_ids.add(row["id"])
    if scope_issue_ids - scope_linked_ids:
        raise DomainError("Scope issues require an explicitly linked current scope procedure")
    for relative, expected in value["source_pins"].items():
        if (
            not isinstance(relative, str)
            or not relative
            or not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            raise DomainError("Invalid authored source pin schema")
        path = Path(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(p.is_symlink() for p in [repository / path, *(repository / path).parents])
        ):
            raise DomainError("Invalid authored source path")
        if sha((repository / path).read_bytes()) != expected:
            raise DomainError("Authored source pin differs from retained source")
    return json.loads(encoded(value))


def _private(path):
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise DomainError("Private snapshot aliases are forbidden")
    if not path.is_dir() or path.stat().st_mode & 0o077:
        raise DomainError("Existing private 0700 parent required")


def _write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def bind_snapshot(
    engine,
    *,
    instructor_id,
    audited_actor_id,
    engagement_id,
    source_operator_id,
    source_as_of,
    source_refs,
    authored,
    output: Path,
):
    """Bind now; source_as_of is operator inspection time, never audited-actor visibility."""
    if engine.store.membership(instructor_id, engagement_id) != "instruct":
        raise DomainError("Scoped instructor access required", status=403)
    state = engine.store.get(instructor_id, engagement_id)
    engine.store.get(audited_actor_id, engagement_id)
    from .history_inspection import inspect_history

    history = inspect_history(engine.store, instructor_id, engagement_id)
    if history["latest"]["state"]["revision"] != state["revision"]:
        raise DomainError("Engagement changed during binding; retry a new snapshot", status=409)
    bound = dict(binding(engine, state))
    portfolio = getattr(engine.company_store, "is_federated", False)
    clock, operator_clock = _time(state["simulated_at"]), _time(source_as_of)
    if not isinstance(source_refs, list) or not source_refs:
        raise DomainError("Explicit source version references required")
    ids, identities = set(), set()
    for ref in source_refs:
        if (
            not isinstance(ref, dict)
            or set(ref)
            != (
                {"id", "company", "branch", "system", "record", "version", "sha256"}
                | (
                    {"source_store_id", "source_system_alias", "registry_sha256"}
                    if portfolio
                    else set()
                )
            )
            or not isinstance(ref["id"], str)
            or not ref["id"]
            or ref["id"] in ids
            or (not portfolio and ref["company"] != bound["company"])
            or (not portfolio and ref["branch"] != bound["branch"])
            or type(ref["version"]) is not int
            or ref["version"] < 1
        ):
            raise DomainError("Exact distinct source identities within the bound branch required")
        identity = tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
        if portfolio:
            identity = (ref["source_store_id"], *identity)
        if identity in identities:
            raise DomainError("Duplicate source version")
        identities.add(identity)
        ids.add(ref["id"])
    authored = _authored(
        authored, ids, {c["id"] for c in state["controls"]}, engine.repository, state=state
    )
    sources, files = [], {}
    try:
        components = []
        watermark = None
        if portfolio:
            from .portfolio_explanation import capture

            sources, files, components = capture(
                engine,
                state=state,
                bound=bound,
                refs=source_refs,
                actor=audited_actor_id,
                operator=source_operator_id,
                clock=clock,
                operator_clock=operator_clock,
            )
        else:
            with engine.company_store._db() as db:
                db.execute("BEGIN")
                watermark = db.execute("SELECT COALESCE(MAX(id),0) FROM access_events").fetchone()[
                    0
                ]
                for index, ref in enumerate(source_refs):
                    key = tuple(ref[k] for k in ("company", "branch", "system", "record"))
                    row = engine.company_store._read(
                        db, source_operator_id, engagement_id, key, ref["version"], operator_clock
                    )
                    if sha(row["content"]) != ref["sha256"]:
                        raise DomainError("Bound source digest mismatch", status=409)
                    grant = db.execute(
                        "SELECT active FROM grants WHERE principal=? AND engagement=? "
                        "AND company=? AND branch=? AND system=?",
                        (audited_actor_id, engagement_id, *key[:3]),
                    ).fetchone()
                    granted = bool(grant and grant[0])
                    exists_now = row["available_at"] <= clock and (
                        row["event_at"] is None or row["event_at"] <= clock
                    )
                    latest = db.execute(
                        "SELECT MAX(version) FROM versions WHERE company=? AND branch=? "
                        "AND system=? AND record=? AND available_at<=? "
                        "AND (event_at IS NULL OR event_at<=?)",
                        (*key, clock, clock),
                    ).fetchone()[0]
                    visibility = (
                        "FUTURE_UNAVAILABLE"
                        if not exists_now
                        else (
                            "ACCESS_NOT_GRANTED"
                            if not granted
                            else (
                                "DISCOVERABLE_LATEST"
                                if latest == ref["version"]
                                else "READABLE_PRIOR_VERSION"
                            )
                        )
                    )
                    artifact_ids = []
                    for artifact in state["artifacts"]:
                        source = artifact.get("source", {}).get("receipt", {}).get("source", {})
                        if all(
                            source.get(k) == ref[k]
                            for k in ("company", "branch", "system", "record", "version", "sha256")
                        ):
                            if sha(engine.artifacts.read(artifact)) != ref["sha256"]:
                                raise DomainError("Retained audit copy differs from bound source")
                            artifact_ids.append(artifact["id"])
                    name = f"sources/{index:05d}.json"
                    files[name] = row["content"]
                    sources.append(
                        {
                            **ref,
                            "path": name,
                            "event_at": row["event_at"],
                            "available_at": row["available_at"],
                            "imported_at": row["imported_at"],
                            "actor_granted_at_binding": granted,
                            "actor_visibility_at_binding": visibility,
                            "retained_audit_artifact_ids": artifact_ids,
                            "fact_verification": (
                                "EXACT_EXISTING_SOURCE_BYTES_AND_ACCESS_STATE_ONLY"
                            ),
                        }
                    )
    except CompanyStoreError as exc:
        raise DomainError(
            "Operator source access unavailable or source version invalid", status=403
        ) from exc
    current = engine.store.get(instructor_id, engagement_id)
    if engine.store.membership(instructor_id, engagement_id) != "instruct":
        raise DomainError("Scoped instructor access required", status=403)
    if current["revision"] != state["revision"] or binding(engine, current) != bound:
        raise DomainError("Engagement or company binding changed during binding", status=409)
    snapshot = {
        "schema_version": "1.0",
        "status": "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED",
        "created_at": datetime.now(UTC).isoformat(),
        "instructor_id": instructor_id,
        "audited_actor_id": audited_actor_id,
        "source_operator_id": source_operator_id,
        "operator_source_as_of": operator_clock,
        "company_binding": bound,
        "engagement": {
            "id": engagement_id,
            "revision": state["revision"],
            "scope": state["scope"],
            "simulated_at": state["simulated_at"],
            "state_sha256": digest(state),
            "history_sha256": history["history_sha256"],
        },
        "access_event_watermark": watermark,
        "sources": sources,
        "software_verified": [
            "Source byte identity",
            "Source availability timestamps",
            "Actor grant state at binding",
            "Exact retained audit-copy hashes",
        ],
        "authored": authored,
        "authored_status": "INSTRUCTOR_AUTHORED_INFERENCE",
        "professional_validation": "UNVALIDATED",
        "grading": "NOT_PERFORMED",
        "limits": [
            "Access status is a captured state, not a permanent grant.",
            "An opened or collected file does not establish learner understanding.",
            "Authored claims and expectations are not software-verified audit conclusions.",
        ],
    }
    if portfolio:
        snapshot["snapshot_isolation"] = "PER_COMPONENT_NOT_GLOBAL"
        snapshot["component_snapshots"] = components
        snapshot["limits"].append(
            "Component capture times differ; no global source snapshot is asserted."
        )
    files["snapshot.json"] = encoded(snapshot)
    output = Path(output).absolute()
    _private(output.parent)
    if output.exists() or output.is_symlink():
        raise DomainError("New snapshot directory required; history cannot be overwritten")
    stage = None
    target = output
    if portfolio:
        inputs = [
            engine.store.root,
            *[Path(c["root"]) for c in engine.company_store._manifest["components"].values()],
        ]
        if any(output.resolve().is_relative_to(Path(root).resolve()) for root in inputs):
            raise DomainError("Portfolio snapshot must be outside original audit/source roots")
        stage = tempfile.TemporaryDirectory(prefix="portfolio-snapshot-", dir=output.parent)
        output = Path(stage.name)
    else:
        output.mkdir(mode=0o700)
    (output / "sources").mkdir(mode=0o700)
    manifest = {
        "schema_version": "1.0",
        "files": {name: sha(raw) for name, raw in files.items()},
        "engagement_id": engagement_id,
        "engagement_revision": state["revision"],
    }
    try:
        for name, raw in files.items():
            _write(output / name, raw)
        _write(output / "manifest.json", encoded(manifest))
        if portfolio:
            from .portfolio_explanation import validate_capture_authority
            from .private_publication import publish

            validate_capture_authority(engine, snapshot)
            final = engine.store.get(instructor_id, engagement_id)
            engine.store.get(audited_actor_id, engagement_id)
            if (
                engine.store.membership(instructor_id, engagement_id) != "instruct"
                or final["revision"] != state["revision"]
                or binding(engine, final) != bound
            ):
                raise DomainError(
                    "Engagement authority changed before snapshot publication", status=409
                )
            publish(output, target)
    finally:
        if stage is not None:
            stage.cleanup()
    return {
        "path": str(target),
        "manifest_sha256": sha(encoded(manifest)),
        "status": snapshot["status"],
        "sources": len(sources),
    }


def verify_snapshot(output: Path, *, expected_manifest_sha256):
    """Internal verifier; HTTP callers require separate scoped instructor authorization."""
    output = Path(output).absolute()
    _private(output)
    manifest_path = output / "manifest.json"
    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
        or manifest_path.stat().st_mode & 0o077
        or sha(manifest_path.read_bytes()) != expected_manifest_sha256
    ):
        raise DomainError("Snapshot manifest changed")
    manifest = json.loads(manifest_path.read_bytes())
    for name, expected in manifest["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise DomainError("Invalid snapshot member")
        target = output / path
        if (
            any(p.is_symlink() for p in [target, *target.parents])
            or target.stat().st_mode & 0o077
            or sha(target.read_bytes()) != expected
        ):
            raise DomainError("Snapshot source or explanation changed")
    return json.loads((output / "snapshot.json").read_bytes())
