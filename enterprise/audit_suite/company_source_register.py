"""Read-only selected-source ownership and migration dispositions, never fact repair."""

import hashlib
import os
import re
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .company_store import _time
from .private_publication import publish
from .source_readiness import IDENTITY, QUALIFIERS, _json, _references
from .store import canonical, digest

DOMAINS = frozenset(
    (
        "identity_hr",
        "tickets_changes",
        "infrastructure_security",
        "incidents",
        "vendors",
        "governance_risk",
        "continuity",
        "training",
        "documentary_cross_domain",
        "finance_reference",
    )
)
LIMIT = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw_file(path, *, private=True, limit=LIMIT):
    path = Path(path)
    require(
        path.is_absolute()
        and path == path.resolve()
        and not any(p.is_symlink() for p in (path, *path.parents)),
        "Canonical nonalias source required",
    )
    st = path.stat()
    require(
        path.is_file()
        and st.st_nlink == 1
        and st.st_uid == os.getuid()
        and not st.st_mode & (0o077 if private else 0o022)
        and st.st_size <= limit,
        "Owned bounded source file required",
    )

    def identity(value):
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
            value.st_mode,
            value.st_nlink,
            value.st_uid,
        )

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        require(
            identity(os.fstat(source.fileno())) == identity(st),
            "Source replaced before descriptor read",
        )
        raw = source.read(limit + 1)
        require(
            len(raw) <= limit and identity(os.fstat(source.fileno())) == identity(st),
            "Source changed during descriptor read",
        )
    require(
        identity(path.stat()) == identity(st)
        and not any(p.is_symlink() for p in (path, *path.parents)),
        "Source changed during read",
    )
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_pin(spec, *, private=True):
    require(
        isinstance(spec, dict) and set(spec) == {"path", "sha256"},
        "Exact input path and SHA pin required",
    )
    require(
        isinstance(spec["sha256"], str) and re.fullmatch("[0-9a-f]{64}", spec["sha256"]),
        "Exact input SHA256 required",
    )
    raw = raw_file(spec["path"], private=private)
    require(sha(raw) == spec["sha256"], "Input file pin differs")
    return _json(raw)


def native_pin(value):
    require(
        isinstance(value, dict) and all(k in value for k in IDENTITY), "Native identity required"
    )
    for k in IDENTITY[:4]:
        require(
            isinstance(value[k], str) and 0 < len(value[k]) <= 256,
            "Explicit native identity string required",
        )
    require(
        type(value["version"]) is int
        and value["version"] > 0
        and isinstance(value["sha256"], str)
        and re.fullmatch("[0-9a-f]{64}", value["sha256"]),
        "Exact native version/hash required",
    )
    return {k: value[k] for k in IDENTITY}


def key(pin):
    return tuple(pin[k] for k in IDENTITY)


def relationships(body, source_id):
    """Preserve explicit native6 only; never guess a producer from names or identical bytes."""
    found = []
    visited = 0

    def walk(value, locator, depth):
        nonlocal visited
        visited += 1
        require(visited <= 100000 and depth <= 40, "Native relationship traversal bound exceeded")
        if isinstance(value, dict):
            if set(IDENTITY) <= set(value):
                ref = native_pin(value)
                found.append(
                    {
                        "from": source_id,
                        "locator": locator,
                        "declared_target": ref,
                        "producer_label": value.get("source_store_id"),
                        "status": "DECLARED_REFERENCE_NOT_YET_RESOLVED",
                    }
                )
            for name, child in value.items():
                walk(child, locator + "." + name, depth + 1)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{locator}[{i}]", depth + 1)

    walk(body, "native", 0)
    return found


def database_pin(path):
    require(
        not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")),
        "Active SQLite sidecars require a later quiescent snapshot",
    )
    return sha(raw_file(path))


