"""Explicit configuration-original admission to a declared local backup dataset.

Trusted local operator, no audit grants or evidence generation. Physical routing
and an exact native runtime definition bind identity, not producer authenticity.
"""

from pathlib import Path

from . import company_backup_runtime as backup
from .company_lifecycle_activity import _source_stamp
from .company_store import _id, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha

MAX_METADATA = 256 * 1024
QUALIFICATION = "EXACT_LOCAL_CONFIGURATION_BYTES_NOT_DEPLOYMENT_OR_ENTERPRISE_COMPLETENESS"


def _hash(value):
    backup.require(
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "Exact SHA256 required",
    )


def _read(source_root, source_pin, source_definition_pin):
    root = backup.private(Path(source_root), True)
    backup.exact_pin(source_pin)
    backup.exact_pin(source_definition_pin)
    backup.require(source_pin["system"] == "configuration_export", "Configuration export required")
    backup.require(
        source_definition_pin["system"] == "configuration_runtime"
        and source_definition_pin["version"] == 1,
        "Original configuration runtime definition required",
    )
    stamp = _source_stamp(root / "company.sqlite3")
    definition_raw = backup.checked_bytes(root / "RUNTIME.json", 2 * 1024 * 1024)
    definition = decode(definition_raw)
    backup.require(
        isinstance(definition, dict)
        and all(isinstance(definition.get(k), str) for k in ("company", "branch", "target_id"))
        and sha(definition_raw) == source_definition_pin["sha256"]
        and definition.get("format") == "LOCAL_CONFIGURATION_RUNTIME_V1",
        "Source runtime definition differs",
    )
    with backup.database(root) as db:
        for ref, limit in (
            (source_pin, backup.MAX_BYTES),
            (source_definition_pin, 2 * 1024 * 1024),
        ):
            size = db.execute(
                "SELECT length(content),length(CAST(provenance AS BLOB)) FROM versions "
                "WHERE company=? AND branch=? AND system=? AND record=? AND version=?",
                tuple(ref[k] for k in backup.FIELDS[:-1]),
            ).fetchone()
            backup.require(
                size is not None and 0 < size[0] <= limit and size[1] <= MAX_METADATA,
                "Bounded source original required",
            )
        original = backup.native(db, source_pin)
        declared = backup.native(db, source_definition_pin)
    backup.require(declared["content"] == definition_raw, "Native source definition differs")
    provenance = decode(original["provenance"])
    backup.require(
        isinstance(provenance, dict)
        and (
            original["company"],
            original["branch"],
            declared["company"],
            declared["branch"],
            declared["record"],
        )
        == (
            definition["company"],
            definition["branch"],
            definition["company"],
            definition["branch"],
            definition["target_id"],
        )
        and provenance.get("runtime_sha256") == source_definition_pin["sha256"]
        and provenance.get("target_id") == definition["target_id"]
        and provenance.get("target_sha256") == source_pin["sha256"],
        "Export runtime identity differs",
    )
    metadata = {
        k: original[k] for k in (*backup.FIELDS, "event_at", "available_at", "origin", "provenance")
    }
    definition_metadata = {
        k: declared[k] for k in (*backup.FIELDS, "event_at", "available_at", "origin", "provenance")
    }
    backup.require(
        declared["event_at"] is not None
        and original["event_at"] is not None
        and _time(declared["event_at"])
        <= _time(declared["available_at"])
        <= _time(original["event_at"]),
        "Source definition unavailable at export",
    )
    metadata_bundle = {"original": metadata, "definition": definition_metadata}
    backup.require(len(encoded(metadata_bundle)) <= MAX_METADATA, "Source metadata limit")
    location = sha(str(root).encode())
    identity = "SOURCE-" + sha(
        encoded({"location_sha256": location, "definition": source_definition_pin})
    )
    backup.require(
        _source_stamp(root / "company.sqlite3") == stamp
        and backup.checked_bytes(root / "RUNTIME.json", 2 * 1024 * 1024) == definition_raw,
        "Source changed during admission read",
    )
    return original["content"], {
        "source_store_id": identity,
        "source_location_sha256": location,
        "source_definition_pin": source_definition_pin,
        "source_pin": source_pin,
        "metadata": metadata,
        "definition_metadata": definition_metadata,
        "metadata_sha256": sha(encoded(metadata_bundle)),
        "identity_basis": "LOCAL_ROUTING_IDENTITY_NOT_PRODUCER_AUTHENTICATION",
    }


def inspect_source(source_root, *, source_pin, source_definition_pin):
    """Read only explicitly pinned original; supplies reviewable metadata, never latest."""
    source_pin, source_definition_pin = decode(encoded([source_pin, source_definition_pin]))
    _, selected = _read(source_root, source_pin, source_definition_pin)
    return selected


