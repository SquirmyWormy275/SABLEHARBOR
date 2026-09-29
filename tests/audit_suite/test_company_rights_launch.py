"""The protected service stays closed without exact private operator configuration."""

from __future__ import annotations

import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.__main__ import main
from enterprise.audit_suite.company_rights_launch import (
    POLICY_MODULE,
    POLICY_PATH,
    REHEARSAL_PATH,
    ROOT,
    _case_for_context,
    _private_config,
    reviewed_company_factories,
    stage_reviewed_company_authority,
)
from enterprise.audit_suite.company_rights_producer import RightsUnavailable, VerifiedCaseContext
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, Store


def _write_config(tmp_path, **changes):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    row = {
        "version": 1,
        "source_commit": "a" * 40,
        "policy_sha256": "b" * 64,
        "policy_module_sha256": "c" * 64,
        "rights_root": str(private / "rights"),
        "checkpoint_root": str(private / "checkpoint"),
    }
    row.update(changes)
    path = private / "company-config.json"
    content = json.dumps(row, sort_keys=True).encode()
    path.write_bytes(content)
    path.chmod(0o600)
    return path, hashlib.sha256(content).hexdigest()


def test_private_launch_config_requires_exact_hash_and_private_regular_file(tmp_path):
    path, digest = _write_config(tmp_path)
    assert _private_config(path, digest)["source_commit"] == "a" * 40
    with pytest.raises(DomainError):
        _private_config(path, "0" * 64)
    path.chmod(0o644)
    with pytest.raises(DomainError):
        _private_config(path, digest)


@pytest.mark.parametrize(
    "changes",
    [
        {"version": True},
        {"source_commit": "bad"},
        {"rights_root": "relative"},
        {"native_manifest_file": "/tmp/manifest.json"},
        {"native_manifest_sha256": "d" * 64},
        {"rehearsal_authority_sha256": "d" * 64},
        {"rehearsal_binding_file": "/tmp/binding.json"},
        {"unexpected_grant": "allow"},
    ],
)
def test_private_launch_config_rejects_extra_authority_or_incomplete_closure(
    tmp_path, changes
):
    path, digest = _write_config(tmp_path, **changes)
    with pytest.raises(DomainError):
        _private_config(path, digest)


@pytest.mark.parametrize(
    "option", ["--company-rights-config", "--company-rights-config-sha256"]
)
def test_cli_rejects_unpaired_protected_launch_option(tmp_path, option):
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text("<html></html>")
    value = str(tmp_path / "config.json") if option.endswith("config") else "a" * 64
    with pytest.raises(SystemExit):
        main(
            [
                "serve", "--private-root", str(tmp_path / "state"),
                "--web-root", str(web_root), "--local-http", option, value,
            ]
        )


def test_case_clock_requires_exact_server_authenticated_person_engagement_and_purpose():
    authority = {
        "person_bindings": [
            {"role": "auditor", "person_id": "SH-EMP-INTERNAL-AUDIT-0001"},
            {"role": "record_owner", "person_id": "SH-EMP-ESS-0005"},
        ],
        "engagement": {"tenant": "SH", "purpose": "inspection"},
        "case_clock_approval": {"case_as_of": "2027-04-02T00:00:00+00:00"},
    }
    binding = {
        "engagement_id": "E-1",
        "principals": {"auditor": "P-A", "record_owner": "P-O"},
    }
    context = VerifiedCaseContext(
        principal_id="P-A", session_id="S-1", engagement_id="E-1",
        person_id="SH-EMP-INTERNAL-AUDIT-0001", tenant="SH", purpose="inspection",
    )
    assert _case_for_context(authority, binding, context) == "2027-04-02T00:00:00+00:00"
    for changed in (
        {"principal_id": "P-O"},
        {"person_id": "SH-EMP-ESS-0005"},
        {"engagement_id": "E-2"},
        {"tenant": "OTHER"},
        {"purpose": "training"},
    ):
        denied = VerifiedCaseContext(**(context.__dict__ | changed))
        with pytest.raises(RightsUnavailable):
            _case_for_context(authority, binding, denied)


