import socket

from enterprise.audit_suite import parser_sandbox
from enterprise.audit_suite.artifacts import inspect_upload, render
from enterprise.audit_suite.review import extract


def test_actual_isolated_pdf_xlsx_and_decoded_text():
    for format in ["pdf", "xlsx", "json", "csv"]:
        data, _ = render(
            {
                "format": format,
                "title": "Neutral parser record",
                "columns": ["record"],
                "rows": [{"record": "Observed record"}],
            }
        )
        inspected = inspect_upload("sample." + format, data)
        assert inspected["status"] == "AVAILABLE", inspected
        assert inspected["parser_isolation"]["network"] == "ISOLATED"
        value = extract(
            {"id": "A", "name": "sample." + format, "sha256": "0" * 64, "status": "AVAILABLE"}, data
        )
        assert value["status"] == "EXTRACTED", value
        assert any("Observed record" in str(s["text"]) for s in value["sources"])


def test_missing_sandbox_and_invalid_pdf_fail_closed(monkeypatch):
    assert inspect_upload("invalid.pdf", b"%PDF- broken")["status"] == "QUARANTINED"
    monkeypatch.setattr(parser_sandbox.shutil, "which", lambda _: None)
    assert inspect_upload("ok.txt", b"text")["status"] == "QUARANTINED"
    result = extract({"id": "A", "name": "ok.txt", "status": "AVAILABLE"}, b"text")
    assert result["status"] == "HUMAN_REVIEW_REQUIRED" and result["sources"] == []


def test_actual_namespace_denies_private_files_network_and_host_environment(tmp_path, monkeypatch):
    secret = tmp_path / "private-secret"
    secret.write_text("must not be mounted")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    worker = tmp_path / "parser_worker.py"
    worker.write_text(
        """import json,os,socket
from pathlib import Path
blocked=False
try:
 socket.create_connection(("127.0.0.1","""
        + str(port)
        + """),timeout=.2)
except OSError: blocked=True
print(json.dumps({"private_absent":not Path("""
        + repr(str(secret))
        + """).exists(),
"network_blocked":blocked,"environment_absent":"AUDIT_TEST_SECRET" not in os.environ}))
"""
    )
    monkeypatch.setattr(parser_sandbox, "__file__", str(tmp_path / "parser_sandbox.py"))
    monkeypatch.setenv("AUDIT_TEST_SECRET", "must not inherit")
    try:
        result = parser_sandbox.parse("extract", {"id": "A", "name": "x.txt"}, b"input")
        assert (
            result["private_absent"] and result["network_blocked"] and result["environment_absent"]
        )
    finally:
        listener.close()


def test_worker_stdout_is_bounded_regular_file_and_timeout_fails_closed(tmp_path, monkeypatch):
    import subprocess

    worker = tmp_path / "parser_worker.py"
    worker.write_text("""import os,resource,stat
assert stat.S_ISREG(os.fstat(1).st_mode)
resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024*1024,8*1024*1024))
for _ in range(10): os.write(1,b'x'*1024*1024)
""")
    monkeypatch.setattr(parser_sandbox, "__file__", str(tmp_path / "parser_sandbox.py"))
    result = parser_sandbox.parse("extract", {"id": "A", "name": "x.txt"}, b"input")
    assert result["status"] == "HUMAN_REVIEW_REQUIRED"

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("isolated-worker", 15)

    monkeypatch.setattr(parser_sandbox.subprocess, "run", timeout)
    assert (
        parser_sandbox.parse("inspect", {"id": "A", "name": "x.txt"}, b"input")["status"]
        == "QUARANTINED"
    )
