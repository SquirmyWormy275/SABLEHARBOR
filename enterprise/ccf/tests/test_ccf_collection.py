import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from enterprise.ccf.operations import collection, connectors, examples


@pytest.fixture
def config(tmp_path):
    evidence, census = tmp_path / "events.json", tmp_path / "roster.json"
    record = examples.record("termination", "reno")
    evidence.write_text(json.dumps([record]))
    census.write_text(json.dumps([{"id": record["id"]}]))
    scope = dict(examples.scope(), boundary_id="reno")
    return collection.config_template(evidence, census, scope)


def packet(config):
    return collection.prepare_packets(
        config["evidence"], config["census"], [], "", examples.AT, examples.EXPIRY
    )


def test_draft_does_not_invent_review(config):
    result = packet(config)
    assert result["ready_for_review"]
    assert result["test_outcome"] == "NOT_RUN"
    assert result["intake"]["manual_tests"] == {}
    assert result["population"]["criteria_review"] == ""
    assert result["provenance"]["census"]["raw_page_sha256"]


def test_independent_missing_and_excluded_census(config):
    path = config["census"]["path"]
    rows = json.loads(open(path).read()) + [{"id": "MISSING"}]
    with open(path, "w") as f:
        json.dump(rows, f)
    result = packet(config)
    assert not result["ready_for_review"]
    assert result["reconciliation"]["missing_ids"] == ["MISSING"]
    result = collection.prepare_packets(
        config["evidence"],
        config["census"],
        ["MISSING"],
        "Outside scope, requires review",
        examples.AT,
        examples.EXPIRY,
    )
    assert result["ready_for_review"]
    assert result["population"]["source_count"] == 2


def test_same_extraction_and_wrong_scope(config):
    config["census"].update(path=config["evidence"]["path"], query=config["evidence"]["query"])
    with pytest.raises(ValueError, match="separately"):
        packet(config)
    config["evidence"]["scope"]["boundary_id"] = "boise"
    with pytest.raises(ValueError, match="boundary"):
        connectors.collect(config["evidence"])


def test_schedule_idempotency_and_tamper(config, tmp_path):
    state, output = tmp_path / "schedule.db", tmp_path / "out"
    first = collection.run_job(config, state, output, examples.AT)
    again = collection.run_job(config, state, output, examples.AT)
    assert first["status"] == "COLLECTED"
    assert again["status"] == "ALREADY_COLLECTED"
    changed = copy.deepcopy(config)
    changed["census"]["query"] = "changed"
    with pytest.raises(ValueError, match="configuration changed"):
        collection.run_job(changed, state, output, examples.AT)
    with open(first["artifact"], "w") as f:
        f.write("{}")
    with pytest.raises(ValueError, match="altered"):
        collection.run_job(config, state, output, examples.AT)


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        mode = "ok"
        auth = []

        def log_message(self, *args):
            pass

        def do_GET(self):
            self.auth.append(self.headers.get("Authorization"))
            row = {"id": "b" if "?" in self.path else "a"}
            next_url = "/export?page=2" if "?" not in self.path else None
            if self.mode == "duplicate":
                row = {"id": "a"}
            if self.mode == "escape":
                next_url = "http://127.0.0.1:1/stolen"
            if self.mode in {"leak", "escaped_leak"}:
                row["secret"] = "test-private-value"
            total = 3 if self.mode == "incomplete" else 2
            raw = json.dumps(dict(records=[row], total=total, next=next_url)).encode()
            if self.mode == "escaped_leak":
                raw = raw.replace(b"test-private-value", b"\\u0074est-private-value")
            if self.mode == "duplicate_key":
                raw = raw.replace(b'"total": 2', b'"total": 2, "total": 2')
            self.send_response(200)
            self.end_headers()
            self.wfile.write(raw)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, Handler
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def test_http_pagination_and_credential_isolation(server, monkeypatch):
    httpd, handler = server
    monkeypatch.setenv("CCF_TEST_KEY", "test-private-value")
    cfg = dict(
        type="https_json",
        purpose="census",
        source_system="demo",
        query="roster",
        endpoint=f"http://127.0.0.1:{httpd.server_port}/export",
        credential={"env": "CCF_TEST_KEY"},
    )
    with pytest.raises(ValueError, match="HTTPS"):
        connectors.collect(cfg)
    result = connectors.collect(cfg, allow_test_http=True)
    assert [r["id"] for r in result["records"]] == ["a", "b"]
    assert len(result["provenance"]["raw_page_sha256"]) == 2
    import base64
    import hashlib

    for encoded, expected_hash in zip(
        result["provenance"]["raw_pages_base64"],
        result["provenance"]["raw_page_sha256"],
        strict=True,
    ):
        original = base64.b64decode(encoded)
        assert hashlib.sha256(original).hexdigest() == expected_hash
        assert isinstance(json.loads(original)["records"], list)
    assert "test-private-value" not in json.dumps(result)
    assert handler.auth == ["Bearer test-private-value"] * 2
    for mode, error in [
        ("duplicate", "Duplicate"),
        ("incomplete", "Incomplete"),
        ("escape", "exact"),
        ("leak", "credential"),
        ("escaped_leak", "credential"),
        ("duplicate_key", "Duplicate source JSON key"),
    ]:
        handler.mode = mode
        with pytest.raises(ValueError, match=error):
            connectors.collect(cfg, allow_test_http=True)


