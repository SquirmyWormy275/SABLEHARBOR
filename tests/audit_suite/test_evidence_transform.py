from copy import deepcopy

import pytest

from enterprise.audit_suite.artifacts import inspect_upload, render
from enterprise.audit_suite.evidence_transform import project
from enterprise.audit_suite.store import DomainError


def source():
    return {
        "artifact_kind": "REVIEW_DECISION",
        "source_identity": "SOURCE-1",
        "recipe": {
            "format": "csv",
            "title": "Review decision",
            "columns": ["record", "preparer", "reviewer"],
            "rows": [{"record": "R1", "preparer": "P1", "reviewer": "P2"}],
        },
    }


def contract(kind="INCOMPLETE_APPROVAL"):
    return {
        "kind": kind,
        "recovery_route": "ACTUAL_SOURCE_RELEASE",
        "runtime_binding": {
            "required_artifact_kind": "REVIEW_DECISION",
            "required_fields": ["record", "preparer"],
            "target_fields": ["reviewer"],
            "approval_roles": {"preparer": "preparer", "reviewer": "reviewer"},
        },
    }


def test_projection_uses_actual_native_rows_and_restores_original_on_followup():
    original = source()
    frozen = deepcopy(original)
    result = project(original, contract())
    data, _ = render(result["initial_recipe"])
    assert b"P2" not in data and b"R1" in data and b"P1" in data
    assert render(result["followup_recipe"])[0] == render(original["recipe"])[0]
    assert original == frozen
    original["recipe"]["rows"][0]["reviewer"] = "P1"
    with pytest.raises(DomainError, match="distinct actual"):
        project(original, contract())


def test_no_invented_alternate_or_missing_field_and_damage_is_observable():
    with pytest.raises(DomainError, match="alternate source is absent"):
        project(source(), contract("SUBSTITUTE_OBSOLETE"))
    missing = contract()
    missing["runtime_binding"]["target_fields"] = ["invented_signoff"]
    with pytest.raises(DomainError, match="semantic fields"):
        project(source(), missing)
    native = source()
    native["recipe"]["format"] = "xlsx"
    result = project(native, contract("DAMAGE_NATIVE"))
    assert (
        inspect_upload("broken.xlsx", render(result["initial_recipe"])[0])["status"]
        == "QUARANTINED"
    )
    assert (
        inspect_upload("original.xlsx", render(result["followup_recipe"])[0])["status"]
        == "AVAILABLE"
    )


def test_native_object_projection_preserves_envelope_and_exact_original():
    import json

    original = source()
    original["recipe"] = {
        "format": "json",
        "title": "Decision export",
        "document": {
            "system": "Neutral system",
            "packet": {
                "records": [
                    {"record": "R1", "preparer": "P1", "reviewer": "P2"},
                ]
            },
        },
    }
    typed = contract()
    typed["runtime_binding"].update(
        object_rows_path=["packet", "records"],
        object_fields=["record", "preparer", "reviewer"],
    )
    frozen = deepcopy(original)
    result = project(original, typed)
    data = render(result["initial_recipe"])[0]
    assert b"P2" not in data
    assert json.loads(data)["system"] == "Neutral system"
    assert json.loads(data)["packet"]["records"][0]["record"] == "R1"
    assert render(result["followup_recipe"])[0] == render(frozen["recipe"])[0]
    assert original == frozen
    original["recipe"]["document"]["signed_by"] = "Signed by P2"
    with pytest.raises(DomainError, match="leak"):
        project(original, typed)


def test_native_object_paths_require_explicit_semantics():
    original = source()
    original["recipe"] = {"format": "json", "document": {"rows": []}}
    with pytest.raises(DomainError, match="explicit row path"):
        project(original, contract())


def test_numeric_redaction_does_not_treat_date_digits_as_disclosure():
    original = {
        "recipe": {
            "format": "csv",
            "title": "Measurement record",
            "columns": ["factor", "recorded_on"],
            "rows": [{"factor": 1, "recorded_on": "2027-01-01"}],
        },
    }
    typed = {
        "kind": "REDACT_FIELDS",
        "recovery_route": "SUPPORTED_LIMITATION",
        "runtime_binding": {"target_fields": ["factor"]},
    }
    result = project(original, typed)
    assert result["initial_recipe"]["rows"][0]["factor"] == "[REDACTED]"
    original["recipe"]["rows"][0]["another_factor"] = 1
    with pytest.raises(DomainError, match="leak"):
        project(original, typed)
