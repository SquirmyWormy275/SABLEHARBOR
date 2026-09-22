"""Independent selected-content/export-boundary tests on disposable private stores."""

import io
import json
import zipfile

import pytest

from enterprise.audit_suite.explanation_binding import bind_snapshot
from enterprise.audit_suite.instructor_releases import InstructorReleases
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_explanation_binding import workspace
from tests.audit_suite.test_instructor_debrief import payload
from tests.audit_suite.test_instructor_releases import change, confirm


@pytest.fixture
def selected(tmp_path):
    engine, args = workspace.__wrapped__(tmp_path)
    args["authored"]["issues"].append(
        {
            "id": "HIDDEN_NEIGHBOR",
            "control_ids": ["CONTROL1"],
            "source_ids": ["R2"],
            "claim": "NEIGHBOR_CLAIM_MUST_NOT_LEAK",
            "uncertainty": "NEIGHBOR_UNCERTAINTY",
        }
    )
    args["authored"]["expectations"].append(
        {
            "id": "HIDDEN_EXPECTATION",
            "issue_ids": ["HIDDEN_NEIGHBOR"],
            "procedure": "NEIGHBOR_PROCEDURE_MUST_NOT_LEAK",
            "acceptable_alternatives": [],
        }
    )
    args["authored"]["uncertainty"].append("GLOBAL_PRIVATE_UNCERTAINTY")
    receipt = bind_snapshot(engine, **args)
    root = tmp_path / "releases"
    root.mkdir(mode=0o700)
    return (
        InstructorReleases(
            root,
            engine,
            {
                args["engagement_id"]: {
                    "path": args["output"],
                    "manifest_sha256": receipt["manifest_sha256"],
                }
            },
        ),
        engine,
        args,
    )


def released(core, args, draft=None):
    return confirm(
        core,
        args,
        core.debrief_preview(args["instructor_id"], args["engagement_id"], draft or payload(args)),
    )


def export_request(core, args, saved, actor=None):
    actor = actor or args["audited_actor_id"]
    preview = core.export_preview(
        actor,
        args["engagement_id"],
        saved["release_id"],
        {
            "release_sha256": saved["release_sha256"],
        },
    )
    return {
        "preview_id": preview["preview"]["id"],
        "preview_sha256": preview["preview_sha256"],
        "command_id": "review-export",
    }


def test_only_selected_content_streamed_history_and_deterministic_archive(selected, monkeypatch):
    core, engine, args = selected

    def forbidden(*a, **kw):
        raise AssertionError("Full historical states must not be materialized")

    monkeypatch.setattr(engine.store, "history", forbidden)
    saved = released(core, args)
    read = core.read(args["audited_actor_id"], args["engagement_id"], saved["release_id"])
    req = export_request(core, args, saved)
    result = core.export_confirm(
        args["audited_actor_id"], args["engagement_id"], saved["release_id"], req
    )
    second_req = export_request(core, args, saved, args["instructor_id"])
    second = core.export_confirm(
        args["instructor_id"], args["engagement_id"], saved["release_id"], second_req
    )
    assert result["bytes"] == second["bytes"]
    with zipfile.ZipFile(io.BytesIO(result["bytes"])) as archive:
        combined = json.dumps(read).encode() + b"".join(archive.read(n) for n in archive.namelist())
        for forbidden_value in (
            b"HIDDEN_NEIGHBOR",
            b"HIDDEN_EXPECTATION",
            b"NEIGHBOR_",
            b"GLOBAL_PRIVATE",
            str(args["output"]).encode(),
        ):
            assert forbidden_value not in combined
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in archive.infolist())
        assert all(not n.startswith("/") and ".." not in n for n in archive.namelist())


@pytest.mark.parametrize("change_kind", ["revision", "recipient_role"])
def test_export_final_authority_or_revision_change_rolls_back_event(
    selected, monkeypatch, change_kind
):
    core, engine, args = selected
    saved = released(core, args)
    req = export_request(core, args, saved)
    original = core._package

    def changed(value):
        result = original(value)
        if change_kind == "revision":
            change(engine, args, lambda state: state.update(test_note="Changed during packaging"))
        else:
            engine.store.grant(args["engagement_id"], args["audited_actor_id"], "review")
        return result

    monkeypatch.setattr(core, "_package", changed)
    with pytest.raises(DomainError):
        core.export_confirm(
            args["audited_actor_id"], args["engagement_id"], saved["release_id"], req
        )
    with core._db() as db:
        assert "EXPORTED" not in core._actions(db, saved["release_id"])


