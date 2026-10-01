"""Genuine neutral shared-company workrooms, normal collection and append records."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import (
    BINDING_SCHEMA,
    GENERAL_METHOD_SCHEMA,
    GENERAL_METHOD_VERDICT,
    PROGRAM_SHA,
    FullScopePair,
    PinnedReview,
    command,
)
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
    quiescent_read,
)

REPO = Path(__file__).resolve().parents[2]
TASK = "TASK-SH-SEC-003-corporate-TOE"
PERFORMED = "Reparse actual neutral retained original revision values"
UNPERFORMED = "No corporate, annual security or qualified assurance examination"
PACK = REPO / "enterprise/generated/audit-suite/build/program-pack.json"
pytestmark = pytest.mark.skipif(
    not PACK.is_file(),
    reason="Exact private 409-task source-verified program pack is not installed",
)


def neutral_source(root):
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    for branch in ("ALPHA", "BETA"):
        for system in ("operations.events", "operations.unselected"):
            store.register_system("NEUTRAL-COMPANY", branch, system, "NEUTRAL-OWNER")
            store.append_version(
                "NEUTRAL-COMPANY",
                branch,
                system,
                "event-one",
                expected_version=0,
                command_id=f"neutral-base-{branch}-{system}",
                event_at="2027-02-01T01:00:00Z",
                available_at="2027-02-01T02:00:00Z",
                content=json.dumps({"engineering_neutral_fixture": True, "revision": 1}).encode(),
                provenance={
                    "source_reference": "neutral-company-native-original",
                    "name": "event.json",
                    "content_type": "application/json",
                },
            )
        store.append_version(
            "NEUTRAL-COMPANY",
            branch,
            "operations.events",
            "event-one",
            expected_version=1,
            command_id=f"neutral-late-{branch}",
            event_at="2028-01-10T01:00:00Z",
            available_at="2028-01-15T12:05:00Z",
            content=json.dumps({"engineering_neutral_fixture": True, "revision": 2}).encode(),
            provenance={
                "source_reference": "neutral-company-later-correction",
                "name": "event.json",
                "content_type": "application/json",
            },
        )
    db = root / "company.sqlite3"
    manifest, review = root / "MANIFEST.json", root / "REVIEW.json"
    write(manifest, {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(db)}})
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {"company.sqlite3": file_sha(db), "MANIFEST.json": file_sha(manifest)},
            "native_versions": 6,
            "engineering_neutral_fixture_not_actual_independent_review": True,
        },
    )
    return AcceptedLibrary(
        db, file_sha(db), manifest, file_sha(manifest), review, file_sha(review), 6
    )


def neutral_routes():
    return {
        mode: [
            BusinessRoute("NEUTRAL-COMPANY", branch, "operations." + system, "operations", system)
            for system in ("events", "unselected")
        ]
        for mode, branch in (("CLEAN", "ALPHA"), ("MESSY", "BETA"))
    }


@pytest.fixture
def pair(tmp_path):
    tmp_path.chmod(0o700)
    accepted = neutral_source(tmp_path / "accepted-neutral")
    return FullScopePair.initialize(
        accepted=accepted,
        repository=REPO,
        program_pack=PACK,
        routes_by_mode=neutral_routes(),
        destination=tmp_path / "neutral-pair",
        operator_id="NEUTRAL-COMPANY-OPERATOR",
        engineering_only=True,
    )


def acquire(room, **extra):
    return room.acquire(
        systems=["operations.events"],
        control_id="SH-SEC-003",
        purpose="Inspect a neutral original directly from its company",
        **extra,
    )


def test_one_company_precedes_two_empty_full_program_workrooms(pair):
    initialization = json.loads((pair.world.root / "INITIALIZATION.json").read_bytes())
    assert initialization["audit_engagements_at_initialization"] == 0
    assert pair.rooms["CLEAN"].session.database == pair.rooms["MESSY"].session.database
    ids = set()
    for mode, room in pair.rooms.items():
        state = room.state()
        binding = json.loads((room.root / "BINDING.json").read_bytes())
        assert binding == room.binding and binding["schema"] == BINDING_SCHEMA
        assert binding["program_pack"]["sha256"] == PROGRAM_SHA
        assert binding["company_root"] == str(pair.world.root)
        assert binding["audit_root"] == str(room.engine.store.root)
        assert not any(binding["zero_workroom_counts"].values())
        assert len(state["tasks"]) == 409 and state["mode"] == mode
        assert all(
            t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN" for t in state["tasks"]
        )
        assert not state["artifacts"] and not state["sample_executions"] and not state["reviews"]
        assert state["simulated_at"].startswith("2027-12-31T09:00:00")
        ids.update(room.binding["identities"].values())
    assert len(ids) == 6 and pair.world.operator.principal not in ids


def test_scoped_collection_reuses_only_this_engagement_and_preserves_historical_original(pair):
    before = native_rows(pair.world.database)
    clean, messy = pair.rooms["CLEAN"], pair.rooms["MESSY"]
    first = acquire(clean)
    assert len(first) == 1 and first[0]["source"]["version"] == 1
    assert first[0]["receipt"]["engagement_id"] == clean.engagement
    same = acquire(clean)
    assert same[0]["artifact_id"] == first[0]["artifact_id"]
    assert len(clean.state()["artifacts"]) == 1
    other = acquire(messy)
    assert other[0]["source"]["branch"] == "BETA"
    assert other[0]["receipt"]["engagement_id"] == messy.engagement
    assert other[0]["artifact_id"] != first[0]["artifact_id"]
    with pytest.raises(ProcedureError, match="actual workroom clock"):
        acquire(clean, as_of="2028-01-16T09:00:00Z")
    command(
        clean.engine,
        clean.auditor,
        clean.engagement,
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2028-01-15T09:00:00Z"},
    )
    assert [r["source"]["version"] for r in acquire(clean)] == [1]
    command(
        clean.engine,
        clean.auditor,
        clean.engagement,
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2028-01-16T09:00:00Z"},
    )
    later = acquire(clean)
    assert [r["source"]["version"] for r in later] == [1, 2]
    assert later[0]["artifact_id"] == first[0]["artifact_id"]
    assert json.loads(later[1]["retained_bytes"])["revision"] == 2
    original = next(a for a in clean.state()["artifacts"] if a["id"] == first[0]["artifact_id"])
    assert clean.engine.artifacts.read(original) == first[0]["retained_bytes"]
    assert native_rows(pair.world.database) == before
    with quiescent_read(pair.world.database) as db:
        assert db.execute("SELECT COUNT(*) FROM grants WHERE active=1").fetchone()[0] == 0
        assert (
            db.execute(
                "SELECT COUNT(*) FROM access_events WHERE system='operations.unselected'"
            ).fetchone()[0]
            == 0
        )
    assert not clean.state()["reviews"] and not messy.state()["reviews"]


def neutral_inspection(rows, *, as_of, scratch_root):
    assert all(r["source"]["company"] == "NEUTRAL-COMPANY" for r in rows)
    return [
        {
            "task_id": TASK,
            "artifact_ids": [r["artifact_id"] for r in rows],
            "performed": PERFORMED,
            "unperformed": UNPERFORMED,
            "disposition": {
                "status": "IN_PROGRESS",
                "conclusion": "LIMITATION",
                "rationale": "Only the neutral stored revision was actually examined",
            },
            "observations": [
                {
                    "id": r["source"]["record"] + "-v" + str(r["source"]["version"]),
                    "facts": {"revision": json.loads(r["retained_bytes"])["revision"]},
                    "status": "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": r["artifact_id"],
                            "sha256": r["artifact_sha256"],
                            "locator": "Exact neutral original revision",
                        }
                    ],
                }
                for r in rows
            ],
            "result": {"scope": "NEUTRAL_ENGINEERING_FIXTURE_ONLY", "as_of": as_of},
        }
    ]


def neutral_failed_inspection(rows, *, as_of, scratch_root):
    result = neutral_inspection(rows, as_of=as_of, scratch_root=scratch_root)
    observed = [json.loads(r["retained_bytes"])["revision"] for r in rows]
    assert observed and all(version != 2 for version in observed)
    result[0].update(
        {
            "performed": "Compare exact neutral stored revisions with required revision two",
            "result": {"required_revision": 2, "observed_revisions": observed},
            "disposition": {
                "status": "COMPLETE",
                "conclusion": "FAIL",
                "rationale": "Every observed neutral revision is one, failing required two",
            },
        }
    )
    return result


def neutral_method_review(pair, *, changes=None, method=neutral_inspection):
    path = pair.root / "NEUTRAL-METHOD-REVIEW.json"
    write(
        path,
        {
            "schema": GENERAL_METHOD_SCHEMA,
            "verdict": GENERAL_METHOD_VERDICT,
            "source_execution_authorized": True,
            "selected_task_ids": [TASK],
            "method_module_sha256": file_sha(Path(__file__)),
            "dependency_module_sha256": {},
            "method_callable": method.__module__ + "." + method.__qualname__,
            "task_contracts": {
                TASK: {
                    "performed": PERFORMED,
                    "unperformed": UNPERFORMED,
                    "allowed_dispositions": [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}],
                }
            },
            "neutral_author_fixture_not_actual_independent_acceptance": True,
            **(changes or {}),
        },
    )
    return PinnedReview(path, file_sha(path))


def test_actual_normal_records_cite_exact_retained_bytes_and_do_not_credit_other_tasks(pair):
    room = pair.rooms["CLEAN"]
    rows = acquire(room)
    links = room.append_reviewed_batch(
        batch="neutral-probe",
        review=neutral_method_review(pair),
        rows=rows,
        method=neutral_inspection,
    )
    assert len(links) == 1 and links[0]["task_id"] == TASK
    state = room.state()
    assert len(state["workpapers"]) == len(state["sample_executions"]) == 1
    assert len({p.get("family_id", p["id"]) for p in state["populations"]}) == 1
    assert len(state["populations"]) == 2 and len(state["selections"]) == 1
    assert state["workpapers"][0]["prepared_by"] == room.auditor
    task = next(t for t in state["tasks"] if t["id"] == TASK)
    assert (task["status"], task["conclusion"]) == ("IN_PROGRESS", "LIMITATION")
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
        for t in state["tasks"]
        if t["id"] != TASK
    )
    assert not state["reviews"] and not pair.rooms["MESSY"].state()["workpapers"]
    with pytest.raises(ProcedureError, match="overwrite previous task work"):
        room.append_reviewed_batch(
            batch="duplicate",
            review=PinnedReview(
                pair.root / "NEUTRAL-METHOD-REVIEW.json",
                file_sha(pair.root / "NEUTRAL-METHOD-REVIEW.json"),
            ),
            rows=rows,
            method=neutral_inspection,
        )


def test_independently_bounded_failed_attribute_can_finish_without_professional_pass(pair):
    room = pair.rooms["CLEAN"]
    rows = acquire(room)
    contract = {
        TASK: {
            "performed": "Compare exact neutral stored revisions with required revision two",
            "unperformed": UNPERFORMED,
            "allowed_dispositions": [{"status": "COMPLETE", "conclusion": "FAIL"}],
        }
    }
    room.append_reviewed_batch(
        batch="neutral-failed-attribute",
        rows=rows,
        method=neutral_failed_inspection,
        review=neutral_method_review(
            pair, method=neutral_failed_inspection, changes={"task_contracts": contract}
        ),
    )
    state = room.state()
    task = next(t for t in state["tasks"] if t["id"] == TASK)
    assert (task["status"], task["conclusion"]) == ("COMPLETE", "FAIL")
    assert state["workpapers"][0]["versions"][0]["conclusion"] == "FAIL"
    assert not state["reviews"] and all(t["conclusion"] != "PASS" for t in state["tasks"])


@pytest.mark.parametrize(
    "change",
    [
        "foreign_receipt",
        "wrong_logical_role",
        "changed_bytes",
        "boolean_version",
        "future_real_collection",
    ],
)
def test_method_input_tampering_rejects_before_any_workpaper(pair, change):
    room = pair.rooms["CLEAN"]
    rows = acquire(room)
    if change == "foreign_receipt":
        rows[0]["receipt"] = {**rows[0]["receipt"], "engagement_id": pair.rooms["MESSY"].engagement}
    elif change == "wrong_logical_role":
        rows[0]["logical_system"] = "unselected"
    elif change == "changed_bytes":
        rows[0]["retained_bytes"] = b'{"revision":99}'
    elif change == "boolean_version":
        rows[0]["source"]["version"] = True
    else:
        rows[0]["receipt"]["collected_at"] = "2100-01-01T00:00:00Z"
    with pytest.raises(ProcedureError, match="actual workroom original"):
        room.append_reviewed_batch(
            batch="tampered",
            review=neutral_method_review(pair),
            rows=rows,
            method=neutral_inspection,
        )
    assert not room.state()["workpapers"] and not (room.root / "BATCH-tampered").exists()


def test_wrong_method_code_pin_rejects_before_fieldwork(pair):
    room = pair.rooms["CLEAN"]
    rows = acquire(room)
    gate = neutral_method_review(pair, changes={"method_module_sha256": "0" * 64})
    with pytest.raises(ProcedureError, match="independently reviewed"):
        room.append_reviewed_batch(
            batch="wrong-code", review=gate, rows=rows, method=neutral_inspection
        )
    assert not room.state()["workpapers"] and not (room.root / "BATCH-wrong-code").exists()


def test_scope_dependency_is_preserved_without_inventing_a_scoped_control(pair):
    room = pair.rooms["CLEAN"]
    rows = acquire(room)
    scope = [t for t in room.state()["tasks"] if t["kind"] == "SCOPE_DEPENDENCY"]
    assert {t["id"] for t in scope} == {"TASK-GATE-SERVICE-FACTS", "TASK-GATE-QUALIFIED-REVIEW"}
    task = scope[0]["id"]
    gate = neutral_method_review(
        pair,
        changes={
            "selected_task_ids": [task],
            "task_contracts": {
                task: {
                    "performed": PERFORMED,
                    "unperformed": UNPERFORMED,
                    "allowed_dispositions": [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}],
                }
            },
        },
    )
    with pytest.raises(ProcedureError, match="separate dedicated examination"):
        room.append_reviewed_batch(
            batch="scope-probe", review=gate, rows=rows, method=neutral_inspection
        )
    assert not (room.root / "BATCH-scope-probe").exists() and not room.state()["workpapers"]
    assert all(t["status"] == "NOT_STARTED" for t in scope)


def test_actual_boundary_requires_current_adapter_runtime_and_pair_gates_before_creation(tmp_path):
    tmp_path.chmod(0o700)
    accepted = neutral_source(tmp_path / "accepted-neutral")
    destination = tmp_path / "unapproved-actual-boundary"
    with pytest.raises(ProcedureError, match="orchestration acceptance"):
        FullScopePair.initialize(
            accepted=accepted,
            repository=REPO,
            program_pack=PACK,
            routes_by_mode=neutral_routes(),
            destination=destination,
            operator_id="NEUTRAL-OPERATOR",
            engineering_only=False,
        )
    assert not destination.exists()
