"""Signed-token identity and real database boundary integration, entirely synthetic."""

import copy
import io
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from enterprise.ccf.operations import examples as ex
from enterprise.ccf.operations import store
from enterprise.ccf.operations.identity import AuthenticationError, Identity, private_json
from enterprise.ccf.operations.service import Application
from enterprise.ccf.tests import test_operations


@pytest.fixture
def plans():
    return test_operations.plans.__wrapped__()


@pytest.fixture
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="fixture", alg="RS256", use="sig")
    config = dict(
        issuer="https://id.example.invalid",
        audience="ccf-api",
        required_claims={"token_use": "access"},
        jwks={"keys": [jwk]},
        bindings=[
            dict(
                issuer="https://id.example.invalid",
                subject="fixture-user",
                principal="DEMO-PREPARER",
            ),
            dict(
                issuer="https://id.example.invalid", subject="reviewer", principal="DEMO-REVIEWER"
            ),
            dict(issuer="https://id.example.invalid", subject="admin", principal="DEMO-ADMIN"),
        ],
    )

    def token(**changes):
        now = int(time.time())
        claims = dict(
            iss=config["issuer"],
            aud="ccf-api",
            sub="fixture-user",
            iat=now - 1,
            nbf=now - 1,
            exp=now + 300,
            token_use="access",
        )
        claims.update(changes)
        return "Bearer " + jwt.encode(claims, key, algorithm="RS256", headers={"kid": "fixture"})

    return config, key, token


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://evil.invalid"},
        {"aud": "other"},
        {"sub": "unmapped"},
        {"exp": 1},
        {"nbf": 9999999999},
        {"iat": 9999999999},
        {"exp": 9999999999},
        {"token_use": "id"},
        {"aud": ["ccf-api"]},
        {"iat": True},
    ],
)
def test_reject_invalid_signed_claims(signing, changes):
    config, _, token = signing
    with pytest.raises(AuthenticationError):
        Identity(config).authenticate(token(**changes))


def test_signature_and_header_attacks(signing):
    config, key, token = signing
    identity = Identity(config)
    good = token()
    assert identity.authenticate(good) == "DEMO-PREPARER"
    claims = jwt.decode(good[7:], options={"verify_signature": False})
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for encoded in [
        jwt.encode(claims, wrong, algorithm="RS256", headers={"kid": "fixture"}),
        jwt.encode(claims, "x" * 32, algorithm="HS256", headers={"kid": "fixture"}),
        jwt.encode(
            claims,
            key,
            algorithm="RS256",
            headers={"kid": "fixture", "jku": "https://evil.invalid/keys"},
        ),
        jwt.encode(claims, key, algorithm="RS256", headers={"kid": "unknown"}),
    ]:
        with pytest.raises(AuthenticationError):
            identity.authenticate("Bearer " + encoded)
    del claims["exp"]
    with pytest.raises(AuthenticationError):
        identity.authenticate(
            "Bearer " + jwt.encode(claims, key, algorithm="RS256", headers={"kid": "fixture"})
        )


def test_config_fails_closed(signing, tmp_path):
    config, _, _ = signing
    for change in (
        {"issuer": "http://id.example.invalid"},
        {"required_claims": {}},
        {"jwks": {"keys": []}},
    ):
        with pytest.raises(ValueError):
            Identity({**config, **change})
    duplicate = copy.deepcopy(config)
    duplicate["bindings"].append(duplicate["bindings"][0])
    with pytest.raises(ValueError):
        Identity(duplicate)
    path = tmp_path / "identity.json"
    path.write_text(json.dumps(config))
    path.chmod(0o644)
    with pytest.raises(ValueError):
        private_json(path)
    path.chmod(0o600)
    assert private_json(path) == config


def request(app, token, path="/v1/report", body=None, **headers):
    raw = json.dumps(body).encode() if body is not None else b""
    env = dict(
        HTTP_HOST="ccf.example.invalid",
        HTTP_AUTHORIZATION=token,
        REQUEST_METHOD="POST" if body is not None else "GET",
        PATH_INFO=path,
        CONTENT_TYPE="application/json",
        CONTENT_LENGTH=str(len(raw)),
    )
    env["wsgi.url_scheme"] = "https"
    env["REMOTE_ADDR"] = "127.0.0.1"
    env["wsgi.input"] = io.BytesIO(raw)
    env.update(headers)
    response = []
    data = b"".join(app(env, lambda status, h: response.extend([status, dict(h)])))
    return response[0], json.loads(data), response[1]


