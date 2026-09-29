"""The protected service stays closed without exact private operator configuration."""

from __future__ import annotations

import hashlib
import json

import pytest

from enterprise.audit_suite.__main__ import main
from enterprise.audit_suite.company_rights_launch import _case_for_context, _private_config
from enterprise.audit_suite.company_rights_producer import RightsUnavailable, VerifiedCaseContext
from enterprise.audit_suite.store import DomainError


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
