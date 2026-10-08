"""Matching against a copied owned world, without changing its audit history."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_private_key_semantic_search import authored


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_matching_existing_world_saved_shape_privacy_and_byte_tamper(
    tmp_path, monkeypatch
):
    # Build only a neutral fixture, then freeze and copy it before the matching
    # exercise. No dated workstation files or expiring saved credentials enter it.
    original_root = tmp_path / "owned-original"
    initial_app = create_app(original_root, allowed_hosts=["testserver"])
    initial_store = initial_app.state.engine.store
    instructor = initial_store.provision("OWN teacher", ["instructor"])
    learner = initial_store.provision("OWN learner", ["learner"])
    state = initial_app.state.engine.create(
        instructor["id"],
        {
            "command_id": "OWN-complete-match-create",
            "title": "OWN literal matching",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2", "HIPAA"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2028-01-18",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-POL-001"],
            },
        },
    )
    initial_store.grant(state["id"], learner["id"], "learn")
    login = {
        "teacher": instructor["credential"],
        "learner": learner["credential"],
        "engagement": state["id"],
    }
    original_sql = original_root / "engagements.sqlite3"
    original_pin = sha(original_sql)
    audit = tmp_path / "audit"
    audit.mkdir(mode=0o700)
    shutil.copy2(original_sql, audit / "engagements.sqlite3")
    (audit / "engagements.sqlite3").chmod(0o600)
    if (original_root / "artifacts").exists():
        shutil.copytree(original_root / "artifacts", audit / "artifacts")
    # Reuse unchanged genuine IDs and credentials only in transient memory.
    value = authored("MM-13.03.V01")
    value["title"] = "α" * 300 + " BeyondPreviewTailNeedle"
    value["facts"] = [
        {
            "id": "F" + str(i),
            "statement": "Ordinary authored statement "
            + (" BeyondScalarNeedle" if i == 59 else str(i)),
            "source_class": "SYNTHETIC_SCENARIO_FACT",
            "visibility": "PRIVATE",
        }
        for i in range(60)
    ]
    value["actor_knowledge"][0]["knows_fact_ids"] = ["F0"]
    definitions = tmp_path / "definitions"
    definitions.mkdir(mode=0o700)
    (definitions / (value["id"] + ".json")).write_text(json.dumps(value, ensure_ascii=False))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [value["id"]])
    archive_parent = tmp_path / "private-corpus"
    archive_parent.mkdir(mode=0o700)
    archive = archive_parent / "archive"
    instructor_key.build_archive(definitions, archive)
    archive_pins = {str(p): sha(p) for p in archive.rglob("*") if p.is_file()}
    app = create_app(audit, instructor_key_root=archive, allowed_hosts=["testserver"])
    teacher = app.state.engine.store.authenticate(login["teacher"])["id"]
    before = app.state.engine.store.get(teacher, login["engagement"])
    headers = {"Authorization": "Bearer " + login["teacher"]}
    denied = {"Authorization": "Bearer " + login["learner"]}
    base = f"/api/engagements/{login['engagement']}/instructor-key"
    saved_route = f"/api/engagements/{login['engagement']}/instructor-key-views"
    with TestClient(app, base_url="https://testserver") as client:
        index = client.get(base, headers=headers).json()
        projection = index["entries"][0]["semantic_search"]
        previews = " ".join(term["text"] for term in projection["terms"])
        assert "BeyondPreviewTailNeedle" not in previews and "BeyondScalarNeedle" not in previews
        assert projection["omitted_scalars"] > 0 and projection["truncated_values"] > 0
        for query in [
            "BeyondPreviewTailNeedle",
            "beyondscalarneedle",
            "ASSET-LAB",
            " no such exact term ",
        ]:
            response = client.get(base, params={"query": query}, headers=headers)
            assert response.status_code == 200, response.text
            result = response.json()
            expected = [] if "no such" in query else [value["id"]]
            assert result["matching_entry_ids"] == expected
            assert result["matched_entries"] == len(expected) and result["total_entries"] == 1
            assert result["query"] == query and result["archive"] == index["archive"]
            assert (
                len(response.content) < 1024
                and "statement" not in result
                and "explanation" not in result
            )
        for params in [
            [("query", "a"), ("query", "b")],
            {"query": "a", "unknown": "b"},
            {"query": "x" * 1001},
        ]:
            assert client.get(base, params=params, headers=headers).status_code == 422
        assert (
            client.get(base, params={"query": "BeyondScalarNeedle"}, headers=denied).status_code
            == 403
        )
        assert client.get(base, params={"unknown": "anything"}, headers=denied).status_code == 403
        user = {
            "title": "Old shape full query",
            "query": "BeyondScalarNeedle",
            "selector": "all",
            "option": "all",
            "review": "all",
            "scenario": None,
            "page": 0,
        }
        saved = client.post(
            saved_route,
            headers=headers,
            json={
                "view_id": None,
                "kind": "ARCHIVE",
                "key_pin": index["archive"]["sha256"],
                "user": user,
                "expected_version": 0,
                "expected_engagement_revision": before["revision"],
                "command_id": "OWN-complete-query-save",
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["user"] == user
        restored = client.post(
            saved_route + "/" + saved.json()["id"] + "/restore",
            headers=headers,
            json={
                "expected_version": saved.json()["version"],
                "expected_engagement_revision": before["revision"],
                "expected_key_pin": index["archive"]["sha256"],
            },
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["restorable"] is True
        context = app.state.instructor_key_views._context(teacher, login["engagement"], "ARCHIVE")
        app.state.instructor_key_views._selection(context, user)
        with pytest.raises(DomainError):
            app.state.instructor_key_views._selection(context, {**user, "page": 1})
        assert app.state.engine.store.get(teacher, login["engagement"]) == before
        assert sha(audit / "engagements.sqlite3") == original_pin
        assert all(sha(Path(p)) == pin for p, pin in archive_pins.items())
        key_path = archive / "keys" / (value["id"] + ".json")
        stamp = key_path.stat()
        raw = key_path.read_bytes().replace(b"BeyondScalarNeedle", b"WrongdScalarNeedle", 1)
        assert len(raw) == stamp.st_size
        key_path.write_bytes(raw)
        os.utime(key_path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        assert (
            client.get(base, params={"query": "BeyondScalarNeedle"}, headers=headers).status_code
            == 503
        )
        assert (
            app.state.instructor_key_views._context(teacher, login["engagement"], "ARCHIVE")[
                "error"
            ]
            == "KEY_UNAVAILABLE"
        )
        assert (
            client.get(base, params={"query": "BeyondScalarNeedle"}, headers=denied).status_code
            == 403
        )
    assert sha(original_sql) == original_pin
    assert sha(audit / "engagements.sqlite3") == original_pin
    files, namespaces = {}, {}
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None)
        spec = getattr(module, "__spec__", None)
        if (
            path
            and Path(path).suffix in (".py", ".so")
            and ("SABLEHARBOR" in path or name.startswith(("enterprise", "tools")))
        ):
            p = Path(path).absolute()
            files[name] = {
                "path": str(p),
                "sha256": sha(p),
                "spec_origin": getattr(spec, "origin", None),
            }
        elif getattr(module, "__path__", None) is not None and name.startswith(
            ("enterprise", "tools")
        ):
            namespaces[name] = {
                "path": list(module.__path__),
                "spec_search_locations": list(spec.submodule_search_locations or []),
            }
    report = {
        "schema": "SH_COMPLETE_PRIVATE_AUTHORED_MATCHING_OWN_CASE_V1",
        "existing_world_copy": str(original_root),
        "new_audit_births": 0,
        "new_source_operations": 0,
        "original_and_copied_audit_sql_sha256": original_pin,
        "engagement_revision": before["revision"],
        "late_scalar_and_long_title_match": True,
        "display_omitted_scalars": projection["omitted_scalars"],
        "query_receipt_bytes_under1024": True,
        "old_saved_shape_and_exact_page": True,
        "learner403": True,
        "same_size_restored_mtime_key_tamper503": True,
        "positive_archive_pins": archive_pins,
        "negative_key_current_archive_not_accepted": True,
        "loaded_file_aliases": files,
        "namespaces": namespaces,
        "actual_eligibility": False,
    }
    (tmp_path / "OWN_CASE.json").write_text(json.dumps(report, indent=2, sort_keys=True))


def test_full_matching_budget_refuses_without_partial_results(tmp_path, monkeypatch):
    value = authored("MM-13.03.V01")
    definitions = tmp_path / "definitions"
    definitions.mkdir(mode=0o700)
    (definitions / (value["id"] + ".json")).write_text(json.dumps(value))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [value["id"]])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "archive"
    instructor_key.build_archive(definitions, archive)
    index = json.loads((archive / "index.json").read_bytes())
    monkeypatch.setattr(instructor_key, "MAX_COMPLETE_SEARCH_BYTES", 1)
    with pytest.raises(DomainError, match="Complete authored search cache limit"):
        instructor_key.semantic_search_bundle(archive, index)
