"""Fresh owned source editions; no current company/audit/Key inputs or outcome imports."""

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite import company_operating_source_edition as edition
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_operating_depth_runtime import (
    full_period,  # noqa: F401 - genuine existing 36-original fixture
    original,
    setup_declaration,
)

REPO = Path(__file__).resolve().parents[2]


def at(value):
    return _time(value)


def ptr(step, *fields):
    return {"$result": {"step": step, "fields": list(fields)}}


def loc(value):
    return {"$edition_path": value}


def save(path, value):
    return edition.write_new(path, value)


@pytest.fixture
def owned(full_period, tmp_path, monkeypatch):  # noqa: F811 - pytest fixture injection
    store, periods, _ = full_period
    scope = {"company": "SH", "branch": "depth-owned"}
    release = original(
        store,
        "transition.site_release",
        "RL-OWN",
        {
            "fictional_in_universe_operating_release": True,
            "status": "OPERATING_RECOVERY_SIMULATED",
        },
    )
    data = original(
        store,
        "config_bytes",
        "CONFIG-BYTES",
        {
            "records": [{"id": "ONE", "value": 1}, {"id": "TWO", "value": 2}],
        },
    )
    doc = original(
        store,
        "supplementalops.policy_document",
        "SUP-OWN-V2",
        {
            "text": "Owned November version2 bytes; no human acknowledgment.",
        },
        at=at("2027-10-30T00:00:00Z"),
        owner="AS-P005",
    )
    values = {"timeout_ms": 40, "attempts": 3, "max_total_ms": 125}
    cfg = original(
        store,
        "configurations",
        "CONFIG-CORRECTED",
        {
            "configuration": values,
            "configuration_sha256": sha(encoded(values)),
        },
        owner="P005",
    )
    package = {"format": "LOCAL_CONFIG_PACKAGE_V1", "configuration": values}
    build = original(
        store,
        "builds",
        "BUILD-CORRECTED",
        {
            "package": package,
            "package_sha256": sha(encoded(package)),
            "source": {
                "system_id": cfg["system"],
                "record_id": cfg["record"],
                "version": 1,
                "sha256": cfg["sha256"],
                "available_at": at("2027-01-01T00:00:00Z"),
            },
        },
        owner="P005",
    )
    tested = original(
        store,
        "tests",
        "TEST-CORRECTED",
        {
            "artifact": {
                "system_id": build["system"],
                "record_id": build["record"],
                "version": 1,
                "sha256": build["sha256"],
                "available_at": at("2027-01-01T00:00:00Z"),
            },
        },
        owner="P005",
    )
    # Whole ordinary seed is independently byte-pinned, including late originals.
    capsule = tmp_path / "capsule"
    capsule.mkdir(mode=0o700)
    (capsule / "company").mkdir(mode=0o700)
    raw = store.path.read_bytes()
    fd = os.open(capsule / "company/company.sqlite3", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    with store._db() as db:
        counts = {
            t: db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
            for t in ("systems", "versions", "grants", "collections", "access_events")
        }
    capsule_pin = save(
        capsule / "MANIFEST.json",
        {
            "format": "PRIVATE_COMPANY_ACTIVITY_RUN_V1",
            "audit_created": False,
            "grants_created": False,
            "counts": counts,
            "members": {"company/company.sqlite3": sha(raw)},
        },
    )
    concrete = tmp_path / "CONCRETE.json"
    # This fixture selects its own tiny authoring contract; actual source-edition
    # admission retains the production CONCRETE_SHA and private reviewed plan.
    concrete_pin = save(
        concrete,
        {
            "schema": "SH_NATIVE_OPERATING_DEPTH_CONCRETE_EDITION_PLAN_V1",
            "qualification": "OWN_AUTHOR_MECHANICS_ONLY_NOT_ACTUAL_ROOT_SOURCE_ACCEPTANCE",
        },
    )
    monkeypatch.setattr(edition, "CONCRETE_SHA", concrete_pin["sha256"])
    inputs = periods + [release, data, doc, cfg, build, tested]
    program = []

    def step(id, action, time, arguments, refs=()):
        program.append(
            dict(
                id=id,
                mode="CLEAN",
                action=action,
                at=at(time),
                arguments=arguments,
                source_refs=list(refs),
            )
        )

    inventory = {
        "systems": [
            {"system": "SVC-compute", "owner": "AS-P007"},
            {
                "system": "POLICY",
                "owner": "AS-P005",
                "recipients": ["AS-P007", "AS-P008"],
                "document_sha256": doc["sha256"],
            },
            {"system": "RETRY", "owner": "P005"},
        ],
        "whole_estate_claim": "NOT_ESTABLISHED_OUTSIDE_DECLARED_NATIVE_SYSTEMS",
        "operating_depth_calendar": {
            "declared_at": at("2027-10-31T00:00:00Z"),
            "period_start": at("2027-11-01T09:00:00Z"),
            "period_end_exclusive": at("2027-12-01T00:00:00Z"),
            "cadence_days": 30,
            "due_offset_days": 1,
            "items": [
                dict(
                    id=id,
                    system_id=system,
                    kind=kind,
                    operating_from=at("2027-01-01T00:00:00Z")
                    if kind == "RESTORE"
                    else at("2027-11-01T09:00:00Z"),
                    operating_to_exclusive=at("2027-12-01T00:00:00Z"),
                    commissioning_ref=release if kind == "RESTORE" else None,
                )
                for id, system, kind in [
                    ("RESTORE", "SVC-compute", "RESTORE"),
                    ("POLICY", "POLICY", "POLICY"),
                    ("RETRY", "RETRY", "RETRY"),
                ]
            ],
            "exclusions": [],
        },
    }
    step(
        "INVENTORY",
        "APPEND_NATIVE",
        "2027-10-31T00:00:00Z",
        {
            "system": "business_inventory",
            "record": "OWN-EDITION.CALENDAR",
            "owner_id": "AS-P007",
            "body": inventory,
            "basis_refs": [release],
        },
        [release],
    )
    calendar_args = dict(
        business_inventory_pin=ptr("INVENTORY", "native_pin"),
        retained_period_refs=[],
        runtime_id="OWN-EDITION.DEPTH",
        actor_id="AS-P007",
        recorded_at=at("2027-10-31T00:01:00Z"),
        command_id="REGISTER-OWN",
    )
    step("CALENDAR", "REGISTER_CALENDAR", "2027-10-31T00:01:00Z", calendar_args)
    due = dict(
        period_id="OWN-EDITION.RECOVERY",
        company_id="SH",
        branch_id="depth-owned",
        owner_id="AS-P007",
        control_ids=["SH-BCM-002", "SH-BCM-003"],
        period_start=at("2027-11-01T00:00:00Z"),
        period_end_exclusive=at("2027-11-04T00:00:00Z"),
        declared_at=at("2027-10-31T00:02:00Z"),
        inventory=[dict(id="DATA", description="Independent owned JSON records")],
        local_basis="Explicit new copy/return slots; never cure historical R1 or R2",
        schedule=[
            dict(
                id=id,
                inventory_ids=["DATA"],
                control_id=control,
                due_at=at(time),
                window_start=at("2027-11-01T00:00:00Z"),
                window_end_exclusive=at("2027-11-04T00:00:00Z"),
                depends_on=[],
            )
            for id, control, time in [
                ("B1", "SH-BCM-002", "2027-11-01T10:00:00Z"),
                ("R1", "SH-BCM-003", "2027-11-02T11:00:00Z"),
            ]
        ],
    )
    step("DUE", "PERIOD_DECLARE", "2027-10-31T00:02:00Z", {"plan": due})
    step(
        "BACKUP",
        "BACKUP_INITIALIZE",
        "2027-10-31T00:03:00Z",
        {
            "declaration_root": loc("ledger:DUE"),
            "declaration_ref": ptr("DUE", "native_pin"),
            "bindings": [
                dict(occurrence_id=id, dataset_id="DATA", operation=op)
                for id, op in [("B1", "BACKUP"), ("R1", "RESTORE")]
            ],
            "datasets": [dict(id="DATA", format="JSON_RECORDS")],
        },
    )
    step(
        "CRITERION",
        "APPEND_NATIVE",
        "2027-11-01T07:00:00Z",
        {
            "system": "service_criterion",
            "record": "OWN-EDITION.RETURN",
            "owner_id": "AS-P007",
            "body": dict(
                schema="SH_LOCAL_SERVICE_RETURN_CRITERION_V1",
                service_id="SVC-compute",
                dataset_id="DATA",
                author_id="AS-P007",
                reviewer_id="AS-P008",
                approved_at=at("2027-11-01T07:00:00Z"),
                max_age_seconds=200000,
                max_restore_seconds=10,
                min_record_count=2,
                qualification="LOCAL_SIMULATED_SERVICE_CRITERION_NOT_ENTERPRISE_BIA",
            ),
            "basis_refs": [release, data],
        },
        [release, data],
    )

    def backup_call(id, action, time, revision, **arguments):
        step(
            id,
            action,
            time,
            dict(
                runtime=loc("runtime:BACKUP"),
                expected_runtime_sha256=ptr("BACKUP", "runtime_sha256"),
                expected_revision=revision,
                command_id=id,
                **arguments,
            ),
            [data] if action == "DATASET_COPY" else [],
        )

    backup_call(
        "DATA",
        "DATASET_COPY",
        "2027-11-01T08:00:00Z",
        0,
        dataset_id="DATA",
        source_content_pin=data,
        expected_sha256=data["sha256"],
        event_at=at("2027-11-01T08:00:00Z"),
    )
    for id, op, revision, time in [
        ("LEASEB", "BACKUP_WRITE", 1, "2027-11-01T09:00:00Z"),
        ("LEASER", "RESTORE_READ", 2, "2027-11-01T09:01:00Z"),
    ]:
        backup_call(
            id,
            "LEASE_RECORD",
            time,
            revision,
            operation=op,
            enabled=True,
            valid_from=at("2027-11-01T00:00:00Z"),
            expires_at=at("2027-11-04T00:00:00Z"),
            event_at=at(time),
        )
    backup_call(
        "CONTRACT",
        "USE_CONTRACT",
        "2027-11-01T09:02:00Z",
        3,
        occurrence_id="R1",
        source_pin=ptr("DATA", "source_pin"),
        reader=dict(kind="JSON_RECORD_FIELD_EQUALS", record_id="ONE", field="value", expected=1),
        rationale="Read actual returned ONE from the independently copied source",
        event_at=at("2027-11-01T09:02:00Z"),
    )
    pp = dict(
        runtime_id="OWN-EDITION.NOVEMBER",
        **scope,
        owner_id="AS-P005",
        cycle_id="NOVEMBER",
        declared_at=at("2027-11-01T09:03:00Z"),
        due_at=at("2027-11-02T09:00:00Z"),
        recipients=["AS-P007", "AS-P008"],
        local_basis="Exact owned native November policy bytes",
    )
    step(
        "POLICY",
        "POLICY_INITIALIZE",
        "2027-11-01T09:03:00Z",
        {
            "plan": pp,
            "documents": [dict(id="NOVEMBER-V2", source_root=loc("company"), source_pin=doc)],
        },
        [doc],
    )
    for revision, (operation, recipient) in enumerate(
        [
            ("DELIVER", "AS-P007"),
            ("READ_RETURN", "AS-P007"),
            ("DELIVER", "AS-P008"),
            ("READ_RETURN", "AS-P008"),
        ]
    ):
        time = f"2027-11-01T09:{10 + revision:02}:00Z"
        step(
            "POL" + str(revision),
            "POLICY_EXECUTE",
            time,
            dict(
                root=loc("runtime:POLICY"),
                expected_runtime_sha256=ptr("POLICY", "runtime_sha256"),
                expected_revision=revision,
                command_id="POL" + str(revision),
                actor_id="AS-P005" if operation == "DELIVER" else recipient,
                operation=operation,
                event_at=at(time),
                rationale="Actual native mailbox bytes and separate recipient read",
                parameters=dict(
                    recipient_id=recipient, document_pin=ptr("POLICY", "selected_document_pin")
                ),
            ),
        )
    backup_call(
        "COPY",
        "BACKUP_RUN",
        "2027-11-01T10:00:00Z",
        4,
        occurrence_id="B1",
        source_pin=ptr("DATA", "source_pin"),
        lease_pin=ptr("LEASEB", "lease_pin"),
        attempted_at=at("2027-11-01T10:00:00Z"),
        rationale="Actual new edition byte copy",
    )
    step(
        "RETRY",
        "RETRY_PROBE",
        "2027-11-01T10:01:00Z",
        dict(
            declaration_pin=ptr("CALENDAR", "native_pin"),
            slot_id="RETRY:0",
            configuration_pin=cfg,
            build_pin=build,
            test_pin=tested,
            actor_id="P005",
            command_id="RETRY-EXISTING-120",
            event_at=at("2027-11-01T10:01:00Z"),
        ),
        [cfg, build, tested],
    )
    backup_call(
        "RETURN",
        "RESTORE_RUN",
        "2027-11-02T11:00:00Z",
        5,
        occurrence_id="R1",
        backup_pin=ptr("COPY", "object_pin"),
        comparison_source_pin=ptr("DATA", "source_pin"),
        lease_pin=ptr("LEASER", "lease_pin"),
        attempted_at=at("2027-11-02T11:00:00Z"),
        rationale="Actual new commissioned return, not predecessor R1 cure",
    )
    backup_call(
        "USE",
        "USE_PROBE",
        "2027-11-02T11:01:00Z",
        6,
        contract_pin=ptr("CONTRACT", "contract_pin"),
        restore_job_pin=ptr("RETURN", "job_pin"),
        restored_dataset_pin=ptr("RETURN", "object_pin"),
        event_at=at("2027-11-02T11:01:00Z"),
    )
    step(
        "BOUND-RETURN",
        "RESTORE_RETURN",
        "2027-11-02T11:02:00Z",
        dict(
            declaration_pin=ptr("CALENDAR", "native_pin"),
            slot_id="RESTORE:0",
            runtime_root=loc("runtime:BACKUP"),
            runtime_sha256=ptr("BACKUP", "runtime_sha256"),
            criterion_pin=ptr("CRITERION", "native_pin"),
            probe_pin=ptr("USE", "probe_pin"),
            actor_id="AS-P007",
            command_id="BOUND-RETURN",
            event_at=at("2027-11-02T11:02:00Z"),
        ),
    )
    step(
        "BOUND-POLICY",
        "POLICY_BIND",
        "2027-11-02T11:03:00Z",
        dict(
            declaration_pin=ptr("CALENDAR", "native_pin"),
            slot_id="POLICY:0",
            runtime_root=loc("runtime:POLICY"),
            runtime_sha256=ptr("POLICY", "runtime_sha256"),
            actor_id="AS-P005",
            command_id="BOUND-POLICY",
            event_at=at("2027-11-02T11:03:00Z"),
        ),
    )
    backup_call(
        "DISABLED",
        "LEASE_RECORD",
        "2027-11-03T00:00:00Z",
        7,
        operation="RESTORE_READ",
        enabled=False,
        valid_from=at("2027-11-01T00:00:00Z"),
        expires_at=at("2027-11-04T00:00:00Z"),
        previous_pin=ptr("LEASER", "lease_pin"),
        event_at=at("2027-11-03T00:00:00Z"),
    )
    backup_call(
        "FAILED",
        "RESTORE_RUN",
        "2027-11-03T01:00:00Z",
        8,
        occurrence_id="R1",
        backup_pin=ptr("COPY", "object_pin"),
        comparison_source_pin=ptr("DATA", "source_pin"),
        lease_pin=ptr("DISABLED", "lease_pin"),
        prior_attempt_pin=ptr("RETURN", "job_pin"),
        attempted_at=at("2027-11-03T01:00:00Z"),
        rationale="New disabled-lease failure remains failed",
    )
    step(
        "BOUND-FAILURE",
        "RESTORE_FAILURE",
        "2027-11-03T01:01:00Z",
        dict(
            declaration_pin=ptr("CALENDAR", "native_pin"),
            slot_id="RESTORE:0",
            runtime_root=loc("runtime:BACKUP"),
            runtime_sha256=ptr("BACKUP", "runtime_sha256"),
            job_pin=ptr("FAILED", "job_pin"),
            actor_id="AS-P007",
            command_id="BOUND-FAILURE",
            event_at=at("2027-11-03T01:01:00Z"),
            expected_version=1,
        ),
    )
    late = deepcopy(calendar_args)
    late.update(
        retained_period_refs=periods,
        recorded_at=at("2028-01-16T13:00:00Z"),
        command_id="LATE-EXACT-36",
        expected_version=1,
    )
    step("LATE36", "REGISTER_CALENDAR", "2028-01-16T13:00:00Z", late, periods)
    plan = dict(
        schema=edition.PLAN,
        edition_id="OWN-EDITION",
        qualification=edition.QUALIFICATION,
        capsule=capsule_pin,
        concrete_plan=dict(path=str(concrete), sha256=sha(concrete.read_bytes())),
        modes=[
            dict(
                mode="CLEAN",
                **scope,
                retained_period_refs=periods,
                original_input_refs=inputs,
                historical_unperformed=[
                    dict(
                        id="PREDECESSORS",
                        reason="Historical R1/R2 have no prospective new criterion",
                        source_refs=[release],
                    )
                ],
            )
        ],
        program=program,
        finish_at=at("2028-01-16T13:00:00Z"),
        fresh_audit_not_before=at("2028-01-17T00:00:00Z"),
        source_unknowns=[
            "Unnamed wider estate and human operating acceptance are not established."
        ],
    )
    return dict(plan=plan, root=tmp_path, source=store, source_raw=store.path.read_bytes())


def authorize(owned, plan=None, name="A"):
    plan = owned["plan"] if plan is None else plan
    root = owned["root"]
    plan_pin = save(root / (name + "-PLAN.json"), plan)
    review = save(
        root / (name + "-OWN-REVIEW.json"),
        {
            "source_only": True,
            "capsule": plan["capsule"],
            "native_fields_preserved": True,
            "qualification": "OWN_AUTHOR_MECHANICS_ONLY_NOT_ACTUAL_ROOT_SOURCE_ACCEPTANCE",
        },
    )
    admission = save(
        root / (name + "-ADMISSION.json"),
        dict(
            schema=edition.ADMISSION,
            status="APPROVED_OWN_NEW_SOURCE_MECHANISM_ONLY",
            plan=plan_pin,
            capsule=plan["capsule"],
            concrete_plan=plan["concrete_plan"],
            code_pins=edition._code(),
            source_review=review,
            original_edition_preserved=True,
            current_pipeline_complete=False,
            actual_execution=False,
        ),
    )
    return plan_pin, admission


def run(owned, pins, destination="edition"):
    return edition.execute(*pins, repository=REPO, destination=owned["root"] / destination)


def test_source_first_real_policy_retry_copy_restore_failure_and_late36(owned):
    pins = authorize(owned)
    preview = edition.preview(*pins, repository=REPO)
    assert preview["audit_state_or_Key_created"] is False
    assert not (owned["root"] / "edition").exists()
    result = run(owned, pins)
    body = json.loads(Path(result["path"]).read_bytes())
    assert body["source_program_steps"] == len(owned["plan"]["program"])
    assert body["audit_or_Key_created"] is False
    assert body["source_period_censuses"][0]["actual_source_census"][
        "complete_registered_2027_period_join"
    ]
    report = body["registered_calendar_censuses"][0]["actual_declared_due_census"]
    histories = {s["slot_id"]: s["history"] for s in report["slots"]}
    assert [h["observation"]["status"] for h in histories["RESTORE:0"]] == [
        "PASS_LOCAL_SERVICE_RETURN_CRITERION",
        "FAIL_LOCAL_RESTORE_NO_RETURN",
    ]
    assert (
        histories["RETRY:0"][0]["observation"]["calculation"]["calculated_total_timeout_ms"] == 120
    )
    assert histories["POLICY:0"][0]["observation"]["all_recipients_read_return"] is True
    assert histories["POLICY:0"][0]["observation"]["human_acknowledgment"] == "NOT_ESTABLISHED"
    assert owned["source"].path.read_bytes() == owned["source_raw"]
    source = CompanyStore(owned["root"] / "edition/company")
    with source._db() as db:
        rows = db.execute(
            "SELECT * FROM versions WHERE system='operating_depth_definition' ORDER BY version"
        ).fetchall()
        first, last = [json.loads(r["content"]) for r in rows]
        assert first["retained_period_refs"] == [] and len(last["retained_period_refs"]) == 36
        assert last["recorded_at"].startswith("2028-01-16")
        assert all(
            db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] == 0
            for t in ("grants", "collections", "access_events")
        )
    cfg = json.loads((owned["root"] / "edition/runtimes/POLICY/RUNTIME.json").read_bytes())
    view = policy.inspect(
        owned["root"] / "edition/runtimes/POLICY",
        expected_runtime_sha256=sha(encoded(cfg)),
        as_of=owned["plan"]["finish_at"],
    )
    assert len(view["report"]["recipients"]) == 2
    original_bytes = Path(owned["plan"]["capsule"]["path"]).parent / "company/company.sqlite3"
    assert sha(original_bytes.read_bytes()) == sha(owned["source_raw"])
    assert run(owned, pins) == result
    # Only after the source edition and its resume are complete is an owned
    # auditor granted access. This is not the current PersistentCompany world.
    from enterprise.audit_suite.source_library_audit import typed_content

    source.grant(
        "OWN-AUDITOR", "OWN-FRESH-AUDIT", "SH", "depth-owned", "operating_depth_definition"
    )
    receipt = source.collect(
        "OWN-AUDITOR",
        "OWN-FRESH-AUDIT",
        "SH",
        "depth-owned",
        "operating_depth_definition",
        "OWN-EDITION.DEPTH",
        version=2,
        as_of=owned["plan"]["fresh_audit_not_before"],
        command_id="OWN-LATE-DEFINITION-COLLECT",
    )
    read = source.read_version(
        "OWN-AUDITOR",
        "OWN-FRESH-AUDIT",
        "SH",
        "depth-owned",
        "operating_depth_definition",
        "OWN-EDITION.DEPTH",
        version=2,
        as_of=owned["plan"]["fresh_audit_not_before"],
    )
    doc, mime = typed_content(read)
    assert mime == "application/json" and doc["runtime_id"] == "OWN-EDITION.DEPTH"
    assert receipt["source"]["sha256"] == read["sha256"]


