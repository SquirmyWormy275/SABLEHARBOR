"""Finite b3/V3/Bound composition on ordinary tiny owned source-before-audit rooms."""

import importlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.instructor_reference_crosswalk import build_reference_crosswalk
from enterprise.audit_suite.persistent_company_journey import native_rows, write
from enterprise.audit_suite.persistent_company_service import (
    SEALED_CODE_MODULES,
    RetainedWorkroom,
)
from enterprise.audit_suite.retained_explanation_service import (
    REFERENCE_MODULES,
    create_explained_app,
    reference_configuration,
)
from enterprise.audit_suite.source_library_audit import file_sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_authority_editions import neutral
from tests.audit_suite.test_persistent_company_service import login

pytest_plugins = [
    "tests.audit_suite.test_persistent_company_service",
    "tests.audit_suite.test_retained_explanation_service",
]
REPO = Path(__file__).resolve().parents[2]


def _private_archive(root, monkeypatch):
    root.mkdir(mode=0o700)
    definitions = root / "definitions"
    definitions.mkdir(mode=0o700)
    variant = "MM-13.03.V01"
    original = neutral(variant)
    original["binding_contract"]["applicable_control_ids"] = ["SH-SEC-003"]
    write(definitions / (variant + ".json"), original)
    # An expressly owned one-version archive, never an actual 1110 denominator.
    monkeypatch.setattr(instructor_key, "obligations", lambda: [variant])
    protected = root / "private-corpus"
    protected.mkdir(mode=0o700)
    archive = protected / "archive"
    instructor_key.build_archive(definitions, archive, migration_version=2)
    return {
        "root": str(archive),
        "index_sha256": file_sha(archive / "index.json"),
        "receipt_sha256": file_sha(archive / "receipt.json"),
        "archive_sha256": file_sha(archive / "instructor-keys.zip"),
    }


def _events(store, engagement):
    with store.connect() as db:
        return [
            tuple(row)
            for row in db.execute(
                "SELECT * FROM events WHERE engagement=? ORDER BY revision", (engagement,)
            )
        ]