def test_reviewed_rehearsal_stages_only_exact_authority_and_protects_http(tmp_path):
    """Use the accepted four-row source and actual policy, portal Store, and HTTP routes."""
    for name in ("portal", "rights", "checkpoint", "config"):
        (tmp_path / name).mkdir(mode=0o700)
    store = Store(tmp_path / "portal")
    auditor = store.provision("Synthetic auditor", ["learner"])
    owner = store.provision("Synthetic source owner", ["reviewer"])
    with store.connect() as db:
        db.execute("INSERT INTO engagements VALUES(?,?,?)", ("ENG-REHEARSAL", 0, "{}"))
    store.grant("ENG-REHEARSAL", auditor["id"], "learn")
    store.grant("ENG-REHEARSAL", owner["id"], "review")

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    binding = {
        "version": 1,
        "authority_sha256": sha(ROOT / REHEARSAL_PATH),
        "engagement_id": "ENG-REHEARSAL",
        "principals": {"auditor": auditor["id"], "record_owner": owner["id"]},
    }
    binding_file = tmp_path / "config" / "binding.json"
    binding_file.write_text(json.dumps(binding, sort_keys=True))
    binding_file.chmod(0o600)
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True)
    config = {
        "version": 1,
        "source_commit": commit.strip(),
        "policy_sha256": sha(ROOT / POLICY_PATH),
        "policy_module_sha256": sha(ROOT / POLICY_MODULE),
        "rights_root": str(tmp_path / "rights"),
        "checkpoint_root": str(tmp_path / "checkpoint"),
        "rehearsal_authority_sha256": binding["authority_sha256"],
        "rehearsal_binding_file": str(binding_file),
        "rehearsal_binding_sha256": sha(binding_file),
    }
    config_file = tmp_path / "config" / "launch.json"
    config_file.write_text(json.dumps(config, sort_keys=True))
    config_file.chmod(0o600)
    config_sha = sha(config_file)
    factory, native = reviewed_company_factories(config_file, config_sha)
    with pytest.raises(RightsUnavailable):
        factory(SimpleNamespace(store=store))
    receipt = stage_reviewed_company_authority(config_file, config_sha, tmp_path / "portal")
    assert (receipt["bindings"], receipt["records"], receipt["rights_revision"]) == (2, 4, 6)
    assert receipt["authority_sha256"] == binding["authority_sha256"]
    with pytest.raises(DomainError):
        stage_reviewed_company_authority(config_file, config_sha, tmp_path / "portal")

    app = create_app(
        tmp_path / "portal", allowed_hosts=["testserver"],
        company_rights_factory=factory, company_native_rights_factory=native,
    )
    client = TestClient(app, base_url="https://testserver")
    login = client.post("/api/session", json={"credential": auditor["credential"]})
    assert login.status_code == 200
    root = "/api/engagements/ENG-REHEARSAL/company/rights/records/"
    for record in ("BASE", "VIEW", "NOTICE"):
        assert client.get(root + f"SH-DAE-REHEARSAL-{record}-001").status_code == 200
    assert client.get(root + "SH-DAE-REHEARSAL-DENIED-001").status_code == 403
    assert client.get("/api/engagements/ENG-REHEARSAL/company/systems").status_code == 403

    producer = factory(SimpleNamespace(store=store))
    source = json.loads((ROOT / REHEARSAL_PATH).read_bytes())
    assert producer.put_record(source["records"][0], expected_revision=6) == 7
    with pytest.raises(RightsUnavailable):
        factory(SimpleNamespace(store=store))  # An unreviewed rights revision blocks startup.
    assert client.get(root + "SH-DAE-REHEARSAL-BASE-001").status_code == 403