def test_failed_job_is_retryable(config, tmp_path):
    source = config["evidence"]["path"]
    original = open(source).read()
    with open(source, "w") as f:
        f.write('[{"id":"bad"}]')
    with pytest.raises(KeyError):
        collection.run_job(config, tmp_path / "jobs.db", tmp_path / "out", examples.AT)
    with open(source, "w") as f:
        f.write(original)
    assert (
        collection.run_job(config, tmp_path / "jobs.db", tmp_path / "out", examples.AT)["status"]
        == "COLLECTED"
    )


def test_public_connection_rejects_rebound_private_ip(monkeypatch):
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    connection = connectors.PublicHTTPSConnection("source.example")
    with pytest.raises(ValueError, match="Public endpoint"):
        connection.connect()


def test_limits_and_private_credentials(server, tmp_path):
    httpd, _ = server
    token = tmp_path / "token"
    token.write_text("test-private-value")
    token.chmod(0o644)
    cfg = dict(
        type="https_json",
        purpose="census",
        source_system="demo",
        query="roster",
        endpoint=f"http://127.0.0.1:{httpd.server_port}/export",
        credential={"file": str(token)},
    )
    with pytest.raises(ValueError, match="private"):
        connectors.collect(cfg, allow_test_http=True)
    token.chmod(0o600)
    cfg["max_pages"] = 1
    with pytest.raises(ValueError, match="page limit"):
        connectors.collect(cfg, allow_test_http=True)
    cfg["max_pages"] = 2
    cfg["max_bytes"] = 10
    with pytest.raises(ValueError, match="byte limit"):
        connectors.collect(cfg, allow_test_http=True)


def test_csv_typed_payload(config, tmp_path):
    import csv

    row = examples.record("termination", "reno")
    row["data"] = json.dumps(row["data"])
    path = tmp_path / "events.csv"
    with path.open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    cfg = dict(config["evidence"], type="local_csv", path=str(path))
    assert connectors.collect(cfg)["records"][0]["data"]["enabled"] is False


def test_unreconciled_attempt_retained_and_repaired_same_slot(config, tmp_path):
    from pathlib import Path

    census = Path(config["census"]["path"])
    original = census.read_text()
    census.write_text(json.dumps(json.loads(original) + [{"id": "MISSING"}]))
    state, output = tmp_path / "state.db", tmp_path / "out"
    failed = collection.run_job(config, state, output, examples.AT)
    assert failed["status"] == "RECONCILIATION_FAILED"
    assert failed["retryable"] and not failed["ready_for_review"]
    assert Path(failed["artifact"]).is_file()
    census.write_text(original)
    fixed = collection.run_job(config, state, output, examples.AT)
    assert fixed["status"] == "COLLECTED" and fixed["ready_for_review"]
    assert Path(failed["artifact"]).is_file()
    again = collection.run_job(config, state, output, examples.AT)
    assert again["status"] == "ALREADY_COLLECTED" and again["ready_for_review"]


def test_orphan_artifact_rejects_public_permissions(config, tmp_path):
    import sqlite3
    from pathlib import Path

    state, output = tmp_path / "state.db", tmp_path / "out"
    result = collection.run_job(config, state, output, examples.AT)
    with sqlite3.connect(state) as db:
        db.execute("DELETE FROM runs")
    Path(result["artifact"]).chmod(0o644)
    with pytest.raises(ValueError, match="collision"):
        collection.run_job(config, state, output, examples.AT)
