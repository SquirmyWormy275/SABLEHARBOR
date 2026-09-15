"""Explicit routed source snapshots for private instructor explanations."""

from datetime import UTC, datetime

from .company_store import CompanyStoreError
from .operating_source_bridge import sha
from .store import DomainError

NATIVE = ("company", "branch", "system", "record", "version", "sha256")
ROUTE = ("source_store_id", "source_system_alias", "registry_sha256")
MAX_BYTES = 64 * 1024 * 1024


def same_route(source, expected):
    """Physical identities can collide across independently registered source stores."""
    return (
        all(source.get(k) == expected.get(k) for k in ROUTE)
        if any(k in expected for k in ROUTE)
        else True
    )


def validate_routes(engine, snapshot):
    if snapshot.get("snapshot_isolation") != "PER_COMPONENT_NOT_GLOBAL":
        return
    store = engine.company_store
    if not getattr(store, "is_federated", False):
        raise CompanyStoreError("Portfolio source routing unavailable")
    store.validate_binding(snapshot["company_binding"])
    for ref in snapshot["sources"]:
        store.resolve_source_identity(ref)


def capture(engine, *, state, bound, refs, actor, operator, clock, operator_clock):
    facade = engine.company_store
    facade.validate_binding(bound)
    if len(refs) > 256:
        raise DomainError("Bounded explicit portfolio source list required")
    groups = {}
    for index, ref in enumerate(refs):
        alias = facade.resolve_source_identity(ref)
        source_id, system, component, native = facade._route(
            bound["company"], bound["branch"], alias
        )
        groups.setdefault(source_id, {"native": native, "component": component, "refs": []})[
            "refs"
        ].append((index, ref))
    sources, files, components = [], {}, []
    total = 0
    for source_id, group in sorted(groups.items()):
        native = group["native"]
        started = datetime.now(UTC).isoformat()
        with native._db() as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            watermark = db.execute("SELECT COALESCE(MAX(id),0) FROM access_events").fetchone()[0]
            for index, ref in group["refs"]:
                key = tuple(ref[k] for k in NATIVE[:4])
                size = db.execute(
                    "SELECT LENGTH(content) FROM versions WHERE company=? AND branch=? "
                    "AND system=? AND record=? AND version=?",
                    (*key, ref["version"]),
                ).fetchone()
                if size is None or total + size[0] > MAX_BYTES:
                    raise CompanyStoreError("Bound source absent or aggregate byte quota exceeded")
                row = native._read(db, operator, state["id"], key, ref["version"], operator_clock)
                content = row["content"]
                total += len(content)
                if total > MAX_BYTES or sha(content) != ref["sha256"]:
                    raise CompanyStoreError("Bound source integrity or size changed")
                grant = db.execute(
                    "SELECT active FROM grants WHERE principal=? AND engagement=? "
                    "AND company=? AND branch=? AND system=?",
                    (actor, state["id"], *key[:3]),
                ).fetchone()
                granted = bool(grant and grant[0])
                visible = row["available_at"] <= clock and (
                    row["event_at"] is None or row["event_at"] <= clock
                )
                latest = db.execute(
                    "SELECT MAX(version) FROM versions WHERE company=? AND branch=? "
                    "AND system=? AND record=? AND available_at<=? "
                    "AND (event_at IS NULL OR event_at<=?)",
                    (*key, clock, clock),
                ).fetchone()[0]
                status = (
                    "FUTURE_UNAVAILABLE"
                    if not visible
                    else "ACCESS_NOT_GRANTED"
                    if not granted
                    else "DISCOVERABLE_LATEST"
                    if latest == ref["version"]
                    else "READABLE_PRIOR_VERSION"
                )
                retained = []
                for artifact in state["artifacts"]:
                    original = artifact.get("source", {}).get("receipt", {}).get("source", {})
                    if same_route(original, ref) and all(original.get(k) == ref[k] for k in NATIVE):
                        if sha(engine.artifacts.read(artifact)) != ref["sha256"]:
                            raise CompanyStoreError(
                                "Retained audit copy differs from exact routed source"
                            )
                        retained.append(artifact["id"])
                path = f"sources/{index:05d}.json"
                files[path] = content
                sources.append(
                    {
                        **ref,
                        "path": path,
                        "event_at": row["event_at"],
                        "available_at": row["available_at"],
                        "imported_at": row["imported_at"],
                        "actor_granted_at_binding": granted,
                        "actor_visibility_at_binding": status,
                        "retained_audit_artifact_ids": retained,
                        "fact_verification": "EXACT_EXISTING_SOURCE_BYTES_AND_ACCESS_STATE_ONLY",
                    }
                )
        components.append(
            {
                "source_store_id": source_id,
                "access_event_watermark": watermark,
                "started_at": started,
                "completed_at": datetime.now(UTC).isoformat(),
                "snapshot_isolation": "ONE_PHYSICAL_SOURCE_TRANSACTION",
                "source_system_aliases": sorted(
                    {r["source_system_alias"] for _, r in group["refs"]}
                ),
            }
        )
    # Read again after all components: changed grants/routes cannot silently become the snapshot.
    for component in components:
        group = groups[component["source_store_id"]]
        with group["native"]._db() as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            current = db.execute("SELECT COALESCE(MAX(id),0) FROM access_events").fetchone()[0]
            if current != component["access_event_watermark"]:
                raise CompanyStoreError("Source authority changed during snapshot")
            for _, ref in group["refs"]:
                facade.resolve_source_identity(ref)
                key = tuple(ref[k] for k in NATIVE[:4])
                row = group["native"]._read(
                    db, operator, state["id"], key, ref["version"], operator_clock
                )
                if sha(row["content"]) != ref["sha256"]:
                    raise CompanyStoreError("Physical source changed during snapshot")
        for _, ref in group["refs"]:
            facade._authorized(
                operator,
                state["id"],
                ref["source_store_id"],
                ref["system"],
                bound["company"],
                bound["branch"],
            )
    facade.validate_binding(bound)
    return sorted(sources, key=lambda r: r["path"]), files, components


def validate_capture_authority(engine, snapshot):
    """Final pre-publication route and access checkpoint; not cross-store atomicity."""
    validate_routes(engine, snapshot)
    facade = engine.company_store
    bound = snapshot["company_binding"]
    for component in snapshot["component_snapshots"]:
        native = facade._stores[component["source_store_id"]]
        with native._db() as db:
            current = db.execute("SELECT COALESCE(MAX(id),0) FROM access_events").fetchone()[0]
        if current != component["access_event_watermark"]:
            raise CompanyStoreError("Source authority changed before snapshot publication")
        for ref in snapshot["sources"]:
            if ref["source_store_id"] == component["source_store_id"]:
                facade._authorized(
                    snapshot["source_operator_id"],
                    snapshot["engagement"]["id"],
                    ref["source_store_id"],
                    ref["system"],
                    bound["company"],
                    bound["branch"],
                )