def test_other_current_instructor_cannot_export_named_release(selected):
    core, engine, args = selected
    saved = released(core, args)
    other = engine.store.provision("Other teacher", ["instructor"])["id"]
    engine.store.grant(args["engagement_id"], other, "instruct")
    with pytest.raises(DomainError):
        export_request(core, args, saved, other)


def test_attachment_exact_bytes_reread_and_no_neighbor_original(selected):
    core, engine, args = selected
    eid = args["engagement_id"]
    chosen = engine.artifacts.retain(
        eid, "hostile.txt", b"selected native bytes", source={}, coverage={}
    )
    neighbor = engine.artifacts.retain(
        eid, "unselected.txt", b"UNSELECTED_ORIGINAL_SECRET", source={}, coverage={}
    )
    change(engine, args, lambda state: state.update(artifacts=[chosen, neighbor]))
    draft = payload(args)
    draft["expected_revision"] = 1
    draft["sections"][0]["annotations"] = [
        {
            "artifact_id": chosen["id"],
            "sha256": chosen["sha256"],
            "note": "Authored note",
            "locator": None,
            "attach": True,
        }
    ]
    saved = released(core, args, draft)
    req = export_request(core, args, saved)
    result = core.export_confirm(args["audited_actor_id"], eid, saved["release_id"], req)
    with zipfile.ZipFile(io.BytesIO(result["bytes"])) as archive:
        members = [n for n in archive.namelist() if n.startswith("originals/")]
        assert len(members) == 1 and archive.read(members[0]) == b"selected native bytes"
        assert all("hostile" not in n and ".." not in n for n in archive.namelist())
        assert b"UNSELECTED_ORIGINAL_SECRET" not in result["bytes"]
    (engine.artifacts.root / chosen["sha256"]).write_bytes(b"corrupt replacement")
    with pytest.raises(DomainError):
        core.export_confirm(args["audited_actor_id"], eid, saved["release_id"], req)


def test_later_authored_support_keeps_historical_clock_and_no_visibility_claim(selected):
    core, _, args = selected
    draft = payload(args)
    draft["sections"][0]["issue_ids"] = ["HIDDEN_NEIGHBOR"]
    draft["sections"][0]["expectation_ids"] = ["HIDDEN_EXPECTATION"]
    saved = released(core, args, draft)
    content = core.read(args["audited_actor_id"], args["engagement_id"], saved["release_id"])[
        "content"
    ]
    learner = content["document"]["learner"]
    assert learner["revision"] == 0
    assert learner["simulated_at"] == "2027-06-01T00:00:00Z"
    assert (
        learner["qualification"]
        == "SHARED_STATE_NOT_SUBMISSION_KEY_SUPPORT_MAY_POSTDATE_LEARNER_REVISION"
    )
    assert "source_ids" not in content["document"]["sections"][0]["issues"][0]


def test_expectation_cannot_expand_hidden_issue_selection(selected):
    core, _, args = selected
    draft = payload(args)
    draft["sections"][0]["expectation_ids"] = ["HIDDEN_EXPECTATION"]
    with pytest.raises(DomainError, match="explicitly selected"):
        released(core, args, draft)
    assert core.list(args["audited_actor_id"], args["engagement_id"]) == []


def test_archive_rejects_rehashed_extra_private_issue_fields(selected):
    from enterprise.audit_suite.instructor_releases import validate_snapshot
    from enterprise.audit_suite.store import digest

    core, _, args = selected
    released(core, args)
    snapshot = core.snapshot()
    for row in snapshot["tables"]["documents"]:
        value = json.loads(row["content"])
        if value.get("content", {}).get("stage") == "EXPLANATION":
            value["content"]["document"]["sections"][0]["issues"][0]["source_path"] = (
                "/private/hidden"
            )
            from enterprise.audit_suite.store import canonical

            row["content"] = canonical(value)
            row["sha256"] = digest(value)
    with pytest.raises(DomainError):
        validate_snapshot(snapshot)
