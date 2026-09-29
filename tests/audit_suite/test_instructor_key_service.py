import json
import os

from fastapi.testclient import TestClient

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_authority_editions import neutral


def test_instructor_only_unbound_routes_and_real_tamper(tmp_path, monkeypatch):
    identifier = "MM-13.03.V01"
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / f"{identifier}.json").write_text(json.dumps(neutral(identifier)))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [identifier])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "keys"
    instructor_key.build_archive(definitions, archive)
    app = create_app(tmp_path / "audit", instructor_key_root=archive, allowed_hosts=["testserver"])
    store = app.state.engine.store
    instructor = store.provision("Instructor", ["instructor"])
    learner = store.provision("Learner", ["learner"])
    reviewer = store.provision("Reviewer", ["reviewer"])
    state = store.create(
        instructor["id"], {"title": "Protected library", "artifacts": []}, "create"
    )
    store.grant(state["id"], learner["id"], "learn")
    store.grant(state["id"], reviewer["id"], "review")
    client = TestClient(app, base_url="https://testserver")
    url = f"/api/engagements/{state['id']}/instructor-key"
    assert client.get(url).status_code == 401
    for principal in [learner, reviewer]:
        headers = {"Authorization": "Bearer " + principal["credential"]}
        assert client.get(url, headers=headers).status_code == 403
        assert client.get(url + "/" + identifier, headers=headers).status_code == 403
    headers = {"Authorization": "Bearer " + instructor["credential"]}
    index = client.get(url, headers=headers)
    assert index.status_code == 200, index.text
    assert index.json()["binding"]["status"] == "NOT_BOUND"
    detail = client.get(url + "/" + identifier, headers=headers)
    assert detail.json()["status"] == "UNBOUND_REFERENCE_LIBRARY"
    assert detail.json()["key"]["review"]["professional"] == "UNVALIDATED"
    assert identifier not in client.get(f"/api/engagements/{state['id']}", headers=headers).text
    source = archive / "sources" / f"{identifier}.json"
    original_stat = source.stat()
    data = source.read_bytes()
    source.write_bytes(b" " + data[1:])
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    denied = client.get(url + "/" + identifier, headers=headers)
    assert denied.status_code == 503
    assert "tampered" not in denied.text and str(archive) not in denied.text
    assert (
        client.get(url, headers={"Authorization": "Bearer " + learner["credential"]}).status_code
        == 403
    )
