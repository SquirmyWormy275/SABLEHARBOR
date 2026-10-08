"""Independent saved-Key privacy, parity and bounded-list review; disposable stores only."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.instructor_key_views import InstructorKeyViews
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_key_views import request
from tests.audit_suite.test_instructor_key_views import views as views_fixture
from tests.audit_suite.test_instructor_releases import change


@pytest.fixture
def views(tmp_path, monkeypatch):
    return views_fixture.__wrapped__(tmp_path, monkeypatch)


def test_deleted_views_do_not_exhaust_active_listing_contract(views):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    p = request(core, args)
    for number in range(17):
        saved = core.save(actor, eid, {**p, "command_id": f"create-{number}"})
        core.delete(
            actor,
            eid,
            saved["id"],
            {
                "command_id": f"delete-{number}",
                "expected_version": 1,
                "expected_engagement_revision": 0,
            },
        )
    current = core.save(actor, eid, {**p, "command_id": "current"})
    assert core.listing(actor, eid, "BOUND")["views"] == [current]
    assert len(core.snapshot()["events"]) == 35
    assert engine.store.get(actor, eid) == before


def test_archive_option_must_belong_to_selected_selector():
    # The existing archive selector removes options from all other selectors.
    context = {
        "kind": "ARCHIVE",
        "error": None,
        "authored_matching_texts": {"A.01.V1": "", "B.01.V1": ""},
        "data": {
            "entries": [
                {"id": "A.01.V1", "review": {"professional": "UNVALIDATED", "gaps": []}},
                {"id": "B.01.V1", "review": {"professional": "UNVALIDATED", "gaps": []}},
            ]
        },
    }
    user = {
        "title": "Private",
        "query": "",
        "page": 0,
        "selector": "A",
        "option": "B.01",
        "review": "all",
        "scenario": None,
    }
    with pytest.raises(DomainError):
        InstructorKeyViews._selection(context, user)
    InstructorKeyViews._selection(context, {**user, "option": "A.01"})


@pytest.mark.parametrize("kind", ["BOUND", "ARCHIVE"])
def test_exact_save_replay_after_context_change_redacts_original_title_query(views, kind):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    p = request(core, args, kind)
    p["user"].update(title="Private reason not in stale metadata", query="Private search")
    saved = core.save(actor, eid, p)
    history = deepcopy(core.snapshot())
    change(engine, args, lambda state: state.update(evidence_acquisition={"changed": True}))
    replay = core.save(actor, eid, p)
    assert replay["id"] == saved["id"] and replay["context_status"] == "CONTEXT_CHANGED"
    assert not replay["personal_content_visible"] and not replay["restorable"]
    assert replay["navigation"] is None and "user" not in replay and "key_pin" not in replay
    assert core.snapshot() == history


def test_final_key_change_rejects_list_without_returning_cached_title(views, monkeypatch):
    core, _, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    core.save(actor, eid, request(core, args))
    original = core._finish

    def changed(*args):
        core.bindings[eid]["manifest_sha256"] = "f" * 64
        return original(*args)

    monkeypatch.setattr(core, "_finish", changed)
    with pytest.raises(DomainError) as error:
        core.listing(actor, eid, "BOUND")
    assert error.value.status == 409


def test_unrelated_private_archive_file_is_rejected_without_reading_its_content(views, monkeypatch):
    from pathlib import Path

    core, _, _ = views
    extra = core.archive_root / "unrelated-private.bin"
    extra.write_bytes(b"Unrelated private bytes")
    extra.chmod(0o600)
    open_file = Path.open
    touched = []

    def tracked(path, *args, **kwargs):
        if path == extra:
            touched.append(path)
        return open_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked)
    with pytest.raises(DomainError):
        core._archive()
    assert touched == []


def test_oversized_archive_index_rejected_before_reading_large_bytes(views, monkeypatch):
    from pathlib import Path

    core, _, _ = views
    index = core.archive_root / "index.json"
    with index.open("r+b") as stream:
        stream.truncate(257 * 1024 * 1024)  # Sparse fixture; no giant allocation.
    open_file = Path.open

    def tracked(path, *args, **kwargs):
        if path == index:
            pytest.fail("Oversized index must be rejected using metadata before opening bytes")
        return open_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked)
    with pytest.raises(DomainError):
        core._archive()
