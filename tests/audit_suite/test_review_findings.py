import pytest

from enterprise.audit_suite.inference import _response_schema, validate_result
from enterprise.audit_suite.store import DomainError


def fixture():
    finding = {
        "category": "SUPPORTED",
        "claim": "The submitted work identifies the observed date.",
        "learner_excerpt": {"source_ref": "WP1", "text": "Observed approval April 10"},
        "source_refs": ["WP1", "AUTH1"],
        "rationale": "The cited work records that date.",
        "uncertainty": "Only the inspected source is addressed.",
        "suggested_followup": "Inspect other originals before extending the conclusion.",
    }
    context = {
        "source_ids": ["WP1", "AUTH1"],
        "observable_source_ids": ["WP1"],
        "sources": [
            {"id": "WP1", "text": {"conclusion": "Observed approval April 10", "amount": 125.5}},
            {"id": "AUTH1", "text": "Normative authority text"},
        ],
    }
    return {
        "text": "Scoped experimental suggestions.",
        "source_refs": ["WP1"],
        "findings": [finding],
    }, context


def test_typed_finding_exact_decoded_excerpt_and_schema():
    value, context = fixture()
    result = validate_result("experimental_reviewer", value, context)
    assert result["findings"][0]["category"] == "SUPPORTED"
    assert result["whole_audit_grade"] is None
    schema = _response_schema("experimental_reviewer", context["source_ids"], context)
    assert "findings" in schema["required"]
    assert schema["properties"]["findings"]["maxItems"] == 5
    value["findings"][0]["learner_excerpt"]["text"] = "125.5"
    validate_result("experimental_reviewer", value, context)


@pytest.mark.parametrize(
    "mutation",
    [
        "falsified",
        "missing_ref",
        "authority_excerpt",
        "key_not_value",
        "numeric_substring",
        "quoted_rationale",
        "grade_category",
        "extra_grade",
    ],
)
def test_false_or_ineligible_finding_rejected(mutation):
    value, context = fixture()
    finding = value["findings"][0]
    if mutation == "falsified":
        finding["learner_excerpt"]["text"] = "Approval never occurred"
    elif mutation == "missing_ref":
        finding["source_refs"] = ["AUTH1"]
    elif mutation == "authority_excerpt":
        finding["learner_excerpt"] = {"source_ref": "AUTH1", "text": "Normative authority text"}
    elif mutation == "key_not_value":
        finding["learner_excerpt"]["text"] = "conclusion"
    elif mutation == "numeric_substring":
        finding["learner_excerpt"]["text"] = "25.5"
    elif mutation == "quoted_rationale":
        finding["rationale"] = 'The work states "Invented source text".'
    elif mutation == "grade_category":
        finding["category"] = "WHOLE_AUDIT_PASS"
    elif mutation == "extra_grade":
        value["whole_audit_grade"] = 99
    with pytest.raises(DomainError):
        validate_result("experimental_reviewer", value, context)


@pytest.mark.parametrize("category", ["NOT_OBSERVABLE", "REQUIRES_REVIEW"])
def test_unobservable_explicit_empty_excerpt(category):
    value, context = fixture()
    value["findings"][0].update(
        category=category, learner_excerpt={"source_ref": None, "text": ""}, source_refs=[]
    )
    validate_result("experimental_reviewer", value, context)
    value["findings"][0]["category"] = "UNSUPPORTED"
    with pytest.raises(DomainError):
        validate_result("experimental_reviewer", value, context)


def test_legacy_observations_and_empty_findings_preserved():
    value, context = fixture()
    value.pop("findings")
    value["observations"] = [
        {
            "text": "Historical suggestion",
            "source_refs": ["WP1"],
            "limitation": "Original bounded review",
        }
    ]
    result = validate_result("experimental_reviewer", value, context)
    assert result["observations"] == value["observations"]
    value["findings"] = []
    assert validate_result("experimental_reviewer", value, context)["findings"] == []
    value["findings"] = [fixture()[0]["findings"][0]] * 6
    with pytest.raises(DomainError, match="bounded"):
        validate_result("experimental_reviewer", value, context)
    with pytest.raises(DomainError, match="Only experimental"):
        validate_result("persona", {**value, "findings": []}, context)


def test_new_model_call_cannot_omit_findings_but_legacy_validator_can(tmp_path, monkeypatch):
    import json

    from enterprise.audit_suite.inference import LocalInference

    path = tmp_path / "provider.json"
    path.write_text(
        json.dumps(
            {
                "endpoint": "http://127.0.0.1:8791",
                "model": "fixture",
                "api_key": "fixture-test-only",
            }
        )
    )
    path.chmod(0o600)
    provider = LocalInference(path)
    monkeypatch.setattr(
        provider,
        "_complete",
        lambda *args, **kwargs: {"text": "Limited historical output", "source_refs": []},
    )
    with pytest.raises(DomainError, match="requires structured findings"):
        provider.generate(
            "experimental_reviewer",
            {
                "allowed_roles": ["experimental_reviewer"],
                "experimental_consent": True,
                "source_ids": [],
                "sources": [],
            },
            [{"role": "user", "content": "Review only observable work"}],
        )


def test_workpaper_excerpt_decodes_prose_not_serialized_metadata():
    import json

    value, context = fixture()
    context["sources"][0] = {
        "id": "WP1",
        "kind": "LEARNER_WORK",
        "text": json.dumps(
            {
                "text": 'Observed approval April 10; owner wrote "signed".',
                "actor": "SECRET_METADATA_ACTOR",
            }
        ),
    }
    value["findings"][0]["learner_excerpt"]["text"] = 'owner wrote "signed"'
    validate_result("experimental_reviewer", value, context)
    value["findings"][0]["learner_excerpt"]["text"] = "SECRET_METADATA_ACTOR"
    with pytest.raises(DomainError, match="decoded source"):
        validate_result("experimental_reviewer", value, context)
