"""Explicit native original export of actual persistent local configuration bytes."""

from pathlib import Path

from . import company_configuration_runtime as runtime_core
from .company_backup_runtime import database, native, require
from .company_store import _id, _json, _now, _time
from .inference import _json as decode
from .operating_source_bridge import encoded, sha

SYSTEM = "configuration_export"
QUALIFICATION = "EXACT_PERSISTENT_LOCAL_TARGET_EXPORT_NOT_DEPLOYMENT_OR_APPROVAL"


def _code_pins():
    return {
        "export_module": sha(Path(__file__).read_bytes()),
        "runtime_module": sha(Path(runtime_core.__file__).read_bytes()),
    }


def _append(db, cfg, raw, at, command_id, provenance):
    require(0 < len(raw) <= runtime_core.LIMIT, "Bounded target export required")
    require(
        db.execute("SELECT count(*) FROM versions").fetchone()[0] < 20000,
        "Runtime native record bound reached",
    )
    key = [
        cfg["company"],
        cfg["branch"],
        SYSTEM,
        "EXPORT-" + sha(encoded([cfg["target_id"], command_id])),
    ]
    fingerprint = sha(
        _json([key, 0, at, at, "AUTHORED_TRAINING_SOURCE", provenance, sha(raw)]).encode()
    )
    db.execute(
        "INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            *key,
            1,
            at,
            at,
            _now(),
            "AUTHORED_TRAINING_SOURCE",
            _json(provenance),
            raw,
            sha(raw),
            command_id,
            fingerprint,
        ),
    )
    return dict(
        zip(
            ("company", "branch", "system", "record", "version", "sha256"),
            (*key, 1, sha(raw)),
            strict=True,
        )
    )


def export_current(
    runtime,
    *,
    expected_runtime_sha256,
    expected_revision,
    command_id,
    expected_current_sha256,
    operator_id,
    event_at,
    rationale,
):
    """Trusted local export; all native/journal/revision writes share one transaction."""
    require(type(expected_revision) is int and expected_revision >= 0, "Exact revision required")
    _id(command_id)
    _id(operator_id)
    require(
        isinstance(rationale, str) and 1 <= len(rationale.strip()) <= 2000,
        "Bounded export rationale required",
    )
    cfg = runtime_core._config(runtime, expected_runtime_sha256)
    require(operator_id == cfg["operator_id"], "Scoped local operator required")
    at = _time(event_at)
    payload = {
        "operation": "EXPORT_CURRENT_CONFIGURATION",
        "expected_runtime_sha256": expected_runtime_sha256,
        "expected_revision": expected_revision,
        "command_id": command_id,
        "expected_current_sha256": expected_current_sha256,
        "operator_id": operator_id,
        "event_at": at,
        "rationale": rationale,
    }
    digest = sha(encoded(payload))
    code = _code_pins()
    with database(runtime, True) as db:
        state, raw, _ = runtime_core._current(runtime, db, cfg, expected_runtime_sha256)
        old = db.execute(
            "SELECT * FROM configuration_commands WHERE command=?", (command_id,)
        ).fetchone()
        if old:
            require(old["digest"] == digest, "Command replay differs")
            result = decode(old["result"])
            original = native(db, result["native_pin"])
            require(
                sha(original["content"]) == expected_current_sha256,
                "Retained export differs from original command target",
            )
            require(
                result["native_pin"]["sha256"] == expected_current_sha256,
                "Retained export target pin differs",
            )
            require(
                runtime_core._config(runtime, expected_runtime_sha256) == cfg,
                "Runtime sources changed during export replay",
            )
            replay_state, replay_raw, _ = runtime_core._current(
                runtime, db, cfg, expected_runtime_sha256
            )
            require(
                replay_state == state and replay_raw == raw and _code_pins() == code,
                "Runtime or implementation changed during export replay",
            )
            return result
        require(state["revision"] == expected_revision, "Runtime revision conflict")
        require(state["sha256"] == expected_current_sha256, "Current target pin differs")
        require(at >= state["event_at"], "Export precedes current runtime event")
        registered = db.execute(
            "SELECT owner FROM systems WHERE company=? AND branch=? AND system=?",
            (cfg["company"], cfg["branch"], SYSTEM),
        ).fetchone()
        require(
            registered is None or registered["owner"] == operator_id, "Export system owner differs"
        )
        db.execute(
            "INSERT OR IGNORE INTO systems VALUES(?,?,?,?)",
            (cfg["company"], cfg["branch"], SYSTEM, operator_id),
        )
        provenance = {
            "name": cfg["target_id"] + "-configuration.json",
            "source_reference": cfg["target_id"],
            "classification": QUALIFICATION,
            "control_ids": ["SH-ENG-004", "SH-CFG-002"],
            "runtime_sha256": expected_runtime_sha256,
            "target_id": cfg["target_id"],
            "runtime_revision_at_export": state["revision"],
            "target_sha256": sha(raw),
            "target_object_name": state["file"],
            "prior_runtime_operation_at": state["event_at"],
            "exported_at": at,
            "operator_id": operator_id,
            "rationale": rationale,
            "authorization": "EXPLICIT_LOCAL_OPERATOR_EXPORT_NOT_RELEASE_APPROVAL",
            "source_pins": cfg["source_pins"],
            "code_sha256": code,
        }
        exported = _append(db, cfg, raw, at, command_id, provenance)
        result = {
            "operation": "EXPORT_CURRENT_CONFIGURATION",
            "revision": expected_revision + 1,
            "native_pin": exported,
            "current_sha256": sha(raw),
            "target_changed": False,
            "runtime_sha256": expected_runtime_sha256,
            "provenance": provenance,
            "qualification": QUALIFICATION,
            "automatic_ticket_closure": False,
        }
        require(
            runtime_core._config(runtime, expected_runtime_sha256) == cfg,
            "Runtime source pins changed before export commit",
        )
        final_state, final_raw, _ = runtime_core._current(runtime, db, cfg, expected_runtime_sha256)
        require(final_state == state and final_raw == raw, "Current target changed during export")
        require(_code_pins() == code, "Export implementation changed before commit")
        db.execute(
            "UPDATE configuration_state SET revision=?,event_at=? WHERE id=1",
            (result["revision"], at),
        )
        db.execute(
            "INSERT INTO configuration_commands VALUES(?,?,?)",
            (command_id, digest, encoded(result)),
        )
    return result
