import pytest

from enterprise.audit_suite import company_activity_plan_sources as strict
from enterprise.audit_suite import company_activity_source_capture as capture
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_activity_plan_sources import source as producer_source


@pytest.fixture
def source(tmp_path):
    original = producer_source.__wrapped__(tmp_path)
    binding = original.pop("binding")
    return original | {
        "source_store_id": binding["source_store_id"],
        "expected_records": binding["expected_records"],
    }


def test_actual_producer_capture_preserves_content_labels_and_originals(source):
    originals = {
        p: sha(p.read_bytes())
        for p in source["source_manifest_path"].parent.rglob("*")
        if p.is_file()
    }
    result = capture.capture_source(**source)
    receipt = result["receipt"]
    assert receipt["capture_basis"] == capture.CAPTURE_BASIS
    assert receipt["selected_records"] == source["expected_records"]
    assert receipt["source_store_id"] == "EXPLICIT-CALLER-LABEL"
    assert receipt["caller_predeclared_selected_metadata_pin"] is False
    assert receipt["strict_recheck_completed"] is True
    assert receipt["capture_count"] == 1
    assert set(receipt["metadata_fields"]) == {
        "company",
        "branch",
        "system",
        "record",
        "version",
        "sha256",
        "event_at",
        "available_at",
        "origin",
        "provenance",
    }
    assert result["source_versions_sha256"] == receipt["captured_selected_metadata_sha256"]
    assert all(sha(p.read_bytes()) == checksum for p, checksum in originals.items())
    assert not source["destination"].exists()


@pytest.mark.parametrize(
    "fault",
    [
        "missing_sha",
        "wrong_sha",
        "bool",
        "duplicate",
        "future",
        "alias",
        "inside",
        "ancestor",
        "manifest",
    ],
)
def test_rejects_undeclared_or_invalid_content_and_unsafe_routes(source, tmp_path, fault):
    if fault == "missing_sha":
        del source["expected_records"][0]["sha256"]
    elif fault == "wrong_sha":
        source["expected_records"][0]["sha256"] = "0" * 64
    elif fault == "bool":
        source["expected_records"][0]["version"] = True
    elif fault == "duplicate":
        source["expected_records"][1] = source["expected_records"][0]
    elif fault == "future":
        source["consumed_at"] = "2027-01-01T00:00:00Z"
    elif fault == "alias":
        link = tmp_path / "alias"
        link.symlink_to(source["source_root"], target_is_directory=True)
        source["source_root"] = link
    elif fault == "inside":
        source["destination"] = source["source_root"] / "consumer"
    elif fault == "ancestor":
        source["destination"] = tmp_path
    else:
        source["expected_manifest_sha256"] = "0" * 64
    with pytest.raises(CompanyStoreError):
        capture.capture_source(**source)


def test_changed_metadata_is_not_recaptured(source, monkeypatch):
    original = strict.read_inputs

    def changed(*args):
        rows, _ = original(*args)
        return rows, "a" * 64

    monkeypatch.setattr(strict, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="metadata pin differs"):
        capture.capture_source(**source)


def test_manifest_changed_after_capture_rejected(source, monkeypatch):
    original = capture.read_inputs

    def changed(*args):
        result = original(*args)
        with source["source_manifest_path"].open("ab") as stream:
            stream.write(b"\n")
        return result

    monkeypatch.setattr(capture, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="manifest pin differs"):
        capture.capture_source(**source)


def test_manifest_changed_during_strict_read_rejected(source, monkeypatch):
    original = strict.read_inputs

    def changed(*args):
        result = original(*args)
        with source["source_manifest_path"].open("ab") as stream:
            stream.write(b"\n")
        return result

    monkeypatch.setattr(strict, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="manifest pin differs"):
        capture.capture_source(**source)