def source_snapshot(
    root, company, branch, systems, expected, *, profile, component, namespace, domain, controls
):
    root = Path(root)
    require(
        root.is_absolute()
        and root == root.resolve()
        and root.is_dir()
        and not root.stat().st_mode & 0o077,
        "Private source root required",
    )
    path = root / "company.sqlite3"
    before = database_pin(path)
    started = datetime.now(UTC).isoformat()
    expected_count = len(expected)
    expected = {key(native_pin(p)): p for p in expected}
    require(len(expected) == expected_count, "Duplicate historical native identity")
    require(
        expected and isinstance(systems, list) and len(systems) == len(set(systems)),
        "Explicit source systems and expected inventory required",
    )
    records = []
    owners = []
    extras = []
    links = []
    native_rows = {}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        require(
            {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            >= {"systems", "versions", "grants", "collections", "access_events"},
            "Application source tables required",
        )
        total = 0
        for system in systems:
            registered = db.execute(
                "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
                (company, branch, system),
            ).fetchall()
            require(len(registered) == 1, "Registered source system missing or ambiguous")
            owner = registered[0]["owner"]
            owners.append(
                {
                    "system": system,
                    "registered_owner_id": owner,
                    "access_alias": namespace + ":" + system,
                }
            )
            sizes = db.execute(
                "SELECT COUNT(*),COALESCE(SUM(length(content)+length(CAST(provenance "
                "AS BLOB))),0) FROM versions WHERE company=? AND branch=? AND system=?",
                (company, branch, system),
            ).fetchone()
            total += sizes[1]
            require(sizes[0] <= 10000 and total <= LIMIT, "Source snapshot bound exceeded")
            for row in db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                "ORDER BY record,version",
                (company, branch, system),
            ):
                pin = native_pin(dict(row))
                require(sha(row["content"]) == pin["sha256"], "Native original bytes differ")
                if key(pin) not in expected:
                    extras.append(
                        {
                            "native": pin,
                            "disposition": "CURRENT_EXTRA_OUTSIDE_PINNED_HISTORICAL_SELECTION",
                        }
                    )
                    continue
                historical = expected.pop(key(pin))
                require(
                    all(
                        historical.get(k) == row[k] for k in ("event_at", "available_at", "origin")
                    ),
                    "Historical native metadata differs",
                )
                provenance = _json(row["provenance"])
                require(isinstance(provenance, dict), "Typed source provenance required")
                try:
                    body = _json(row["content"])
                except (ValueError, UnicodeError):
                    body = {}
                if not isinstance(body, dict):
                    body = {}
                control_refs = _references(provenance, "provenance") + _references(body, "native")
                scoped = []
                for cid in sorted({r["control_id"] for r in control_refs}):
                    control = controls.get(cid)
                    scoped.append(
                        {
                            "control_id": cid,
                            "status": "IN_SELECTED_SCOPE" if control else "OUTSIDE_SELECTED_SCOPE",
                            "title": control.get("title") if control else None,
                            "assignment": control.get("assignment") if control else None,
                        }
                    )
                identity = digest([str(root), pin])
                record = {
                    "physical_record_id": identity,
                    "profile": profile,
                    "component_id": component,
                    "domain": domain,
                    "domain_basis": "EXPLICIT_OPERATOR_COMPONENT_MAPPING_NOT_NATIVE_BUSINESS_FACT",
                    "native": pin,
                    "registered_owner_id": owner,
                    "historical_owner_status": "NOT_ESTABLISHED_BY_CURRENT_REGISTRATION",
                    "event_at": row["event_at"],
                    "event_time_status": "UNKNOWN"
                    if row["event_at"] is None
                    else "SOURCE_RECORDED",
                    "available_at": row["available_at"],
                    "imported_at": row["imported_at"],
                    "origin": row["origin"],
                    "classification": "DOCUMENTARY_CUSTODY"
                    if row["origin"]
                    in ("MIGRATED_SYNTHETIC_HISTORY", "REPOSITORY_SYNTHETIC_DOCUMENT")
                    else "QUALIFIED_NATIVE_REFERENCE_ACTIVITY",
                    "execution_capability": "NOT_ESTABLISHED_BY_INVENTORY",
                    "source_qualifiers": {
                        f"{loc}.{k}": obj[k]
                        for loc, obj in (("provenance", provenance), ("native", body))
                        for k in QUALIFIERS
                        if k in obj
                    },
                    "control_references": control_refs,
                    "scoped_control_routes": scoped,
                    "scoped_route_basis": (
                        "PINNED_HISTORICAL_INVENTORY_NOT_CURRENT_ORGANIZATION_VALIDATION"
                    ),
                    "original_bytes_verified": True,
                    "bytes": len(row["content"]),
                }
                records.append(record)
                links.extend(relationships(body, identity))
                native_rows[key(pin)] = {**dict(row), "provenance": provenance}
        require(not expected, "Pinned historical original missing or changed")
        require(len(records) + len(extras) <= 10000, "Selected source row bound exceeded")
        access = {
            "registered_system_count": len(owners),
            "selected_branch_active_grants": db.execute(
                "SELECT COUNT(*) FROM grants WHERE company=? AND branch=? AND active=1",
                (company, branch),
            ).fetchone()[0],
        }
        for table in ("collections", "access_events"):
            access[table + "_store_total"] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[
                0
            ]
    after = database_pin(path)
    require(before == after, "Source database changed during snapshot")
    return {
        "profile": profile,
        "component_id": component,
        "physical_store_root": str(root),
        "company": company,
        "branch": branch,
        "namespace": namespace,
        "domain": domain,
        "systems": owners,
        "records": records,
        "unselected_extras": extras,
        "access": access,
        "capture_started_at": started,
        "capture_finished_at": datetime.now(UTC).isoformat(),
        "database_sha256": after,
        "native_set_sha256": digest([r["native"] for r in records]),
        "relationships": links,
    }, native_rows


