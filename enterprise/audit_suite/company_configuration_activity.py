"""Read-through original release inputs produce independent local inventory/drift records."""

import json
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .company_change_activity import QUALIFICATION as CHANGE_QUALIFICATION
from .company_change_activity import evaluate
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "LOCAL_CONFIGURATION_INVENTORY_NOT_ENTERPRISE_OR_DEPLOYED_ASSET_CENSUS"
CONTROLS = ["SH-CFG-001", "SH-CFG-002"]
MAX_SOURCE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class ConfigurationRecipe:
    company_id: str
    source_store_id: str
    source_versions_sha256: str
    branch_ids: tuple[str, ...]
    checkpoints: tuple[str, ...]
    local_asset_id: str


def read_originals(source_root):
    """Trusted operator read only; never initialize, grant access or execute incoming schema."""
    path = Path(source_root).absolute() / "company.sqlite3"
    if (
        not path.is_file()
        or any(p.is_symlink() for p in [path, *path.parents])
        or path.stat().st_mode & 0o077
        or path.stat().st_nlink != 1
        or path.parent.stat().st_mode & 0o077
    ):
        raise CompanyStoreError("Existing private nonsymlink company source required")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        count, size = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(content)),0) FROM versions"
        ).fetchone()
        if not 1 <= count <= 1000 or size > MAX_SOURCE_BYTES:
            raise CompanyStoreError("Bounded original source set required")
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT company,branch,system,record,version,event_at,"
                "available_at,origin,provenance,content,sha256 FROM versions "
                "ORDER BY company,branch,system,record,version"
            )
        ]
    finally:
        db.close()
    if not 1 <= len(rows) <= 1000 or sum(len(row["content"]) for row in rows) > MAX_SOURCE_BYTES:
        raise CompanyStoreError("Bounded original source set required")
    for row in rows:
        if sha(row["content"]) != row["sha256"]:
            raise CompanyStoreError("Original source hash mismatch")
    pin = sha(encoded([{k: v for k, v in row.items() if k != "content"} for row in rows]))
    return rows, pin


def compare_configuration(actual, desired):
    evaluate(actual)
    evaluate(desired)
    differences = [
        {"field": key, "actual": actual[key], "desired": desired[key]}
        for key in sorted(desired)
        if actual[key] != desired[key]
    ]
    return {
        "actual_configuration_sha256": sha(encoded(actual)),
        "desired_configuration_sha256": sha(encoded(desired)),
        "field_differences": differences,
        "matches_approved_desired": not differences,
        "actual_local_calculation": evaluate(actual),
        "desired_local_calculation": evaluate(desired),
    }


