import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import instructor_key, instructor_original
from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_authority_editions import neutral


@pytest.fixture
def original(tmp_path, monkeypatch):
    ident = "MM-13.03.V01"
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    value = neutral(ident)
    value["title"] = "Unicode 雪 é preserved"
    raw = (json.dumps(value, ensure_ascii=False, indent=3) + "\n\n").encode()
    (definitions / f"{ident}.json").write_bytes(raw)
    monkeypatch.setattr(instructor_key, "obligations", lambda: [ident])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "keys"
    instructor_key.build_archive(definitions, archive)
    app = create_app(tmp_path / "audit", instructor_key_root=archive, allowed_hosts=["testserver"])
    store = app.state.engine.store
    actor = store.provision("Instructor", ["instructor"])
    learner = store.provision("Learner", ["learner"])
    state = store.create(actor["id"], {"title": "Neutral", "artifacts": []}, "create")
    store.grant(state["id"], learner["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    url = f"/api/engagements/{state['id']}/instructor-key/{ident}/original"
    return client, store, actor, learner, state, archive, raw, url


def headers(actor):
    return {"Authorization": "Bearer " + actor["credential"]}


def test_exact_original_and_denied_and_missing(original):
    client, store, actor, learner, state, archive, raw, url = original
    before = store.history(actor["id"], state["id"])
    assert client.get(url).status_code == 401
    assert client.get(url, headers=headers(learner)).status_code == 403
    assert (
        client.get(url.replace("MM-13.03.V01", "MISSING"), headers=headers(actor)).status_code
        == 404
    )
    response = client.get(url, headers=headers(actor))
    assert response.status_code == 200, response.text
    body = response.json()
    assert base64.b64decode(body["content_base64"], validate=True) == raw
    assert body["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert body["byte_count"] == len(raw)
    assert body["binding"] == {"status": "NOT_BOUND", "engagement_id": state["id"]}
    assert str(archive) not in response.text
    assert response.headers["cache-control"] == "no-store, private"
    assert store.history(actor["id"], state["id"]) == before
    log = [
        json.loads(line)
        for line in (store.root / "instructor-key-access/access.jsonl").read_text().splitlines()
    ]
    assert [r["outcome"] for r in log] == ["DENIED", "NOT_FOUND", "SUCCESS"]
    assert all(r["operation"] == "ORIGINAL" for r in log)


@pytest.mark.parametrize("mutation", ["tamper", "missing", "oversize", "alias"])
def test_original_fails_closed(original, mutation, monkeypatch):
    client, store, actor, _, _, archive, raw, url = original
    path = archive / "sources/MM-13.03.V01.json"
    if mutation == "tamper":
        path.write_bytes(raw + b" ")
    elif mutation == "missing":
        path.unlink()
    elif mutation == "oversize":
        monkeypatch.setattr(instructor_original, "MAX_ORIGINAL_BYTES", len(raw) - 1)
    else:
        path.unlink()
        path.symlink_to(archive / "index.json")
    response = client.get(url, headers=headers(actor))
    assert response.status_code == 503
    assert "content_base64" not in response.text and str(archive) not in response.text


def test_late_revocation_prevents_original_delivery(original, monkeypatch):
    client, store, actor, _, _, _, _, url = original
    real = instructor_original.read_original
    calls = 0

    def read(*args):
        nonlocal calls
        value = real(*args)
        calls += 1
        if calls == 2:
            with store.connect() as db:
                db.execute("UPDATE principals SET revoked=1 WHERE id=?", (actor["id"],))
        return value

    monkeypatch.setattr(instructor_original, "read_original", read)
    response = client.get(url, headers=headers(actor))
    assert response.status_code == 401
    assert "content_base64" not in response.text


def test_instructor_without_engagement_membership_denied(original):
    client, store, _, _, _, _, _, url = original
    outsider = store.provision("Other instructor", ["instructor"])
    response = client.get(url, headers=headers(outsider))
    assert response.status_code == 403
    assert "content_base64" not in response.text


def test_changed_original_during_read_denied(original, monkeypatch):
    client, _, actor, _, _, archive, _, url = original
    real = instructor_original.read_original
    calls = 0

    def read(*args):
        nonlocal calls
        value = real(*args)
        calls += 1
        if calls == 2:
            (archive / "sources/MM-13.03.V01.json").write_bytes(value + b" ")
        return value

    monkeypatch.setattr(instructor_original, "read_original", read)
    response = client.get(url, headers=headers(actor))
    assert response.status_code == 503
    assert "content_base64" not in response.text