def finance_references(repository, config):
    acceptance = load_pin(config["acceptance"], private=False)
    lock = load_pin(config["source_lock"], private=False)
    require(
        acceptance.get("status") == "OWNER_ACCEPTED_EXACT_PACKET",
        "Exact accepted finance packet required",
    )
    controlling = lock.get("controlling_source", {})
    commit = controlling.get("commit")
    require(
        isinstance(commit, str) and re.fullmatch("[0-9a-f]{40}", commit),
        "Exact historical finance commit required",
    )

    def path(name):
        value = Path(name)
        require(
            not value.is_absolute() and ".." not in value.parts,
            "Relative finance source path required",
        )
        result = repository / value
        require(result.resolve().is_relative_to(repository), "Finance path outside repository")
        return result

    artifacts = []
    require(
        isinstance(acceptance.get("artifacts"), dict) and len(acceptance["artifacts"]) <= 256,
        "Explicit accepted finance artifacts required",
    )
    for name, pin in acceptance["artifacts"].items():
        current = sha(raw_file(path(name), private=False))
        require(current == pin, "Accepted finance artifact bytes changed")
        artifacts.append(
            {
                "path": name,
                "accepted_sha256": pin,
                "current_sha256": current,
                "status": "EXACT_ACCEPTED_BYTES_READ_ONLY",
            }
        )
    locked = []
    require(
        isinstance(controlling.get("files"), list) and len(controlling["files"]) <= 256,
        "Explicit historical finance sources required",
    )
    for name in controlling["files"]:
        current = sha(raw_file(path(name), private=False))
        result = subprocess.run(
            ["git", "show", f"{commit}:{name}"], cwd=repository, capture_output=True, check=False
        )
        require(len(result.stdout) <= LIMIT, "Historical finance source bound exceeded")
        old = sha(result.stdout) if result.returncode == 0 else None
        locked.append(
            {
                "path": name,
                "controlling_commit": commit,
                "historical_blob_sha256": old,
                "current_sha256": current,
                "current_matches_historical": current == old if old else None,
                "disposition": "SAME_BYTES"
                if current == old
                else "CURRENT_DIFFERS_PRESERVE_HISTORICAL_LOCK"
                if old
                else "HISTORICAL_OBJECT_NOT_AVAILABLE_LOCALLY_UNRESOLVED",
            }
        )
    return {
        "classification": "READ_ONLY_ACCEPTED_SYNTHETIC_FINANCE_REFERENCE_NOT_IMPORTED",
        "acceptance_status": acceptance.get("status"),
        "accepted_date": acceptance.get("accepted_date"),
        "artifacts": artifacts,
        "historical_source_lock": locked,
        "scoped_finance_procedures": "NOT_ESTABLISHED_BY_SELECTED_BASELINE",
        "business_event_at": None,
        "historical_system_owner": None,
        "limits": [
            "Exact packet acceptance is not an executed invoice, signature, "
            "independent corroboration or approved forecast.",
            "Current source differences do not rewrite the historical finance lock. "
            "No finance source was imported or modified.",
        ],
    }


