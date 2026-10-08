"""A reviewed adapter may authorize only its explicitly reviewed source boundary."""

import hashlib
import json
from pathlib import Path

import pytest

from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_library_security_execution import adapter_gate
from enterprise.audit_suite.source_privacy_execution import gate

PINS = {
    "database_sha256": "a" * 64,
    "manifest_sha256": "b" * 64,
    "review_sha256": "c" * 64,
    "version_count": 17,
    "independent_acceptance_verdict": "PASS_COMPANY_FACING_LIBRARY_SELECTED_BOUNDARY",
    "source_quality_accepted_for_final_learner_audit": True,
}


@pytest.fixture
def reviewed_adapter(tmp_path):
    from enterprise.audit_suite import source_library_audit

    path = tmp_path / "independent-adapter-review.json"
    path.write_text(
        json.dumps(
            {
                "schema": "SH_ROOT_SOURCE_LIBRARY_ADAPTER_INDEPENDENT_REVIEW_V2",
                "verdict": "PASS_QUIESCENT_ENGINE_BOUND_ADAPTER",
                "source_execution_authorized": True,
                "adapter_module_sha256": hashlib.sha256(
                    Path(source_library_audit.__file__).read_bytes()
                ).hexdigest(),
                "accepted_main_library_pins": PINS,
            }
        )
    )
    path.chmod(0o600)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def check(kind, reviewed_adapter, pins):
    path, expected = reviewed_adapter
    if kind == "security":
        return adapter_gate(path, expected, pins)
    return gate(path, expected, method=False, library_pins=pins)


@pytest.mark.parametrize("kind", ["security", "privacy"])
def test_exact_reviewed_source_boundary_is_allowed(kind, reviewed_adapter):
    assert check(kind, reviewed_adapter, dict(PINS))["sha256"] == reviewed_adapter[1]


@pytest.mark.parametrize("kind", ["security", "privacy"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("database_sha256", "d" * 64),
        ("manifest_sha256", "e" * 64),
        ("review_sha256", "f" * 64),
        ("version_count", 18),
        ("independent_acceptance_verdict", "CANDIDATE"),
        ("source_quality_accepted_for_final_learner_audit", False),
    ],
)
def test_adapter_review_cannot_authorize_another_library(kind, reviewed_adapter, field, value):
    with pytest.raises(ProcedureError, match="does not authorize this exact source library"):
        check(kind, reviewed_adapter, {**PINS, field: value})


@pytest.mark.parametrize("kind", ["security", "privacy"])
def test_source_boundary_cannot_be_omitted(kind, reviewed_adapter):
    with pytest.raises(ProcedureError, match="does not authorize this exact source library"):
        check(kind, reviewed_adapter, None)
