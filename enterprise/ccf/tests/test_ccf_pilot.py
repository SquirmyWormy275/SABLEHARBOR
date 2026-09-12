"""Pilot isolation, clean assessment initialization and private request handling."""

import json

import pytest
from cryptography import x509

from enterprise.ccf.operations import examples, pilot, store
from enterprise.ccf.tests import test_operations


def test_build_copies_plans_into_empty_private_store(tmp_path, monkeypatch):
    plans = test_operations.plans.__wrapped__()
    source = tmp_path / "delivery"
    (source / "control-exercise").mkdir(parents=True)
    store.initialize(
        source / "control-exercise/workflow.sqlite3", plans, examples.principals(["B"])
    )
    monkeypatch.setattr(pilot.delivery, "verify", lambda path: dict(verified=True))
    output = tmp_path / "pilot"
    result = pilot.build(source, output)
    assert result["actual_appointments"] == [] and result["actual_assurance"] == "NOT_ASSERTED"
    assert result["identity_setup"]["output"] == str(output / "identity")
    db = store.connect(output / "workflow.sqlite3")
    try:
        assert store.replay(db) == {}
        assert store.configuration(db)["plans"] == plans
        assert {r[0] for r in db.execute("SELECT id FROM principal")} == {
            "PILOT-PREPARER",
            "PILOT-REVIEWER",
            "PILOT-OPERATOR",
        }
    finally:
        db.close()
    assert not list(output.glob("*.credential"))
    assert all(not p.stat().st_mode & 0o077 for p in output.rglob("*"))
    assert (output / "tls/ca.pem").read_bytes() == (output / "identity/ca.pem").read_bytes()
    cert = x509.load_pem_x509_certificate((output / "tls/server.pem").read_bytes())
    assert cert.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName) == ["localhost"]
    with pytest.raises(ValueError, match="new private directory"):
        pilot.build(source, output)


@pytest.mark.parametrize("symlink", [False, True])
def test_request_rejects_exposed_or_linked_token_before_network(tmp_path, symlink):
    token = tmp_path / "token.json"
    token.write_text(json.dumps(dict(access_token="private-fixture")))
    if symlink:
        target = token
        target.chmod(0o600)
        token = tmp_path / "link.json"
        token.symlink_to(target)
    else:
        token.chmod(0o644)
    with pytest.raises(ValueError, match="private regular file"):
        pilot.request(tmp_path, token, tmp_path / "report.json")
    assert not (tmp_path / "report.json").exists()