def generate(destination, *, repository, source_root, recipe: ConfigurationRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in [destination, *destination.parents])
    ):
        raise CompanyStoreError("New private configuration destination required")
    if destination.resolve().is_relative_to(Path(source_root).resolve()):
        raise CompanyStoreError("Configuration output must be outside original source tree")
    for value in (recipe.company_id, recipe.source_store_id, recipe.local_asset_id):
        _id(value)
    if (
        not isinstance(recipe.branch_ids, tuple)
        or not 1 <= len(recipe.branch_ids) <= 8
        or len(set(recipe.branch_ids)) != len(recipe.branch_ids)
    ):
        raise CompanyStoreError("Distinct explicit original source branches required")
    for branch in recipe.branch_ids:
        _id(branch)
    if not isinstance(recipe.checkpoints, tuple) or not 1 <= len(recipe.checkpoints) <= 24:
        raise CompanyStoreError("Bounded explicit checkpoint list required")
    times = [_time(t) for t in recipe.checkpoints]
    if times != sorted(set(times)):
        raise CompanyStoreError("Strictly increasing checkpoints required")
    originals, pin = read_originals(source_root)
    if pin != recipe.source_versions_sha256:
        raise CompanyStoreError("Frozen input source versions changed")
    org = snapshot(repository, as_of=datetime.fromisoformat(times[0]).date().isoformat())
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    assignment = [assignments[c] for c in CONTROLS]
    owner = assignment[0]["primary_person_id"]
    reviewer = assignment[0]["operating_reviewer_person_id"]
    if not owner or not reviewer or any(a["primary_person_id"] != owner for a in assignment):
        raise CompanyStoreError("Actual scoped configuration ownership required")
    pins = dict(org["source_sha256"])
    for path in [
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/audit_suite/company_configuration_activity.py",
    ]:
        pins[path] = sha((repository / path).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    prepared = []
    for branch in recipe.branch_ids:
        rows = [r for r in originals if r["company"] == recipe.company_id and r["branch"] == branch]
        indexed = {(r["system"], r["record"], r["version"]): r for r in rows}

        def ref(row):
            return {
                "source_store_id": recipe.source_store_id,
                "company_id": row["company"],
                "branch_id": row["branch"],
                "system_id": row["system"],
                "record_id": row["record"],
                "version": row["version"],
                "sha256": row["sha256"],
                "available_at": row["available_at"],
            }

        def native(row):
            value = json.loads(row["content"])
            if (
                row["origin"] != "AUTHORED_TRAINING_SOURCE"
                or value.get("classification") != CHANGE_QUALIFICATION
            ):
                raise CompanyStoreError("Explicit local change source required")
            return value

        def linked(link, at, indexed=indexed):
            row = indexed.get((link["system_id"], link["record_id"], link["version"]))
            if (
                row is None
                or row["sha256"] != link["sha256"]
                or row["available_at"] > at
                or row["event_at"] is None
                or row["event_at"] > at
            ):
                raise CompanyStoreError("Unavailable or changed exact upstream source")
            return row

        for at in times:
            visible = [
                r
                for r in rows
                if r["available_at"] <= at and r["event_at"] is not None and r["event_at"] <= at
            ]
            reviews = [
                r
                for r in visible
                if r["system"] == "peer_reviews" and native(r).get("decision") == "APPROVED"
            ]
            releases = [r for r in visible if r["system"] == "local_releases"]
            if not reviews or not releases:
                raise CompanyStoreError(
                    "No actual available approved desired and released configuration"
                )

            def latest(values):
                ordered = sorted(values, key=lambda item: (item["event_at"], item["available_at"]))
                if len(ordered) > 1 and (ordered[-1]["event_at"], ordered[-1]["available_at"]) == (
                    ordered[-2]["event_at"],
                    ordered[-2]["available_at"],
                ):
                    raise CompanyStoreError("Ambiguous simultaneous source state")
                return ordered[-1]

            approval, release = latest(reviews), latest(releases)
            desired_build = linked(native(approval)["artifact"], at)
            actual_build = linked(native(release)["artifact"], at)
            desired_config = linked(native(desired_build)["source"], at)
            actual_config = linked(native(actual_build)["source"], at)
            actual = native(actual_config)["configuration"]
            desired = native(desired_config)["configuration"]
            for build, config in ((actual_build, actual), (desired_build, desired)):
                package = native(build)["package"]
                if (
                    package["configuration"] != config
                    or sha(encoded(package)) != native(build)["package_sha256"]
                ):
                    raise CompanyStoreError(
                        "Upstream package does not match configuration original"
                    )
            if native(release)["active_configuration_sha256"] != sha(encoded(actual)):
                raise CompanyStoreError("Release target pin does not match original package")
            common = {
                "classification": QUALIFICATION,
                "asset_id": recipe.local_asset_id,
                "asset_kind": "IN_MEMORY_LOCAL_CONFIGURATION_TARGET",
                "source_service_reference": native(release)["service_reference"],
                "service_status": native(release)["service_status"],
                "site_references_only": native(release)["site_references_only"],
                "boundary_id": "corporate",
                "observed_at": at,
                "owner_id": owner,
                "operating_reviewer_id": reviewer,
                "custody_basis": "PROPOSED_SCOPED_ASSIGNMENT_NOT_EMPLOYMENT_HISTORY",
                "policy_status": "LOCAL_REFERENCE_RULE_NOT_ACCEPTED_CORPORATE_POLICY",
                "source_versions_sha256": pin,
                "source_store_id": recipe.source_store_id,
            }
            prepared.append(
                (
                    branch,
                    at,
                    common,
                    {
                        "release": ref(release),
                        "build": ref(actual_build),
                        "configuration_source": ref(actual_config),
                        "configuration": actual,
                    },
                    {
                        "approval": ref(approval),
                        "build": ref(desired_build),
                        "configuration_source": ref(desired_config),
                        "configuration": desired,
                    },
                    compare_configuration(actual, desired),
                )
            )
    receipts = []
    with tempfile.TemporaryDirectory(prefix="configuration-stage-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for branch in recipe.branch_ids:
            for system in [
                "configuration_inventory",
                "configuration_desired",
                "configuration_drift",
            ]:
                store.register_system(recipe.company_id, branch, system, owner)
        for index, (branch, at, common, actual, desired, comparison) in enumerate(prepared):
            references = {}
            for system, body, controls in [
                ("configuration_inventory", actual, ["SH-CFG-001"]),
                ("configuration_desired", desired, ["SH-CFG-002"]),
                ("configuration_drift", comparison, ["SH-CFG-002"]),
            ]:
                identity = f"CFG-{index:03}-{system}"
                data = encoded(
                    {**common, **body, "source_records": dict(references), "control_ids": controls}
                )
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    identity,
                    expected_version=0,
                    command_id="CFG-" + sha(encoded([recipe_pin, branch, identity])),
                    event_at=at,
                    available_at=at,
                    content=data,
                    provenance={
                        "name": identity + ".json",
                        "source_reference": identity,
                        "classification": QUALIFICATION,
                        "control_ids": controls,
                        "operational_fact_status": "COMPUTED_LOCAL_REFERENCE_ONLY",
                        "recipe_sha256": recipe_pin,
                        "source_sha256": pins,
                        "upstream_versions_sha256": pin,
                        "source_store_id": recipe.source_store_id,
                        "owner_assignment": assignment,
                    },
                )
                receipts.append(row)
                references[system] = {
                    "system_id": system,
                    "record_id": identity,
                    "version": 1,
                    "sha256": row["sha256"],
                }
        # Verify source did not change while deriving the new independent originals.
        if read_originals(source_root)[1] != pin:
            raise CompanyStoreError("Upstream source changed during computation")
        result = {
            "status": "LOCAL_CONFIGURATION_SOURCES_CREATED",
            "source_versions_sha256": pin,
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_sha256": pins,
            "records": receipts,
            "owner_id": owner,
            "reviewer_id": reviewer,
            "control_ids": CONTROLS,
            "not_exercised": ["SH-CFG-003", "SH-CFG-004"],
            "limitations": [
                "One local target, not enterprise inventory or full-period coverage.",
                "No live deployment, patching, secrets or accepted corporate policy.",
            ],
        }
        receipt_path = Path(temp) / "SOURCE_RECEIPT.json"
        receipt_path.write_bytes(encoded(result))
        receipt_path.chmod(0o600)
        publish(Path(temp), destination)
    return result