def test_genuine_retained_v3_same_room_saved_index_cold_and_privacy(keycase, tmp_path, monkeypatch):
    assert sys.version_info >= (3, 11)
    work = keycase["case"]
    world = keycase["retained"]["world"]
    eid, teacher, learner = work["engagement"], work["ids"]["operator"], work["ids"]["auditor"]
    selected = sorted(set(SEALED_CODE_MODULES) | set(REFERENCE_MODULES))
    opening = {name: file_sha(REPO / "enterprise/audit_suite" / name) for name in selected}
    for name in selected:
        module = importlib.import_module("enterprise.audit_suite." + name[:-3])
        expected = REPO / "enterprise/audit_suite" / name
        assert Path(module.__file__).absolute() == expected
        assert Path(module.__spec__.origin).absolute() == expected
    assert len(selected) == 92
    selection = _private_archive(tmp_path / "owned-archive", monkeypatch)
    snapshot = json.loads((keycase["snapshot"] / "snapshot.json").read_bytes())
    crosswalk = build_reference_crosswalk(
        selection, snapshot, tmp_path / "OWN-CROSSWALK.json", engineering_neutral_only=True
    )
    config = tmp_path / "OWN-V3-CONFIG.json"
    write(
        config,
        reference_configuration(
            work["config"],
            work["config_sha256"],
            keycase["bindings"],
            file_sha(keycase["bindings"]),
            repository=REPO,
            instructor_writeback=True,
            background_jobs=False,
            reference_archive=selection,
            reference_crosswalk=crosswalk,
        ),
    )
    room = RetainedWorkroom(
        work["config"], work["config_sha256"], private_root=work["root"], repository=REPO
    )
    # Ordinary unsealed initialization may invalidate its pre-constructor stamp.
    # Complete the normal current integrity refresh before asking for live reuse.
    room.refresh_integrity(teacher)
    before_state = room.engine.store.get(learner, eid)
    before_events = _events(room.engine.store, eid)
    before_native = native_rows(world.database)
    before_company = file_sha(world.database)
    app = create_explained_app(
        work["root"],
        config,
        file_sha(config),
        repository=REPO,
        retained_workroom=room,
        allowed_hosts=["testserver"],
        workspace_contexts=True,
    )
    assert app.state.engine is room.engine
    client, headers = login(app, work, "operator")
    student, learner_headers = login(app, work, "auditor")
    url = "/api/engagements/" + eid
    private = client.get(url + "/instructor-binding")
    assert private.status_code == 200, private.text
    assert (
        private.json()["reference_crosswalk"]["rows"][0]["relations"][0]["status"]
        == "SHARED_CONTROL_ONLY"
    )
    for suffix in (
        "/instructor-key",
        "/instructor-key/MM-13.03.V01",
        "/instructor-key/MM-13.03.V01/original",
    ):
        assert client.get(url + suffix).status_code == 200
        assert student.get(url + suffix, headers=learner_headers).status_code == 403
    core = app.state.instructor_key_views
    context = core._context(teacher, eid, "BOUND")
    user = {
        "title": "Owned V3 saved index",
        "query": "",
        "issue_id": "neutral-source-check",
        "scope_to_issue": True,
        "source": None,
        "page": 0,
    }
    payload = {
        "view_id": None,
        "kind": "BOUND",
        "key_pin": context["key"],
        "user": user,
        "expected_version": 0,
        "expected_engagement_revision": before_state["revision"],
        "command_id": "own-old-five-field-user",
    }
    first = client.post(url + "/instructor-key-views", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    old_events = deepcopy(core.snapshot()["events"])
    payload["user"] = {
        **user,
        "issue_index": {"query": "neutral-source", "control_id": "SH-SEC-003", "page": 0},
    }
    payload["command_id"] = "own-optional-bound-index"
    saved = client.post(url + "/instructor-key-views", headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert core.snapshot()["events"][:1] == old_events
    assert "issue_index" not in first.json()["user"]
    assert student.get(url + "/instructor-key-views?kind=BOUND").status_code == 403
    cold = create_explained_app(
        work["root"],
        config,
        file_sha(config),
        repository=REPO,
        allowed_hosts=["testserver"],
        workspace_contexts=True,
    )
    assert cold.state.engine is not room.engine
    fresh, fresh_headers = login(cold, work, "operator")
    value = saved.json()
    restored = fresh.post(
        url + "/instructor-key-views/" + value["id"] + "/restore",
        headers=fresh_headers,
        json={
            "expected_version": value["version"],
            "expected_engagement_revision": before_state["revision"],
            "expected_key_pin": value["key_pin"],
        },
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["navigation"]["issue_index"] == payload["user"]["issue_index"]
    assert cold.state.instructor_key_views.snapshot()["events"][:1] == old_events
    assert cold.state.engine.store.get(learner, eid) == before_state
    assert _events(cold.state.engine.store, eid) == before_events
    assert native_rows(world.database) == before_native
    assert file_sha(world.database) == before_company
    public = student.get(url)
    assert (
        public.status_code == 200
        and "reference_crosswalk" not in public.text
        and "MM-13.03" not in public.text
    )
    bad = json.loads(config.read_bytes())
    bad["code_pins"].pop("instructor_reference_crosswalk.py")
    bad_path = tmp_path / "OWN-INCOMPLETE-V3-CONFIG.json"
    write(bad_path, bad)
    with pytest.raises(ProcedureError, match="Exact explanation module pins"):
        create_explained_app(work["root"], bad_path, file_sha(bad_path), repository=REPO)
    assert opening == {name: file_sha(REPO / "enterprise/audit_suite" / name) for name in selected}
    loaded = {}
    namespaces = {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        spec = getattr(module, "__spec__", None)
        if name in {"tools", "tools.audit_suite"}:
            expected = REPO.joinpath(*name.split("."))
            assert path is None
            assert set(module.__path__) == {str(expected)}
            if spec is not None:
                assert spec.origin is None
                assert list(spec.submodule_search_locations) == list(module.__path__)
            namespaces[name] = {
                "paths": list(module.__path__),
                "spec_paths": list(spec.submodule_search_locations) if spec is not None else None,
                "file": None,
            }
        if path and (
            Path(path).is_relative_to(REPO) or name.startswith(("cryptography", "_cffi_backend"))
        ):
            if spec is None:
                continue  # Required runtime module origins were checked explicitly above.
            path = Path(path).absolute()
            assert spec is not None and Path(spec.origin).absolute() == path
            loaded[name] = {"path": str(path), "sha256": file_sha(path), "spec_origin": spec.origin}
    write(
        Path(os.environ.get("B3_V3_OWN_OUTPUT", str(tmp_path))) / "OWN_COMPOSITION_RESULT.json",
        {
            "status": "PASS_FINITE_OWN_RETAINED_V3_BOUND_INDEX_COMPOSITION",
            "engineering_fixture_only": True,
            "actual_pair_acceptance": False,
            "task_count": len(before_state["tasks"]),
            "native_versions": len(before_native),
            "selected_python_count": len(selected),
            "selected_code_pins": opening,
            "loaded_file_modules": loaded,
            "namespaces": namespaces,
            "same_room_reused": True,
            "genuine_cold": True,
            "public_raw_events_unchanged": True,
            "source_database_unchanged": True,
            "old_saved_user_bytes_unchanged": True,
            "private_archive_learner403": True,
            "professional_acceptance": "NOT_ASSERTED",
        },
    )


def test_archive_index_extension_stays_unsupported():
    from enterprise.audit_suite.instructor_key_views import validate_user

    with pytest.raises(DomainError):
        validate_user(
            "ARCHIVE",
            {
                "title": "Owned",
                "query": "",
                "page": 0,
                "selector": "all",
                "option": "all",
                "review": "all",
                "scenario": None,
                "issue_index": {"query": "", "control_id": None, "page": 0},
            },
        )