def test_authenticated_workflow_scoping_and_revocation(signing, plans, tmp_path, monkeypatch):
    config, _, token = signing
    path = tmp_path / "workflow.sqlite3"
    store.initialize(path, plans, ex.principals(["B"]))
    monkeypatch.setattr(store, "now", lambda: ex.AT)
    app = Application(path, Identity(config), "https://ccf.example.invalid")
    body = dict(
        case_id="CASE",
        action="create",
        payload=dict(plan_id="COLLECT:SH-IAM-004:B", scope=ex.scope()),
        expected_revision=0,
    )
    status, result, headers = request(app, token(), "/v1/command", body)
    assert status == "200 OK" and result["assignee"] == "DEMO-PREPARER"
    assert headers["Cache-Control"] == "no-store"
    assert request(app, token(), "/v1/command", body)[0].startswith("400")
    rows = [ex.record("termination", "B", True)]
    population = dict(
        case_id="CASE", action="population", payload=ex.population(rows), expected_revision=1
    )
    assert request(app, token(), "/v1/command", population)[0].startswith("400")
    assert request(app, token(sub="reviewer"), "/v1/command", population)[0] == "200 OK"
    intake = dict(
        case_id="CASE",
        action="intake",
        payload=ex.submission(plans["COLLECT:SH-IAM-004:B"], rows),
        expected_revision=2,
    )
    status, state, _ = request(app, token(), "/v1/command", intake)
    assert status == "200 OK" and state["submissions"][-1]["result"]["outcome"] == "FAIL"
    review = dict(
        case_id="CASE",
        action="review",
        payload=dict(
            submission_id=state["submissions"][-1]["id"],
            decision="ACCEPT",
            rationale="Synthetic independent review",
        ),
        expected_revision=3,
    )
    assert request(app, token(), "/v1/command", review)[0].startswith("400")
    status, state, _ = request(app, token(sub="reviewer"), "/v1/command", review)
    assert status == "200 OK" and state["historical_failure"] and state["state"] == "FINDING_OPEN"
    body["actor"] = "DEMO-ADMIN"
    assert request(app, token(), "/v1/command", body)[0].startswith("400")
    assert request(app, "", HTTP_X_AUTHENTICATED_USER="DEMO-ADMIN")[0].startswith("401")
    assert request(app, token(), HTTP_HOST="evil.invalid")[0].startswith("400")
    assert request(app, token(), REMOTE_ADDR="203.0.113.7")[0].startswith("400")
    assert request(app, token(), **{"wsgi.url_scheme": "http"})[0].startswith("400")
    assert request(app, token(), HTTP_ORIGIN="https://evil.invalid")[0].startswith("400")
    monkeypatch.setattr(store, "now", lambda: "2026-09-10T10:01:00+00:00")
    assert (
        request(app, token(sub="admin"), "/v1/revoke", {"subject": "DEMO-PREPARER"})[0] == "200 OK"
    )
    assert request(app, token())[0] != "200 OK"
    assert "CASE" in request(app, token(sub="reviewer"))[1]["cases"]


def test_size_and_malformed_input_rejected(signing, plans, tmp_path):
    config, _, token = signing
    path = tmp_path / "workflow.sqlite3"
    store.initialize(path, plans, ex.principals(["B"]))
    app = Application(path, Identity(config), "https://ccf.example.invalid")
    for headers in [
        {"CONTENT_LENGTH": "999999999"},
        {"CONTENT_LENGTH": "-1"},
        {"CONTENT_TYPE": "text/plain"},
        {"HTTP_TRANSFER_ENCODING": "chunked"},
    ]:
        assert request(app, token(), "/v1/command", {}, **headers)[0].startswith("400")


@pytest.mark.parametrize("missing", ["iss", "sub", "aud", "exp", "iat", "nbf", "token_use"])
def test_required_signed_claims_cannot_be_omitted(signing, missing):
    config, key, token = signing
    claims = jwt.decode(token()[7:], options={"verify_signature": False})
    del claims[missing]
    encoded = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "fixture"})
    with pytest.raises(AuthenticationError):
        Identity(config).authenticate("Bearer " + encoded)


