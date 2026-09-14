"""Neutral access history; no authored case answers or real credentials."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.instructor_access import InstructorAccessLog, identity_digest
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_authority_editions import neutral


def test_hash_chain_sanitization_and_concurrent_append(tmp_path):
    tmp_path.chmod(0o700)
    log = InstructorAccessLog(tmp_path / "private-log")

    def append(i):
        return log.append(
            actor="neutral-actor",
            engagement="neutral-engagement",
            target=f"untrusted-ID-{i}",
            outcome="DENIED",
            http_status=403,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append, range(12)))
    rows = log.verify()
    assert len(rows) == 12
    raw = (log.root / "access.jsonl").read_text()
    assert "neutral-actor" not in raw and "untrusted-ID" not in raw
    assert all(r["actor_digest"] == identity_digest("neutral-actor") for r in rows)
    assert log.root.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in log.root.iterdir())
    original = (log.root / "access.jsonl").read_bytes()
    (log.root / "access.jsonl").write_bytes(original.splitlines(keepends=True)[0])
    with pytest.raises(DomainError, match="integrity"):
        append(20)
    assert (log.root / "access.jsonl").read_bytes() == original.splitlines(keepends=True)[0]


def test_symlink_and_public_modes_rejected(tmp_path):
    tmp_path.chmod(0o700)
    outside = tmp_path / "outside"
    outside.write_text("untouched")
    root = tmp_path / "audit"
    root.mkdir(mode=0o700)
    (root / "access.jsonl").symlink_to(outside)
    log = InstructorAccessLog(root)
    with pytest.raises(DomainError):
        log.append(actor="a", engagement="e", target=None, outcome="DENIED", http_status=403)
    assert outside.read_text() == "untouched"
    other = tmp_path / "public"
    other.mkdir(mode=0o755)
    with pytest.raises(DomainError):
        InstructorAccessLog(other).append(
            actor="a", engagement="e", target=None, outcome="DENIED", http_status=403
        )


def test_authenticated_routes_log_pins_without_company_history_or_key_mutation(
    tmp_path, monkeypatch
):
    identifier = "MM-13.03.V01"
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / f"{identifier}.json").write_text(json.dumps(neutral(identifier)))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [identifier])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    archive = parent / "keys"
    instructor_key.build_archive(definitions, archive)
    pins_before = {
        p.relative_to(archive): p.read_bytes() for p in archive.rglob("*") if p.is_file()
    }
    app = create_app(tmp_path / "audit", instructor_key_root=archive, allowed_hosts=["testserver"])
    store = app.state.engine.store
    teacher = store.provision("Neutral instructor", ["instructor"])
    learner = store.provision("Neutral learner", ["learner"])
    state = store.create(
        teacher["id"],
        {
            "title": "Neutral archive",
            "artifacts": [],
            "discipline": "IT",
            "mode": "CLEAN",
            "phase": "ACTIVE",
            "simulated_at": "2027-01-01T00:00:00Z",
        },
        "create",
    )
    store.grant(state["id"], learner["id"], "learn")
    client = TestClient(app, base_url="https://testserver")
    headers = {"Authorization": "Bearer " + teacher["credential"]}
    student = {"Authorization": "Bearer " + learner["credential"]}
    base = f"/api/engagements/{state['id']}"
    before = client.get(base, headers=headers).json()
    assert client.get(base + "/instructor-key/" + identifier, headers=student).status_code == 403
    index = client.get(base + "/instructor-key", headers=headers)
    assert index.status_code == 200
    assert client.get(base + "/instructor-key/" + identifier, headers=headers).status_code == 200
    assert (
        client.get(base + "/instructor-key/UNKNOWN-PRIVATE-ID", headers=headers).status_code == 404
    )
    log = InstructorAccessLog(store.root / "instructor-key-access")
    rows = log.verify()
    assert [r["outcome"] for r in rows] == ["DENIED", "SUCCESS", "SUCCESS", "NOT_FOUND"]
    assert rows[1]["archive_sha256"] == index.json()["archive"]["sha256"]
    assert rows[2]["key_sha256"] == index.json()["entries"][0]["key_sha256"]
    assert rows[2]["source_sha256"] == index.json()["entries"][0]["raw_sha256"]
    assert client.get(base, headers=headers).json() == before
    for endpoint in (base, "/api/bootstrap"):
        raw = client.get(endpoint, headers=student).text
        assert identifier not in raw and "actor_digest" not in raw
    raw = (log.root / "access.jsonl").read_text()
    assert teacher["credential"] not in raw and identifier not in raw
    assert "UNKNOWN-PRIVATE-ID" not in raw and "Neutral source comparison" not in raw
    assert {
        p.relative_to(archive): p.read_bytes() for p in archive.rglob("*") if p.is_file()
    } == pins_before
    source = archive / "sources" / f"{identifier}.json"
    source.write_bytes(b"corrupt retained source")
    denied = client.get(base + "/instructor-key/" + identifier, headers=headers)
    assert denied.status_code == 503
    assert log.verify()[-1]["outcome"] == "UNAVAILABLE"
    assert source.read_bytes() == b"corrupt retained source"
    # Restore this neutral source explicitly: the next 503 must prove log failure,
    # rather than the already demonstrated source failure.
    source.write_bytes(pins_before[source.relative_to(archive)])
    # Audit corruption itself blocks delivery and is never silently repaired.
    log_path = log.root / "access.jsonl"
    damaged = log_path.read_bytes().replace(b'"DENIED"', b'"SUCCESS"', 1)
    log_path.write_bytes(damaged)
    assert client.get(base + "/instructor-key", headers=headers).status_code == 503
    assert log_path.read_bytes() == damaged
