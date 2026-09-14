"""Neutral instructor indexing mechanics; no authored private answers."""

import hashlib
import json

import pytest

from enterprise.audit_suite import instructor_key
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_authority_editions import neutral


def test_pins_raw_and_canonical_source_without_inventing_graph_links():
    value = neutral("MM-13.03.V01")
    raw = json.dumps(value, indent=2).encode()
    key = instructor_key.migrate_definition(raw)
    compact = instructor_key.migrate_definition(json.dumps(value).encode())
    assert key["source"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert key["source"]["raw_sha256"] != compact["source"]["raw_sha256"]
    assert key["source"]["canonical_sha256"] == compact["source"]["canonical_sha256"]
    assert key["explanation"] == value
    assert {e["relation"] for e in key["graph"]["edges"]} == {
        "AUTHORED_KNOWLEDGE",
        "AUTHORED_RELEASE",
    }
    assert key["review"]["unlinked_path_actions"] == 1
    assert key["review"]["professional"] == "UNVALIDATED"
    assert key["review"]["grading"] == "NOT_RUN"
    assert key["company_store_import"] == "PROHIBITED"


def test_only_exact_action_reference_becomes_edge():
    value = neutral("MM-13.03.V01")
    value["playable_paths"][0]["actions"] = ["E1", "inspect E1"]
    key = instructor_key.migrate_definition(json.dumps(value).encode())
    edges = [e for e in key["graph"]["edges"] if e["relation"] == "EXACT_ACTION_REFERENCE"]
    assert len(edges) == 1 and edges[0]["to"] == "event:E1"
    assert key["review"]["unlinked_path_actions"] == 1


def test_missing_reference_rejected_by_existing_corpus_validator():
    value = neutral("MM-13.03.V01")
    value["actor_knowledge"][0]["knows_fact_ids"] = ["ABSENT"]
    with pytest.raises(DomainError, match="missing facts"):
        instructor_key.migrate_definition(json.dumps(value).encode())


@pytest.fixture
def archive_inputs(tmp_path, monkeypatch):
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    identifier = "MM-13.03.V01"
    (definitions / f"{identifier}.json").write_text(json.dumps(neutral(identifier)))
    monkeypatch.setattr(instructor_key, "obligations", lambda: [identifier])
    parent = tmp_path / "private-corpus"
    parent.mkdir(mode=0o700)
    return definitions, parent / "new-key"


def test_private_archive_actual_reread_and_no_overwrite(archive_inputs):
    definitions, output = archive_inputs
    result = instructor_key.build_archive(definitions, output)
    assert result["reread_verification"] == {
        "status": "PASS",
        "sources": 1,
        "keys": 1,
        "members": 3,
    }
    assert output.stat().st_mode & 0o777 == 0o700
    for path in output.rglob("*"):
        assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600)
    with pytest.raises(DomainError, match="already exists"):
        instructor_key.build_archive(definitions, output)
    source = next((output / "sources").glob("*.json"))
    source.write_bytes(b"{}")
    with pytest.raises(DomainError, match="digest mismatch"):
        instructor_key.verify_archive(output)


def test_inventory_missing_public_and_symlink_destinations_rejected(archive_inputs, tmp_path):
    definitions, output = archive_inputs
    with pytest.raises(DomainError, match="protected"):
        instructor_key.build_archive(definitions, tmp_path / "public-key")
    alias = tmp_path / "private-corpus" / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(DomainError, match="protected"):
        instructor_key.build_archive(definitions, alias / "key")
    next(definitions.glob("*.json")).unlink()
    with pytest.raises(DomainError, match="denominator"):
        instructor_key.build_archive(definitions, output)
    assert not output.exists()


def test_archive_corruption_is_detected(archive_inputs):
    definitions, output = archive_inputs
    instructor_key.build_archive(definitions, output)
    archive = output / "instructor-keys.zip"
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    with pytest.raises(DomainError, match="Archive digest"):
        instructor_key.verify_archive(output)
