"""One genuinely authored small private archive; source bytes remain authoritative."""

import hashlib
import json
import os
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.instructor_key import semantic_search_projection
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_authority_editions import neutral


def authored(identifier):
    value = neutral(identifier)
    value["title"] = "Authored exception: P014 and lab asset α"
    value["mechanism"]["cause"] = "A literal retry exception, not a grade"
    value["facts"][0]["statement"] = "Operator P014 inspected ASSET-LAB on 2027-11-01"
    value["actor_knowledge"][0]["role_ref"] = "P014 named role"
    value["artifacts"][0]["name"] = "ASSET-LAB.csv"
    value["playable_paths"][0]["rationale"] = "Authored discovery requires corroboration"
    return value


def entry_and_raw(value):
    source = json.dumps(value, ensure_ascii=False).encode()
    key = instructor_key.migrate_definition(source)
    raw = json.dumps(key, ensure_ascii=False).encode()
    return {
        "id": value["id"],
        "raw_sha256": hashlib.sha256(source).hexdigest(),
        "canonical_sha256": digest(value),
        "key_sha256": hashlib.sha256(raw).hexdigest(),
    }, raw


def test_authored_private_http_saved_query_cache_and_tamper(tmp_path, monkeypatch):
    identifier = "MM-13.03.V01"
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    value = authored(identifier)
    (definitions / (identifier + ".json")).write_text(json.dumps(value, ensure_ascii=False))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [identifier])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "archive"
    instructor_key.build_archive(definitions, archive)
    original = {str(p): p.read_bytes() for p in archive.rglob("*") if p.is_file()}
    app = create_app(tmp_path / "audit", instructor_key_root=archive, allowed_hosts=["testserver"])
    store = app.state.engine.store
    teacher = store.provision("OWN teacher", ["instructor"])
    learner = store.provision("OWN learner", ["learner"])
    state = app.state.engine.create(
        teacher["id"],
        {
            "command_id": "OWN-create",
            "title": "OWN literal terms",
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
    before_state = store.get(teacher["id"], state["id"])
    store.grant(state["id"], learner["id"], "learn")
    headers = {"Authorization": "Bearer " + teacher["credential"]}
    denied_headers = {"Authorization": "Bearer " + learner["credential"]}
    url = f"/api/engagements/{state['id']}/instructor-key"
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get(url, headers=headers)
        assert response.status_code == 200, response.text
        index = response.json()
        projection = index["entries"][0]["semantic_search"]
        assert projection["terms"][0] == {"pointer": "/title", "text": value["title"]}
        terms = {t["pointer"]: t["text"] for t in projection["terms"]}
        assert "P014" in terms["/facts/0/statement"] and "ASSET-LAB" in terms["/artifacts/0/name"]
        assert projection["source_sha256"] == index["entries"][0]["raw_sha256"]
        assert len(json.dumps(projection).encode()) <= 4096
        assert client.get(url, headers=denied_headers).status_code == 403
        assert (
            "semantic_search"
            not in client.get(f"/api/engagements/{state['id']}", headers=denied_headers).text
        )
        # Existing saved shape receives no new semantic field or fabricated facet.
        user = {
            "title": "Literal old-shape search",
            "query": "ASSET-LAB",
            "selector": "all",
            "option": "all",
            "review": "all",
            "scenario": None,
            "page": 0,
        }
        route = f"/api/engagements/{state['id']}/instructor-key-views"
        saved = client.post(
            route,
            headers=headers,
            json={
                "view_id": None,
                "kind": "ARCHIVE",
                "key_pin": index["archive"]["sha256"],
                "user": user,
                "expected_version": 0,
                "expected_engagement_revision": 0,
                "command_id": "OWN-semantic-save",
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["user"] == user
        context = app.state.instructor_key_views._context(teacher["id"], state["id"], "ARCHIVE")
        assert context["data"]["entries"][0]["semantic_search"] == projection
        assert client.get(url, headers=headers).json() == index
        assert store.get(teacher["id"], state["id"]) == before_state
        assert all(p.read_bytes() == original[str(p)] for p in archive.rglob("*") if p.is_file())
        # Changed bytes cannot retain cached authored terms, even with restored mtime.
        key = archive / "keys" / (identifier + ".json")
        before = key.stat()
        raw = key.read_bytes().replace(b"retry exception", b"wrong exception", 1)
        assert len(raw) == before.st_size
        key.write_bytes(raw)
        os.utime(key, ns=(before.st_atime_ns, before.st_mtime_ns))
        refused = client.get(url, headers=headers)
        assert refused.status_code == 503 and "P014" not in refused.text
        assert (
            app.state.instructor_key_views._context(teacher["id"], state["id"], "ARCHIVE")["error"]
            == "KEY_UNAVAILABLE"
        )
        assert client.get(url, headers=denied_headers).status_code == 403
        assert store.get(teacher["id"], state["id"]) == before_state


@pytest.mark.parametrize("field", ["id", "raw_sha256", "canonical_sha256", "key_sha256"])
def test_projection_refuses_mismatched_source_binding(field):
    entry, raw = entry_and_raw(authored("MM-13.03.V01"))
    wrong = deepcopy(entry)
    wrong[field] = "MM-13.03.V02" if field == "id" else "0" * 64
    with pytest.raises(DomainError):
        semantic_search_projection(raw, wrong)


def test_projection_budget_discloses_omissions_and_exact_long_value_basis():
    value = authored("MM-13.03.V01")
    value["title"] = "α" * 500
    value["facts"] = [
        {
            "id": "F" + str(i),
            "statement": "literal " * 100,
            "source_class": "SYNTHETIC_SCENARIO_FACT",
            "visibility": "PRIVATE",
        }
        for i in range(100)
    ]
    value["actor_knowledge"][0]["knows_fact_ids"] = ["F0"]
    entry, raw = entry_and_raw(value)
    projection = semantic_search_projection(raw, entry)
    assert len(instructor_key._json(projection)) <= 4096
    assert len(projection["terms"]) <= 32 and projection["omitted_scalars"] > 0
    title = projection["terms"][0]
    assert title["pointer"] == "/title" and title["truncated"] is True
    assert title["value_sha256"] == digest(value["title"]) and title["full_characters"] == 500
    assert sum(projection["included_by_field"].values()) == len(projection["terms"])
    assert sum(projection["omitted_by_field"].values()) == projection["omitted_scalars"]
    assert all(projection["included_by_field"][f] > 0 for f in projection["coverage_fields"])
