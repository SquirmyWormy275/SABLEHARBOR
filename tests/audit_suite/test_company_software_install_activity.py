"""An inert native source exercise exists before the auditor collects it."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

import pytest

from enterprise.audit_suite.company_software_install_activity import decide_install, run_exercise
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.engine import COLLECTIONS, Engine


@pytest.fixture
def exercise(tmp_path):
    root = tmp_path / "company"
    root.mkdir(mode=0o700)
    destination = root / "local-install"
    receipt = run_exercise(
        destination,
        company_id="LOCAL",
        branch_id="software-install-exercise",
        exercise_id="SWI-EXERCISE-1",
        owner_id="LOCAL-OWNER",
        approver_id="LOCAL-APPROVER",
        responder_id="LOCAL-RESPONDER",
    )
    return destination, receipt


def original(root, pin):
    with sqlite3.connect(f"file:{root / 'company.sqlite3'}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT event_at,available_at,content,sha256 FROM versions WHERE "
            "company=? AND branch=? AND system=? AND record=? AND version=?",
            tuple(pin[k] for k in ("company", "branch", "system", "record", "version")),
        ).fetchone()
    assert row is not None
    event, available, raw, digest = row
    assert event == available and digest == pin["sha256"]
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw), raw


def test_native_chain_and_exact_local_decisions(exercise):
    root, receipt = exercise
    pins = receipt["native_pins"]
    assert len(pins) == 12
    bodies = {name: original(root, pin)[0] for name, pin in pins.items()}
    definition = bodies["DEFINITION"]
    assert definition["fixture_kind"] == "UTF8_TEXT_DIGEST_ONLY_NO_EXECUTABLE_FILE"
    assert definition["owner_id"] != definition["approver_id"] != definition["responder_id"]
    assert bodies["APPROVED-UPDATE"]["approval_pin"] == pins["UPDATE-APPROVAL"]
    assert bodies["APPROVED-UPDATE"]["to_version"] == "fixture-v2"
    assert bodies["INVENTORY-AFTER-UPDATE"]["update_pin"] == pins["APPROVED-UPDATE"]
    denied = bodies["UNAPPROVED-ATTEMPT"]
    assert denied["decision"] == "DENIED_UNAPPROVED_DIGEST"
    assert denied["effect"] == "NO_OS_INSTALL_NO_EXECUTION"
    assert bodies["BLOCK-ALERT-RESPONSE"]["attempt_pin"] == pins["UNAPPROVED-ATTEMPT"]
    assert bodies["BLOCK-ALERT-RESPONSE"]["responder_id"] == "LOCAL-RESPONDER"
    assert bodies["EXCEPTION-DECISION"]["request_pin"] == pins["EXCEPTION-REQUEST"]
    assert bodies["EXCEPTION-DECISION"]["approver_id"] == "LOCAL-APPROVER"
    assert bodies["EXCEPTION-RETRY"]["exception_pin"] == pins["EXCEPTION-DECISION"]
    assert bodies["EXCEPTION-RETRY"]["decision"] == "ALLOWED_BY_ACTIVE_EXACT_LOCAL_EXCEPTION"
    assert bodies["POST-EXPIRY-ATTEMPT"]["decision"] == "DENIED_EXPIRED_LOCAL_EXCEPTION"
    assert bodies["EXCEPTION-RETRY"]["simulated_at"] < bodies["EXCEPTION-DECISION"]["expires_at"]
    assert (
        bodies["POST-EXPIRY-ATTEMPT"]["simulated_at"] == bodies["EXCEPTION-DECISION"]["expires_at"]
    )
    assert bodies["LOCAL-COVERAGE"]["untested_declared_asset_ids"] == ["LOCAL-ASSET-2"]
    exception = bodies["EXCEPTION-DECISION"]
    assert (
        decide_install(
            definition,
            asset_id="LOCAL-ASSET-2",
            fixture_sha256=definition["unapproved_fixture_sha256"],
            simulated_at=bodies["EXCEPTION-RETRY"]["simulated_at"],
            exception=exception,
        )
        == "DENIED_UNAPPROVED_DIGEST"
    )
    assert (
        decide_install(
            definition,
            asset_id="LOCAL-ASSET-1",
            fixture_sha256=definition["approved_fixture_sha256"],
            simulated_at=bodies["EXCEPTION-RETRY"]["simulated_at"],
        )
        == "ALLOWED_APPROVED_DIGEST"
    )
    with pytest.raises(CompanyStoreError, match="Undeclared local asset"):
        decide_install(
            definition,
            asset_id="UNDECLARED",
            fixture_sha256=definition["unapproved_fixture_sha256"],
            simulated_at=bodies["EXCEPTION-RETRY"]["simulated_at"],
            exception=exception,
        )
    assert all(body["qualification"] == receipt["qualification"] for body in bodies.values())
    assert all(
        datetime.fromisoformat(body["recorded_at"]) <= datetime.now(UTC) for body in bodies.values()
    )
    assert (root / "SOURCE-RECEIPT.json").read_bytes() == json.dumps(
        receipt, sort_keys=True, separators=(",", ":")
    ).encode()


def test_distinct_authority_and_new_destination_fail_before_source_write(tmp_path, exercise):
    root, receipt = exercise
    with pytest.raises(CompanyStoreError, match="Distinct local"):
        run_exercise(
            tmp_path / "company" / "invalid",
            company_id="LOCAL",
            branch_id="second",
            exercise_id="SWI-EXERCISE-2",
            owner_id="SAME",
            approver_id="SAME",
            responder_id="OTHER",
        )
    assert not (tmp_path / "company" / "invalid").exists()
    with pytest.raises(CompanyStoreError, match="New canonical private destination"):
        run_exercise(
            root,
            company_id="LOCAL",
            branch_id="second",
            exercise_id="SWI-EXERCISE-2",
            owner_id="OWNER",
            approver_id="APPROVER",
            responder_id="RESPONDER",
        )
    assert json.loads((root / "SOURCE-RECEIPT.json").read_bytes()) == receipt


def test_ordinary_engine_collection_retains_selected_originals_without_source_mutation(
    exercise, tmp_path
):
    root, receipt = exercise
    engine = Engine(tmp_path / "audit", company_root=root)
    actor = engine.store.provision("Technical auditor", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Prospective local installation source collection",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at=datetime.now(UTC).isoformat(),
        configuration={"selections": []},
        scope={
            "boundaries": ["corporate"],
            "period_start": "2026-09-29",
            "period_end": "2026-09-30",
            "timezone": "UTC",
        },
    )
    state["requests"] = [{"id": "REQUEST", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(actor, state, "create")
    engine.company_bindings[state["id"]] = {"company": "LOCAL", "branch": receipt["branch"]}
    for system in (
        "software_definition",
        "software_operation",
        "software_detection",
        "software_exception",
    ):
        engine.company_store.grant(actor, state["id"], "LOCAL", receipt["branch"], system)
    before = hashlib.sha256((root / "company.sqlite3").read_bytes()).hexdigest()
    for name in (
        "DEFINITION",
        "UNAPPROVED-ATTEMPT",
        "BLOCK-ALERT-RESPONSE",
        "EXCEPTION-DECISION",
        "POST-EXPIRY-ATTEMPT",
    ):
        pin = receipt["native_pins"][name]
        command = {
            "command_id": f"collect-{name}",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {
                "system_id": pin["system"],
                "record_id": pin["record"],
                "version": pin["version"],
                "request_id": "REQUEST",
            },
        }
        state = engine.command(actor, state["id"], command)
        artifact = state["artifacts"][-1]
        assert artifact["sha256"] == pin["sha256"]
        assert engine.artifacts.read(artifact) == original(root, pin)[1]
    after = hashlib.sha256((root / "company.sqlite3").read_bytes()).hexdigest()
    assert before != after  # Collection receipts are an append-only company journal.
    with sqlite3.connect(f"file:{root / 'company.sqlite3'}?mode=ro", uri=True) as db:
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 12
        assert db.execute("SELECT count(*) FROM collections").fetchone()[0] == 5
    assert not state["workpapers"] and all(
        task["status"] == "NOT_STARTED" for task in state["tasks"]
    )
