"""Public operator commands use neutral inputs; no installed case bank is required."""

import json

import pytest

from tools.audit_suite.operator import main, private_write


def test_validate_configuration_outputs_digest_without_input_contents(tmp_path, capsys):
    path = tmp_path / "configuration.json"
    path.write_text('{"selections": []}')
    assert main(["validate-config", "--mode", "CLEAN", "--configuration", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PASS_CONFIGURATION"
    assert len(output["configuration_sha256"]) == 64
    assert "selections" not in output


def test_invalid_configuration_fails_closed(tmp_path, capsys):
    path = tmp_path / "configuration.json"
    path.write_text('{"selections": [{"selector_id": "INVALID"}]}')
    assert main(["validate-config", "--mode", "MESSY", "--configuration", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"


def test_private_outputs_reject_overwrite_and_symlink(tmp_path):
    tmp_path.chmod(0o700)
    target = tmp_path / "receipt.json"
    private_write(target, {"value": "original"})
    with pytest.raises(FileExistsError):
        private_write(target, {"value": "changed"})
    alias = tmp_path / "alias.json"
    alias.symlink_to(target)
    with pytest.raises(FileExistsError):
        private_write(alias, {"value": "changed"})
    assert json.loads(target.read_text()) == {"value": "original"}
    assert target.stat().st_mode & 0o077 == 0


def test_demo_missing_sources_creates_no_store(tmp_path, capsys):
    state = tmp_path / "state"
    result = main(
        [
            "demo",
            "--corpus-root",
            str(tmp_path / "absent"),
            "--private-root",
            str(state),
            "--credentials",
            str(tmp_path / "credentials.json"),
            "--receipt",
            str(tmp_path / "receipt.json"),
        ]
    )
    assert result == 1 and not state.exists()
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"


@pytest.mark.parametrize(
    "action",
    [
        "DOCUMENT_SCOPED_CONCLUSION",
        "REQUEST_MISSING_CORROBORATION",
        "REQUEST_PRIMARY_AUTHORITY_AND_APPLICABILITY_REVIEW",
    ],
)
def test_manual_path_intentions_never_release_evidence(action):
    from enterprise.audit_suite.corpus import validate_bound_variant
    from tests.audit_suite.test_authority_editions import neutral

    value = neutral("MM-13.03.V01")
    value["playable_paths"][0]["actions"] = [action, "INSPECT:A1"]
    result = validate_bound_variant(
        value,
        {"owner": "Neutral owner"},
        {"period_start": "2027-01-04", "period_end": "2027-12-31"},
    )
    assert result["status"] == "FAIL"
    assert result["event_paths"][0]["released_count"] == 0
    assert all("Unsupported executable" not in e["error"] for e in result["errors"])
    assert any("actually released" in e["error"] for e in result["errors"])


def test_unknown_manual_action_still_rejected():
    from enterprise.audit_suite.corpus import validate_bound_variant
    from tests.audit_suite.test_authority_editions import neutral

    value = neutral("MM-13.03.V01")
    value["playable_paths"][0]["actions"] = ["UNKNOWN_ACTION"]
    result = validate_bound_variant(
        value,
        {"owner": "Neutral owner"},
        {"period_start": "2027-01-04", "period_end": "2027-12-31"},
    )
    assert result["status"] == "FAIL"
    assert any("Unsupported executable" in e["error"] for e in result["errors"])