def verify_previous(previous):
    old = load_pin(previous)
    require(
        old.get("schema") == "COMPANY_SOURCE_REGISTER_MANIFEST_V1"
        and type(old.get("register_version")) is int
        and old["register_version"] >= 1,
        "Explicit predecessor register required",
    )
    require(
        isinstance(old.get("members"), dict) and 1 <= len(old["members"]) <= 16,
        "Bounded predecessor members required",
    )
    for name, member in old["members"].items():
        require(
            isinstance(name, str) and Path(name).name == name and name not in (".", ".."),
            "Safe predecessor member required",
        )
        content = raw_file(Path(previous["path"]).parent / name, limit=128 * 1024 * 1024)
        require(
            sha(content) == member["sha256"] and len(content) == member["bytes"],
            "Predecessor register member differs",
        )
    return old


def build(config, *, repository):
    repository = Path(repository).resolve()
    require(
        isinstance(config, dict)
        and set(config) == {"schema", "profiles", "migration", "finance", "previous"},
        "Exact source-register configuration required",
    )
    require(
        config["schema"] == "COMPANY_SOURCE_REGISTER_INPUT_V1"
        and isinstance(config["profiles"], list)
        and 1 <= len(config["profiles"]) <= 4,
        "Explicit bounded profile selection required",
    )
    require(
        len({s["id"] for s in config["profiles"]}) == len(config["profiles"]),
        "Duplicate profile identifier",
    )
    records = []
    snapshots = []
    native = {}
    inputs = []
    profiles = []
    physical = {}
    for selector in config["profiles"]:
        require(
            set(selector) == {"id", "registry", "profile_id", "inventory", "component_domains"},
            "Exact profile selector required",
        )
        registry = load_pin(selector["registry"])
        matrix = load_pin(selector["inventory"])
        inputs += [selector["registry"], selector["inventory"]]
        require(
            registry.get("schema") == "COMPANY_SOURCE_PORTFOLIO_V1"
            and matrix.get("schema") == "SOURCE_READINESS_INVENTORY_V1",
            "Maintained registry/inventory required",
        )
        profile = registry["profiles"][selector["profile_id"]]
        components = profile["components"]
        require(
            set(selector["component_domains"]) == set(components),
            "Every selected component requires explicit domain declaration",
        )
        controls = {r["control"]["id"]: r["control"] for r in matrix["controls"]}
        require(len(controls) == len(matrix["controls"]), "Duplicate scoped control identity")
        profiles.append(
            {
                "id": selector["id"],
                "scope": matrix["scope"],
                "historical_audit_snapshots": matrix["audit_snapshots"],
                "registry_sha256": selector["registry"]["sha256"],
                "historical_matrix_sha256": selector["inventory"]["sha256"],
                "qualification": profile["qualification"],
                "logical_profile_company": profile["company"],
                "physical_company_identity_policy": (
                    "EXPLICIT_REGISTRY_ROUTING_NOT_COMPANY_EQUIVALENCE"
                ),
            }
        )
        aliases = set()
        for component in components:
            declaration = registry["components"][component]
            domain = selector["component_domains"][component]
            require(
                isinstance(domain, str) and domain in DOMAINS, "Supported explicit domain required"
            )

            for system in declaration["systems"]:
                alias = declaration["namespace"] + ":" + system
                require(alias not in aliases, "Ambiguous access alias within profile")
                aliases.add(alias)
            expected = [p for p in matrix["source_versions"] if p["component_id"] == component]
            require(
                all(
                    p["company"] == declaration["company"]
                    and p["branch"] == declaration["branch"]
                    and p["system"] in declaration["systems"]
                    for p in expected
                ),
                "Inventory/registry identity differs",
            )
            snapshot, rows = source_snapshot(
                declaration["root"],
                declaration["company"],
                declaration["branch"],
                declaration["systems"],
                expected,
                profile=selector["id"],
                component=component,
                namespace=declaration["namespace"],
                domain=domain,
                controls=controls,
            )
            snapshots.append(snapshot)
            records.extend(snapshot["records"])
            for pin, row in rows.items():
                native[(str(Path(declaration["root"])), pin)] = row
            for record in snapshot["records"]:
                physical.setdefault(record["physical_record_id"], []).append(
                    {"profile": selector["id"], "component": component, "native": record["native"]}
                )
    migration = config["migration"]
    require(
        set(migration) == {"plan", "receipt", "legacy_root"}, "Explicit migration inputs required"
    )
    plan = load_pin(migration["plan"])
    receipt = load_pin(migration["receipt"])
    inputs += [migration["plan"], migration["receipt"]]
    require(
        receipt["custody_plan_sha256"] == plan["custody_plan_sha256"]
        and receipt["document_count"] == len(plan["legacy_plan"]["documents"]),
        "Migration plan/receipt conflict",
    )
    old_root = Path(migration["legacy_root"])
    require(
        old_root.is_absolute() and old_root == old_root.resolve(),
        "Explicit legacy source root required",
    )
    reconciled = []
    archives = {r["control_id"]: r for r in plan["archives"]}
    for document in plan["legacy_plan"]["documents"]:
        matches = [r for r in receipt["records"] if r["record"] == document["record_id"]]
        require(len(matches) == 1, "Ambiguous migration record identity")
        imported = matches[0]
        pin = native_pin(imported)
        candidates = [(root, row) for (root, k), row in native.items() if k == key(pin)]
        require(len(candidates) == 1, "Migration physical source missing or ambiguous")
        root, row = candidates[0]
        archive = archives[document["control_id"]]
        require(
            row["system"] == archive["system_id"]
            and row["record"] in archive["record_ids"]
            and row["sha256"] == document["sha256"]
            and row["event_at"] is None
            and row["origin"] == "MIGRATED_SYNTHETIC_HISTORY",
            "Documentary migration identity/origin differs",
        )
        relative = Path(document["original_relative_path"])
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and relative.parts[0] == "artifacts",
            "Explicit original artifact path required",
        )
        original = old_root / relative
        require(sha(raw_file(original)) == document["sha256"], "Legacy original byte mismatch")
        require(
            row["available_at"] == _time(document["available_at"])
            and row["imported_at"] == imported["imported_at"]
            and row["provenance"] == imported["provenance"],
            "Migration metadata/provenance differs",
        )
        reconciled.append(
            {
                "id": "MIG-" + digest(document["source_identity"])[:32],
                "old_source_identity": document["source_identity"],
                "old_original_path": str(original),
                "old_original_sha256": document["sha256"],
                "company_store": root,
                "native": pin,
                "custodian_person_id": archive["owner_id"],
                "custody_status": archive["custody_status"],
                "custody_basis": archive["custody_basis"],
                "control_id": document["control_id"],
                "event_at": None,
                "available_at": row["available_at"],
                "actual_imported_at": row["imported_at"],
                "historical_owner": None,
                "dispositions": [
                    {"code": "EXACT_DOCUMENTARY_COPY_VERIFIED", "status": "VERIFIED_BYTES_ONLY"},
                    {"code": "UNKNOWN_BUSINESS_EVENT_DATE", "status": "UNRESOLVED_PRESERVED"},
                    {
                        "code": "HISTORICAL_SYSTEM_OWNER_UNESTABLISHED",
                        "status": "UNRESOLVED_PRESERVED",
                    },
                    {
                        "code": "NOT_CANONICAL_OPERATING_HISTORY",
                        "status": "EXPLICIT_LIMIT_RETAINED",
                    },
                ],
            }
        )
    all_links = [link for s in snapshots for link in s["relationships"]]
    for link in all_links:
        matches = {
            r["physical_record_id"]
            for r in records
            if key(r["native"]) == key(link["declared_target"])
        }
        link["matching_physical_record_ids"] = sorted(matches)
        link["status"] = (
            "UNRESOLVED_OUTSIDE_SELECTED_NATIVE_SET"
            if not matches
            else "UNRESOLVED_AMBIGUOUS_PHYSICAL_STORE"
            if len(matches) > 1
            else "EXACT_NATIVE_MATCH_PRODUCER_LABEL_NOT_GLOBALLY_EQUATED"
        )
    finance = finance_references(repository, config["finance"])
    inputs += [config["finance"]["acceptance"], config["finance"]["source_lock"]]
    previous = config["previous"]
    version = 1
    predecessor = None
    if previous is not None:
        old = verify_previous(previous)
        version = old["register_version"] + 1
        predecessor = previous["sha256"]
        inputs.append(previous)
    return {
        "schema": "COMPANY_SOURCE_OWNERSHIP_REGISTER_V1",
        "register_version": version,
        "predecessor_manifest_sha256": predecessor,
        "profiles": profiles,
        "source_snapshots": snapshots,
        "migration_register": reconciled,
        "finance_references": finance,
        "duplicate_cross_profile_references": [
            {
                "physical_record_id": k,
                "references": v,
                "disposition": (
                    "SAME_PHYSICAL_VERSION_MULTIPLE_PROFILE_REFERENCES_NOT_DUPLICATE_OPERATIONS"
                ),
            }
            for k, v in physical.items()
            if len(v) > 1
        ],
        "relationships": all_links,
        "input_pins": inputs,
        "counts": {
            "profile_native_references": len(records),
            "unique_physical_versions": len(physical),
            "migration_documents": len(reconciled),
            "current_extra_versions_outside_historical_selection": sum(
                len(s["unselected_extras"]) for s in snapshots
            ),
        },
        "limits": [
            "Selected base A/B only; standalone newer operations are not silently included.",
            "Current native verification is separate from historical inventory and "
            "collection claims.",
            "Current access counts are not proof of authorization for a particular "
            "actor or a collection attempt.",
            "Domain declarations and current owner registrations do not establish "
            "historical ownership, employment, deployment or period sufficiency.",
            "Native relationships preserve exact company/branch; SH and SABLEHARBOR "
            "are not merged.",
            "No hidden instructor/world/rubric source was read.",
            "Per-store snapshots are not globally atomic.",
        ],
    }