def test_boundary_scoping_for_reports_commands_and_revocation(
    signing, plans, tmp_path, monkeypatch
):
    config, _, token = signing
    config = copy.deepcopy(config)
    config["bindings"].append(
        dict(issuer=config["issuer"], subject="other-boundary", principal="OTHER-PREPARER")
    )
    plans = copy.deepcopy(plans)
    other = copy.deepcopy(plans["COLLECT:SH-IAM-004:B"])
    other.update(id="COLLECT:SH-IAM-004:C", boundary_id="C")
    plans[other["id"]] = other
    people = ex.principals(["B"])
    people.append(
        dict(
            id="OTHER-PREPARER",
            permissions=["prepare"],
            boundaries=["C"],
            valid_from="2026-01-01T00:00:00+00:00",
            expires_at="2027-01-01T00:00:00+00:00",
        )
    )
    path = tmp_path / "workflow.sqlite3"
    store.initialize(path, plans, people)
    monkeypatch.setattr(store, "now", lambda: ex.AT)
    app = Application(path, Identity(config), "https://ccf.example.invalid")
    create = dict(
        case_id="C-CASE",
        action="create",
        payload=dict(plan_id=other["id"], scope=ex.scope()),
        expected_revision=0,
    )
    assert request(app, token(), "/v1/command", create)[0].startswith("400")
    assert request(app, token(sub="other-boundary"), "/v1/command", create)[0] == "200 OK"
    assert request(app, token())[1]["cases"] == {}
    assert "C-CASE" in request(app, token(sub="other-boundary"))[1]["cases"]
    population = dict(
        case_id="C-CASE",
        action="population",
        payload=ex.population([ex.record("termination", "C")]),
        expected_revision=1,
    )
    assert request(app, token(sub="reviewer"), "/v1/command", population)[0].startswith("400")
    monkeypatch.setattr(store, "now", lambda: "2026-09-10T10:01:00+00:00")
    assert request(app, token(sub="admin"), "/v1/revoke", {"subject": "OTHER-PREPARER"})[
        0
    ].startswith("400")
    assert request(app, token(sub="other-boundary"))[0] == "200 OK"
    db = store.connect(path)
    try:
        assert db.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM revocation").fetchone()[0] == 0
    finally:
        db.close()


@pytest.mark.parametrize(
    "raw",
    [
        b'{"subject":"A","subject":"B"}',
        b'{"subject":NaN}',
        b'{"subject":Infinity}',
        b'{"subject":-Infinity}',
    ],
)
def test_duplicate_keys_and_nonfinite_json_rejected(signing, plans, tmp_path, raw):
    config, _, token = signing
    path = tmp_path / "workflow.sqlite3"
    store.initialize(path, plans, ex.principals(["B"]))
    app = Application(path, Identity(config), "https://ccf.example.invalid")
    status, _, _ = request(
        app,
        token(),
        "/v1/revoke",
        {},
        **{"CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)},
    )
    assert status.startswith("400")


@pytest.mark.parametrize("field", ["actor", "at", "clock", "result"])
def test_reserved_payload_fields_cannot_override_store_context(
    signing, plans, tmp_path, monkeypatch, field
):
    config, _, token = signing
    path = tmp_path / "workflow.sqlite3"
    store.initialize(path, plans, ex.principals(["B"]))
    monkeypatch.setattr(store, "now", lambda: ex.AT)
    app = Application(path, Identity(config), "https://ccf.example.invalid")
    payload = dict(plan_id="COLLECT:SH-IAM-004:B", scope=ex.scope())
    payload[field] = "CALLER-INJECTION"
    create = dict(case_id="CASE", action="create", payload=payload, expected_revision=0)
    assert request(app, token(), "/v1/command", create)[0].startswith("400")
    assert request(app, token())[1]["cases"] == {}


def test_production_gunicorn_trusts_only_explicit_local_https_scheme(signing, plans, tmp_path):
    """Exercise actual HTTP parsing/WSGI scheme propagation using an ephemeral listener."""
    import importlib.util
    import os
    import socket
    import subprocess
    import sys
    import urllib.error
    import urllib.request
    from pathlib import Path

    if importlib.util.find_spec("gunicorn") is None:
        pytest.skip("Production Gunicorn requires the ccf-service extra on Python 3.12+")
    config, _, token = signing
    database = tmp_path / "workflow.sqlite3"
    people = ex.principals(["B"])
    for person in people:
        person.update(
            valid_from="2000-01-01T00:00:00+00:00", expires_at="2100-01-01T00:00:00+00:00"
        )
    store.initialize(database, plans, people)
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps(config))
    identity.chmod(0o600)
    root = Path(__file__).resolve().parents[3]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            str(root / "enterprise/ccf/operations/deploy/gunicorn.conf.py"),
            "--bind",
            f"127.0.0.1:{port}",
            "enterprise.ccf.operations.service:from_environment()",
        ],
        cwd=root,
        env={
            **os.environ,
            "CCF_DATABASE": str(database),
            "CCF_IDENTITY_CONFIG": str(identity),
            "CCF_PUBLIC_ORIGIN": "https://ccf.example.invalid",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Gunicorn did not start")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("Gunicorn did not become ready")

        def status(scheme=None, host="ccf.example.invalid", authenticated=True):
            headers = {"Host": host}
            if scheme is not None:
                headers["X-Forwarded-Proto"] = scheme
            if authenticated:
                headers["Authorization"] = token()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/report", headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.status
            except urllib.error.HTTPError as error:
                return error.code

        assert status() == 400
        assert status("http") == 400
        assert status("https") == 200
        assert status("https", host="evil.invalid") == 400
        assert status("https", authenticated=False) == 401
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
