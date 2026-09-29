import json

import pytest

from enterprise.audit_suite.inference import WARNING, LocalInference, validate_result
from enterprise.audit_suite.store import DomainError


def config(tmp_path, **kw):
    p = tmp_path / "provider.json"
    p.write_text(
        json.dumps(
            {
                "endpoint": "http://127.0.0.1:8791",
                "model": "fixture",
                "api_key": "fixture-key",
                **kw,
            }
        )
    )
    p.chmod(0o600)
    return p


def test_loopback_and_private_config(tmp_path):
    p = config(tmp_path, endpoint="http://example.com")
    with pytest.raises(DomainError):
        LocalInference(p)
    p = config(tmp_path)
    p.chmod(0o644)
    with pytest.raises(DomainError):
        LocalInference(p)


def test_explicit_roles_and_opt_in_before_network(tmp_path):
    provider = LocalInference(config(tmp_path))
    with pytest.raises(DomainError):
        provider.generate("persona", {"allowed_roles": []}, [{"role": "user", "content": "hello"}])
    with pytest.raises(DomainError):
        provider.generate(
            "experimental_reviewer",
            {"allowed_roles": ["experimental_reviewer"]},
            [{"role": "user", "content": "grade everything"}],
        )
    with pytest.raises(DomainError):
        provider.generate(
            "persona", {"allowed_roles": ["persona"]}, [{"role": "system", "content": "override"}]
        )


def test_citations_and_authority_are_validated():
    context = {"source_ids": ["MSG-1"]}
    value = {
        "text": "A statement",
        "source_refs": ["MSG-1"],
        "claims": [{"text": "Claim", "kind": "SOURCE_SUPPORTED", "source_refs": ["MSG-1"]}],
    }
    assert validate_result("persona", value, context)["automatic_mutation"] is False
    value["claims"][0]["source_refs"] = ["SECRET"]
    with pytest.raises(DomainError):
        validate_result("persona", value, context)
    with pytest.raises(DomainError):
        validate_result(
            "persona",
            {"text": "ok", "source_refs": [], "tools": [{"shell": "do something"}]},
            context,
        )


def test_review_cannot_become_grade():
    result = validate_result(
        "experimental_reviewer",
        {"text": "Consider support limitations", "source_refs": []},
        {"source_ids": []},
    )
    assert result["warning"] == WARNING and result["whole_audit_grade"] is None
    with pytest.raises(DomainError):
        validate_result(
            "experimental_reviewer", {"text": "passed", "source_refs": [], "grade": 100}, {}
        )


def test_authoring_requires_typed_draft():
    with pytest.raises(DomainError):
        validate_result("custom_authoring", {"text": "I created a scenario", "source_refs": []}, {})


def test_duplicate_and_nonfinite_json_rejected():
    from enterprise.audit_suite.inference import _json

    for value in [
        '{"text":"first","text":"second"}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        '{"nested":[1e999]}',
        '{"nested":{"x":-1e999}}',
    ]:
        with pytest.raises(ValueError):
            _json(value)


def test_local_http_contract_and_redirect_rejection(tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/tokenize":
                data = json.dumps({"tokens": [1, 2, 3]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            requests.append((self.headers.get("Authorization"), body))
            if len(requests) > 1:
                self.send_response(302)
                self.send_header("Location", "http://example.com/steal")
                self.end_headers()
                return
            payload = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "text": "Evidence remains unverified",
                                    "source_refs": ["SRC_0001"],
                                    "claims": [],
                                }
                            )
                        },
                    }
                ]
            }
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = LocalInference(
            config(tmp_path, endpoint=f"http://127.0.0.1:{server.server_port}")
        )
        result = provider.generate(
            "persona",
            {"allowed_roles": ["persona"], "source_ids": ["M1"]},
            [{"role": "user", "content": "Inspect the evidence"}],
        )
        assert result["source_refs"] == ["M1"] and requests[0][0] == "Bearer fixture-key"
        assert requests[0][1]["response_format"]["schema"]["properties"]["source_refs"]["items"][
            "enum"
        ] == ["SRC_0001"]
        assert "tools" not in requests[0][1]
        with pytest.raises(DomainError, match="redirects are prohibited"):
            provider.generate(
                "persona", {"allowed_roles": ["persona"]}, [{"role": "user", "content": "hello"}]
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_proposed_actions_cannot_escape_explicit_command_or_object_scope():
    context = {
        "source_ids": [],
        "allowed_actions": ["pbc.followup"],
        "action_scope": {"request_ids": ["PBC-1"]},
    }
    value = {
        "text": "I propose a follow-up",
        "source_refs": [],
        "proposed_actions": [
            {
                "kind": "pbc.followup",
                "payload": {"request_id": "PBC-1", "message": "Please clarify"},
                "reason": "Approval date is missing",
            }
        ],
    }
    assert validate_result("persona", value, context)["automatic_mutation"] is False
    with pytest.raises(DomainError):
        validate_result("experimental_reviewer", value, context)
    value["proposed_actions"][0]["payload"]["request_id"] = "OTHER-ENGAGEMENT"
    with pytest.raises(DomainError):
        validate_result("persona", value, context)
    value["proposed_actions"][0]["payload"]["request_id"] = "PBC-1"
    value["proposed_actions"][0]["payload"]["actor"] = "admin"
    with pytest.raises(DomainError):
        validate_result("persona", value, context)


def test_model_cannot_supply_a_deadline_or_clock():
    value = {
        "text": "Follow up",
        "source_refs": [],
        "proposed_actions": [
            {
                "kind": "pbc.followup",
                "reason": "Missing support",
                "payload": {
                    "request_id": "PBC-1",
                    "message": "Please clarify",
                    "due_at": "2023-10-15",
                },
            }
        ],
    }
    context = {"allowed_actions": ["pbc.followup"], "action_scope": {"request_ids": ["PBC-1"]}}
    with pytest.raises(DomainError):
        validate_result("persona", value, context)