def admit_dataset(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    dataset_id,
    operator_id,
    event_at,
    source_root,
    source_store_id,
    source_pin,
    source_definition_pin,
    expected_source_metadata_sha256,
    previous_pin=None,
):
    """Dataset original, dependency provenance, command and revision commit together."""
    source_pin, source_definition_pin, previous_pin = decode(
        encoded([source_pin, source_definition_pin, previous_pin])
    )
    _id(dataset_id)
    _id(source_store_id)
    _hash(expected_source_metadata_sha256)
    root = backup.private(Path(runtime), True)
    source_root = backup.private(Path(source_root), True)
    backup.require(
        not source_root.is_relative_to(root) and not root.is_relative_to(source_root),
        "Source and consumer roots must be disjoint",
    )
    at = _time(event_at)
    raw, selected = _read(source_root, source_pin, source_definition_pin)
    backup.require(
        selected["source_store_id"] == source_store_id
        and selected["metadata_sha256"] == expected_source_metadata_sha256,
        "Pinned source binding or metadata differs",
    )
    metadata = selected["metadata"]
    backup.require(
        metadata["event_at"] is not None
        and _time(metadata["event_at"]) <= _time(metadata["available_at"]) <= at,
        "Future, undated or inconsistent source chronology",
    )
    cfg = backup._config(root, expected_runtime_sha256)
    backup.require(operator_id == cfg["operator_id"], "Configured local operator required")
    backup.require(dataset_id in cfg["datasets"], "Dataset not declared")
    if previous_pin is not None:
        backup.exact_pin(previous_pin)
    if cfg["datasets"][dataset_id] == "JSON_RECORDS":
        backup._records(raw)
    code = {p.name: sha(p.read_bytes()) for p in (Path(__file__), Path(backup.__file__))}
    dependency = {
        **selected,
        "dataset_id": dataset_id,
        "consumer_runtime_sha256": expected_runtime_sha256,
        "consumer_runtime_id": cfg["runtime_id"],
        "consumed_at": at,
        "qualification": QUALIFICATION,
    }
    payload = {
        "kind": "NATIVE_DATASET_ADMISSION",
        "dataset_id": dataset_id,
        "operator_id": operator_id,
        "dependency": dependency,
        "previous_pin": previous_pin,
    }

    def perform(db, current, moment):
        backup.require(current == cfg, "Consumer definition changed")
        backup._previous(db, current, "source_dataset", dataset_id, previous_pin, moment)
        receipt_dependency = {**dependency, "execution_source_sha256": code}
        ref = backup._insert(
            db,
            current,
            "source_dataset",
            dataset_id,
            raw,
            moment,
            "ADMIT-" + sha(command_id.encode())[:48],
            source_admission=receipt_dependency,
        )
        again_raw, again = _read(source_root, source_pin, source_definition_pin)
        backup.require(
            again_raw == raw and encoded(again) == encoded(selected),
            "Original changed during admission",
        )
        backup.require(
            all(
                sha(p.read_bytes()) == code[p.name] for p in (Path(__file__), Path(backup.__file__))
            ),
            "Admission implementation changed",
        )
        return {
            "status": "SOURCE_DATASET_ADMITTED",
            "source_pin": ref,
            "dependency": receipt_dependency,
        }

    result = backup._execute(
        root, expected_runtime_sha256, expected_revision, command_id, at, payload, perform
    )
    # This check also runs for an existing command: legacy _execute replay does
    # not inspect consumer originals. A post-commit failure never rolls back an
    # already committed operation; inspect/replay the unchanged command.
    backup.require(
        isinstance(result, dict)
        and set(result)
        == {
            "command_id",
            "revision",
            "event_at",
            "runtime_sha256",
            "qualification",
            "status",
            "source_pin",
            "dependency",
        }
        and result["command_id"] == command_id
        and type(result["revision"]) is int
        and result["revision"] == expected_revision + 1
        and result["event_at"] == at
        and result["runtime_sha256"] == expected_runtime_sha256
        and result["qualification"] == backup.QUALIFICATION
        and result["status"] == "SOURCE_DATASET_ADMITTED"
        and isinstance(result["dependency"], dict)
        and isinstance(result["source_pin"], dict),
        "Retained admission receipt differs",
    )
    with backup.database(root) as db:
        current = backup._config(root, expected_runtime_sha256)
        backup._bound_config(db, current, expected_runtime_sha256)
        backup.require(
            current == cfg and operator_id == current["operator_id"],
            "Current configured operator or runtime differs",
        )
        admitted = backup.native(db, result["source_pin"])
        retained = result["dependency"]
        backup.require(
            encoded({k: v for k, v in retained.items() if k != "execution_source_sha256"})
            == encoded(dependency)
            and (admitted["company"], admitted["branch"], admitted["system"], admitted["record"])
            == (cfg["plan"]["company_id"], cfg["plan"]["branch_id"], "source_dataset", dataset_id)
            and admitted["version"] == (1 if previous_pin is None else previous_pin["version"] + 1)
            and admitted["command_id"] == "ADMIT-" + sha(command_id.encode())[:48]
            and admitted["content"] == raw
            and admitted["event_at"] == at
            and admitted["available_at"] == at
            and encoded(decode(admitted["provenance"]).get("source_admission"))
            == encoded(retained),
            "Retained consumer original or dependency differs",
        )
        again_raw, again = _read(source_root, source_pin, source_definition_pin)
        backup.require(
            again_raw == raw and encoded(again) == encoded(selected),
            "Original changed before admission receipt return",
        )
        backup.require(
            backup._config(root, expected_runtime_sha256) == cfg,
            "Consumer definition changed before receipt return",
        )
    return result