@pytest.mark.parametrize(
    "fault",
    ["foreign", "clock", "unknown", "future_pointer", "foreign_path", "missing36", "kwargs"],
)
def test_preview_refuses_before_any_new_source(owned, fault):
    plan = deepcopy(owned["plan"])
    if fault == "foreign":
        plan["program"][0]["source_refs"][0]["branch"] = "foreign"
    elif fault == "clock":
        plan["program"][1]["at"] = at("2027-01-01T00:00:00Z")
    elif fault == "unknown":
        plan["program"][0]["action"] = "AUTHOR_AUDIT_RESULTS"
    elif fault == "future_pointer":
        plan["program"][1]["arguments"]["business_inventory_pin"] = ptr("LATE36", "native_pin")
    elif fault == "foreign_path":
        plan["program"][3]["arguments"]["declaration_root"] = "/tmp/foreign"
    elif fault == "missing36":
        plan["modes"][0]["retained_period_refs"].pop()
    else:
        next(s for s in plan["program"] if s["action"] == "BACKUP_RUN")["arguments"][
            "secret_override"
        ] = True
    pins = authorize(owned, plan)
    with pytest.raises(CompanyStoreError):
        run(owned, pins)
    assert not (owned["root"] / "edition").exists()
    assert owned["source"].path.read_bytes() == owned["source_raw"]


