"""Pilot credentials are private fictional accounts; no weak token grant is enabled."""

import json

import pytest
from cryptography import x509

from enterprise.ccf.operations import pilot_identity as pilot


def test_private_realm_has_separate_random_subjects_and_secure_grants(tmp_path):
    output = tmp_path / "identity"
    result = pilot.build(output, [{"id": "PILOT-PREPARE"}, {"id": "PILOT-REVIEW"}])
    assert result["origin"] == "SYNTHETIC" and result["production_ready"] is False
    realm = json.loads((output / "ccf-pilot-realm.json").read_text())
    client = realm["clients"][0]
    assert client["standardFlowEnabled"] and client["publicClient"]
    assert not client["directAccessGrantsEnabled"] and not client["implicitFlowEnabled"]
    assert not client["serviceAccountsEnabled"]
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["attributes"]["oauth2.device.authorization.grant.enabled"] == "true"
    assert realm["accessTokenLifespan"] == 300 and realm["sslRequired"] == "all"
    bindings = json.loads((output / "identity.pending.json").read_text())["bindings"]
    credentials = json.loads((output / "pilot-credentials.json").read_text())["users"]
    assert {b["subject"] for b in bindings} == {u["id"] for u in realm["users"]}
    assert len({u["password"] for u in credentials}) == 2
    assert all(len(u["password"]) >= 32 for u in credentials)
    assert all(p.stat().st_mode & 0o077 == 0 for p in output.iterdir())
    cert = x509.load_pem_x509_certificate((output / "server.pem").read_bytes())
    assert "localhost" in cert.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName)
    assert not (output / "ca-key.pem").exists()
    with pytest.raises(FileExistsError):
        pilot.build(output, [{"id": "PILOT-PREPARE"}])


@pytest.mark.parametrize(
    "issuer",
    [
        "http://localhost:8443/realms/ccf-pilot",
        "https://external.example:8443/realms/ccf-pilot",
        "https://localhost/realms/ccf-pilot",
        "https://localhost:8443/realms/other",
        "https://localhost:8443/realms/ccf-pilot?x=y",
    ],
)
def test_pilot_rejects_external_or_ambiguous_issuer(issuer):
    with pytest.raises(ValueError):
        pilot.local_issuer(issuer)


def test_pin_rejects_redirected_issuer_or_keys(tmp_path, monkeypatch):
    output = tmp_path / "identity"
    pilot.build(output, [{"id": "PILOT-PREPARE"}])
    monkeypatch.setattr(
        pilot,
        "fetch",
        lambda *_: {"issuer": "https://evil.invalid", "jwks_uri": "https://evil.invalid/keys"},
    )
    with pytest.raises(ValueError):
        pilot.pin(output)
    assert not (output / "identity.json").exists()


def test_device_request_does_not_print_device_secret(tmp_path, monkeypatch):
    output = tmp_path / "identity"
    pilot.build(output, [{"id": "PILOT-PREPARE"}])
    calls = []

    def response(root, path, data):
        calls.append((path, data))
        return dict(
            device_code="PRIVATE-DEVICE-CODE",
            user_code="VISIBLE-CODE",
            verification_uri="https://localhost:8443/realms/ccf-pilot/device",
            verification_uri_complete="https://localhost:8443/realms/ccf-pilot/device?user_code=VISIBLE-CODE",
            expires_in=600,
            interval=5,
        )

    monkeypatch.setattr(pilot, "fetch", response)
    visible = pilot.start_device(output)
    assert "device_code" not in visible
    assert "password" not in calls[0][1]
    assert (output / "device-session.json").stat().st_mode & 0o077 == 0
    monkeypatch.setattr(pilot, "fetch", lambda *_: {"error": "authorization_pending"})
    assert pilot.poll_device(output) == {"error": "authorization_pending"}
    assert not (output / "access-token.json").exists()


def test_launcher_uses_separate_pilot_database_and_no_password_arguments(tmp_path, monkeypatch):
    import os
    import runpy
    import subprocess

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setenv("KEYCLOAK_HOME", str(runtime))
    monkeypatch.setattr(os, "umask", lambda _: 0o022)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)))
    for name in ("first", "second"):
        output = tmp_path / name
        pilot.build(output, [{"id": "PILOT-PREPARE"}])
        runpy.run_path(str(output / "start-keycloak.py"))
    assert len(calls) == 4
    for index in (0, 2):
        command, options = calls[index]
        assert command[1] == "import" and "--override=false" in command
        assert any(arg.startswith("--file=") for arg in command)
        assert not any("password" in arg.lower() for arg in command)
        assert "KC_BOOTSTRAP_ADMIN_PASSWORD" in options["env"]
        start = calls[index + 1][0]
        assert "--http-enabled=false" in start and "--http-host=127.0.0.1" in start
        assert "--import-realm" not in start
    first = next(arg for arg in calls[0][0] if arg.startswith("--db-url="))
    second = next(arg for arg in calls[2][0] if arg.startswith("--db-url="))
    assert (
        first != second and "/first/keycloak-data/" in first and "/second/keycloak-data/" in second
    )
    assert not (runtime / "data/import").exists()
