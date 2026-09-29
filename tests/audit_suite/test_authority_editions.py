"""Neutral edition-selection fixtures; no real case bank or hidden mechanisms."""

import copy
import json

import pytest

from enterprise.audit_suite.corpus import Corpus, obligations
from enterprise.audit_suite.store import DomainError, digest


def neutral(variant_id):
    return {
        "schema_version": "1.0",
        "id": variant_id,
        "option_id": "MM-13.03",
        "selector_id": "MM-13",
        "title": "Neutral edition fixture",
        "disciplines": ["IT"],
        "applicability": {"IT": "Neutral scoped fixture", "FINANCIAL": "Not applicable"},
        "mechanism": {
            "cause": "Neutral source comparison",
            "process": "Neutral process",
            "control_domains": ["TEST"],
            "objective": "Preserve source identity",
            "failure_type": "NEUTRAL",
        },
        "facts": [
            {
                "id": "F1",
                "statement": "Neutral fixture",
                "source_class": "SYNTHETIC_SCENARIO_FACT",
                "visibility": "PRIVATE",
            }
        ],
        "actor_knowledge": [
            {"role_ref": "{{owner}}", "knows_fact_ids": ["F1"], "allowed_actions": ["clarify"]}
        ],
        "artifacts": [
            {
                "id": f"A{i}",
                "name": f"Source{i}.csv",
                "stage": stage,
                "request_purpose": "Neutral source",
                "recipe": {"format": "csv", "columns": ["id"], "rows": [{"id": str(i)}]},
            }
            for i, stage in [(1, "INITIAL"), (2, "FOLLOWUP")]
        ],
        "events": [
            {
                "id": "E1",
                "trigger": "REQUEST",
                "offset_business_days": 0,
                "effects": [{"operation": "release_artifact", "target": "A1", "value": "A1"}],
            }
        ],
        "playable_paths": [
            {
                "id": "P1",
                "actions": ["REQUEST"],
                "terminal_state": "SUPPORTED_LIMITATION",
                "rationale": "Neutral source limitation",
            }
        ],
        "rubric": {
            "supported_conclusions": ["Bounded"],
            "acceptable_alternatives": ["Further work"],
            "unsupported_guesses": ["Automatic pass"],
            "professional_validation": "UNVALIDATED",
        },
        "clean_counterpart": {"mechanism": "Neutral prevention"},
        "source_refs": ["Neutral fixture"],
        "binding_contract": {
            "authority_mode": "FICTIONAL_RULEBOOK",
            "applicable_control_ids": ["C1"],
        },
    }


@pytest.fixture
def edition_corpus(tmp_path):
    canonical = tmp_path / "definitions"
    canonical.mkdir()
    for i in range(1, 11):
        value = neutral(f"MM-13.03.V{i:02}")
        (canonical / (value["id"] + ".json")).write_text(json.dumps(value))
    edition = neutral("MM-13.03.V01")
    edition["title"] = "Distinct neutral real-source edition"
    edition["binding_contract"]["authority_mode"] = "REAL_SOURCE"
    edition["authority_source_pins"] = [
        {"sha256": "a" * 64, "url": "https://example.org/neutral", "locator": "section1"}
    ]
    path = tmp_path / "authority-editions/REAL_SOURCE/MM-13.03.V01.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(edition))
    return Corpus(tmp_path), path, edition


def test_source_edition_is_selected_without_replacing_canonical_or_obligation_count(edition_corpus):
    corpus, _, edition = edition_corpus
    before = digest(corpus.load(edition["id"]))
    selected = corpus.select(
        "MM-13.03", b"seed", discipline="IT", control_ids={"C1"}, parameters={"type": "REAL_SOURCE"}
    )
    assert selected == edition
    selected["title"] = "Caller mutation"
    assert digest(corpus.load(edition["id"])) == before
    assert len(obligations()) == 1110
    assert (
        corpus.select(
            "MM-13.03", b"seed", discipline="IT", parameters={"type": "FICTIONAL_RULEBOOK"}
        )["binding_contract"]["authority_mode"]
        == "FICTIONAL_RULEBOOK"
    )


def test_missing_source_edition_never_falls_back_to_fiction(edition_corpus):
    corpus, path, _ = edition_corpus
    path.unlink()
    with pytest.raises(DomainError) as error:
        corpus.select("MM-13.03", b"seed", discipline="IT", parameters={"type": "REAL_SOURCE"})
    assert error.value.code == "NO_APPLICABLE_AUTHORED_VARIANT"


@pytest.mark.parametrize("fault", ["identity", "pin", "mode", "symlink"])
def test_invalid_editions_fail_closed(edition_corpus, fault):
    corpus, path, original = edition_corpus
    edition = copy.deepcopy(original)
    if fault == "identity":
        edition["id"] = "MM-13.03.V02"
    elif fault == "pin":
        edition["authority_source_pins"] = []
    elif fault == "mode":
        edition["binding_contract"]["authority_mode"] = "FICTIONAL_RULEBOOK"
    else:
        target = path.with_suffix(".target")
        target.write_text(json.dumps(edition))
        path.unlink()
        path.symlink_to(target)
    if fault != "symlink":
        path.write_text(json.dumps(edition))
    with pytest.raises(DomainError):
        corpus.select("MM-13.03", b"seed", discipline="IT", parameters={"type": "REAL_SOURCE"})