@pytest.mark.parametrize("interrupted", ["DUE", "BACKUP", "POLICY", "DATA"])
def test_committed_operation_without_checkpoint_resumes_exactly(owned, monkeypatch, interrupted):
    pins = authorize(owned)
    original_write = edition.write_new
    raised = False

    def write(path, value):
        nonlocal raised
        if path.name.endswith("-" + interrupted + ".json") and not raised:
            raised = True
            raise OSError("OWN interruption after ordinary source commit, before checkpoint")
        return original_write(path, value)

    monkeypatch.setattr(edition, "write_new", write)
    with pytest.raises(OSError, match="OWN interruption"):
        run(owned, pins)
    root = owned["root"] / "edition"
    ledger = CompanyStore(root / "ledgers/DUE")
    original_raw = ledger.path.read_bytes()
    with ledger._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 1
    result = run(owned, pins)
    assert Path(result["path"]).exists() and ledger.path.read_bytes() == original_raw
    assert len(list(root.glob("FAILURE-*.json"))) == 1


def test_later_unavailable_original_preserves_earlier_operations(owned):
    plan = deepcopy(owned["plan"])
    plan["program"][1]["source_refs"] = [plan["modes"][0]["retained_period_refs"][-1]]
    pins = authorize(owned, plan)
    with pytest.raises(CompanyStoreError, match="not yet available"):
        run(owned, pins)
    root = owned["root"] / "edition"
    assert (root / "receipts/0000-INVENTORY.json").exists()
    assert json.loads((root / "FAILURE-0000.json").read_bytes())["failed_step"] == "CALENDAR"
    assert not (root / "SOURCE_EDITION_COMPLETION.json").exists()
    assert owned["source"].path.read_bytes() == owned["source_raw"]