def write_register(config_path, destination, *, repository):
    config_path = Path(config_path)
    config_raw = raw_file(config_path, limit=1024 * 1024)
    config = _json(config_raw)
    destination = Path(destination)
    require(
        destination.is_absolute()
        and destination == destination.resolve()
        and not destination.exists()
        and destination.parent.is_dir()
        and not destination.parent.stat().st_mode & 0o077,
        "New private report destination required",
    )
    roots = [Path(config["migration"]["legacy_root"]), Path(repository).resolve() / "docs"]
    for selector in config["profiles"]:
        registry = load_pin(selector["registry"])
        roots += [
            Path(registry["components"][c]["root"]).parent
            for c in registry["profiles"][selector["profile_id"]]["components"]
        ]
    require(
        all(not destination.is_relative_to(r) and not r.is_relative_to(destination) for r in roots),
        "Report output overlaps original source",
    )
    code_files = [
        Path(__file__),
        *[
            Path(__file__).with_name(name)
            for name in (
                "source_readiness.py",
                "company_store.py",
                "store.py",
                "private_publication.py",
            )
        ],
    ]
    code_pins = {p.name: sha(p.read_bytes()) for p in code_files}
    code = code_pins[Path(__file__).name]
    report = build(config, repository=repository)

    def recheck():
        require(raw_file(config_path) == config_raw, "Configuration changed during report")
        for spec in report["input_pins"]:
            load_pin(
                spec,
                private=not str(spec["path"]).startswith(
                    str(Path(repository).resolve() / "docs") + "/"
                ),
            )
        for snapshot in report["source_snapshots"]:
            require(
                database_pin(Path(snapshot["physical_store_root"]) / "company.sqlite3")
                == snapshot["database_sha256"],
                "Source changed before publication",
            )
        for row in report["migration_register"]:
            require(
                sha(raw_file(row["old_original_path"])) == row["old_original_sha256"],
                "Old original changed before publication",
            )
        require(
            finance_references(Path(repository).resolve(), config["finance"])
            == report["finance_references"],
            "Finance reference changed before publication",
        )
        if config["previous"] is not None:
            verify_previous(config["previous"])
        require(
            all(sha(p.read_bytes()) == code_pins[p.name] for p in code_files),
            "Register implementation changed before publication",
        )

    recheck()
    parts = {
        "CONFIG.json": config,
        "DOMAIN_MAP.json": {
            k: report[k]
            for k in (
                "schema",
                "register_version",
                "predecessor_manifest_sha256",
                "profiles",
                "source_snapshots",
                "duplicate_cross_profile_references",
                "relationships",
                "counts",
                "limits",
            )
        },
        "MIGRATION_REGISTER.json": {
            "register_version": report["register_version"],
            "predecessor_manifest_sha256": report["predecessor_manifest_sha256"],
            "records": report["migration_register"],
        },
        "FINANCE_REFERENCES.json": report["finance_references"],
        "INPUT_PINS.json": {
            "config_sha256": sha(config_raw),
            "inputs": report["input_pins"],
            "module_sha256": code,
            "implementation_sha256": code_pins,
        },
        "VALIDATION.json": {
            "status": "PASS_READ_ONLY_WITH_EXPLICIT_UNRESOLVED_DISPOSITIONS",
            "counts": report["counts"],
            "originals_unchanged": True,
            "operating_history_migration": "NOT_COMPLETE",
            "professional_sufficiency": "NOT_ASSESSED",
            "globally_atomic": False,
        },
    }
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix="source-register-") as folder:
        stage = Path(folder) / "report"
        stage.mkdir(mode=0o700)
        members = {}
        for name, value in parts.items():
            raw = config_raw if name == "CONFIG.json" else canonical(value).encode()
            require(len(raw) <= 128 * 1024 * 1024, "Report member exceeds bound")
            path = stage / name
            path.write_bytes(raw)
            path.chmod(0o600)
            members[name] = {"sha256": sha(raw), "bytes": len(raw)}
        manifest = {
            "schema": "COMPANY_SOURCE_REGISTER_MANIFEST_V1",
            "register_version": report["register_version"],
            "predecessor_manifest_sha256": report["predecessor_manifest_sha256"],
            "created_at": datetime.now(UTC).isoformat(),
            "members": members,
        }
        path = stage / "MANIFEST.json"
        path.write_text(canonical(manifest))
        path.chmod(0o600)
        recheck()
        publish(stage, destination)
    return manifest