@pytest.mark.parametrize("fault", ["system", "record"])
def test_declaration_requires_registered_physical_identity_without_append(tmp_path, fault):
    root = tmp_path / "declared"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    manual, definition = setup_declaration(store, "IAM")
    legitimate = depth.register_declaration(
        store,
        repository=REPO,
        business_inventory_pin=definition["business_inventory_ref"],
        retained_period_refs=[],
        runtime_id="REGISTERED",
        actor_id="AS-P007",
        recorded_at=definition["recorded_at"],
        command_id="NORMAL-REGISTER",
    )
    with store._db() as db:
        _, body = depth.selected(db, depth.pin(legitimate), definition["recorded_at"])
    copied = original(
        store,
        "unrelated_family" if fault == "system" else "operating_depth_definition",
        "REGISTERED" if fault == "system" else "OTHER-RECORD",
        body,
        at=definition["recorded_at"],
    )
    before = store.path.read_bytes()
    assert (
        depth.declare(
            store,
            repository=REPO,
            declaration_pin=depth.pin(legitimate),
            as_of=definition["recorded_at"],
        )["canonical_person_count"]
        == 52
    )
    with pytest.raises(CompanyStoreError, match="registered operating-depth declaration"):
        depth.declare(
            store, repository=REPO, declaration_pin=copied, as_of=definition["recorded_at"]
        )
    assert store.path.read_bytes() == before
